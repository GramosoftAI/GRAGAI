"""
Analytics models for tracking conversational intelligence.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Index,
    Text,
    Enum,
    UUID as SQLAlchemyUUID,
)
from sqlalchemy.sql import func
import uuid
import enum
from ...models.base import Base

class ResponseStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    UNANSWERED = "UNANSWERED"
    CONFIDENCE_FAILURE = "CONFIDENCE_FAILURE"
    ERROR = "ERROR"

class AnalyticsSummary(Base):
    """Aggregated metrics for a session or report."""
    __tablename__ = "analytics_summaries"

    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    session_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        index=True,
        nullable=True,
    )

    total_queries = Column(Integer, default=0, nullable=False)
    answered_queries = Column(Integer, default=0, nullable=False)
    unanswered_queries = Column(Integer, default=0, nullable=False)
    accuracy_score = Column(Float, default=0.0, nullable=False)
    avg_confidence = Column(Float, default=0.0, nullable=False)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_analytics_summaries_tenant_id", "tenant_id"),
        Index("ix_analytics_summaries_session_id", "session_id"),
    )

class AnalyticsQueryLog(Base):
    """Per-query analytics for deep-dive tracking."""
    __tablename__ = "analytics_query_logs"

    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )

    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    session_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        index=True,
        nullable=True,
    )

    query = Column(Text, nullable=False)
    response_status = Column(Enum(ResponseStatus), default=ResponseStatus.SUCCESS, nullable=False)
    confidence_score = Column(Float, default=0.0, nullable=False)
    latency_ms = Column(Float, default=0.0, nullable=False)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_query_logs_tenant_id", "tenant_id"),
        Index("ix_query_logs_session_id", "session_id"),
    )
