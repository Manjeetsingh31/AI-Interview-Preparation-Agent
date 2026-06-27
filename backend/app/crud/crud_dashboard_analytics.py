"""CRUD operations for ``DashboardAnalytics``.

Extends the generic ``CRUDBase`` with user-scoped lookups and
dashboard-specific queries for history, trends, and reports.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.dashboard_analytics import DashboardAnalytics
from backend.app.schemas.dashboard_analytics import (
    DashboardAnalyticsCreate,
    DashboardAnalyticsUpdate,
)

logger = logging.getLogger(__name__)


class CRUDDashboardAnalytics(
    CRUDBase[DashboardAnalytics, DashboardAnalyticsCreate, DashboardAnalyticsUpdate]
):
    """CRUD operations scoped to ``DashboardAnalytics``.

    Provides user-scoped queries for retrieving dashboard data,
    history snapshots, trends, and periodic reports.
    """

    # ------------------------------------------------------------------
    # User-scoped queries
    # ------------------------------------------------------------------

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Optional[DashboardAnalytics]:
        """Return the dashboard analytics for a user, or None."""
        return (
            db.query(DashboardAnalytics)
            .filter(DashboardAnalytics.user_id == user_id)
            .first()
        )

    def get_or_create(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> DashboardAnalytics:
        """Return existing dashboard or create a new empty one."""
        record = self.get_by_user(db=db, user_id=user_id)
        if record:
            return record
        record = self.create(
            db=db,
            obj_in=DashboardAnalyticsCreate(user_id=user_id),
        )
        logger.info("Created dashboard analytics for user %s", user_id)
        return record

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(
        self,
        db: Session,
        *,
        user_id: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return historical snapshots as a list of dicts.

        Since dashboard analytics is a single-row-per-user table,
        history is approximated by tracking changes via the
        ``updated_at`` timestamp and generating simulated history
        from existing data.
        """
        record = self.get_by_user(db=db, user_id=user_id)
        if not record:
            return []

        return [
            {
                "snapshot_date": record.updated_at.isoformat()
                if record.updated_at
                else record.created_at.isoformat(),
                "overall_readiness_score": record.overall_readiness_score,
                "total_sessions": record.total_sessions,
                "average_evaluation_score": record.average_evaluation_score,
                "improvement_rate": record.improvement_rate,
                "completed_study_tasks": record.completed_study_tasks,
            }
        ]

    # ------------------------------------------------------------------
    # Trends
    # ------------------------------------------------------------------

    def get_trend(
        self,
        db: Session,
        *,
        user_id: str,
        metric: str = "overall_readiness_score",
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return trend data for a specific metric."""
        record = self.get_by_user(db=db, user_id=user_id)
        if not record:
            return []

        trend_data = getattr(record, metric, None)
        if trend_data is None:
            return []

        return [
            {
                "date": record.updated_at.isoformat()
                if record.updated_at
                else record.created_at.isoformat(),
                "metric": metric,
                "value": trend_data,
            }
        ]

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def get_progress(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Optional[dict]:
        """Return progress summary for a user."""
        record = self.get_by_user(db=db, user_id=user_id)
        if not record:
            return None
        return {
            "overall_readiness_score": record.overall_readiness_score,
            "total_sessions": record.total_sessions,
            "completed_study_tasks": record.completed_study_tasks,
            "pending_study_tasks": record.pending_study_tasks,
            "improvement_rate": record.improvement_rate,
            "average_evaluation_score": record.average_evaluation_score,
            "average_interview_score": record.average_interview_score,
            "average_ats_score": record.average_ats_score,
        }

    # ------------------------------------------------------------------
    # Periodic reports
    # ------------------------------------------------------------------

    def _compute_period_range(
        self, period: str
    ) -> Optional[timedelta]:
        """Map period string to timedelta."""
        mapping = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
        }
        return mapping.get(period)

    def get_report(
        self,
        db: Session,
        *,
        user_id: str,
        period: str = "weekly",
    ) -> Optional[dict]:
        """Return a periodic report summarising recent activity."""
        record = self.get_by_user(db=db, user_id=user_id)
        if not record:
            return None

        delta = self._compute_period_range(period)
        if not delta:
            return None

        return {
            "period": period,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_readiness_score": record.overall_readiness_score,
            "total_sessions": record.total_sessions,
            "improvement_rate": record.improvement_rate,
            "completed_study_tasks": record.completed_study_tasks,
            "pending_study_tasks": record.pending_study_tasks,
        }

    # ------------------------------------------------------------------
    # Overall readiness
    # ------------------------------------------------------------------

    def get_readiness(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Optional[dict]:
        """Return readiness score with breakdown."""
        record = self.get_by_user(db=db, user_id=user_id)
        if not record:
            return None

        resume_stats = record.resume_stats or {}
        ats_stats = record.ats_stats or {}
        interview_stats = record.interview_stats or {}
        evaluation_stats = record.evaluation_stats or {}
        study_stats = record.study_stats or {}

        return {
            "overall_readiness_score": record.overall_readiness_score,
            "breakdown": {
                "resume_score": resume_stats.get("readiness_contribution", 0),
                "ats_score": ats_stats.get("readiness_contribution", 0),
                "interview_score": interview_stats.get(
                    "readiness_contribution", 0
                ),
                "evaluation_score": evaluation_stats.get(
                    "readiness_contribution", 0
                ),
                "study_score": study_stats.get("readiness_contribution", 0),
            },
        }


dashboard_analytics_crud = CRUDDashboardAnalytics(DashboardAnalytics)
