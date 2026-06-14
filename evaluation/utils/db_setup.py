import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.models import Tenant, User
from app.modules.agents.models import Agent
from app.core.neo4j_repository import Neo4jRepository
from app.core.neo4j_retry import retry_neo4j_operation
from app.core.security import hash_password
from ..configs.eval_config import TEST_TENANT_ID, TEST_AGENT_ID, TEST_USER_ID
from ..logs.logger import eval_logger

async def ensure_db_setup(db: AsyncSession):
    """Ensures that the evaluation tenant, user, and agent exist in Postgres and Neo4j."""
    eval_logger.info("Initializing database test fixtures...")
    tenant_uuid = uuid.UUID(TEST_TENANT_ID)
    user_uuid = uuid.UUID(TEST_USER_ID)
    agent_uuid = uuid.UUID(TEST_AGENT_ID)

    # 1. Ensure Tenant
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
    tenant = res.scalar_one_or_none()
    if not tenant:
        eval_logger.info(f"Seeding evaluation tenant with ID: {TEST_TENANT_ID}")
        tenant = Tenant(
            id=tenant_uuid,
            name="Evaluation Tenant",
            slug="evaluation-tenant",
            is_active=True
        )
        db.add(tenant)
        await db.commit()
    else:
        eval_logger.info("Evaluation tenant already exists.")

    # 2. Ensure User
    res = await db.execute(select(User).where(User.id == user_uuid))
    user = res.scalar_one_or_none()
    if not user:
        eval_logger.info(f"Seeding evaluation user with ID: {TEST_USER_ID}")
        user = User(
            id=user_uuid,
            tenant_id=tenant_uuid,
            email="evaluator@graphmind.ai",
            first_name="GRAG",
            last_name="Evaluator",
            hashed_password=hash_password("evaluation_password_123"),
            is_active=True,
            is_admin=True
        )
        db.add(user)
        await db.commit()
    else:
        eval_logger.info("Evaluation user already exists.")

    # 3. Ensure Agent
    res = await db.execute(select(Agent).where(Agent.id == agent_uuid))
    agent = res.scalar_one_or_none()
    if not agent:
        eval_logger.info(f"Seeding evaluation agent with ID: {TEST_AGENT_ID}")
        agent = Agent(
            id=agent_uuid,
            tenant_id=tenant_uuid,
            user_id=user_uuid,
            name="Evaluation Agent",
            system_prompt="You are an evaluation assistant.",
            is_active=True
        )
        db.add(agent)
        await db.commit()
    else:
        eval_logger.info("Evaluation agent already exists.")

    # 4. Ensure Neo4j Agent Node
    try:
        neo4j_repo = Neo4jRepository(str(tenant_uuid))
        neo4j_query = """
        MERGE (a:Agent {id: $agent_id, tenant_id: $tenant_id})
        ON CREATE SET a.name = $name, a.created_at = timestamp()
        RETURN a
        """
        await retry_neo4j_operation(
            lambda: neo4j_repo.execute_write(
                neo4j_query,
                {
                    "agent_id": str(agent_uuid),
                    "tenant_id": str(tenant_uuid),
                    "name": "Evaluation Agent"
                }
            )
        )
        eval_logger.info("Evaluation agent node verified in Neo4j.")
    except Exception as e:
        eval_logger.error(f"Failed to verify evaluation agent in Neo4j: {e}")
        raise
