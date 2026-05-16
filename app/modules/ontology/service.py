"""Ontology service - manages entity and relationship types in the graph"""

import logging
from typing import List, Dict, Optional
from ..graphs.neo4j_repository import Neo4jRepository
from ...core.embeddings import EmbeddingGenerator
from . import schemas

logger = logging.getLogger(__name__)

class OntologyService:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.neo4j_repo = Neo4jRepository(tenant_id)

    async def create_class(self, request: schemas.OntologyClassCreate) -> dict:
        """Create a new grounded entity type (Ontology Class)"""
        name = request.name.upper().strip().replace(" ", "_")
        
        # Generate embedding for fuzzy matching later
        text_to_embed = f"{name}: {request.description or ''}"
        embedding = await EmbeddingGenerator.generate_embedding(text_to_embed)
        
        query = """
        MERGE (c:OntologyClass {tenant_id: $tenant_id, name: $name})
        SET c.description = $description,
            c.embedding = $embedding,
            c.updated_at = timestamp()
        RETURN c.name as name
        """
        
        await self.neo4j_repo.execute_write(query, {
            "tenant_id": self.tenant_id,
            "name": name,
            "description": request.description,
            "embedding": embedding
        })
        
        logger.info(f"✅ Ontology Class created: {name} for tenant {self.tenant_id}")
        return {"success": True, "name": name}

    async def create_relation(self, request: schemas.OntologyRelationCreate) -> dict:
        """Create a new grounded relationship type"""
        name = request.name.upper().strip().replace(" ", "_")
        
        query = """
        MERGE (r:OntologyRelation {tenant_id: $tenant_id, name: $name})
        SET r.description = $description,
            r.updated_at = timestamp()
        RETURN r.name as name
        """
        
        await self.neo4j_repo.execute_write(query, {
            "tenant_id": self.tenant_id,
            "name": name,
            "description": request.description
        })
        
        logger.info(f"✅ Ontology Relation created: {name}")
        return {"success": True, "name": name}

    async def get_ontology(self) -> dict:
        """Fetch the full ontology for a tenant"""
        query = """
        MATCH (c:OntologyClass {tenant_id: $tenant_id})
        WITH collect({name: c.name, description: c.description}) as classes
        MATCH (r:OntologyRelation {tenant_id: $tenant_id})
        WITH classes, collect({name: r.name, description: r.description}) as relations
        RETURN classes, relations
        """
        
        results = await self.neo4j_repo.execute_read(query, {"tenant_id": self.tenant_id})
        if not results:
            return {"classes": [], "relations": []}
            
        return results[0]

    async def ground_type(self, raw_type: str) -> Optional[str]:
        """
        Fuzzy ground a raw extraction type to the nearest ontology class.
        Uses vector similarity.
        """
        raw_type = raw_type.upper().strip().replace(" ", "_")
        
        # 1. Try exact match first
        query_exact = """
        MATCH (c:OntologyClass {tenant_id: $tenant_id, name: $name})
        RETURN c.name as name
        """
        exact = await self.neo4j_repo.execute_read(query_exact, {"tenant_id": self.tenant_id, "name": raw_type})
        if exact:
            return exact[0]["name"]
            
        # 2. Try fuzzy match via embedding
        raw_embedding = await EmbeddingGenerator.generate_embedding(raw_type)
        if not raw_embedding:
            return None
            
        query_fuzzy = """
        MATCH (c:OntologyClass {tenant_id: $tenant_id})
        WHERE c.embedding IS NOT NULL AND size(c.embedding) > 0
        WITH c, vector.similarity.cosine(c.embedding, $embedding) as sim
        WHERE sim > 0.85
        RETURN c.name as name
        ORDER BY sim DESC
        LIMIT 1
        """
        
        fuzzy = await self.neo4j_repo.execute_read(query_fuzzy, {
            "tenant_id": self.tenant_id, 
            "embedding": raw_embedding
        })
        
        if fuzzy:
            return fuzzy[0]["name"]
            
        return None
