import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.feedback import Feedback
from backend.app.schemas.feedback import FeedbackCreate, FeedbackUpdate

logger = logging.getLogger(__name__)


class CRUDFeedback(CRUDBase[Feedback, FeedbackCreate, FeedbackUpdate]):
    """CRUD operations for Feedback.

    Supports filtering by user and computing average scores.
    """

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Feedback]:
        """Retrieve all feedback entries for a user (most recent first)."""
        return (
            db.query(Feedback)
            .filter(Feedback.user_id == user_id)
            .order_by(Feedback.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_average_overall(self, db: Session, *, user_id: str) -> Optional[float]:
        """Calculate the average overall_score across all feedback for a user.

        Returns None if no feedback exists yet.
        """
        from sqlalchemy import func

        result = (
            db.query(func.avg(Feedback.overall_score))
            .filter(Feedback.user_id == user_id, Feedback.overall_score.isnot(None))
            .scalar()
        )
        return float(result) if result is not None else None


feedback = CRUDFeedback(Feedback)
