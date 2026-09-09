import logging
from typing import Optional, Dict, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import get_settings, settings
import tempfile
import os
import re
import json
from typing import Optional, Dict, Literal, List
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

def normalize_query_text(text: str) -> str:
    """Normalizes Unicode dashes, curly quotes, diameter symbols, and non-breaking spaces to standard ASCII."""
    if not text:
        return ""
    text = str(text)
    # Replace diameter and Phi symbols (Ø, ø, ⌀, Φ, ϕ) with space
    text = re.sub(r'[\u00d8\u00f8\u2300\u03a6\u03d5\U0001D719\U0001D6F7]', ' ', text)
    # Replace en-dash, em-dash, non-breaking hyphen, figure dash, minus sign with ASCII hyphen
    text = re.sub(r'[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]', '-', text)
    # Replace curly single quotes with standard ASCII single quote
    text = re.sub(r'[\u2018\u2019\u201a\u201b\u2032\u2035]', "'", text)
    # Replace curly double quotes with standard ASCII double quote
    text = re.sub(r'[\u201c\u201d\u201e\u201f\u2033\u2036]', '"', text)
    # Replace non-breaking spaces and zero-width spaces with standard space
    text = re.sub(r'[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000\ufeff\u200b]', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def _clean_sql_query(sql: str) -> str:
    """Ensures FROM dataset is present and cleans up malformed aliases."""
    s = sql.strip().rstrip(';')
    # Fix malformed alias like 'AS difference BETWEEN highest_and_lowest_MRP'
    s = re.sub(r'(?i)\bAS\s+difference\s+BETWEEN\s+\w+', 'AS difference', s)
    # Ensure FROM dataset is present
    if "FROM dataset" not in s and "FROM dataset" not in s.upper():
        if re.search(r'(?i)\bWHERE\b', s):
            s = re.sub(r'(?i)\bWHERE\b', 'FROM dataset WHERE', s, count=1)
        elif re.search(r'(?i)\bORDER\s+BY\b', s):
            s = re.sub(r'(?i)\bORDER\s+BY\b', 'FROM dataset ORDER BY', s, count=1)
        elif re.search(r'(?i)\bGROUP\s+BY\b', s):
            s = re.sub(r'(?i)\bGROUP\s+BY\b', 'FROM dataset GROUP BY', s, count=1)
        elif re.search(r'(?i)\bLIMIT\b', s):
            s = re.sub(r'(?i)\bLIMIT\b', 'FROM dataset LIMIT', s, count=1)
        else:
            s += ' FROM dataset'
    return s + ';'

def build_heuristic_sql(query: str, columns: List[str]) -> str:
    """Builds a deterministic fuzzy SQL query matching identifiers and keywords from the user prompt."""
    norm_query = normalize_query_text(query)
    tokens = re.findall(r'[A-Za-z0-9\-_/]+', norm_query)
    stop_words = {
        "this", "is", "my", "for", "oem", "and", "part", "number", "based", "on", 
        "detail", "details", "give", "me", "the", "exact", "mrp", "product", "name", 
        "what", "how", "much", "find", "show", "get", "tell", "which", "where", "with",
        "please", "can", "you", "item", "items", "dataset", "table", "record", "records"
    }
    val_tokens = [t for t in tokens if t.lower() not in stop_words and len(t) >= 2]
    
    if not val_tokens:
        return "SELECT * FROM dataset LIMIT 10;"
        
    where_clauses = []
    for token in val_tokens:
        token_escaped = token.replace("'", "''")
        col_matches = []
        for col in columns:
            col_str = f'"{col}"'
            col_matches.append(f"CAST({col_str} AS VARCHAR) ILIKE '%{token_escaped}%'")
        if col_matches:
            where_clauses.append(f"({' OR '.join(col_matches)})")
            
    if where_clauses:
        return f"SELECT * FROM dataset WHERE {' AND '.join(where_clauses)} LIMIT 20;"
    return "SELECT * FROM dataset LIMIT 10;"

def parse_json_from_thinking(text: str) -> dict:
    """Strips <think> tags from Qwen/DeepSeek outputs and parses the JSON robustly."""
    raw_text = str(text or "")
    text = raw_text.strip()
    # Remove closed <think>...</think> blocks
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    # Remove unclosed <think>... blocks if truncated
    if '<think>' in text and '</think>' not in text:
        text = re.sub(r'<think>.*', '', text, flags=re.DOTALL).strip()
    
    # Strip markdown code blocks
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE).strip()
    
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]
    else:
        text = ""
        
    if not text:
        logger.warning(f"LLM returned empty or non-JSON text after stripping think tags: {raw_text[:100]}")
        return {"intents": ["row_lookup"], "sql": "SELECT * FROM dataset LIMIT 10;", "explanation": "Retrieved sample records from dataset"}
        
    try:
        cleaned = re.sub(r',\s*}', '}', text)
        cleaned = re.sub(r',\s*\]', ']', cleaned)
        return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"json.loads failed on text, trying yaml.safe_load: {e}")
        try:
            import yaml
            res = yaml.safe_load(text)
            if isinstance(res, dict):
                return res
        except Exception as e_yaml:
            logger.error(f"Both json.loads and yaml.safe_load failed on text: {text} | error: {e_yaml}")
            
        return {"intents": ["row_lookup"], "sql": "SELECT * FROM dataset LIMIT 10;", "explanation": "Retrieved sample records from dataset"}

