import asyncio
from app.core.database import AsyncSessionLocal, init_db
from app.modules.agents.repository import AgentRepository
from sqlalchemy import select

async def main():
    await init_db()
    
    async with AsyncSessionLocal() as db:
        # Check an existing tenant or get one
        from app.modules.auth.models import Tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        if not tenant:
            print("No tenant found")
            return
            
        print(f"Using tenant: {tenant.id}")
        
        # We also need a user
        from app.modules.auth.models import User
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("No user found")
            return
            
        repo = AgentRepository(db, str(tenant.id))
        agent = await repo.create(
            name="Test Support Agent",
            user_id=str(user.id),
            agent_type="integrated",
            organization_name="Acme Corp",
            contact_phone="123-456-7890",
            contact_email="support@acme.com",
            website_url="https://acme.com",
            fallback_message_enabled=True,
            brand_persona="Helpful and Professional"
        )
        print(f"Created Agent: {agent.name}, Type: {agent.agent_type}, Phone: {agent.contact_phone}")
        
        await repo.hard_delete(str(agent.id))
        print("Deleted test agent")
        
asyncio.run(main())
