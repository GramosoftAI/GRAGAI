"""REST routes for Chat History & Memory

ENDPOINTS:
    POST   /api/v1/chats/{agent_id}/sessions            - Create new session
    GET    /api/v1/chats/{agent_id}/sessions            - List sessions
    GET    /api/v1/chats/{agent_id}/sessions/{id}       - Get session with messages
    PATCH  /api/v1/chats/{agent_id}/sessions/{id}       - Update session title
    DELETE /api/v1/chats/{agent_id}/sessions/{id}       - Delete session
    POST   /api/v1/chats/{agent_id}/message             - Send message (core)
    POST   /api/v1/chats/messages/feedback              - Save chat message feedback

PATTERN: Follows existing route conventions from agents/routes.py and rag/routes.py
    - Tenant context from middleware (request.state)
    - AsyncSessionLocal() context manager for DB sessions
    - format_success() / format_error() for standardized responses
    - HTTPException for error handling

NON-BREAKING: These are entirely NEW routes. No existing routes are modified.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks

from .schemas import (
    SendMessageRequest,
    CreateSessionRequest,
    UpdateSessionRequest,
    SendMessageResponse,
    SessionResponse,
    SessionDetailResponse,
    MessageResponse,
    ChatMessageFeedbackRequest,
    ChatMessageFeedbackResponse,
)
from .service import ChatService
from .knowledge_service import ChatKnowledgeService
from ...core.database import AsyncSessionLocal
from ...utils.formatters import format_success, format_error, format_paginated

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chats", tags=["Chats"])


# ============================================================================
# REQUEST CONTEXT HELPERS
# ============================================================================


def get_tenant_and_user(request: Request) -> tuple:
    """
    Extract tenant_id and user_id from request context (set by middleware).

    CRITICAL: These are injected by TenantContextMiddleware.
    Never trust values from request body or query params.

    Returns:
        Tuple of (tenant_id, user_id)

    Raises:
        HTTPException if not found in request state
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)

    if not tenant_id or not user_id:
        logger.error("Missing tenant_id or user_id in request state")
        raise HTTPException(status_code=401, detail="Unauthorized")

    return str(tenant_id), str(user_id)


def _format_message_for_list(message) -> dict:
    """Format a ChatMessage model with extra details for list views."""
    metadata = message.message_metadata or {}

    # Extract confidence score if present in metadata
    confidence = metadata.get("confidence")

    # Extract sources/nodes count
    sources = metadata.get("sources")
    nodes = len(sources) if isinstance(sources, list) else None

    msg_dict = {
        "role": message.role,
        "content": message.content,
    }

    if confidence is not None:
        msg_dict["confidence"] = confidence
    if nodes is not None:
        msg_dict["nodes"] = nodes
    if message.created_at:
        msg_dict["timestamp"] = message.created_at.isoformat()

    msg_dict["message_count"] = message.position + 1

    return msg_dict


def _format_session(session) -> dict:
    """Format a ChatSession model into API response dict."""
    formatted = {
        "id": str(session.id),
        "agent_id": str(session.agent_id),
        "title": session.title,
        "message_count": session.message_count,
        "is_active": session.is_active,
        "last_message_at": (
            session.last_message_at.isoformat() if session.last_message_at else None
        ),
        "created_at": (
            session.created_at.isoformat() if session.created_at else None
        ),
    }

    if hasattr(session, "messages"):
        formatted["messages"] = [_format_message_for_list(m) for m in session.messages]

    return formatted


def _format_message(message) -> dict:
    """Format a ChatMessage model into API response dict."""
    formatted = {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "position": message.position,
        "metadata": message.message_metadata,
        "created_at": (
            message.created_at.isoformat() if message.created_at else None
        ),
    }
    if getattr(message, "feedback_type", None) is not None:
        formatted["feedback_type"] = message.feedback_type
    if getattr(message, "feedback_reason", None) is not None:
        formatted["feedback_reason"] = message.feedback_reason
    if getattr(message, "feedback_at", None) is not None:
        formatted["feedback_at"] = message.feedback_at.isoformat()
    if getattr(message, "feedback_score", None) is not None:
        formatted["feedback_score"] = message.feedback_score
    return formatted



# ============================================================================
# SESSION ENDPOINTS
# ============================================================================


@router.post(
    "/{agent_id}/sessions",
    status_code=status.HTTP_200_OK,
    summary="Create a new chat session",
    description="Creates a new conversation session with an agent.",
)
async def create_session(
    request: Request,
    agent_id: str,
    body: CreateSessionRequest,
):
    """
    Create a new chat session for an agent.

    Args:
        agent_id: Agent UUID (path param)
        body: Optional title

    Returns:
        Created session metadata
    """
    tenant_id, user_id = get_tenant_and_user(request)

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db=db, tenant_id=tenant_id)

        try:
            session = await chat_service.create_session(
                agent_id=agent_id.strip(),
                user_id=user_id,
                title=body.title,
            )

            return format_success(_format_session(session))

        except ValueError as e:
            logger.warning(f"Invalid UUID: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parameter format: {str(e)}"
            )
        except Exception as e:
            logger.error(f" Failed to create session: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to create session: {str(e)}"
            )


