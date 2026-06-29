import pandas as pd
import json
import logging
import traceback

logger = logging.getLogger(__name__)

class PandasQueryEngine:
    """
    Executes analytical queries directly on CSV datasets using Pandas and LLMs.
    """
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.allowed_builtins = {
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "round": round,
            "len": len,
        }

    async def execute_query(self, query: str, csv_path: str) -> str:
        """
        Reads CSV, generates Pandas code from LLM, and evaluates safely.
        """
        logger.info(f" PandasEngine: Loading CSV from {csv_path}")
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            logger.error(f" Failed to load CSV {csv_path}: {e}")
            return f"Error loading dataset: {e}"

        # Build schema representation
        columns_info = {}
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            columns_info[col] = dtype_str

        schema_json = json.dumps(columns_info, indent=2)

        prompt = f"""You are a Pandas data analyst expert. Write a single python expression that answers the user's question.
You have a DataFrame named `df`.
Here are the columns and their datatypes:
{schema_json}

USER QUESTION: {query}

INSTRUCTIONS:
1. Return ONLY the python expression. No markdown, no explanation.
2. The expression must be evaluable via python's `eval()` function, where `df` is provided in the local namespace.
3. If filtering is needed, use standard pandas syntax, e.g., df[df['genre'].str.contains('Action', na=False, case=False)]
4. If aggregating, make sure it evaluates to a string or a primitive, e.g., str(df['popularity'].max()) or df['vote_average'].mean().
5. If returning multiple rows (like Top 10), convert it to JSON or string so it can be read easily. e.g., df.nlargest(10, 'popularity')[['title', 'popularity']].to_json(orient='records')
6. Do NOT include `print()`. Just the expression itself.
"""

        try:
            code = await self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a Pandas code generator. Return only raw python code.",
                temperature=0.0,
                max_tokens=500
            )
            
            # Clean up the output in case the LLM included markdown
            code = code.strip()
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            code = code.strip()
            
            logger.info(f" PandasEngine: Generated Pandas Expression: {code}")

            # Safe evaluation context
            local_context = {"df": df, "pd": pd}
            
            # Execute
            result = eval(code, {"__builtins__": self.allowed_builtins}, local_context)
            
            # Formatting
            if isinstance(result, pd.Series):
                result_str = result.to_json()
            elif isinstance(result, pd.DataFrame):
                result_str = result.to_json(orient="records")
            else:
                result_str = str(result)
                
            explanation = (
                f"\n\n---\n**Data Analytics Pipeline (Pandas Engine)**\n"
                f"- **CSV Source**: {csv_path.split('/')[-1].split(chr(92))[-1]}\n"
                f"- **Computed Expression**: `{code}`\n"
            )
            
            return result_str + explanation

        except Exception as e:
            logger.error(f" PandasEngine Error: {e}\n{traceback.format_exc()}")
            return f"Error executing analytics query: {str(e)}"
