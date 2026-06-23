"""Agent model - stored in PostgreSQL with graph node in Neo4j"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UUID as SQLAlchemyUUID,
)
from sqlalchemy.sql import func
from datetime import datetime
import uuid

# Use the shared Base from models package (ensures proper metadata registration)
from ...models.base import Base


class Agent(Base):
    """
    Agent model - stored in PostgreSQL.

    CRITICAL:
    - Each agent belongs to one tenant
    - Each agent is created by one user
    - Agent also represented as (:Agent) node in Neo4j
    - Deletion cascades to Neo4j (soft-delete via service layer)

    Properties:
    - id: Unique UUID per agent
    - tenant_id: Multi-tenancy scoping (RLS filtered)
    - user_id: Agent owner (created by)
    - name: Human-readable agent name
    - system_prompt: Agent's personality/behavior instruction
    - description: Optional description
    - is_active: For soft-deletion (set to False instead of DELETE)
    """

    __tablename__ = "agents"

    # ============= PRIMARY KEY =============
    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )

    # ============= MULTI-TENANCY =============
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ============= OWNER =============
    user_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ============= AGENT FIELDS =============
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)  # Deprecated in favor of personality
    personality = Column(String(255), nullable=True)  # New field for agent tone
    personality_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("personalities.id", ondelete="SET NULL"),
        nullable=True,
    )
    system_prompt = Column(Text, nullable=True)  # Agent's system instruction

    # ============= INTEGRATED AGENT FIELDS =============
    agent_type = Column(String(50), default="platform", nullable=False) # 'platform' or 'integrated'
    organization_name = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_email = Column(String(255), nullable=True)
    website_url = Column(String(255), nullable=True)
    fallback_message_enabled = Column(Boolean, default=True, nullable=False)
    brand_persona = Column(String(255), nullable=True)

    # ============= STATUS =============
    is_active = Column(Boolean, default=True, nullable=False)

    # ============= SOFT DELETE TRACKING =============
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ============= AUDIT TRACKING =============
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ============= INDEXES =============
    __table_args__ = (
        # RLS enforcement
        Index("ix_agents_tenant_id", "tenant_id"),
        # Find by owner
        Index("ix_agents_user_id", "user_id"),
        # Composite for tenant + user listing
        Index("ix_agents_tenant_user", "tenant_id", "user_id"),
        # Search by name (case-insensitive would require tenant_id + LOWER(name))
        Index("ix_agents_name", "name"),
        # Soft-delete filtering
        Index("ix_agents_is_active", "is_active"),
        # Support: SELECT * FROM agents WHERE tenant_id=X AND name=Y AND is_active=TRUE
        # (idempotency check - ensure no duplicate active agents per tenant)
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name} tenant_id={self.tenant_id}>"