@router.get(
    "/{agent_id}/sessions",
    summary="List chat sessions",
    description="List all chat sessions for the authenticated user with an agent.",
)
async def list_sessions(
    request: Request,
    agent_id: str,
    limit: int = 50,
    offset: int = 0,
):
    """
    List chat sessions for a user+agent pair, sorted by most recent first.

    Args:
        agent_id: Agent UUID (path param)
        limit: Max results (default 50)
        offset: Pagination offset

    Returns:
        Paginated list of sessions
    """
    tenant_id, user_id = get_tenant_and_user(request)

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db=db, tenant_id=tenant_id)

        try:
            sessions, total = await chat_service.list_sessions(
                agent_id=agent_id.strip(),
                user_id=user_id,
                limit=limit,
                offset=offset,
            )

            formatted = [_format_session(s) for s in sessions]
            return format_paginated(formatted, total, skip=offset, limit=limit)

        except ValueError as e:
            logger.warning(f"Invalid UUID: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parameter format: {str(e)}"
            )
        except Exception as e:
            logger.error(f" Failed to list sessions: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to list sessions: {str(e)}"
            )


@router.get(
    "/{agent_id}/sessions/{session_id}",
    summary="Get session with messages",
    description="Get a chat session with all its messages, ordered chronologically.",
)
async def get_session(
    request: Request,
    agent_id: str,
    session_id: str,
):
    """
    Get a session with all its messages.

    Args:
        agent_id: Agent UUID (path param)
        session_id: Session UUID (path param)

    Returns:
        Session metadata + list of messages
    """
    tenant_id, user_id = get_tenant_and_user(request)

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db=db, tenant_id=tenant_id)

        try:
            clean_session_id = session_id.strip()
            clean_agent_id = agent_id.strip()

            result = await chat_service.get_session_with_messages(clean_session_id)

            if not result:
                raise HTTPException(status_code=404, detail="Session not found")

            session = result["session"]

            # Validate agent ownership
            if str(session.agent_id) != clean_agent_id:
                raise HTTPException(
                    status_code=403,
                    detail="Session does not belong to this agent",
                )

            formatted = {
                "session": _format_session(session),
                "messages": [_format_message(m) for m in result["messages"]],
            }

            return format_success(formatted)

        except HTTPException:
            raise
        except ValueError as e:
            logger.warning(f"Invalid UUID: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parameter format: {str(e)}"
            )
        except Exception as e:
            logger.error(f" Failed to get session: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to get session: {str(e)}"
            )


@router.patch(
    "/{agent_id}/sessions/{session_id}",
    summary="Update session",
    description="Update a chat session's title.",
)
async def update_session(
    request: Request,
    agent_id: str,
    session_id: str,
    body: UpdateSessionRequest,
):
    """
    Update session metadata (currently: title only).

    Args:
        agent_id: Agent UUID (path param)
        session_id: Session UUID (path param)
        body: Fields to update

    Returns:
        Updated session metadata
    """
    tenant_id, user_id = get_tenant_and_user(request)

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db=db, tenant_id=tenant_id)

        try:
            clean_session_id = session_id.strip()
            clean_agent_id = agent_id.strip()

            session = await chat_service.update_session(
                session_id=clean_session_id,
                title=body.title,
            )

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            # Validate agent ownership
            if str(session.agent_id) != clean_agent_id:
                raise HTTPException(
                    status_code=403,
                    detail="Session does not belong to this agent",
                )

            return format_success(_format_session(session))

        except HTTPException:
            raise
        except ValueError as e:
            logger.warning(f"Invalid UUID: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parameter format: {str(e)}"
            )
        except Exception as e:
            logger.error(f" Failed to update session: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to update session: {str(e)}"
            )


