"""
Pydantic schemas for the Analytics Module.
"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from .models import ResponseStatus

class AnalyticsSummaryBase(BaseModel):
    session_id: Optional[UUID] = None
    total_queries: int = Field(0, ge=0)
    answered_queries: int = Field(0, ge=0)
    unanswered_queries: int = Field(0, ge=0)
    accuracy_score: float = Field(0.0, ge=0.0, le=100.0)
    avg_confidence: float = Field(0.0, ge=0.0, le=1.0)

class AnalyticsSummaryCreate(AnalyticsSummaryBase):
    pass

class AnalyticsSummaryUpdate(BaseModel):
    total_queries: Optional[int] = None
    answered_queries: Optional[int] = None
    unanswered_queries: Optional[int] = None
    accuracy_score: Optional[float] = None
    avg_confidence: Optional[float] = None

class AnalyticsSummaryResponse(AnalyticsSummaryBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class AnalyticsQueryLogBase(BaseModel):
    session_id: Optional[UUID] = None
    query: str
    response_status: ResponseStatus = ResponseStatus.SUCCESS
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    latency_ms: float = Field(0.0, ge=0.0)

class AnalyticsQueryLogCreate(AnalyticsQueryLogBase):
    pass

class AnalyticsQueryLogResponse(AnalyticsQueryLogBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class DashboardMetrics(BaseModel):
    total_queries: int
    accuracy_percent: float
    unanswered_count: int
    avg_confidence: float
    trend_queries: List[dict] # {date: string, count: int}
    confidence_distribution: List[dict] # {bucket: string, count: int}
