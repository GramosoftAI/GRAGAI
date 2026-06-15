import json
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.neo4j_repository import Neo4jRepository
from ..configs.eval_config import TEST_TENANT_ID
from ..logs.logger import eval_logger

class GraphAuditor:
    """Audits the quality of the constructed Knowledge Graph against ground truths."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.neo4j_repo = Neo4jRepository(TEST_TENANT_ID)

    async def get_extracted_graph(self, kb_id: str) -> tuple[list[dict], list[dict]]:
        """Queries Neo4j for actual entity nodes and relationship edges created for a KB."""
        # 1. Fetch Standard Entities (from :Entity)
        query_entities = """
        MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})
        -[:HAS_CHUNK]->(c:Chunk {tenant_id: $tenant_id})
        -[:MENTIONS]->(e:Entity {tenant_id: $tenant_id})
        RETURN DISTINCT e.text as text, e.type as type
        """
        entity_records = await self.neo4j_repo.execute_read(query_entities, {"kb_id": kb_id})
        
        # 2. Fetch Triplet Entities (if any Triplet nodes exist)
        query_triplet_entities = """
        MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})
        -[:HAS_CHUNK]->(c:Chunk {tenant_id: $tenant_id})
        -[:HAS_TRIPLET]->(t:Triplet {tenant_id: $tenant_id})
        RETURN DISTINCT t.subject as text, "CONCEPT" as type
        UNION
        MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})
        -[:HAS_CHUNK]->(c:Chunk {tenant_id: $tenant_id})
        -[:HAS_TRIPLET]->(t:Triplet {tenant_id: $tenant_id})
        RETURN DISTINCT t.object as text, "CONCEPT" as type
        """
        try:
            triplet_ent_records = await self.neo4j_repo.execute_read(query_triplet_entities, {"kb_id": kb_id})
        except Exception:
            triplet_ent_records = []

        # Combine unique entities
        entities = []
        seen_ents = set()
        for r in entity_records + triplet_ent_records:
            t_lower = r["text"].strip().lower()
            if t_lower not in seen_ents:
                seen_ents.add(t_lower)
                entities.append({"text": r["text"].strip(), "type": r["type"].strip()})

        # 3. Fetch Relationships (from Triplet nodes or RELATES_TO relationships)
        query_relations = """
        MATCH (kb:KnowledgeBase {id: $kb_id, tenant_id: $tenant_id})
        -[:HAS_CHUNK]->(c:Chunk {tenant_id: $tenant_id})
        -[:HAS_TRIPLET]->(t:Triplet {tenant_id: $tenant_id})
        RETURN DISTINCT t.subject as source, t.predicate as type, t.object as target
        """
        try:
            relation_records = await self.neo4j_repo.execute_read(query_relations, {"kb_id": kb_id})
        except Exception:
            relation_records = []

        relationships = []
        seen_rels = set()
        for r in relation_records:
            rel_key = f"{r['source'].strip().lower()}|{r['type'].strip().lower()}|{r['target'].strip().lower()}"
            if rel_key not in seen_rels:
                seen_rels.add(rel_key)
                relationships.append({
                    "source": r["source"].strip(),
                    "type": r["type"].strip(),
                    "target": r["target"].strip()
                })

        return entities, relationships

    def _calculate_metrics(self, actual: list, expected: list, key_fn) -> tuple[float, float, float]:
        """Generic calculator for Precision, Recall, and F1 score."""
        if not expected:
            return 0.0, 0.0, 0.0
        if not actual:
            return 0.0, 0.0, 0.0

        actual_set = {key_fn(x) for x in actual}
        expected_set = {key_fn(x) for x in expected}

        tp = len(actual_set.intersection(expected_set))
        fp = len(actual_set - expected_set)
        fn = len(expected_set - actual_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return precision, recall, f1

    async def audit_graph(self, kb_id: str, file_info: dict) -> dict:
        """Compares extracted graph nodes/edges against ground truth files."""
        document = file_info["file_name"]
        eval_logger.info(f"Auditing Graph Construction for {document}...")

        # 1. Load Ground Truth
        expected_entities = []
        expected_relations = []

        ent_gt_path = file_info["entities_gt_path"]
        rel_gt_path = file_info["relationships_gt_path"]

        if ent_gt_path and Path(ent_gt_path).exists():
            with open(ent_gt_path, "r", encoding="utf-8") as f:
                expected_entities = json.load(f)
        
        if rel_gt_path and Path(rel_gt_path).exists():
            with open(rel_gt_path, "r", encoding="utf-8") as f:
                expected_relations = json.load(f)

        # 2. Get Actual Extracted Graph
        extracted_entities, extracted_relations = await self.get_extracted_graph(kb_id)

        # 3. Calculate Entity Metrics (Normalize and match case-insensitive text)
        def ent_key(e):
            return e["text"].strip().lower()

        p_ent, r_ent, f1_ent = self._calculate_metrics(
            extracted_entities, expected_entities, ent_key
        )

        # 4. Calculate Relationship Metrics
        def rel_key(r):
            # Normalize: source, target and connection type
            src = r["source"].strip().lower()
            tgt = r["target"].strip().lower()
            rel_type = r["type"].strip().lower().replace(" ", "_")
            return f"{src}|{rel_type}|{tgt}"

        p_rel, r_rel, f1_rel = self._calculate_metrics(
            extracted_relations, expected_relations, rel_key
        )

        eval_logger.info(
            f"Graph Audit: {document}\n"
            f"  Entities: Exp={len(expected_entities)}, Ext={len(extracted_entities)}, F1={f1_ent:.2f}\n"
            f"  Relations: Exp={len(expected_relations)}, Ext={len(extracted_relations)}, F1={f1_rel:.2f}"
        )

        return {
            "document": document,
            "expected_entities": len(expected_entities),
            "extracted_entities": len(extracted_entities),
            "entity_precision": p_ent,
            "entity_recall": r_ent,
            "entity_f1": f1_ent,
            "expected_relations": len(expected_relations),
            "extracted_relations": len(extracted_relations),
            "relation_precision": p_rel,
            "relation_recall": r_rel,
            "relation_f1": f1_rel
        }
