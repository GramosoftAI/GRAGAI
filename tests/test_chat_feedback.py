import pytest
from unittest.mock import patch
import uuid
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi.testclient import TestClient

from app.modules.chats.models import ChatSession, ChatMessage
from app.modules.chats.repository import ChatRepository
from app.modules.chats.service import ChatService
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
        if os.path.exists(self.db_file):
            try:
                os.remove(self.db_file)
            except:
                pass

@pytest.fixture
def db_session():
    db_file = f"test_{uuid.uuid4().hex}.db"
    
    # Create tables synchronously
    sync_engine = create_engine(f"sqlite:///{db_file}")
    ChatSession.__table__.create(bind=sync_engine)
    ChatMessage.__table__.create(bind=sync_engine)
    sync_engine.dispose()
    
    return SessionManager(db_file)


@pytest.mark.asyncio
async def test_repository_save_feedback(db_session):
    async with db_session as db:
        tenant_id = uuid.uuid4()
        session_id = uuid.uuid4()
        message_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Create session
        session = ChatSession(
            id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            title="Test Session",
            message_count=1,
            is_active=True,
        )
        db.add(session)

        # Create message
        message = ChatMessage(
            id=message_id,
            session_id=session_id,
            tenant_id=tenant_id,
            role="assistant",
            content="Test reply",
            position=0,
        )
        db.add(message)
        await db.commit()

        repo = ChatRepository(db, str(tenant_id))

        # Test get message
        fetched = await repo.get_message_by_id(str(message_id))
        assert fetched is not None
        assert fetched.id == message_id

        # Test save feedback
        updated = await repo.save_message_feedback(
            message=fetched,
            feedback_type="thumbs_up",
            feedback_reason="Great answer!",
        )
        await db.commit()

        assert updated.feedback_type == "thumbs_up"
        assert updated.feedback_reason == "Great answer!"
        assert updated.feedback_at is not None


@pytest.mark.asyncio
async def test_service_save_feedback(db_session):
    async with db_session as db:
        tenant_id = uuid.uuid4()
        session_id = uuid.uuid4()
        message_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        user_id = uuid.uuid4()

        session = ChatSession(
            id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            title="Test Session",
            message_count=1,
            is_active=True,
        )
        db.add(session)

        message = ChatMessage(
            id=message_id,
            session_id=session_id,
            tenant_id=tenant_id,
            role="assistant",
            content="Test reply",
            position=0,
        )
        db.add(message)
        await db.commit()

        service = ChatService(db, str(tenant_id))

        # Valid thumbs up
        updated = await service.save_message_feedback(
            message_id=str(message_id),
            feedback_type="thumbs_up",
            feedback_reason="Useful",
        )
        assert updated.feedback_type == "thumbs_up"
        assert updated.feedback_reason == "Useful"

        # Invalid type
        with pytest.raises(ValueError) as exc:
            await service.save_message_feedback(
                message_id=str(message_id),
                feedback_type="invalid_type",
            )
        assert "feedback_type must be" in str(exc.value)

        # Missing message
        with pytest.raises(KeyError):
            await service.save_message_feedback(
                message_id=str(uuid.uuid4()),
                feedback_type="thumbs_up",
            )


@pytest.mark.asyncio
async def test_route_save_feedback(db_session):
    async with db_session as db:
        tenant_id = uuid.uuid4()
        session_id = uuid.uuid4()
        message_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Insert test data using sqlite directly
        session = ChatSession(
            id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            title="Test Session",
            message_count=1,
            is_active=True,
        )
        db.add(session)

        message = ChatMessage(
            id=message_id,
            session_id=session_id,
            tenant_id=tenant_id,
            role="assistant",
            content="Test reply",
            position=0,
        )
        db.add(message)
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

                # Successful save
                response = client.post(
                    "/api/v1/chats/messages/feedback",
                    json={
                        "message_id": str(message_id),
                        "feedback_type": "thumbs_up",
                        "feedback_reason": "Correct response",
                        "feedback_score": 5,
                    },
                    headers={"Authorization": "Bearer dummy_token"},
                )
                assert response.status_code == 200
                assert response.json() == {
                    "success": True,
                    "message": "Feedback saved successfully",
                }

                # Validate database update
                db.expire_all()
                result = await db.execute(
                    select(ChatMessage).where(ChatMessage.id == message_id)
                )
                updated_msg = result.scalar_one_or_none()
                assert updated_msg.feedback_type == "thumbs_up"
                assert updated_msg.feedback_reason == "Correct response"
                assert updated_msg.feedback_score == 5
                assert updated_msg.feedback_at is not None

                # Invalid feedback type request validation error
                response = client.post(
                    "/api/v1/chats/messages/feedback",
                    json={
                        "message_id": str(message_id),
                        "feedback_type": "thumbs_up_down",
                    },
                    headers={"Authorization": "Bearer dummy_token"},
                )
                assert response.status_code == 422

                # Missing message 404
                response = client.post(
                    "/api/v1/chats/messages/feedback",
                    json={
                        "message_id": str(uuid.uuid4()),
                        "feedback_type": "thumbs_down",
                    },
                    headers={"Authorization": "Bearer dummy_token"},
                )
                assert response.status_code == 404
