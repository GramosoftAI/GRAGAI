"""
Excel/CSV Ingestion Service - High-Intelligence Ontological Graph Builder

Enables structured ingestion of Excel and CSV spreadsheets.
Preserves tabular relationships, column constraints, entity associations,
and row context by:
1. Dynamically discovering schema using LLM context mapping.
2. Grounding types against the tenant's active Enterprise Ontology.
3. Creating high-quality semantic row chunks and storing them in pgvector + Neo4j.
4. Spawning fine-grained ontological entity nodes and linking them with typed edges
   (e.g., REPORTS_TO, BELONGS_TO) in Neo4j.
5. Connecting row chunks to entities via MENTIONS for hybrid RAG compatibility.
"""

import io
import re
import json
import uuid
import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.knowledge_bases.models import DocumentChunk
from app.modules.ontology.service import OntologyService
from app.core.neo4j_repository import Neo4jRepository
from app.core.neo4j_retry import retry_neo4j_operation
from app.core.embeddings import EmbeddingGenerator
from app.core.llm.deepinfra_llm import DeepInfraLLMClient

logger = logging.getLogger(__name__)

# LLM Prompt to discover relational spreadsheet mappings dynamically
SCHEMA_DISCOVERY_PROMPT = """You are an expert database schema mapping engine.
Analyze this spreadsheet's sheet name, headers, and sample data. 
Identify how to convert each row of this sheet into a clean Knowledge Graph under an Enterprise Ontology.

Identify:
1. The **Primary Entity Type**: What represents a single row (e.g., EMPLOYEE, SHIPMENT, CUSTOMER, TRANSACTION, INVOICE, VENDOR)?
2. The **Identifier Column**: Which column represents the unique key/ID of this primary entity (e.g., Employee ID, Transaction ID, Invoice Number)? If no clear ID column exists, specify null.
3. The **Attribute Columns**: Which columns directly describe this primary entity as simple properties (e.g., Salary, Amount, Status, Birth Date)?
4. The **Related Entities**: Which columns represent links to OTHER distinct entities (e.g., Department, Manager, Destination Country, Vendor Name)? 
   For each link, identify:
   - The column name.
   - The related entity type (e.g., DEPARTMENT, MANAGER, LOCATION, VENDOR).
   - The semantic **Relationship Type** (predicate) connecting the primary entity to this target (e.g., BELONGS_TO, REPORTS_TO, IMPORTED_FROM, SUPPLIED_BY). Relationship types MUST be standard UPPERCASE with underscores.

ACTIVE ENTERPRISE ONTOLOGY SCHEMAS:
Classes: {classes}
Allowed Rules: {rules}

Use this ontology to ground your types! If an entity type or relationship fits one of the active ontology classes or rules, you MUST use that exact class/relationship. Otherwise, suggest a natural UPPERCASE name.

TEXT SPECIFICATIONS:
Sheet Name: {sheet_name}
Headers: {headers}
Sample Rows (JSON format):
{sample_data}

Return ONLY valid JSON in this exact structure:
{{
    "primary_entity": {{
        "column": "Employee ID",
        "type": "EMPLOYEE"
    }},
    "attributes": {{
        "Employee Name": "name",
        "Salary Grade": "salary_grade",
        "Salary": "salary"
    }},
    "relationships": [
        {{
            "column": "Department",
            "relation": "BELONGS_TO",
            "target_type": "DEPARTMENT"
        }},
        {{
            "column": "Manager",
            "relation": "REPORTS_TO",
            "target_type": "MANAGER"
        }}
    ]
}}

JSON:"""