@router.delete(
    "/{agent_id}/sessions/{session_id}",
    summary="Delete session",
    description="Soft-delete a chat session and all its messages.",
)
async def delete_session(
    request: Request,
    agent_id: str,
    session_id: str,
):
    """
    Soft-delete a chat session.

    Args:
        agent_id: Agent UUID (path param)
        session_id: Session UUID (path param)

    Returns:
        Success confirmation
    """
    tenant_id, user_id = get_tenant_and_user(request)

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db=db, tenant_id=tenant_id)

        try:
            clean_session_id = session_id.strip()
            clean_agent_id = agent_id.strip()

            # First verify existence and agent ownership
            result = await chat_service.get_session_with_messages(clean_session_id)
            if not result:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = result["session"]
            if str(session.agent_id) != clean_agent_id:
                raise HTTPException(
                    status_code=403,
                    detail="Session does not belong to this agent",
                )

            deleted = await chat_service.delete_session(clean_session_id)

            if not deleted:
                raise HTTPException(status_code=404, detail="Session not found")

            return format_success({"deleted": True, "session_id": clean_session_id})

        except HTTPException:
            raise
        except ValueError as e:
            logger.warning(f"Invalid UUID: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parameter format: {str(e)}"
            )
        except Exception as e:
            logger.error(f" Failed to delete session: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to delete session: {str(e)}"
            )


# ============================================================================
# CORE: SEND MESSAGE
# ============================================================================


@router.post(
    "/{agent_id}/message",
    summary="Send message to agent",
    description=(
        "Send a message to an agent and get a RAG-powered response. "
        "Conversation history is automatically injected as memory context. "
        "If session_id is omitted, a new session is created."
    ),
)
async def send_message(
    request: Request,
    agent_id: str,
    body: SendMessageRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a message to an agent and receive a response.

    FLOW:
    1. Create or retrieve session
    2. Save user message
    3. Load conversation history (memory injection)
    4. Augment query with memory context
    5. Call existing RAG pipeline (UNTOUCHED)
    6. Save assistant response
    7. Return answer + session info

    Args:
        agent_id: Agent UUID (path param)
        body: Message request with text and optional session_id

    Returns:
        Agent response with sources, session ID, and memory metadata
    """
    tenant_id, user_id = get_tenant_and_user(request)
    clean_agent_id = agent_id.strip()
    clean_session_id = body.session_id.strip() if (body.session_id and body.session_id.strip()) else None

    logger.info(
        f" Chat message: agent={clean_agent_id}, "
        f"session={clean_session_id or 'NEW'}, "
        f"msg_len={len(body.message)}"
    )

    # Validate message length
    if not body.message or len(body.message.strip()) < 1:
        raise HTTPException(
            status_code=400, detail="Message cannot be empty"
        )

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db=db, tenant_id=tenant_id)

        try:
            result = await chat_service.send_message(
                agent_id=clean_agent_id,
                user_id=user_id,
                message=body.message.strip(),
                session_id=clean_session_id,
                top_k=body.top_k or 10,
                max_depth=body.max_depth or 2,
            )

            # ============= KNOWLEDGE FLYWHEEL (Sync Session to Graph) =============
            # Triggered in background to avoid latency. Extract facts from this turn.
            if result.get("answer") and result.get("sources"):
                # Use the top source chunk to ground the new knowledge
                top_chunk_id = result["sources"][0]["chunk_id"]
                kb_id = result.get("context", {}).get("kb_id")
                
                if top_chunk_id and kb_id:
                    background_tasks.add_task(
                        ChatKnowledgeService.run_sync_background,
                        tenant_id=tenant_id,
                        session_id=result["session_id"],
                        kb_id=kb_id,
                        chunk_id=top_chunk_id,
                        user_message=body.message.strip(),
                        assistant_message=result["answer"]
                    )

            return format_success(result)

        except ValueError as e:
            logger.warning(f"Invalid UUID: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parameter format: {str(e)}"
            )
        except Exception as e:
            logger.error(f" Chat message failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to process message: {str(e)}"
            )


# ============================================================================
# FEEDBACK ENDPOINT
# ============================================================================


@router.post(
    "/messages/feedback",
    response_model=ChatMessageFeedbackResponse,
    summary="Save message feedback",
    description="Save thumbs_up/thumbs_down feedback and optional reason for an assistant message.",
)
async def save_message_feedback(
    request: Request,
    body: ChatMessageFeedbackRequest,
):
    """
    Save or update thumbs_up/thumbs_down feedback for a chat message.

    Args:
        body: ChatMessageFeedbackRequest (message_id, feedback_type, feedback_reason)

    Returns:
        ChatMessageFeedbackResponse
    """
    tenant_id, user_id = get_tenant_and_user(request)

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db=db, tenant_id=tenant_id)

        try:
            await chat_service.save_message_feedback(
                message_id=str(body.message_id),
                feedback_type=body.feedback_type,
                feedback_reason=body.feedback_reason,
                feedback_score=body.feedback_score,
            )
            return {
                "success": True,
                "message": "Feedback saved successfully"
            }

        except KeyError as e:
            logger.warning(f"Message not found for feedback: {body.message_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        except ValueError as e:
            logger.warning(f"Feedback validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to save message feedback: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save feedback: {str(e)}"
            )
