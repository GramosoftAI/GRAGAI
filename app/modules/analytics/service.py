"""
Analytics Service - Domain logic and statistical computation.
"""

from typing import List, Optional
from uuid import UUID
from .repository import AnalyticsRepository
from .schemas import (
    AnalyticsSummaryCreate, 
    AnalyticsSummaryUpdate, 
    AnalyticsQueryLogCreate,
    DashboardMetrics
)
from .models import AnalyticsSummary, AnalyticsQueryLog

class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository):
        self.repo = repository

    async def create_summary(self, data: AnalyticsSummaryCreate) -> AnalyticsSummary:
        summary_dict = data.model_dump()
        
        # Recalculate accuracy to ensure integrity
        if summary_dict["total_queries"] > 0:
            summary_dict["accuracy_score"] = (summary_dict["answered_queries"] / summary_dict["total_queries"]) * 100
        else:
            summary_dict["accuracy_score"] = 0.0

        return await self.repo.create_summary(summary_dict)

    async def get_dashboard_metrics(self) -> DashboardMetrics:
        # Aggregated stats
        stats = await self.repo.get_aggregated_metrics()
        
        # Trends
        trends_raw = await self.repo.get_query_trends()
        trend_list = [{"date": t[0], "count": t[1]} for t in trends_raw]
        
        # Calculate accuracy across all
        accuracy = 0.0
        if stats["total_queries"] > 0:
            accuracy = (stats["answered_queries"] / stats["total_queries"]) * 100

        # Dummy distribution for now
        distribution = [
            {"bucket": "0.0-0.2", "count": 0},
            {"bucket": "0.2-0.4", "count": 0},
            {"bucket": "0.4-0.6", "count": 0},
            {"bucket": "0.6-0.8", "count": 0},
            {"bucket": "0.8-1.0", "count": 0},
        ]

        return DashboardMetrics(
            total_queries=stats["total_queries"],
            accuracy_percent=round(accuracy, 2),
            unanswered_count=stats["unanswered_queries"],
            avg_confidence=round(stats["avg_confidence"], 4),
            trend_queries=trend_list,
            confidence_distribution=distribution
        )

    async def log_query(self, data: AnalyticsQueryLogCreate) -> AnalyticsQueryLog:
        return await self.repo.create_query_log(data.model_dump())

    async def get_all_summaries(self, skip: int = 0, limit: int = 100) -> List[AnalyticsSummary]:
        return await self.repo.get_all_summaries(skip, limit)

    async def get_summary(self, summary_id: UUID) -> Optional[AnalyticsSummary]:
        return await self.repo.get_summary_by_id(summary_id)

    async def update_summary(self, summary_id: UUID, data: AnalyticsSummaryUpdate) -> Optional[AnalyticsSummary]:
        return await self.repo.update_summary(summary_id, data.model_dump(exclude_unset=True))

    async def delete_summary(self, summary_id: UUID) -> bool:
        return await self.repo.delete_summary(summary_id)
        
    async def get_unanswered_logs(self) -> List[AnalyticsQueryLog]:
        return await self.repo.get_unanswered_logs()
