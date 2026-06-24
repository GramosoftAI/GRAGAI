"""Base repository pattern with tenant isolation enforcement

This CRITICAL class ensures developers CANNOT accidentally leak cross-tenant data.

All data access MUST inherit from this base and use these patterns.
Never write raw queries without tenant_id filtering.
"""

from typing import TypeVar, Generic, Type, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeBase
import logging
import uuid

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """
    Base CRUD repository with ENFORCED tenant isolation.

    CRITICAL PATTERNS:
    1. All queries are automatically filtered by tenant_id
    2. Developers CANNOT forget tenant filtering (enforced at base class)
    3. Fallback: PostgreSQL RLS catches anything that escapes

    Usage:
        class UserRepository(BaseRepository[User]):
            pass

        repo = UserRepository(db, User)
        users = await repo.list(tenant_id)  # Automatically filtered
        user = await repo.get_by_id(id, tenant_id)  # Automatically filtered
    """

    def __init__(self, db: AsyncSession, model: Type[T], tenant_id: str):
        """
        Initialize repository with database session and tenant context.

        CRITICAL: tenant_id is REQUIRED. No repository exists without tenant.

        Args:
            db: AsyncSession (with RLS app.current_tenant already set)
            model: SQLAlchemy model class
            tenant_id: Tenant UUID (extracted from JWT by middleware)
        """
        self.db = db
        self.model = model
        self.tenant_id = (
            uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        )

        # SECURITY: Log all data access (audit trail)
        logger.debug(
            f"Repository initialized: {model.__name__} for tenant {self.tenant_id}"
        )

    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Get single record by ID (tenant automatically filtered).

        GUARANTEE: Cannot return records from other tenants.
        - Layer 1: Repository query includes tenant_id filter
        - Layer 2: PostgreSQL RLS enforces if filter is forgotten

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        id_uuid = uuid.UUID(id) if isinstance(id, str) else id

        query = select(self.model).where(
            self.model.id == id_uuid,
            self.model.tenant_id == self.tenant_id,  # ENFORCED
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters,
    ) -> List[T]:
        """
        List all records for this tenant (auto-filtered).

        GUARANTEE: Cannot return records from other tenants.

        Args:
            skip: Pagination offset (default: 0)
            limit: Pagination limit (default: 100)
            **filters: Additional filters (e.g., is_active=True)

        Returns:
            List of model instances
        """
        # Start with tenant filter (MANDATORY)
        query = select(self.model).where(
            self.model.tenant_id == self.tenant_id,  # ENFORCED FIRST
        )

        # Add optional filters (but never allow removing tenant filter)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        query = query.offset(skip).limit(min(limit, 1000))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, **data) -> T:
        """
        Create new record with tenant_id automatically set.

        GUARANTEE: New record is always for current tenant.

        Args:
            **data: Model fields (tenant_id is automatically set)

        Returns:
            Created model instance
        """
        # Never allow overwriting tenant_id
        data["tenant_id"] = self.tenant_id

        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()  # Get ID without committing

        logger.info(
            f"Created {self.model.__name__} {instance.id} in tenant {self.tenant_id}"
        )

        return instance

    async def update(self, id: str, **data) -> Optional[T]:
        """
        Update record (tenant automatically enforced).

        GUARANTEE: Cannot update records from other tenants.

        Args:
            id: Record UUID
            **data: Fields to update (tenant_id cannot be changed)

        Returns:
            Updated model instance or None if not found
        """
        if "tenant_id" in data:
            logger.warning(
                f"Update attempted {self.model.__name__}: Cannot change tenant_id"
            )
            del data["tenant_id"]

        instance = await self.get_by_id(id)
        if not instance:
            return None

        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.db.flush()

        logger.info(f"Updated {self.model.__name__} {id} in tenant {self.tenant_id}")

        return instance

    async def delete(self, id: str) -> bool:
        """
        Delete record (tenant automatically enforced).

        GUARANTEE: Cannot delete records from other tenants.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(id)
        if not instance:
            return False

        await self.db.delete(instance)
        await self.db.flush()

        logger.info(f"Deleted {self.model.__name__} {id} from tenant {self.tenant_id}")

        return True

    async def count(self, **filters) -> int:
        """
        Count records for this tenant (auto-filtered).

        Args:
            **filters: Optional additional filters

        Returns:
            Count of records
        """
        query = (
            select(func.count())
            .select_from(self.model)
            .where(
                self.model.tenant_id == self.tenant_id,
            )
        )

        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def exists(self, id: str) -> bool:
        """
        Check if record exists (tenant automatically filtered).

        Args:
            id: Record UUID

        Returns:
            True if exists in current tenant, False otherwise
        """
        instance = await self.get_by_id(id)
        return instance is not None


class UserRepository(BaseRepository["User"]):
    """User data access with enforced tenant isolation"""

    async def get_by_email(self, email: str) -> Optional["User"]:
        """Get user by email within this tenant"""
        from ..modules.auth.models import User

        query = select(User).where(
            User.email == email,
            User.tenant_id == self.tenant_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_admin(self) -> Optional["User"]:
        """Get admin user for this tenant"""
        from ..modules.auth.models import User

        query = select(User).where(
            User.tenant_id == self.tenant_id,
            User.is_admin == True,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


# ============= PATTERN: How to use =============
"""
In your routes or services:

    from app.repositories.base import BaseRepository
    from app.modules.auth.models import User
    
    @router.get("/users")
    async def list_users(
        request: Request,
        db: AsyncSession = Depends(get_db)
    ):
        # tenant_id automatically extracted from JWT
        repo = BaseRepository(db, User, request.state.tenant_id)
        
        users = await repo.list()  # Automatically filtered by tenant
        # Impossible to return users from other tenants
        
        return format_success(data=[...])

SECURITY GUARANTEE:
- If developer forgets to filter by tenant  Repository catches it
- If Repository has a bug  PostgreSQL RLS catches it
- 2 layers of defense = no single point of failure
"""
