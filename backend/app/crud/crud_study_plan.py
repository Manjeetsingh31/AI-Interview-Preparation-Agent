import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.study_plan import StudyPlan
from backend.app.schemas.study_plan import StudyPlanCreate, StudyPlanUpdate

logger = logging.getLogger(__name__)


class CRUDStudyPlan(CRUDBase[StudyPlan, StudyPlanCreate, StudyPlanUpdate]):
    """CRUD operations for StudyPlan.

    Supports filtering by user, status, and day-ordering.
    """

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[StudyPlan]:
        """Retrieve all study plan entries for a user (ordered by day)."""
        return (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id)
            .order_by(StudyPlan.day.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_status(
        self,
        db: Session,
        *,
        user_id: str,
        status: str,
    ) -> List[StudyPlan]:
        """Filter a user's study plan by completion status."""
        return (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id, StudyPlan.status == status)
            .order_by(StudyPlan.day.asc())
            .all()
        )

    def mark_completed(
        self,
        db: Session,
        *,
        id: str,
    ) -> Optional[StudyPlan]:
        """Convenience method to mark a study plan entry as completed."""
        plan = self.get(db, id=id)
        if plan:
            plan.status = "completed"
            db.add(plan)
            db.commit()
            db.refresh(plan)
            logger.info("Marked study plan id=%s as completed", id)
        return plan

    def get_completion_rate(self, db: Session, *, user_id: str) -> float:
        """Calculate the percentage of completed vs total entries for a user.

        Returns a float between 0.0 and 100.0. Returns 0.0 if no entries exist.
        """
        total = db.query(StudyPlan).filter(StudyPlan.user_id == user_id).count()
        if total == 0:
            return 0.0
        completed = (
            db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id, StudyPlan.status == "completed")
            .count()
        )
        return round((completed / total) * 100, 2)


study_plan = CRUDStudyPlan(StudyPlan)
