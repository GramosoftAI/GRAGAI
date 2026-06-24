"""Audit logging for Agent lifecycle events"""

import logging
from enum import Enum
from datetime import datetime
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Event types for audit logging"""

    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    AGENT_RESTORED = "agent.restored"


class AgentAuditLog:
    """
    Audit logging for Agent lifecycle events.

    These logs are CRITICAL for:
    - Compliance (audit trail of agent modifications)
    - Debugging (understand what happened when)
    - Security (track who did what - user_id is included)
    - Recovery (know which agents were deleted)
    """

    @staticmethod
    async def log_event(
        tenant_id: str,
        user_id: str,
        agent_id: str,
        event_type: AuditEventType,
        details: Optional[dict] = None,
    ) -> None:
        """
        Log an audit event for agent operations.

        CRITICAL: This is async but non-blocking.
        If audit logging fails, it should NOT block the primary operation.
        Log the failure but continue.

        Args:
            tenant_id: Tenant UUID
            user_id: User who performed the action
            agent_id: Agent UUID involved
            event_type: Type of event (created, updated, deleted)
            details: Optional additional context (agent name, changes, etc.)

        Example:
            await AgentAuditLog.log_event(
                tenant_id="123",
                user_id="456",
                agent_id="789",
                event_type=AuditEventType.AGENT_CREATED,
                details={"name": "My Agent", "has_system_prompt": True},
            )
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            details = details or {}

            log_entry = {
                "timestamp": timestamp,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "agent_id": agent_id,
                "event_type": event_type.value,
                "details": details,
            }

            # Log to application logs
            logger.info(
                f" AUDIT: {event_type.value} | Agent: {agent_id} | User: {user_id} | Details: {details}"
            )

            # TODO: Phase 3 - Persist to audit_logs table in PostgreSQL
            # For now, logs go to stdout/application logs only

        except Exception as e:
            # Do NOT block primary operation if auditing fails
            logger.error(f" Failed to log audit event: {e}")
            pass
