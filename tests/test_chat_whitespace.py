import pytest
from unittest.mock import patch
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi.testclient import TestClient

from app.modules.chats.models import ChatSession, ChatMessage
from app.core.security import TokenPayload
from app.main import app

class SessionManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", connect_args={"check_same_thread": False})
        self.session_factory = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            bind=self.engine,
            class_=AsyncSession
        )
        
    async def __aenter__(self):
        self.session = self.session_factory()
        return self.session
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
        await self.engine.dispose()
        import os
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except:
                pass

@pytest.fixture
def db_session():
    import uuid
    db_file = f"test_{uuid.uuid4().hex}.db"
    
    # Create tables synchronously
    sync_engine = create_engine(f"sqlite:///{db_file}")
    ChatSession.__table__.create(bind=sync_engine)
    ChatMessage.__table__.create(bind=sync_engine)
    sync_engine.dispose()
    
    return SessionManager(db_file)


@pytest.mark.asyncio
async def test_route_whitespace_uuid_handling(db_session):
    async with db_session as db:
        tenant_id = uuid.uuid4()
        session_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Insert test session using sqlite directly
        session = ChatSession(
            id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            title="Test Session",
            message_count=0,
            is_active=True,
        )
        db.add(session)
        await db.commit()

        # Create an async context manager mock to override AsyncSessionLocal
        class AsyncContextManagerMock:
            def __init__(self, session):
                self.session = session
            async def __aenter__(self):
                return self.session
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        async_session_mock = lambda: AsyncContextManagerMock(db)

        # Mock access token verification middleware
        mock_payload = TokenPayload(
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            type="access",
            exp=datetime.now(timezone.utc),
            jti="dummy_jti",
        )

        with patch("app.core.middleware.verify_access_token", return_value=mock_payload):
            with patch("app.modules.chats.routes.AsyncSessionLocal", new=async_session_mock):
                client = TestClient(app)

                # Test 1: Get session with trailing/leading spaces in IDs
                # E.g. session_id with space, agent_id with space
                response = client.get(
                    f"/api/v1/chats/ {str(agent_id)} /sessions/ {str(session_id)} ",
                    headers={"Authorization": "Bearer dummy_token"},
                )
                assert response.status_code == 200
                res_data = response.json()
                assert res_data["success"] is True
                assert res_data["data"]["session"]["id"] == str(session_id)

                # Test 2: Get session with invalid/badly formed UUID should return 400 Bad Request
                response = client.get(
                    f"/api/v1/chats/{str(agent_id)}/sessions/invalid-uuid-string",
                    headers={"Authorization": "Bearer dummy_token"},
                )
                assert response.status_code == 400
                assert response.json()["success"] is False
                assert "Invalid parameter format" in response.json()["message"]

                # Test 3: List sessions with whitespace in agent_id
                response = client.get(
                    f"/api/v1/chats/  {str(agent_id)}  /sessions",
                    headers={"Authorization": "Bearer dummy_token"},
                )
                assert response.status_code == 200
                assert response.json()["success"] is True

                # Test 4: Create session with whitespace in agent_id
                response = client.post(
                    f"/api/v1/chats/ {str(agent_id)} /sessions",
                    json={"title": "New Thread"},
                    headers={"Authorization": "Bearer dummy_token"},
                )
                assert response.status_code == 200
                assert response.json()["success"] is True

                # Test 5: Update session title with whitespace in IDs
                response = client.patch(
                    f"/api/v1/chats/ {str(agent_id)} /sessions/ {str(session_id)} ",
                    json={"title": "Updated Title"},
                    headers={"Authorization": "Bearer dummy_token"},
                )
                assert response.status_code == 200
                assert response.json()["success"] is True
                assert response.json()["data"]["title"] == "Updated Title"

                # Test 6: Delete session with whitespace in IDs
                response = client.delete(
                    f"/api/v1/chats/ {str(agent_id)} /sessions/ {str(session_id)} ",
                    headers={"Authorization": "Bearer dummy_token"},
                )
                assert response.status_code == 200
                assert response.json()["success"] is True
