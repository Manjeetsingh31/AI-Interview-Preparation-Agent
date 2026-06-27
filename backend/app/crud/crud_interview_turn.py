"""CRUD operations for ``InterviewTurn``.

Extends the generic ``CRUDBase`` with interview-specific queries for
session management, conversation history, and session analytics.
"""

import logging
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.interview_turn import InterviewTurn
from backend.app.schemas.interview_turn import (
    InterviewTurnCreate,
    InterviewTurnUpdate,
)

logger = logging.getLogger(__name__)


class CRUDInterviewTurn(
    CRUDBase[InterviewTurn, InterviewTurnCreate, InterviewTurnUpdate]
):
    """CRUD operations scoped to ``InterviewTurn``.

    Adds convenience methods for session-scoped queries, pagination,
    conversation transcript building, and scoring analytics.
    """

    # ------------------------------------------------------------------
    # Session-scoped queries
    # ------------------------------------------------------------------

    def get_by_session(
        self,
        db: Session,
        *,
        session_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[InterviewTurn]:
        """Return all turns for a session, ordered by question number."""
        return (
            db.query(InterviewTurn)
            .filter(InterviewTurn.session_id == session_id)
            .order_by(InterviewTurn.question_number.asc())
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
    ) -> List[InterviewTurn]:
        """Return all turns for a user, newest first."""
        return (
            db.query(InterviewTurn)
            .filter(InterviewTurn.user_id == user_id)
            .order_by(InterviewTurn.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_session_turns(
        self,
        db: Session,
        *,
        session_id: str,
    ) -> List[InterviewTurn]:
        """Return ALL turns for a session (no pagination)."""
        return (
            db.query(InterviewTurn)
            .filter(InterviewTurn.session_id == session_id)
            .order_by(InterviewTurn.question_number.asc())
            .all()
        )

    # ------------------------------------------------------------------
    # Single-turn queries
    # ------------------------------------------------------------------

    def get_latest_turn(
        self,
        db: Session,
        *,
        session_id: str,
    ) -> Optional[InterviewTurn]:
        """Return the most recent turn in a session."""
        return (
            db.query(InterviewTurn)
            .filter(InterviewTurn.session_id == session_id)
            .order_by(InterviewTurn.question_number.desc())
            .first()
        )

    def get_next_question_number(
        self,
        db: Session,
        *,
        session_id: str,
    ) -> int:
        """Return the next question number for a session (1-based)."""
        result = (
            db.query(func.max(InterviewTurn.question_number))
            .filter(InterviewTurn.session_id == session_id)
            .scalar()
        )
        return (result or 0) + 1

    # ------------------------------------------------------------------
    # Answer management
    # ------------------------------------------------------------------

    def update_answer(
        self,
        db: Session,
        *,
        turn_id: str,
        candidate_answer: str,
        evaluation: Optional[str] = None,
        score: Optional[int] = None,
        follow_up: Optional[str] = None,
        response_time: Optional[int] = None,
    ) -> Optional[InterviewTurn]:
        """Update a turn with the candidate's answer and evaluation."""
        db_obj = self.get(db, id=turn_id)
        if not db_obj:
            logger.warning("Turn not found for answer update: id=%s", turn_id)
            return None

        update_data = {}
        if candidate_answer is not None:
            update_data["candidate_answer"] = candidate_answer
        if evaluation is not None:
            update_data["evaluation"] = evaluation
        if score is not None:
            update_data["score"] = score
        if follow_up is not None:
            update_data["follow_up"] = follow_up
        if response_time is not None:
            update_data["response_time"] = response_time

        return self.update(db=db, db_obj=db_obj, obj_in=update_data)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def average_score(
        self,
        db: Session,
        *,
        session_id: str,
    ) -> Optional[float]:
        """Return the average score across all answered turns in a session."""
        result = (
            db.query(func.avg(InterviewTurn.score))
            .filter(
                InterviewTurn.session_id == session_id,
                InterviewTurn.score.isnot(None),
            )
            .scalar()
        )
        return float(result) if result is not None else None

    def count_by_session(
        self,
        db: Session,
        *,
        session_id: str,
    ) -> int:
        """Return the total number of turns in a session."""
        return (
            db.query(InterviewTurn)
            .filter(InterviewTurn.session_id == session_id)
            .count()
        )

    # ------------------------------------------------------------------
    # Transcript
    # ------------------------------------------------------------------

    def get_transcript(
        self,
        db: Session,
        *,
        session_id: str,
    ) -> str:
        """Build a human-readable conversation transcript for a session.

        Returns:
            A formatted string of all Q&A turns.
        """
        turns = self.get_session_turns(db=db, session_id=session_id)
        if not turns:
            return ""

        lines: List[str] = []
        for t in turns:
            lines.append(f"Q{t.question_number} ({t.category}/{t.difficulty}): {t.question}")
            if t.candidate_answer:
                lines.append(f"A{t.question_number}: {t.candidate_answer}")
            if t.evaluation:
                lines.append(f"Eval{t.question_number}: {t.evaluation} (Score: {t.score})")
            if t.follow_up:
                lines.append(f"Follow-up{t.question_number}: {t.follow_up}")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_by_session(
        self,
        db: Session,
        *,
        session_id: str,
    ) -> int:
        """Delete all turns for a session. Returns count of deleted rows."""
        deleted = (
            db.query(InterviewTurn)
            .filter(InterviewTurn.session_id == session_id)
            .delete()
        )
        db.commit()
        logger.info(
            "Deleted %d InterviewTurn records for session %s",
            deleted,
            session_id,
        )
        return deleted

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
    ) -> List[InterviewTurn]:
        """Search turns by question or answer content for a user."""
        search_pattern = f"%{query}%"
        return (
            db.query(InterviewTurn)
            .filter(
                InterviewTurn.user_id == user_id,
                (
                    InterviewTurn.question.ilike(search_pattern)
                    | InterviewTurn.candidate_answer.ilike(search_pattern)
                ),
            )
            .order_by(InterviewTurn.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )


interview_turn_crud = CRUDInterviewTurn(InterviewTurn)
