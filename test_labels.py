import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.modules.connectors.google.auth import GoogleAuthManager, execute_google_request
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.modules.knowledge_bases.models import DatabaseConnection

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(DatabaseConnection).where(DatabaseConnection.db_type=='gmail').limit(1))
        conn = res.scalar_one_or_none()
        
    auth = GoogleAuthManager()
    auth.load_credentials(conn.connection_params)
    async with auth.get_client('gramosoft450@gmail.com') as client:
        res = await execute_google_request(client, 'GET', '/gmail/v1/users/gramosoft450@gmail.com/labels')
        for label in res.get('labels', []):
            if label['name'] in ['STARRED', 'INBOX', 'Starred', 'Inbox']:
                print(f"{label['name']} -> {label['id']}")

asyncio.run(check())