class IntentClassification(BaseModel):
    """Classifies the user query into one or more execution engines."""
    intents: List[Literal['aggregation', 'row_lookup', 'relationship', 'free_text']] = Field(
        ..., 
        description="aggregation (math/counts), row_lookup (fetching raw rows/pagination), relationship (graph traversal), free_text (vector semantic search)."
    )

class DuckDBSemanticQuery(BaseModel):
    """Structured DuckDB SQL plan for enterprise data querying."""
    sql: str = Field(
        ..., 
        description="Valid read-only DuckDB SELECT SQL query targeting the view named 'dataset'."
    )
    explanation: str = Field(
        ...,
        description="Explanation of what the SQL query does."
    )

class PandasQueryEngine:
    """
    Hybrid Execution Engine for 1M+ rows.
    Implements Intent Routing, Parquet querying, and strict Semantic SQL building.
    """
    def __init__(self, data_path_or_client=None, llm_client=None, all_dataset_paths: Optional[List[str]] = None):
        if isinstance(data_path_or_client, str):
            self.data_path = data_path_or_client
            self.llm_client = llm_client
        else:
            self.data_path = None
            self.llm_client = data_path_or_client
        self.all_dataset_paths = all_dataset_paths or ([self.data_path] if self.data_path else [])
        
        api_key = getattr(settings, "deepinfra_api_key", "")
        base_url = getattr(settings, "deepinfra_api_url", "https://api.deepinfra.com/v1/openai")
        model_name = settings.model_answer
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.0,
            max_tokens=2048,
            extra_body={"enable_thinking": False}
        )
        router_model_name = getattr(settings, "model_intent", model_name)
        self.router_llm = ChatOpenAI(
            model=router_model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.0,
            max_tokens=512,
            extra_body={"enable_thinking": False}
        )

    def _build_union_query(self, paths: List[str], with_row_id: bool = False) -> str:
        """Builds a DuckDB UNION ALL BY NAME query across all provided CSV/Parquet dataset paths."""
        valid_readers = []
        for p in paths:
            if not p or not os.path.exists(p):
                continue
            safe_path = str(p).replace('\\', '/')
            if safe_path.lower().endswith(".parquet"):
                valid_readers.append(f"SELECT * FROM read_parquet('{safe_path}')")
            else:
                valid_readers.append(f"SELECT * FROM read_csv_auto('{safe_path}', sample_size=10000, nullstr='NULL')")
        if not valid_readers:
            return "SELECT 1 WHERE FALSE"
        union_sql = " UNION ALL BY NAME ".join(valid_readers)
        if with_row_id:
            return f"SELECT row_number() OVER () AS row_id, * FROM ({union_sql})"
        return f"SELECT * FROM ({union_sql})"

    def get_schema_columns(self, data_path: Optional[str] = None) -> List[str]:
        """Fast helper to retrieve columns of the active dataset(s) for schema-aware intent routing."""
        target_path = data_path or getattr(self, "data_path", None)
        paths_to_check = [p for p in (self.all_dataset_paths or ([target_path] if target_path else [])) if p and os.path.exists(p)]
        if not paths_to_check:
            return []
        try:
            temp_db_path = os.path.join(tempfile.gettempdir(), f"duckdb_{id(self)}.db")
            engine = create_engine(f"duckdb:///{temp_db_path}")
            with engine.connect() as conn:
                union_sql = self._build_union_query(paths_to_check, with_row_id=False)
                conn.execute(text("DROP VIEW IF EXISTS dataset;"))
                conn.execute(text(f"CREATE VIEW dataset AS {union_sql};"))
                result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'dataset';"))
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.warning(f"Failed fetching schema columns for routing: {e}")
            return []

    async def _synthesize_analytical_response(self, question: str, table_md: str, explanation: str) -> str:
        """Synthesizes an executive natural-language answer from SQL table results for comparative or analytical queries."""
        try:
            synth_prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are an Executive Data Analyst. Given a user's question and the retrieved database result from an enterprise spreadsheet dataset, write a clear, fluent, natural-language executive answer.\n"
                 "CRITICAL RULES:\n"
                 "1. Answer ONLY using the retrieved data. Do not invent or assume information.\n"
                 "2. Answer the user's specific question DIRECTLY in the very first sentence.\n"
                 "3. FOR SENIORITY / TENURE QUESTIONS: Remember that an employee who joined EARLIER in time (earliest year/date, e.g. 2018 vs 2021) or has MORE years of experience is MORE SENIOR.\n"
                 "4. Respond naturally, concisely, and use bolding formatting for key names, figures, dates, and comparisons.\n"
                 "5. Include the formatted Markdown table below your explanation as supporting evidence.\n"
                 "6. FOR FULL DETAILS OR MOVIE/ENTITY QUERIES: Give the complete details of the movie/entity (Title, Release Date, Overview/Plot, Popularity, Vote Average, Genre, etc.) from the table clearly and accurately. If multiple records are returned, summarize the top items clearly and concisely so the response remains focused and does not exceed token length limits.\n"
                 "7. IMPORTANT: Do NOT output any <think> tags or internal reasoning. Output ONLY the final answer directly.\n"
                 "8. DO NOT include the SQL Explanation in your answer. The SQL Explanation is for your internal context only."),
                ("user", "User Question: {question}\n\nRetrieved Database Result Table:\n{table}")
            ])
            from langchain_core.output_parsers import StrOutputParser
            synth_chain = synth_prompt | self.llm | StrOutputParser()
            synthesis = await synth_chain.ainvoke({
                "question": question,
                "table": table_md
            })
            # Strip any <think> tags the LLM may have injected
            synthesis = re.sub(r'<think>.*?</think>', '', synthesis, flags=re.DOTALL).strip()
            if '<think>' in synthesis:
                synthesis = synthesis[:synthesis.index('<think>')].strip()
            if not synthesis:
                return table_md
            return synthesis
        except Exception as e:
            logger.warning(f"Analytical synthesis failed ({e}), returning formatted table.")
            return table_md

    async def _resolve_to_local_path(self, path: str) -> str:
        """
        If path is an S3/HTTP(S) URL, download it to a local temp file and return that path.
        If it's already a local path that exists, return it unchanged.
        This is required because DuckDB can only read local filesystem paths.
        """
        if not path:
            return path
        if path.startswith("http://") or path.startswith("https://"):
            try:
                import httpx, tempfile
                ext = ".csv" if path.lower().endswith(".csv") else ".parquet"
                logger.info(f"Downloading remote CSV to temp file: {path}")
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    resp = await client.get(path)
                    resp.raise_for_status()
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp.write(resp.content)
                tmp.close()
                logger.info(f"Downloaded {len(resp.content)} bytes -> {tmp.name}")
                return tmp.name
            except Exception as e:
                logger.error(f"Failed to download remote CSV from {path}: {e}")
                return path  # Return original - caller will catch os.path.exists failure
        return path

    async def execute_query(self, query: str, data_path: Optional[str] = None) -> Optional[str]:
        query = normalize_query_text(query)
        raw_path = data_path or getattr(self, "data_path", None)
        # Resolve S3/HTTPS URLs to local temp files before DuckDB can read them
        target_path = await self._resolve_to_local_path(raw_path) if raw_path else None
        paths_to_register = [target_path] if (target_path and os.path.exists(target_path)) else [p for p in (self.all_dataset_paths or []) if p and os.path.exists(p)]
        if not paths_to_register:
            logger.error(f"No valid local dataset path found. raw_path={raw_path!r}, resolved={target_path!r}")
            return "Error: No valid spreadsheet datasets found on server."
            
        from langchain_core.output_parsers import StrOutputParser
        # DUCKDB BINDING (CSV or PARQUET)
        logger.info(f"Initializing DuckDB on dataset(s): {target_path} | total_paths: {len(paths_to_register)}")
        engine = None
        temp_db_path = None
        try:
            import asyncio
            import uuid
            temp_db_id = uuid.uuid4().hex
            temp_db_path = os.path.join(tempfile.gettempdir(), f"duckdb_{temp_db_id}.db")
            
            def _setup_db():
                eng = create_engine(f"duckdb:///{temp_db_path}")
                
                with eng.connect() as conn:
                    union_sql = self._build_union_query(paths_to_register, with_row_id=True)
                    conn.execute(text("DROP VIEW IF EXISTS dataset;"))
                    conn.execute(text(f"CREATE VIEW dataset AS {union_sql};"))
                    
                    # Also register individual views (dataset_1, dataset_2, etc.) for backwards compatibility
                    for idx, path_item in enumerate(paths_to_register):
                        safe_path = str(path_item).replace('\\', '/')
                        view_name = f"dataset_{idx+1}"
                        conn.execute(text(f"DROP VIEW IF EXISTS {view_name};"))
                        reader = f"read_parquet('{safe_path}')" if safe_path.lower().endswith(".parquet") else f"read_csv_auto('{safe_path}', sample_size=10000, nullstr='NULL')"
                        conn.execute(text(f"CREATE VIEW {view_name} AS SELECT row_number() OVER () AS row_id, * FROM {reader};"))
                    try:
                        conn.commit()
                    except:
                        pass
                        
                    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'dataset';"))
                    cols = [row[0] for row in result.fetchall()]
                return eng, cols
                
            engine, columns = await asyncio.to_thread(_setup_db)

            # 3. GENERATE DUCKDB SQL DIRECTLY
            prompt = ChatPromptTemplate.from_messages([
                ("system", 
                 "You are an enterprise data engine and SQL expert. Convert the user's natural language question into a clean, read-only DuckDB SELECT SQL query on the view named 'dataset'.\n\n"
                 "Available columns in 'dataset':\n{columns}\n\n"
                 "CRITICAL RULES FOR DUCKDB SQL:\n"
                 "1. Table name MUST ALWAYS be 'dataset'.\n"
                 "2. COLUMN NAMES WITH SPACES OR SYMBOLS: You MUST ALWAYS wrap column names containing spaces, punctuation, or special characters in DOUBLE QUOTES (e.g., \"Customer ID\", \"Customer Name\", \"Total Amount\"). NEVER write unquoted multi-word column names like Customer ID.\n"
                 "3. When performing mathematical calculations (SUM, AVG, arithmetic) on string/varchar columns, ALWAYS wrap the column in TRY_CAST(\"col\" AS DOUBLE), e.g., SUM(TRY_CAST(\"exchange_rate\" AS DOUBLE)), AVG(TRY_CAST(\"exchange_rate\" AS DOUBLE)), to prevent type conversion issues.\n"
                 "4. For counting total records, use SELECT COUNT(*) AS total_records FROM dataset;\n"
                 "5. For most frequent items or duplicate checks, use GROUP BY \"col\" ORDER BY COUNT(*) DESC LIMIT N (always quote column names if they contain spaces);\n"
                 "6. For boolean columns (like mb_part), NEVER use '= TRUE' or '= FALSE' directly. ALWAYS compare as uppercase string: UPPER(TRY_CAST(\"col\" AS VARCHAR)) = 'TRUE' or UPPER(TRY_CAST(\"col\" AS VARCHAR)) = 'FALSE' because boolean columns may contain string 'NULL' values.\n"
                 "7. For time differences or durations between two timestamps, NEVER use SQLite julianday(). ALWAYS use DuckDB date_diff('day', TRY_CAST(\"col1\" AS TIMESTAMP), TRY_CAST(\"col2\" AS TIMESTAMP)) or (epoch(TRY_CAST(\"col2\" AS TIMESTAMP)) - epoch(TRY_CAST(\"col1\" AS TIMESTAMP))) / 86400.0.\n"
                 "8. For date comparisons or min/max, handle strings appropriately.\n"
                 "9. Include descriptive column aliases (e.g. AS average_rate, AS total_count).\n"
                 "10. NEVER use INSERT, UPDATE, DELETE, DROP, or ALTER. ONLY read-only SELECT queries.\n"
                 "11. Output ONLY valid JSON matching the schema with 'sql' and 'explanation'.\n"
                 "12. In your 'explanation' string, NEVER use the words 'error', 'errors', 'exception', or 'fail' (use 'issues' or 'problems' instead).\n"
                 "13. For extracting YEAR, MONTH, or date parts from timestamp columns, ALWAYS cast to timestamp first: EXTRACT(YEAR FROM TRY_CAST(\"col\" AS TIMESTAMP)).\n"
                 "14. NO PROXY METRICS: If the user asks for information or columns that DO NOT EXIST in the schema (e.g. 'Age', 'wholesale price', 'CEO'), DO NOT hallucinate or substitute an unrelated column to estimate it (e.g. DO NOT use 'Hire Date' to calculate 'Age'). You MUST generate exactly: SELECT 'Not present in dataset' AS info WHERE FALSE; with explanation stating the information is not present in the dataset.\n"
                 "15. STRING FILTERING & ENTITY MATCHING: When filtering string columns (e.g. employee names, IDs, departments in WHERE clauses), NEVER use exact '=' or 'LOWER(col) = ...' with mismatching case. Instead, ALWAYS use case-insensitive matching using the ILIKE operator (e.g., \"Employee ID\" ILIKE 'EMP1005' or \"Employee Name\" ILIKE '%Matthew%') so that case differences or spacing never cause zero results.\n"
                 "16. COMPARATIVE & SUPERLATIVE QUERIES: When the user asks to compare two or more entities (e.g. 'who has higher salary', 'compare the salary of both', 'who is better', 'who earns more', 'which has better'):\n"
                 "   - If the query mentions 'both', 'all', or does not specify explicit employee names, DO NOT filter with WHERE name = 'both'. Instead, select all rows from dataset and ORDER BY the comparison metric DESC (e.g., SELECT * FROM dataset ORDER BY TRY_CAST(\"Salary\" AS DOUBLE) DESC LIMIT 10;).\n"
                 "   - Select all relevant columns (name, department, salary, hire date, etc.) so the response synthesizer has full structured comparison data.\n"
                 "17. SENIORITY, TENURE & JOINING DATE QUERIES: When the user asks who is the 'senior' ('snior'), 'most senior', 'oldest', or 'who joined first/earliest' among employees:\n"
                 "   - If comparing by JOINING DATE / HIRE DATE / START DATE: A senior employee joined EARLIEST in time. You MUST cast string dates to date/timestamp and order ASCENDING (ORDER BY TRY_CAST(\"Joining Date\" AS DATE) ASC) so the earliest date (earliest year, e.g. 2018 before 2022) is ranked FIRST.\n"
                 "   - If comparing by YEARS OF EXPERIENCE / TENURE / AGE: A senior employee has more years. You MUST order DESCENDING (ORDER BY TRY_CAST(\"Experience\" AS DOUBLE) DESC).\n"
                 "   - If selecting among specific people (e.g. 'between John and Jane'), always use case-insensitive fuzzy matching (LOWER(\"col\") LIKE '%name%') for the WHERE clause. If selecting 'among both', DO NOT filter by the word 'both'.\n"
                 "18. POSITIONAL & CHRONOLOGICAL ROW ORDERING (first, last, top, bottom, latest, oldest):\n"
                 "   - When the user asks for the 'last row(s)', 'last N rows', 'last record(s)', 'last entry', or 'last movie/item in the dataset/excel/table' without a specific date filter, you MUST use ANSI OFFSET from total count: SELECT * FROM dataset OFFSET (SELECT COUNT(*) FROM dataset) - N LIMIT N; (e.g. OFFSET (SELECT COUNT(*) FROM dataset) - 1 LIMIT 1; for the last row). NEVER rely on row_id ordering alone as parallel ingestion can make row_id order non-deterministic.\n"
                 "   - When the user asks for the 'first row(s)', 'first N rows', 'first record(s)', 'first entry', or 'first movie/item in the dataset/excel/table', select directly from top: SELECT * FROM dataset LIMIT N;\n"
                 "   - When the user asks for 'latest', 'newest', or 'most recent' by date/release date, cast date strings to DATE and order DESCENDING: ORDER BY TRY_CAST(\"Release_Date\" AS DATE) DESC LIMIT N;\n"
                 "   - When the user asks for 'oldest' or 'earliest' by date, order ASCENDING: ORDER BY TRY_CAST(\"Release_Date\" AS DATE) ASC LIMIT N;\n"
                 "19. SPECIFIC RECORD DETAILS LOOKUP, STRING APOSTROPHES & LENGTH GUARDS:\n"
                 "   - When asking for 'details', 'full details', or information about a specific movie, person, or title (e.g. 'Ron''s Gone Wrong full details', 'details of King''s Man'), generate a SELECT * FROM dataset WHERE LOWER(\"Title\") LIKE '%ron%gone%wrong%'; (or corresponding name column). NEVER generate a COUNT(*) aggregation query when the user asks for details of a specific item!\n"
                 "   - When a title or search string contains an apostrophe or single quote (''), you MUST escape it by doubling the single quote in SQL (e.g., '%ron''s gone wrong%') OR omit the apostrophe using wildcards (e.g., '%ron%gone%wrong%').\n"
                 "   - When querying general details without an explicit WHERE name/title filter (e.g. 'show me all movies' or general overview), ALWAYS append LIMIT 10 to prevent large result sets from causing token overflow.\n"
                 "20. SPECIFIC PROPERTY & RECORD LOOKUPS:\n"
                 "   - When the user asks for a specific attribute of an entity (e.g. 'What is the ArticleNo for PartNo 7803-9636473A?', 'What is the MRP of Part X?', 'What is the salary of John?'), ALWAYS generate a query that selects all columns (`SELECT * FROM dataset WHERE \"PartNo\" ILIKE '%7803-9636473A%' LIMIT 5;`) or includes both the identifier column and the requested property. NEVER select ONLY the isolated target column without the entity key, because downstream verification models require both to establish grounded truth.\n"
                 "21. DIFFERENCE BETWEEN HIGHEST AND LOWEST / MIN-MAX ARITHMETIC:\n"
                 "   - When calculating the difference between the highest and lowest of a metric (e.g. 'difference between highest and lowest MRP', 'difference between max and min price/salary'):\n"
                 "   - ALWAYS generate: SELECT (MAX(TRY_CAST(\"col\" AS DOUBLE)) - MIN(TRY_CAST(\"col\" AS DOUBLE))) AS difference, MAX(TRY_CAST(\"col\" AS DOUBLE)) AS highest_val, MIN(TRY_CAST(\"col\" AS DOUBLE)) AS lowest_val FROM dataset;\n"
                 "   - If there are multiple candidate price columns (e.g. MRP, New MRP), pick the primary price/MRP column. NEVER write aliases containing SQL keywords like 'AS difference BETWEEN ...'.\n"
                 "22. DIAMETER, MEASUREMENTS & MULTI-KEYWORD ENTITY FILTERING (e.g. Dia, Diameter, Ø180, clutch set):\n"
                 "   - In automotive/engineering datasets, 'Dia' stands for diameter and stores values like 'Ø180', 'Ø430', '180mm'.\n"
                 "   - For highest/lowest diameter (e.g. 'Which product has the highest diameter?'): Extract numeric digits and cast: SELECT * FROM dataset ORDER BY TRY_CAST(regexp_extract(\"Dia\", '[0-9]+') AS DOUBLE) DESC LIMIT 5;\n"
                 "   - For filtering by diameter and product type (e.g. 'List all Ø180 clutch sets'): Separate distinct attributes using AND across candidate columns: WHERE (\"Dia\" ILIKE '%180%' OR \"Description\" ILIKE '%180%') AND (\"Description\" ILIKE '%clutch%' OR \"Ceekay Part No\" ILIKE '%clutch%'). NEVER combine distinct concepts into a single literal string like '%180%clutch%'.\n"
                 "IMPORTANT: DO NOT generate any <think> tags or internal reasoning steps. Output ONLY valid JSON immediately without any thinking."),
                ("user", "{question}")
            ])
            
            from langchain_core.output_parsers import StrOutputParser
            chain = prompt | self.llm | StrOutputParser() | parse_json_from_thinking
            
            try:
                query_plan_dict = await chain.ainvoke({
                    "columns": ", ".join(f'"{c}"' if ' ' in str(c) or not str(c).isalnum() else str(c) for c in columns), 
                    "question": query
                })
            except Exception as plan_err:
                logger.warning(f"LLM SQL generation failed: {plan_err}. Generating heuristic SQL query.")
                query_plan_dict = {
                    "sql": build_heuristic_sql(query, columns),
                    "explanation": "Heuristic match based on query parameters."
                }
            
            # If the LLM defaulted to a generic limit 10 sample query but the user had specific keywords/part numbers, refine it
            raw_sql = str(query_plan_dict.get("sql", "")).strip()
            if raw_sql == "SELECT * FROM dataset LIMIT 10;" or not raw_sql:
                refined_sql = build_heuristic_sql(query, columns)
                if "WHERE" in refined_sql:
                    logger.info(f"Refining default sample query to targeted heuristic SQL: {refined_sql}")
                    query_plan_dict["sql"] = refined_sql
                    query_plan_dict["explanation"] = "Targeted match on query identifiers."

            query_plan = DuckDBSemanticQuery(**query_plan_dict)
            
            sql_query = _clean_sql_query(query_plan.sql)
            
            # 4. DETERMINISTIC COLUMN AUTO-QUOTING (Layer 1 Protection)
            # Automatically wrap multi-word or special column names in double quotes if left unquoted by the LLM
            for col in sorted(columns, key=lambda c: len(str(c)), reverse=True):
                col_str = str(col)
                if ' ' in col_str or not col_str.isalnum():
                    quoted = f'"{col_str}"'
                    if quoted not in sql_query:
                        pattern = r'(?<!["\w])' + re.escape(col_str) + r'(?!["\w])'
                        sql_query = re.sub(pattern, quoted, sql_query)
            
            sql_query = _clean_sql_query(sql_query)
            logger.info(f"Generated DuckDB SQL: {sql_query} | Explanation: {query_plan.explanation}")
            
            # Security check
            forbidden_kw = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "CREATE ", "REPLACE ", "EXEC ", "ATTACH ", "DETACH "]
            if any(kw in sql_query.upper() for kw in forbidden_kw):
                return "Error: Security violation - only read-only SELECT queries are permitted."
            
            # 5. EXECUTE SECURELY (with Layer 2 Self-Healing SQL Repair on Parser/Syntax Errors)
            rows = []
            col_names = []
            
            def _execute_sql(sql_str):
                cleaned_sql = _clean_sql_query(sql_str)
                with engine.connect() as conn:
                    res = conn.execute(text(cleaned_sql))
                    return res.fetchall(), list(res.keys())
                    
            try:
                rows, col_names = await asyncio.to_thread(_execute_sql, sql_query)
            except Exception as e:
                logger.warning(f"Initial SQL execution failed ({sql_query}): {e}. Attempting self-healing repair...")
                try:
                    repair_prompt = ChatPromptTemplate.from_messages([
                        ("system",
                         "You are an enterprise DuckDB SQL expert. Fix the syntax error in the DuckDB SELECT SQL query on table 'dataset'.\n\n"
                         "Available columns in 'dataset':\n{columns}\n\n"
                         "CRITICAL RULES:\n"
                         "1. Return ONLY valid JSON with 'sql' and 'explanation'. No markdown, no <think> tags.\n"
                         "2. ALWAYS enclose column names containing spaces or symbols in DOUBLE QUOTES (e.g. \"Customer ID\").\n"
                         "3. When searching for strings containing apostrophes or single quotes (e.g. 'Ron''s Gone Wrong'), double the single quotes in SQL ('%ron''s gone wrong%') or use wildcards ('%ron%gone%wrong%').\n"
                         "4. NO PROXY METRICS: If the DuckDB Error Message indicates that a column requested by the user does not exist (e.g. 'Referenced column \"Age\" not found'), DO NOT hallucinate or substitute an unrelated column (e.g. DO NOT use 'Hire Date' to estimate 'Age'). You MUST return exactly: SELECT 'not present in dataset' AS info WHERE FALSE;\n"
                         "5. The query MUST be a read-only DuckDB SELECT on table 'dataset'."),
                        ("user",
                         "User Question: {question}\n\nFailed SQL Query:\n{sql}\n\nDuckDB Error Message:\n{error}\n\nProvide the corrected DuckDB SQL query in valid JSON.")
                    ])
                    repair_chain = repair_prompt | self.llm | StrOutputParser() | parse_json_from_thinking
                    repaired_dict = await repair_chain.ainvoke({
                        "columns": ", ".join(f'"{c}"' if ' ' in str(c) or not str(c).isalnum() else str(c) for c in columns),
                        "question": query,
                        "sql": sql_query,
                        "error": str(e)
                    })
                    repaired_plan = DuckDBSemanticQuery(**repaired_dict)
                    sql_query = _clean_sql_query(repaired_plan.sql)
                    logger.info(f"Self-Healed DuckDB SQL: {sql_query} | Explanation: {repaired_plan.explanation}")
                    
                    rows, col_names = await asyncio.to_thread(_execute_sql, sql_query)
                    query_plan = repaired_plan
                except Exception as e_retry:
                    logger.error(f"Self-healing SQL retry failed: {e_retry}", exc_info=True)
                    return f"Error executing SQL ({sql_query}): {str(e)}"
                    
            # Early semantic exit
            if "WHERE FALSE" in sql_query.upper() or "not present in dataset" in query_plan.explanation.lower():
                return f"{query_plan.explanation}\nNo records matched your query."
                    
            if not rows and "WHERE " in sql_query.upper():
                logger.warning(f"Query returned 0 rows with WHERE filter ({sql_query}). Attempting Layer 3 fuzzy string matching retry...")
                try:
                    fuzzy_prompt = ChatPromptTemplate.from_messages([
                        ("system",
                         "You are an enterprise DuckDB SQL expert. The previous SQL query returned 0 rows because the WHERE filter was too strict or queried the wrong column.\n"
                         "CRITICAL RECOVERY RULES:\n"
                         "1. Rewrite the DuckDB SELECT query on table 'dataset' using case-insensitive partial string matching (ILIKE or LOWER(\"col\") LIKE '%val%') so matching rows are found.\n"
                         "2. If searching for multiple keywords (e.g. diameter 180 and clutch set), separate with AND across candidate columns (e.g. (Dia ILIKE '%180%' OR Description ILIKE '%180%') AND Description ILIKE '%clutch%').\n"
                         "3. Omit hyphens, apostrophes, and punctuation by inserting wildcards between alphanumeric tokens (e.g. '%7803%9636473%a%'). Select all columns (`SELECT * FROM dataset ...`).\n\n"
                         "Available columns in 'dataset':\n{columns}\n\n"
                         "Return ONLY valid JSON with 'sql' and 'explanation' without markdown fences."),
                        ("user",
                         "User Question: {question}\nPrevious SQL that returned 0 rows:\n{sql}")
                    ])
                    fuzzy_chain = fuzzy_prompt | self.llm | StrOutputParser() | parse_json_from_thinking
                    fuzzy_dict = await fuzzy_chain.ainvoke({
                        "columns": ", ".join(f'"{c}"' if ' ' in str(c) or not str(c).isalnum() else str(c) for c in columns),
                        "question": query,
                        "sql": sql_query
                    })
                    fuzzy_plan = DuckDBSemanticQuery(**fuzzy_dict)
                    sql_query = _clean_sql_query(fuzzy_plan.sql)
                    logger.info(f"Layer 3 Healed DuckDB SQL: {sql_query} | Explanation: {fuzzy_plan.explanation}")
                    
                    rows, col_names = await asyncio.to_thread(_execute_sql, sql_query)
                    query_plan = fuzzy_plan
                except Exception as fuzzy_err:
                    logger.warning(f"Fuzzy retry failed: {fuzzy_err}")

            if not rows:
                return f"{query_plan.explanation}\nNo records matched your query."
                
            formatted = ""
            # Format clean, enterprise-grade response
            if len(rows) == 1 and len(col_names) == 1:
                val = rows[0][0]
                formatted += f"- **{col_names[0]}**: {val}"
            elif len(rows) == 1:
                parts = []
                for k, v in zip(col_names, rows[0]):
                    if v is not None and str(v).strip() != '' and str(v).lower() != 'null':
                        parts.append(f"- **{k}**: {v}")
                formatted += "\n".join(parts)
            else:
                headers = " | ".join(str(c) for c in col_names)
                sep = " | ".join("---" for _ in col_names)
                formatted += f"| {headers} |\n| {sep} |\n"
                for r in rows[:100]:
                    row_str = " | ".join(str(item) if item is not None else "NULL" for item in r)
                    formatted += f"| {row_str} |\n"
                    
            # 6. UNIVERSAL NATURAL-LANGUAGE SYNTHESIS
            # (Removed redundant synthesis step. The final RAG LLM will read the formatted Markdown table directly, saving 20-60 seconds.)

            # For large result sets (>50 rows): strip <think> and return formatted table
            formatted = re.sub(r'<think>.*?</think>', '', formatted, flags=re.DOTALL).strip()
            if '<think>' in formatted:
                formatted = formatted[:formatted.index('<think>')].strip()
            return formatted
            
        except Exception as e:
            logger.error(f"PandasQueryEngine Execution Failed: {e}", exc_info=True)
            return f"Error during data analysis: {str(e)}"
        finally:
            if engine is not None:
                try:
                    engine.dispose()
                except Exception:
                    pass
            if temp_db_path and os.path.exists(temp_db_path):
                try:
                    os.remove(temp_db_path)
                except Exception:
                    pass
