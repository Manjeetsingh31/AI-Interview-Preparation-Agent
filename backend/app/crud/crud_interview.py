import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.interview_history import InterviewHistory
from backend.app.schemas.interview_history import InterviewHistoryCreate, InterviewHistoryUpdate

logger = logging.getLogger(__name__)


class CRUDInterviewHistory(CRUDBase[InterviewHistory, InterviewHistoryCreate, InterviewHistoryUpdate]):
    """CRUD operations for InterviewHistory.

    Supports filtering by user, interview type, and date range.
    """

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[InterviewHistory]:
        """Retrieve all interview turns for a user (most recent first)."""
        return (
            db.query(InterviewHistory)
            .filter(InterviewHistory.user_id == user_id)
            .order_by(InterviewHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_type(
        self,
        db: Session,
        *,
        user_id: str,
        interview_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[InterviewHistory]:
        """Filter a user's history by interview type."""
        return (
            db.query(InterviewHistory)
            .filter(
                InterviewHistory.user_id == user_id,
                InterviewHistory.interview_type == interview_type,
            )
            .order_by(InterviewHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_scored(self, db: Session, *, user_id: str, min_score: int = 0) -> List[InterviewHistory]:
        """Retrieve interview turns that have been scored (for analytics)."""
        return (
            db.query(InterviewHistory)
            .filter(
                InterviewHistory.user_id == user_id,
                InterviewHistory.score.isnot(None),
                InterviewHistory.score >= min_score,
            )
            .order_by(InterviewHistory.created_at.desc())
            .all()
        )


interview_history = CRUDInterviewHistory(InterviewHistory)
