"""
Analytics Router - API endpoints for conversational intelligence.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import AsyncSessionLocal
from ...core.auth.middleware import get_current_tenant_id
from .schemas import (
    AnalyticsSummaryResponse, 
    AnalyticsSummaryCreate, 
    AnalyticsSummaryUpdate,
    AnalyticsQueryLogResponse,
    AnalyticsQueryLogCreate,
    DashboardMetrics
)
from .repository import AnalyticsRepository
from .service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

# Dependency to get AnalyticsService
async def get_analytics_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    async with AsyncSessionLocal() as db:
        repo = AnalyticsRepository(db, tenant_id)
        service = AnalyticsService(repo)
        yield service
        await db.commit()

# ================= SUMMARY APIs =================

@router.post("", response_model=AnalyticsSummaryResponse)
async def create_analytics_summary(
    data: AnalyticsSummaryCreate,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Create a new analytics summary record."""
    return await service.create_summary(data)

@router.get("", response_model=List[AnalyticsSummaryResponse])
async def list_analytics_summaries(
    skip: int = 0,
    limit: int = 100,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Fetch paginated analytics summaries."""
    return await service.get_all_summaries(skip, limit)

@router.get("/{id}", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    id: UUID,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Fetch a single analytics summary by ID."""
    summary = await service.get_summary(id)
    if not summary:
        raise HTTPException(status_code=404, detail="Analytics summary not found")
    return summary

@router.put("/{id}", response_model=AnalyticsSummaryResponse)
async def update_analytics_summary(
    id: UUID,
    data: AnalyticsSummaryUpdate,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Update an existing analytics summary."""
    summary = await service.update_summary(id, data)
    if not summary:
        raise HTTPException(status_code=404, detail="Analytics summary not found")
    return summary

@router.delete("/{id}")
async def delete_analytics_summary(
    id: UUID,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Soft delete (remove) an analytics summary."""
    success = await service.delete_summary(id)
    if not success:
        raise HTTPException(status_code=404, detail="Analytics summary not found")
    return {"status": "deleted"}

# ================= QUERY LOG APIs =================

@router.post("/query-log", response_model=AnalyticsQueryLogResponse)
async def log_query_analytics(
    data: AnalyticsQueryLogCreate,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Log an individual query's analytics."""
    return await service.log_query(data)

@router.get("/query-log", response_model=List[AnalyticsQueryLogResponse])
async def list_query_logs(
    skip: int = 0,
    limit: int = 100,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Fetch paginated query analytics logs."""
    return await service.repo.get_query_logs(skip, limit)

# ================= ADVANCED ANALYTICS APIs =================

@router.get("/dashboard", response_model=DashboardMetrics)
async def get_analytics_dashboard(
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Get aggregated dashboard metrics for the tenant."""
    return await service.get_dashboard_metrics()

@router.get("/unanswered", response_model=List[AnalyticsQueryLogResponse])
async def get_unanswered_queries(
    service: AnalyticsService = Depends(get_analytics_service)
):
    """Fetch recent queries that were unanswered or failed."""
    return await service.get_unanswered_logs()
