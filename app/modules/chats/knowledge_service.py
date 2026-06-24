"""
Chat Knowledge Service - The "Knowledge Flywheel"
Extracts structured triplets from chat conversations and merges them into the Neo4j graph.
"""

import logging
import uuid
from typing import List, Dict, Any
from datetime import datetime

from app.core.triplet_extractor import TripletExtractor, TripletGraphWriter, TripletExtractionResult
from .models import ChatMessage

logger = logging.getLogger(__name__)

class ChatKnowledgeService:
    """
    Orchestrates the "Session  Graph Sync".
    
    This service turns conversations into permanent knowledge.
    It is designed to run in the background after a chat turn is complete.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.extractor = TripletExtractor()
        self.writer = TripletGraphWriter(tenant_id)

    async def sync_turn_to_graph(
        self, 
        session_id: str,
        kb_id: str,
        chunk_id: str,
        user_message: str, 
        assistant_message: str
    ) -> Dict[str, Any]:
        """
        Extract knowledge from a single conversation turn and persist to graph.
        
        Args:
            session_id: The chat session ID
            user_message: The raw text from the user
            assistant_message: The raw text response from the assistant
            
        Returns:
            Dict with extraction stats
        """
        logger.info(f" Syncing chat turn to graph: session={session_id[:8]}")
        
        # 1. Prepare the text for extraction
        # We combine both because the context of the answer often completes the fact
        combined_text = (
            f"User context/question: {user_message}\n"
            f"Assistant fact/answer: {assistant_message}"
        )
        
        try:
            # 2. Extract Triplets
            # We ground the triplet in the most relevant chunk from the RAG response
            result = await self.extractor.extract_from_chunk(
                chunk_id=chunk_id,
                chunk_text=combined_text
            )
            result.kb_id = kb_id  # Ensure the result knows which KB it belongs to
            
            if not result.triplets:
                logger.debug(f" No clear facts extracted from session turn {session_id[:8]}")
                return {"success": True, "triplets_created": 0}

            # 3. Add Session Metadata to Triplets
            # We want to know these came from a conversation
            for triplet in result.triplets:
                # We can't easily modify the dataclass without changing core
                # But TripletGraphWriter takes the extraction results
                pass
            
            # 4. Persist to Graph
            # The TripletGraphWriter handles deduplication and ontology grounding
            persist_result = await self.writer.persist_triplets([result])
            
            logger.info(
                f" Knowledge Flywheel: Extracted {persist_result.get('triplets_created', 0)} "
                f"triplets from session {session_id[:8]}"
            )
            
            return {
                "success": True,
                "session_id": session_id,
                **persist_result
            }

        except Exception as e:
            logger.error(f" Failed to sync chat to graph: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def run_sync_background(
        tenant_id: str,
        session_id: str,
        kb_id: str,
        chunk_id: str,
        user_message: str,
        assistant_message: str
    ):
        """
        Entry point for FastAPI BackgroundTasks.
        Ensures errors don't crash the main thread.
        """
        try:
            service = ChatKnowledgeService(tenant_id)
            await service.sync_turn_to_graph(
                session_id=session_id, 
                kb_id=kb_id, 
                chunk_id=chunk_id,
                user_message=user_message, 
                assistant_message=assistant_message
            )
        except Exception as e:
            logger.error(f"Background Sync Error: {e}")
