"""Repository layer for Agent (PostgreSQL)"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete, func
from typing import Optional, List
import logging
import uuid

from .models import Agent
from ..auth.models import User
from ..tenants.models import Tenant
from ..knowledge_bases.models import KnowledgeBase
from ...core.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AgentRepository(BaseRepository):
    """
    Repository for Agent CRUD operations.

    CRITICAL: All queries include tenant_id filtering (RLS enforcement).
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize agent repository with tenant context.

        Args:
            db: Database session
            tenant_id: Tenant UUID (for RLS filtering)
        """
        super().__init__(db, tenant_id)
        self.model = Agent

    async def create(
        self,
        name: str,
        user_id: str,
        personality: Optional[str] = "Friendly",
        personality_id: Optional[uuid.UUID] = None,
        system_prompt: Optional[str] = None,
        agent_type: str = "platform",
        organization_name: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        website_url: Optional[str] = None,
        fallback_message_enabled: bool = True,
        brand_persona: Optional[str] = None,
    ) -> Agent:
        """
        Create a new agent.

        CRITICAL:
        - tenant_id is ALWAYS set from context
        - Returns agent for immediate Neo4j node creation

        Args:
            name: Agent name
            user_id: User ID (agent owner)
            personality: Optional personality/tone
            system_prompt: Optional system prompt

        Returns:
            Created Agent model instance
        """
        agent = Agent(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            user_id=uuid.UUID(user_id),
            name=name,
            personality=personality,
            personality_id=personality_id,
            system_prompt=system_prompt,
            is_active=True,
            agent_type=agent_type,
            organization_name=organization_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            website_url=website_url,
            fallback_message_enabled=fallback_message_enabled,
            brand_persona=brand_persona,
        )

        self.db.add(agent)
        await self.db.flush()  # Create without commit (let service handle transaction)

        logger.info(
            f" Created agent in PostgreSQL: {agent.id} (tenant: {self.tenant_id})"
        )
        return agent

    async def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """
        Get agent by ID with tenant_id filtering (RLS).

        Args:
            agent_id: Agent UUID

        Returns:
            Agent model or None

        GUARANTEE: Cannot return agent from other tenants (RLS enforced)
        """
        result = await self.db.execute(
            select(Agent).where(
                and_(
                    Agent.id == uuid.UUID(agent_id),
                    Agent.tenant_id == self.tenant_id,
                    Agent.is_active == True,
                )
            )
        )
        agent = result.scalar_one_or_none()

        if agent:
            logger.debug(f"Found agent: {agent_id}")
        else:
            logger.debug(f"Agent not found: {agent_id}")

        return agent

    async def get_by_name_and_user(self, name: str, user_id: str) -> Optional[Agent]:
        """
        Check if an active agent with this name already exists for this user.
        """
        result = await self.db.execute(
            select(Agent).where(
                and_(
                    Agent.tenant_id == self.tenant_id,
                    Agent.user_id == uuid.UUID(user_id),
                    Agent.name == name,
                    Agent.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_agents(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[List[Agent], int]:
        """
        List all agents for tenant with pagination.
        """
        # Get count
        count_result = await self.db.execute(
            select(Agent).where(
                and_(Agent.tenant_id == self.tenant_id, Agent.is_active == True)
            )
        )
        total = len(count_result.all())

        # Get paginated results
        result = await self.db.execute(
            select(Agent)
            .where(and_(Agent.tenant_id == self.tenant_id, Agent.is_active == True))
            .order_by(Agent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        agents = result.scalars().all()

        logger.info(f"Listed {len(agents)} agents for tenant {self.tenant_id}")
        return agents, total

    async def list_agents_enhanced(
        self, search: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> tuple[List[dict], int]:
        """
        List agents with User/Tenant/KB details and smart search.
        
        Searches across:
        - Agent Name
        - Owner (User) Name
        - Tenant Name
        """
        # Base query with joins
        query = (
            select(
                Agent.id.label("agent_id"),
                Agent.name.label("agent_name"),
                Agent.user_id.label("owner_id"),
                User.email.label("owner_name"),
                Agent.tenant_id.label("tenant_id"),
                Tenant.name.label("tenant_name"),
                KnowledgeBase.id.label("kb_id"),
                Agent.is_active.label("is_active"),
                Agent.created_at.label("created_at")
            )
            .join(User, Agent.user_id == User.id)
            .join(Tenant, Agent.tenant_id == Tenant.id)
            .outerjoin(KnowledgeBase, Agent.id == KnowledgeBase.agent_id)
            .where(and_(Agent.tenant_id == self.tenant_id, Agent.is_active == True))
        )

        # Apply search filters if provided
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Agent.name.ilike(search_pattern)) |
                (User.email.ilike(search_pattern)) |
                (Tenant.name.ilike(search_pattern))
            )

        # Get total count for pagination
        count_stmt = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_stmt)).scalar()

        # Apply pagination and sorting
        query = query.order_by(Agent.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        
        # Format as list of dicts for schema validation
        agents = [dict(row._mapping) for row in result]
        
        return agents, total or 0

    async def list_by_user(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[List[Agent], int]:
        """
        List all agents created by a specific user (within tenant).

        Args:
            user_id: User UUID
            limit: Max results
            offset: Pagination offset

        Returns:
            Tuple of (agents, total_count)

        GUARANTEE: Only returns agents for this tenant + user
        """
        # Get count
        count_result = await self.db.execute(
            select(Agent).where(
                and_(
                    Agent.tenant_id == self.tenant_id,
                    Agent.user_id == uuid.UUID(user_id),
                    Agent.is_active == True,
                )
            )
        )
        total = len(count_result.all())

        # Get paginated results
        result = await self.db.execute(
            select(Agent)
            .where(
                and_(
                    Agent.tenant_id == self.tenant_id,
                    Agent.user_id == uuid.UUID(user_id),
                    Agent.is_active == True,
                )
            )
            .order_by(Agent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        agents = result.scalars().all()

        return agents, total

    async def update(self, agent_id: str, **kwargs) -> Optional[Agent]:
        """
        Update agent fields (PATCH).

        CRITICAL:
        - tenant_id filtering prevents cross-tenant updates
        - Only updates fields provided in kwargs

        Args:
            agent_id: Agent UUID
            **kwargs: Fields to update (name, description, system_prompt, is_active)

        Returns:
            Updated Agent or None if not found

        GUARANTEE: Cannot update agent from other tenants (RLS enforced)
        """
        agent = await self.get_by_id(agent_id)
        if not agent:
            logger.warning(f"Cannot update: agent not found: {agent_id}")
            return None

        # Update provided fields
        update_fields = {
            k: v for k, v in kwargs.items() if v is not None and hasattr(agent, k)
        }

        for field, value in update_fields.items():
            setattr(agent, field, value)

        await self.db.flush()

        logger.info(
            f"Updated agent: {agent_id} with fields: {list(update_fields.keys())}"
        )
        return agent

    async def soft_delete(self, agent_id: str) -> bool:
        """
        Soft delete agent (set is_active = False, deleted_at = now()).

        CRITICAL:
        - Does NOT delete from PostgreSQL (keeps history)
        - Marks with deleted_at timestamp (proves when deletion happened)
        - Neo4j deletion handled by service layer (before this)
        - tenant_id filtering prevents cross-tenant deletion

        Args:
            agent_id: Agent UUID

        Returns:
            True if deleted, False if not found

        GUARANTEE: Cannot delete agent from other tenants (RLS enforced)
        """
        from ..knowledge_bases.models import KnowledgeBase
        from sqlalchemy import update
        from datetime import datetime

        agent = await self.get_by_id(agent_id)
        if not agent:
            logger.warning(f"Cannot soft delete: agent not found: {agent_id}")
            return False

        now = datetime.utcnow()
        
        # 1. Soft delete the agent
        agent.is_active = False
        agent.deleted_at = now
        
        # 2. Soft delete all associated knowledge bases
        await self.db.execute(
            update(KnowledgeBase)
            .where(
                and_(
                    KnowledgeBase.agent_id == uuid.UUID(agent_id),
                    KnowledgeBase.tenant_id == self.tenant_id,
                    KnowledgeBase.is_active == True
                )
            )
            .values(is_active=False, deleted_at=now)
        )
        
        await self.db.flush()

        logger.info(f"Soft deleted agent: {agent_id} and its KnowledgeBases (deleted_at={now})")
        return True

    async def hard_delete(self, agent_id: str) -> bool:
        """
        Hard delete agent (actually remove from database).

        CRITICAL:
        - Only use for testing/cleanup
        - Production: use soft_delete()
        - tenant_id filtering prevents cross-tenant deletion

        Args:
            agent_id: Agent UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            delete(Agent).where(
                and_(
                    Agent.id == uuid.UUID(agent_id),
                    Agent.tenant_id == self.tenant_id,
                )
            )
        )

        if result.rowcount > 0:
            logger.info(f"Hard deleted agent: {agent_id}")
            return True
        else:
            logger.warning(f"Cannot hard delete: agent not found: {agent_id}")
            return False
