"""Audit logging for Knowledge Base lifecycle events"""

import logging
from enum import Enum
from datetime import datetime
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class KBauditEventType(str, Enum):
    """Event types for KB audit logging"""

    KB_CREATED = "kb.created"
    KB_UPDATED = "kb.updated"
    KB_DOCUMENT_INGESTED = "kb.document_ingested"
    KB_DELETED = "kb.deleted"


class KBauditLog:
    """
    Audit logging for Knowledge Base lifecycle events.

    These logs are CRITICAL for:
    - Compliance (audit trail of KB operations)
    - Debugging (track document ingestions, failures)
    - Security (know who did what)
    - Recovery (know which KBs were deleted)
    """

    @staticmethod
    async def log_event(
        tenant_id: str,
        user_id: str,
        kb_id: str,
        event_type: KBauditEventType,
        details: Optional[dict] = None,
    ) -> None:
        """
        Log an audit event for KB operations.

        CRITICAL: This is async but non-blocking.
        If audit logging fails, it should NOT block the primary operation.
        Log the failure but continue.

        Args:
            tenant_id: Tenant UUID
            user_id: User who performed the action
            kb_id: KB UUID involved
            event_type: Type of event (created, ingested, deleted)
            details: Optional additional context (KB name, chunks, etc.)

        Example:
            await KBauditLog.log_event(
                tenant_id="123",
                user_id="456",
                kb_id="789",
                event_type=KBauditEventType.KB_CREATED,
                details={"name": "My KB", "agent_id": "..."},
            )
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            details = details or {}

            log_entry = {
                "timestamp": timestamp,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "kb_id": kb_id,
                "event_type": event_type.value,
                "details": details,
            }

            # Log to application logs
            logger.info(
                f" AUDIT: {event_type.value} | KB: {kb_id} | User: {user_id} | Details: {details}"
            )

            # TODO: Phase 4 - Persist to audit_logs table in PostgreSQL
            # For now, logs go to stdout/application logs only

        except Exception as e:
            # Do NOT block primary operation if auditing fails
            logger.error(f" Failed to log KB audit event: {e}")
            pass
