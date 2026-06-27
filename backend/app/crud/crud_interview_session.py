"""CRUD operations for ``InterviewSession``.

Thin wrapper around the ``InterviewSession`` model from ``models.py``,
providing basic CRUD via the generic base class.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.models import InterviewSession
from backend.app.schemas.interview_session import (
    InterviewSessionCreate,
    InterviewSessionUpdate,
)

logger = logging.getLogger(__name__)


class CRUDInterviewSession(
    CRUDBase[InterviewSession, InterviewSessionCreate, InterviewSessionUpdate]
):
    """Minimal CRUD for InterviewSession with user-scoped lookups."""

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ):
        """Return sessions for a user, newest first."""
        return (
            db.query(InterviewSession)
            .filter(InterviewSession.user_id == user_id)
            .order_by(InterviewSession.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


interview_session_crud = CRUDInterviewSession(InterviewSession)
