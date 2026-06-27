"""CRUD operations for ``InterviewQuestion``.

Extends the generic ``CRUDBase`` with user-scoped queries and
bulk-creation for question generation results.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.interview_question import InterviewQuestion
from backend.app.schemas.interview_question import (
    InterviewQuestionCreate,
    InterviewQuestionUpdate,
)

logger = logging.getLogger(__name__)


class CRUDInterviewQuestion(
    CRUDBase[InterviewQuestion, InterviewQuestionCreate, InterviewQuestionUpdate]
):
    """CRUD operations scoped to ``InterviewQuestion``.

    Adds convenience methods for creating questions in bulk and
    retrieving questions by resume analysis.
    """

    def create_in_bulk(
        self,
        db: Session,
        *,
        questions_data: List[InterviewQuestionCreate],
    ) -> List[InterviewQuestion]:
        """Create multiple interview question records in a single transaction.

        Args:
            db: Database session.
            questions_data: List of ``InterviewQuestionCreate`` schemas.

        Returns:
            List of created ``InterviewQuestion`` instances.
        """
        db_objs: List[InterviewQuestion] = []
        for data in questions_data:
            obj = InterviewQuestion(**data.model_dump())
            db.add(obj)
            db_objs.append(obj)

        db.commit()
        for obj in db_objs:
            db.refresh(obj)

        logger.info(
            "Bulk-created %d InterviewQuestion records", len(db_objs)
        )
        return db_objs

    def get_by_resume_analysis(
        self,
        db: Session,
        *,
        resume_analysis_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[InterviewQuestion]:
        """Return all questions generated for a specific resume analysis."""
        return (
            db.query(InterviewQuestion)
            .filter(
                InterviewQuestion.resume_analysis_id == resume_analysis_id
            )
            .order_by(InterviewQuestion.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[InterviewQuestion]:
        """Return all questions for a given user, newest first."""
        return (
            db.query(InterviewQuestion)
            .filter(InterviewQuestion.user_id == user_id)
            .order_by(InterviewQuestion.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_analysis(
        self,
        db: Session,
        *,
        user_id: str,
        resume_analysis_id: str,
    ) -> List[InterviewQuestion]:
        """Return questions for a specific user and analysis combination."""
        return (
            db.query(InterviewQuestion)
            .filter(
                InterviewQuestion.user_id == user_id,
                InterviewQuestion.resume_analysis_id == resume_analysis_id,
            )
            .order_by(InterviewQuestion.created_at.desc())
            .all()
        )


interview_question = CRUDInterviewQuestion(InterviewQuestion)
