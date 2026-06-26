import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.resume_analysis import ResumeAnalysis
from backend.app.schemas.resume_analysis import ResumeAnalysisCreate, ResumeAnalysisUpdate

logger = logging.getLogger(__name__)


class CRUDResumeAnalysis(CRUDBase[ResumeAnalysis, ResumeAnalysisCreate, ResumeAnalysisUpdate]):
    """CRUD operations for ResumeAnalysis.

    Adds user-scoped queries (all analyses for a given user).
    """

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ResumeAnalysis]:
        """Retrieve all resume analyses belonging to a specific user."""
        return (
            db.query(ResumeAnalysis)
            .filter(ResumeAnalysis.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_latest_by_user(self, db: Session, *, user_id: str) -> Optional[ResumeAnalysis]:
        """Get the most recent resume analysis for a user."""
        return (
            db.query(ResumeAnalysis)
            .filter(ResumeAnalysis.user_id == user_id)
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )


resume_analysis = CRUDResumeAnalysis(ResumeAnalysis)
