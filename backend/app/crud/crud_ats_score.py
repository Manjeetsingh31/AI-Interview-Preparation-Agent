"""CRUD operations for ``AtsScore``.

Extends the generic ``CRUDBase`` with user-scoped queries to retrieve
all ATS scores for a given user or the most recent one.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.ats_score import AtsScore
from backend.app.schemas.ats_score import AtsScoreCreate, AtsScoreUpdate

logger = logging.getLogger(__name__)


class CRUDAtsScore(CRUDBase[AtsScore, AtsScoreCreate, AtsScoreUpdate]):
    """CRUD operations scoped to ``AtsScore``.

    Adds convenience methods for retrieving scores by user, which is
    the most common access pattern in this application.
    """

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AtsScore]:
        """Return all ATS scores belonging to a user, newest first."""
        return (
            db.query(AtsScore)
            .filter(AtsScore.user_id == user_id)
            .order_by(AtsScore.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_latest_by_user(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Optional[AtsScore]:
        """Return the most recent ATS score for a user, or ``None``."""
        return (
            db.query(AtsScore)
            .filter(AtsScore.user_id == user_id)
            .order_by(AtsScore.created_at.desc())
            .first()
        )

    def get_by_resume_analysis(
        self,
        db: Session,
        *,
        resume_analysis_adk_id: str,
    ) -> Optional[AtsScore]:
        """Return the ATS score for a specific resume analysis, or ``None``."""
        return (
            db.query(AtsScore)
            .filter(AtsScore.resume_analysis_adk_id == resume_analysis_adk_id)
            .first()
        )


ats_score_crud = CRUDAtsScore(AtsScore)
