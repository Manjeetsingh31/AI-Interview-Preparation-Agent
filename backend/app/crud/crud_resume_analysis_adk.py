"""CRUD operations for ``ResumeAnalysisADK``.

Extends the generic ``CRUDBase`` with user-scoped queries to retrieve
all analyses for a given user or the most recent one.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.resume_analysis_adk import ResumeAnalysisADK
from backend.app.schemas.resume_analysis_adk import (
    ResumeAnalysisADKCreate,
    ResumeAnalysisADKUpdate,
)

logger = logging.getLogger(__name__)


class CRUDResumeAnalysisADK(
    CRUDBase[ResumeAnalysisADK, ResumeAnalysisADKCreate, ResumeAnalysisADKUpdate]
):
    """CRUD operations scoped to ``ResumeAnalysisADK``.

    Adds convenience methods for retrieving analyses by user, which is
    the most common access pattern in this application.
    """

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ResumeAnalysisADK]:
        """Return all ADK resume analyses belonging to a user, newest first."""
        return (
            db.query(ResumeAnalysisADK)
            .filter(ResumeAnalysisADK.user_id == user_id)
            .order_by(ResumeAnalysisADK.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_latest_by_user(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Optional[ResumeAnalysisADK]:
        """Return the most recent ADK analysis for a user, or ``None``."""
        return (
            db.query(ResumeAnalysisADK)
            .filter(ResumeAnalysisADK.user_id == user_id)
            .order_by(ResumeAnalysisADK.created_at.desc())
            .first()
        )


resume_analysis_adk = CRUDResumeAnalysisADK(ResumeAnalysisADK)