class ExcelIngestionService:
    """
    Coordinates relational parsing, dynamic schema mapping,
    ontology grounding, and transaction-safe graph writing.
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = str(tenant_id)
        self.neo4j_repo = Neo4jRepository(self.tenant_id)
        self.llm_client = DeepInfraLLMClient()
        self.ontology_service = OntologyService(self.tenant_id)

    async def ingest_file(
        self,
        kb_id: str,
        file_bytes: bytes,
        filename: str,
    ) -> Dict[str, Any]:
        """
        Main entry point for Excel/CSV ingestion.
        Reads worksheets, discovers schema via LLM, and populates both databases.
        """
        logger.info(f" Ingesting structured file '{filename}' for KB {kb_id} under tenant {self.tenant_id}")
        
        # 1. Parse Excel or CSV into sheets dictionary
        sheets_data: Dict[str, pd.DataFrame] = {}
        ext = filename.lower().split(".")[-1]

        try:
            if ext == "csv":
                df = pd.read_csv(io.BytesIO(file_bytes))
                sheets_data["Sheet1"] = df
            elif ext in ["xlsx", "xls"]:
                xl = pd.ExcelFile(io.BytesIO(file_bytes))
                for sheet_name in xl.sheet_names:
                    sheets_data[sheet_name] = xl.parse(sheet_name)
            else:
                raise ValueError(f"Unsupported spreadsheet format: {ext}")
        except Exception as parse_err:
            logger.error(f"Failed parsing spreadsheet file: {parse_err}")
            return {"success": False, "error": f"Failed to parse file: {str(parse_err)}"}

        total_chunks = 0
        total_entities = 0
        total_relationships = 0

        # Fetch Active Ontology to guide LLM mapping
        try:
            ontology = await self.ontology_service.get_ontology()
            ontology_classes = [c["name"] for c in ontology.get("classes", [])]
            ontology_rules = [f"({r['source_class']})-[:{r['relation']}]->({r['target_class']})" for r in ontology.get("rules", [])]
        except Exception as ont_err:
            logger.warning(f"Failed fetching active ontology (non-blocking): {ont_err}")
            ontology_classes = []
            ontology_rules = []

        # Process each sheet individually
        for sheet_name, df in sheets_data.items():
            # Clean dataframe
            df = df.dropna(how="all")  # Drop completely empty rows
            df = df.map(lambda x: str(x).strip() if pd.notnull(x) else None)
            df = df.where(pd.notnull(df), None)  # Replace NaN with None

            if df.empty:
                logger.info(f"Sheet '{sheet_name}' is empty, skipping.")
                continue

            headers = df.columns.tolist()
            sample_rows = df.head(5).to_dict(orient="records")

            # 2. Discover Schema Mapping via LLM
            mapping = await self._discover_schema_mapping(
                sheet_name=sheet_name,
                headers=headers,
                sample_data=sample_rows,
                ontology_classes=ontology_classes,
                ontology_rules=ontology_rules
            )

            if not mapping:
                logger.warning(f"Could not discover schema mapping for sheet '{sheet_name}', falling back to default mapping")
                mapping = self._generate_default_mapping(headers)

            # 3. Ground entity and relationship types against Active Ontology
            grounded_mapping = await self._ground_schema_mapping(mapping)

            # 4. Ingest and write sheet rows
            sheet_stats = await self._ingest_sheet_rows(
                kb_id=kb_id,
                sheet_name=sheet_name,
                df=df,
                mapping=grounded_mapping
            )

            total_chunks += sheet_stats.get("chunks_created", 0)
            total_entities += sheet_stats.get("entities_created", 0)
            total_relationships += sheet_stats.get("relationships_created", 0)

        return {
            "success": True,
            "data": {
                "kb_id": kb_id,
                "chunks_created": total_chunks,
                "entities_created": total_entities,
                "relationships_created": total_relationships
            }
        }

    async def _discover_schema_mapping(
        self,
        sheet_name: str,
        headers: List[str],
        sample_data: List[Dict],
        ontology_classes: List[str],
        ontology_rules: List[str]
    ) -> Optional[Dict]:
        """Call LLM client to parse headers/sample and return mapping config."""
        classes_str = ", ".join(ontology_classes) if ontology_classes else "None loaded"
        rules_str = "\n".join(ontology_rules) if ontology_rules else "None loaded"

        prompt = SCHEMA_DISCOVERY_PROMPT.format(
            sheet_name=sheet_name,
            headers=headers,
            sample_data=json.dumps(sample_data, indent=2),
            classes=classes_str,
            rules=rules_str
        )

        try:
            res_text = await self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a schema discovery JSON engine. Return strictly valid JSON structure only.",
                temperature=0.0,
                max_tokens=1024
            )

            # Extract JSON block
            match = re.search(r"\{.*\}", res_text, re.DOTALL)
            if not match:
                logger.error(f"No JSON found in schema discovery LLM response: {res_text}")
                return None

            mapping = json.loads(match.group(0))
            logger.info(f" Schema mapped successfully for sheet '{sheet_name}': {mapping}")
            return mapping

        except Exception as e:
            logger.error(f"LLM Schema mapping failed: {e}")
            return None

    def _generate_default_mapping(self, headers: List[str]) -> Dict:
        """Fallback heuristics to create a schema mapping if LLM fails."""
        primary_col = headers[0] if headers else "RowIndex"
        return {
            "primary_entity": {
                "column": primary_col,
                "type": "RECORD"
            },
            "attributes": {h: h.lower().replace(" ", "_") for h in headers[1:]},
            "relationships": []
        }

    async def _ground_schema_mapping(self, mapping: Dict) -> Dict:
        """Ground extracted types to the active ontology classes using fuzzy embedding match."""
        grounded = mapping.copy()

        # Ground primary entity type
        raw_primary_type = grounded["primary_entity"]["type"]
        grounded_primary = await self.ontology_service.ground_type(raw_primary_type)
        if grounded_primary:
            logger.info(f"Grounding: Primary entity type '{raw_primary_type}' -> '{grounded_primary}'")
            grounded["primary_entity"]["type"] = grounded_primary
        else:
            grounded["primary_entity"]["type"] = raw_primary_type.upper().strip().replace(" ", "_")

        # Ground related entity types
        for rel in grounded.get("relationships", []):
            raw_tgt_type = rel["target_type"]
            grounded_tgt = await self.ontology_service.ground_type(raw_tgt_type)
            if grounded_tgt:
                logger.info(f"Grounding: Target entity type '{raw_tgt_type}' -> '{grounded_tgt}'")
                rel["target_type"] = grounded_tgt
            else:
                rel["target_type"] = raw_tgt_type.upper().strip().replace(" ", "_")

            # Clean relationship type format
            rel["relation"] = rel["relation"].upper().strip().replace(" ", "_")

        return grounded

    async def _ingest_sheet_rows(
        self,
        kb_id: str,
        sheet_name: str,
        df: pd.DataFrame,
        mapping: Dict
    ) -> Dict[str, int]:
        """Ingests rows of a dataframe, generates embeddings, stages pgvector & populates Neo4j."""
        primary_col = mapping["primary_entity"]["column"]
        primary_type = mapping["primary_entity"]["type"]
        attributes_map = mapping.get("attributes", {})
        relationships_config = mapping.get("relationships", [])

        # Resilience: make sure primary_col exists
        if primary_col not in df.columns:
            logger.warning(f"Primary column '{primary_col}' not found. Selecting first column as key.")
            primary_col = df.columns[0] if len(df.columns) > 0 else None

        chunks_created = 0
        entities_created = set()
        relationships_created = 0

        # Collect rows into list
        rows_list = df.to_dict(orient="records")
        logger.info(f"Processing {len(rows_list)} rows from sheet '{sheet_name}'...")

        chunk_ids = [str(uuid.uuid4()) for _ in range(len(rows_list))]
        semantic_texts = []
        row_attributes_list = []

        # 1. Generate Semantic Descriptions for each row
        for idx, row in enumerate(rows_list):
            primary_val = str(row[primary_col]) if primary_col and row.get(primary_col) else f"row_{idx}"
            
            # Identify name property
            name_val = primary_val
            for col, prop in attributes_map.items():
                if prop == "name" and row.get(col):
                    name_val = str(row[col])

            # Properties representation
            props_desc = []
            row_attrs = {}
            for col, prop in attributes_map.items():
                if row.get(col):
                    val = str(row[col])
                    props_desc.append(f"{col}: '{val}'")
                    row_attrs[prop] = val

            # Relationships representation
            rels_desc = []
            row_rels = []
            for rc in relationships_config:
                col = rc["column"]
                pred = rc["relation"]
                tgt_type = rc["target_type"]
                
                if row.get(col):
                    tgt_val = str(row[col])
                    rels_desc.append(f"linked to target {tgt_type} '{tgt_val}' via relationship {pred}")
                    row_rels.append({
                        "target_val": tgt_val,
                        "target_type": tgt_type,
                        "predicate": pred
                    })

            # Format the descriptive paragraph
            props_str = ", ".join(props_desc) if props_desc else "None"
            rels_str = ", and ".join(rels_desc) if rels_desc else "No direct links"
            
            semantic_text = (
                f"Spreadsheet record in sheet '{sheet_name}': "
                f"{primary_type} '{name_val}' (Identifier: '{primary_val}'). "
                f"Attributes -> {props_str}. "
                f"Relationships -> {rels_str}."
            )
            semantic_texts.append(semantic_text)
            row_attributes_list.append({
                "id_val": primary_val,
                "name": name_val,
                "properties": row_attrs,
                "relationships": row_rels
            })

        # 2. Embed all row descriptions in a single batch
        logger.info(f"Generating embeddings for {len(semantic_texts)} row chunks...")
        embeddings = await EmbeddingGenerator.generate_embeddings_batch(semantic_texts)
        if len(embeddings) != len(semantic_texts):
            raise RuntimeError("Embeddings batch generation failed or size mismatched.")

        # 3. Create PG Chunks
        for idx in range(len(rows_list)):
            pg_chunk = DocumentChunk(
                id=uuid.UUID(chunk_ids[idx]),
                tenant_id=uuid.UUID(self.tenant_id),
                kb_id=uuid.UUID(kb_id),
                text=semantic_texts[idx],
                chunk_index=idx,
                embedding=embeddings[idx]
            )
            self.db.add(pg_chunk)
        chunks_created = len(rows_list)

        # 4. Stage Chunk nodes in Neo4j
        chunk_nodes_data = [{
            "chunk_id": chunk_ids[i],
            "tenant_id": self.tenant_id,
            "kb_id": kb_id,
            "text": semantic_texts[i][:1500],  # Cap chunk text size in Neo4j
            "position": i,
            "embedding": embeddings[i],
            "created_at": datetime.utcnow().isoformat()
        } for i in range(len(rows_list))]

        batch_create_query = """
        WITH $chunks AS chunk_list
        UNWIND chunk_list AS data
        CREATE (c:Chunk {
            id: data.chunk_id, tenant_id: $tenant_id, kb_id: data.kb_id,
            text: data.text, position: data.position,
            embedding: data.embedding, created_at: data.created_at
        })
        WITH c, data
        MATCH (kb:KnowledgeBase {id: data.kb_id, tenant_id: $tenant_id})
        CREATE (kb)-[:HAS_CHUNK]->(c)
        """
        await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(batch_create_query, {"chunks": chunk_nodes_data}))
        logger.info(f" Staged row chunks in PostgreSQL and Neo4j")

        # 5. Populate Ontology Graph: Entities and Typed relationships row-by-row
        for idx, item in enumerate(row_attributes_list):
            chunk_id = chunk_ids[idx]
            id_val = item["id_val"]
            name_val = item["name"]
            properties = item["properties"]
            properties["name"] = name_val  # always preserve the clean name

            # Build primary entity labels securely
            clean_primary_label = re.sub(r"[^a-zA-Z0-9_]", "", primary_type.upper())
            
            # Merge primary entity in Neo4j
            # Node has labels: Entity, and its dynamic type (e.g. EMPLOYEE)
            primary_merge_query = f"""
            MERGE (e:Entity {clean_primary_label.join([':', ''])} {{tenant_id: $tenant_id, text: $id_val, type: $type}})
            ON CREATE SET e.id = randomUUID(), e.created_at = timestamp()
            SET e.properties = $properties
            RETURN e.id as id
            """
            await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(
                primary_merge_query,
                {
                    "tenant_id": self.tenant_id,
                    "id_val": id_val,
                    "type": primary_type,
                    "properties": properties
                }
            ))
            entities_created.add(f"{id_val}|{primary_type}")

            # Link row Chunk node to Primary Entity via MENTIONS
            chunk_link_query = """
            MATCH (c:Chunk {id: $chunk_id, tenant_id: $tenant_id})
            MATCH (e:Entity {tenant_id: $tenant_id, text: $id_val, type: $type})
            MERGE (c)-[:MENTIONS {confidence: 1.0}]->(e)
            """
            await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(
                chunk_link_query,
                {
                    "chunk_id": chunk_id,
                    "tenant_id": self.tenant_id,
                    "id_val": id_val,
                    "type": primary_type
                }
            ))

            # Merge target entities and create relationship links
            for rel in item["relationships"]:
                tgt_val = rel["target_val"]
                tgt_type = rel["target_type"]
                pred = rel["predicate"]

                clean_tgt_label = re.sub(r"[^a-zA-Z0-9_]", "", tgt_type.upper())
                clean_rel_type = re.sub(r"[^a-zA-Z0-9_]", "", pred.upper())

                # Merge target entity
                target_merge_query = f"""
                MERGE (tgt:Entity {clean_tgt_label.join([':', ''])} {{tenant_id: $tenant_id, text: $tgt_val, type: $type}})
                ON CREATE SET tgt.id = randomUUID(), tgt.created_at = timestamp()
                RETURN tgt.id as id
                """
                await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(
                    target_merge_query,
                    {
                        "tenant_id": self.tenant_id,
                        "tgt_val": tgt_val,
                        "type": tgt_type
                    }
                ))
                entities_created.add(f"{tgt_val}|{tgt_type}")

                # Link Chunk node to Target Entity
                target_link_query = """
                MATCH (c:Chunk {id: $chunk_id, tenant_id: $tenant_id})
                MATCH (tgt:Entity {tenant_id: $tenant_id, text: $tgt_val, type: $type})
                MERGE (c)-[:MENTIONS {confidence: 1.0}]->(tgt)
                """
                await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(
                    target_link_query,
                    {
                        "chunk_id": chunk_id,
                        "tenant_id": self.tenant_id,
                        "tgt_val": tgt_val,
                        "type": tgt_type
                    }
                ))

                # Create the fine-grained ontology typed relationship edge
                # E.g., (Employee)-[:REPORTS_TO]->(Manager)
                edge_create_query = f"""
                MATCH (src:Entity {{tenant_id: $tenant_id, text: $src_val, type: $src_type}})
                MATCH (tgt:Entity {{tenant_id: $tenant_id, text: $tgt_val, type: $tgt_type}})
                MERGE (src)-[r:{clean_rel_type} {{tenant_id: $tenant_id}}]->(tgt)
                SET r.chunk_id = $chunk_id
                """
                await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(
                    edge_create_query,
                    {
                        "tenant_id": self.tenant_id,
                        "src_val": id_val,
                        "src_type": primary_type,
                        "tgt_val": tgt_val,
                        "tgt_type": tgt_type,
                        "chunk_id": chunk_id
                    }
                ))
                relationships_created += 1

        # 6. Link adjacent chunks with NEXT to preserve row ordering
        next_pairs = [{"id1": chunk_ids[i], "id2": chunk_ids[i+1]} for i in range(len(chunk_ids)-1)]
        if next_pairs:
            next_link_query = """
            UNWIND $rels AS r
            MATCH (c1:Chunk {id: r.id1, tenant_id: $tenant_id})
            MATCH (c2:Chunk {id: r.id2, tenant_id: $tenant_id})
            CREATE (c1)-[:NEXT]->(c2)
            """
            await retry_neo4j_operation(lambda: self.neo4j_repo.execute_write(next_link_query, {"rels": next_pairs}))

        logger.info(f" Ingested sheet '{sheet_name}': {chunks_created} chunks, {len(entities_created)} entities, {relationships_created} relationships")

        return {
            "chunks_created": chunks_created,
            "entities_created": len(entities_created),
            "relationships_created": relationships_created
        }
