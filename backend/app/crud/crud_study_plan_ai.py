"""CRUD operations for ``StudyPlanAI``.

Extends the generic ``CRUDBase`` with study-plan-specific queries for
history, progress, completion tracking, and analytics.
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.study_plan_ai import StudyPlanAI
from backend.app.schemas.study_plan_ai import (
    StudyPlanAICreate,
    StudyPlanAIUpdate,
)

logger = logging.getLogger(__name__)


class CRUDStudyPlanAI(
    CRUDBase[StudyPlanAI, StudyPlanAICreate, StudyPlanAIUpdate]
):
    """CRUD operations scoped to ``StudyPlanAI``.

    Adds convenience methods for user-scoped queries, progress tracking,
    completion analytics, and search.
    """

    # ------------------------------------------------------------------
    # User-scoped queries
    # ------------------------------------------------------------------

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[StudyPlanAI]:
        """Return all plans for a user, newest first."""
        return (
            db.query(StudyPlanAI)
            .filter(StudyPlanAI.user_id == user_id)
            .order_by(StudyPlanAI.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_by_user(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Optional[StudyPlanAI]:
        """Return the active plan for a user, or None."""
        return (
            db.query(StudyPlanAI)
            .filter(
                StudyPlanAI.user_id == user_id,
                StudyPlanAI.status == "active",
            )
            .order_by(StudyPlanAI.created_at.desc())
            .first()
        )

    def get_latest_by_user(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Optional[StudyPlanAI]:
        """Return the most recently created plan for a user."""
        return (
            db.query(StudyPlanAI)
            .filter(StudyPlanAI.user_id == user_id)
            .order_by(StudyPlanAI.created_at.desc())
            .first()
        )

    def get_by_evaluation(
        self,
        db: Session,
        *,
        evaluation_id: str,
    ) -> Optional[StudyPlanAI]:
        """Return the plan linked to a specific evaluation."""
        return (
            db.query(StudyPlanAI)
            .filter(StudyPlanAI.evaluation_id == evaluation_id)
            .first()
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        db: Session,
        *,
        user_id: str,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[StudyPlanAI]:
        """Search plans by target role for a user."""
        search_pattern = f"%{query}%"
        return (
            db.query(StudyPlanAI)
            .filter(
                StudyPlanAI.user_id == user_id,
                StudyPlanAI.target_role.ilike(search_pattern),
            )
            .order_by(StudyPlanAI.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Progress & Completion
    # ------------------------------------------------------------------

    def update_progress(
        self,
        db: Session,
        *,
        plan_id: str,
        completion_percentage: float,
        status: Optional[str] = None,
    ) -> Optional[StudyPlanAI]:
        """Update completion percentage and optionally status."""
        plan = self.get(db=db, id=plan_id)
        if not plan:
            return None

        plan.completion_percentage = completion_percentage
        if status:
            plan.status = status

        if completion_percentage >= 100.0:
            plan.status = "completed"

        db.add(plan)
        db.commit()
        db.refresh(plan)
        logger.info(
            "Plan %s progress updated to %.1f%% (status=%s)",
            plan_id,
            completion_percentage,
            plan.status,
        )
        return plan

    def get_progress(
        self,
        db: Session,
        *,
        plan_id: str,
    ) -> Optional[dict]:
        """Return detailed progress breakdown for a plan."""
        plan = self.get(db=db, id=plan_id)
        if not plan:
            return None

        daily_tasks = plan.daily_tasks or []
        total_days = plan.study_duration
        days_completed = int(
            (plan.completion_percentage / 100.0) * total_days
        )

        progress_by_week = []
        if plan.weekly_tasks:
            for week in plan.weekly_tasks:
                if isinstance(week, dict):
                    progress_by_week.append(week)

        return {
            "plan_id": plan.id,
            "target_role": plan.target_role,
            "completion_percentage": plan.completion_percentage,
            "status": plan.status,
            "days_completed": min(days_completed, total_days),
            "total_days": total_days,
            "daily_tasks_done": days_completed,
            "daily_tasks_total": len(daily_tasks),
            "progress_by_week": progress_by_week if progress_by_week else None,
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def count_by_user(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> int:
        """Return total plans for a user."""
        return (
            db.query(StudyPlanAI)
            .filter(StudyPlanAI.user_id == user_id)
            .count()
        )

    def average_completion(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> float:
        """Return average completion percentage across all plans."""
        result = (
            db.query(func.avg(StudyPlanAI.completion_percentage))
            .filter(StudyPlanAI.user_id == user_id)
            .scalar()
        )
        return float(result) if result else 0.0

    def plans_by_status(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Dict[str, int]:
        """Return count of plans grouped by status."""
        rows = (
            db.query(
                StudyPlanAI.status,
                func.count(StudyPlanAI.id),
            )
            .filter(StudyPlanAI.user_id == user_id)
            .group_by(StudyPlanAI.status)
            .all()
        )
        return {row[0]: row[1] for row in rows}

    def statistics(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> dict:
        """Return comprehensive statistics for a user's plans."""
        return {
            "total_plans": self.count_by_user(db=db, user_id=user_id),
            "average_completion": self.average_completion(
                db=db, user_id=user_id
            ),
            "plans_by_status": self.plans_by_status(
                db=db, user_id=user_id
            ),
        }

    def dashboard(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> dict:
        """Return dashboard data for a user."""
        active = self.get_active_by_user(db=db, user_id=user_id)
        recent = self.get_by_user(db=db, user_id=user_id, limit=5)
        stats = self.statistics(db=db, user_id=user_id)

        return {
            "active_plan": active,
            "recent_plans": recent,
            **stats,
        }


study_plan_ai_crud = CRUDStudyPlanAI(StudyPlanAI)
