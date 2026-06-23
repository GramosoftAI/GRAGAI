import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, BigInteger, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.models.base import Base

class GmailMessage(Base):
    __tablename__ = "gmail_messages"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), index=True, nullable=False)
    message_id = Column(String(255), unique=True, index=True, nullable=False)
    thread_id = Column(String(255), index=True)
    subject = Column(Text)
    sender = Column(String(255), index=True)
    body = Column(Text)
    labels = Column(JSON, default=list)
    received_at = Column(DateTime(timezone=True))
    sync_status = Column(String(50), default="pending", index=True)  # pending, processed, error
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_gmail_user_msg", "user_id", "message_id"),
    )

class GmailSyncState(Base):
    __tablename__ = "gmail_sync_state"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), unique=True, index=True, nullable=False)
    history_id = Column(BigInteger)
    last_sync_time = Column(DateTime(timezone=True), default=datetime.utcnow)
