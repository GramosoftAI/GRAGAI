"""
WebSocket RAG routes - Streaming chat interface for GraphRAG
Phase 3: Real-time Conversational Retrieval
"""

import logging
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from .service import RAGService
from ..knowledge_bases.repository import KnowledgeBaseRepository
from ...core.database import AsyncSessionLocal, get_db_with_tenant
from ...core.security import verify_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket RAG"])


@router.websocket("/{agent_id}")
async def rag_websocket(
    websocket: WebSocket,
    agent_id: str,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time RAG chat.
    
    SECURITY:
    1. Authenticates via token in query params (standard for WS)
    2. Enforces tenant isolation from JWT payload
    3. Validates agent ownership in every request
    
    PROTOCOL:
    - Client sends: {"query": "message"}
    - Server sends (metadata): {"type": "metadata", "sources": [...]}
    - Server sends (chunk): "text chunk"
    - Server sends (done): {"type": "done"}
    """
    # 1. ACCEPT CONNECTION IMMEDIATELY (Prevent handshake timeouts)
    await websocket.accept()
    
    # 2. AUTHENTICATION
    payload = await verify_access_token(token)
    if not payload:
        logger.warning(f"WebSocket auth failed for agent {agent_id}")
        await websocket.send_text(json.dumps({"error": "Unauthorized: Invalid or expired token"}))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    tenant_id = payload.tenant_id
    user_id = payload.user_id
    
    logger.info(f"✅ WebSocket connected: Agent={agent_id}, Tenant={tenant_id}")

    # 3. INITIALIZE SERVICE (Once per session for max speed)
    async with get_db_with_tenant(tenant_id) as db:
        rag_service = RAGService(db=db, tenant_id=tenant_id)
        kb_repo = KnowledgeBaseRepository(db, tenant_id)
        
        # AUTO-RESOLVE KBs (Cached for session duration)
        kbs, _ = await kb_repo.list_by_agent(agent_id, limit=10)
        if not kbs:
            await websocket.send_text(json.dumps({"error": "Knowledge Base not found"}))
            await websocket.close()
            return
        
        kb_ids = [str(kb.id) for kb in kbs]
        logger.info(f"🚀 Session ready: Agent={agent_id}, KBs={len(kb_ids)}")

        try:
            while True:
                # 4. WAIT FOR MESSAGE
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    query = msg.get("query")
                except:
                    await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
                    continue

                if not query:
                    continue

                # 5. STREAM RESPONSE (Optimized path)
                async for chunk in rag_service.stream_rag_answer(
                    query=query,
                    agent_id=agent_id,
                    kb_id=kb_ids
                ):
                    await websocket.send_text(chunk)

                # 6. SIGNAL COMPLETION
                await websocket.send_text(json.dumps({"type": "done"}))
        except WebSocketDisconnect:
            logger.info(f"❌ WebSocket disconnected: Agent={agent_id}")
        except Exception as e:
            logger.error(f"❌ WebSocket session error: {e}")
            try:
                await websocket.send_text(json.dumps({"error": "Session interrupted"}))
            except:
                pass
