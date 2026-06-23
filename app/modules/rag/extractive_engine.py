import logging
import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.knowledge_bases.models import DocumentEntity

logger = logging.getLogger(__name__)

class ExtractiveEngine:
    """
    Extractive Intelligence Engine.
    Handles exact value retrieval for strictly structured identifiers.
    Never uses an LLM to generate values; directly fetches from PostgreSQL.
    """
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        
    async def execute_query(self, entity_type: str, kb_ids: List[str]) -> Optional[List[Dict[str, Any]]]:
        """
        Lookup exact entities by type across specified knowledge bases.
        Returns provenance metadata for all matched unique entities.
        """
        kb_uuids = [uuid.UUID(k) for k in kb_ids]
        tenant_uuid = uuid.UUID(self.tenant_id)
        
        query = (
            select(DocumentEntity)
            .where(
                DocumentEntity.tenant_id == tenant_uuid,
                DocumentEntity.document_id.in_(kb_uuids),
                DocumentEntity.entity_type == entity_type.upper()
            )
            .order_by(DocumentEntity.confidence.desc(), DocumentEntity.created_at.desc())
        )
        
        result = await self.db.execute(query)
        entities = result.scalars().all()
        
        if entities:
            # Group by value to deduplicate identical extractions
            unique_entities = {}
            for entity in entities:
                if entity.entity_value not in unique_entities:
                    unique_entities[entity.entity_value] = {
                        "extracted_value": entity.entity_value,
                        "metadata": {
                            "entity_type": entity.entity_type,
                            "page_number": entity.page_number,
                            "source_text": entity.source_text,
                            "confidence": float(entity.confidence) if entity.confidence else 1.0,
                            "entity_status": entity.entity_status,
                            "document_id": str(entity.document_id)
                        }
                    }
            return list(unique_entities.values())
        
        return None
