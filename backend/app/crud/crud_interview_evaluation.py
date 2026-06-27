"""CRUD operations for ``InterviewEvaluation``.

Extends the generic ``CRUDBase`` with evaluation-specific queries for
session management, history, analytics, and statistics.
"""

import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.interview_evaluation import InterviewEvaluation
from backend.app.schemas.interview_evaluation import (
    InterviewEvaluationCreate,
    InterviewEvaluationUpdate,
)

logger = logging.getLogger(__name__)


class CRUDInterviewEvaluation(
    CRUDBase[
        InterviewEvaluation,
        InterviewEvaluationCreate,
        InterviewEvaluationUpdate,
    ]
):
    """CRUD operations scoped to ``InterviewEvaluation``.

    Adds convenience methods for session-scoped queries, user history,
    analytics aggregation, and statistics.
    """

    # ------------------------------------------------------------------
    # Session-scoped queries
    # ------------------------------------------------------------------

    def get_by_session(
        self,
        db: Session,
        *,
        session_id: str,
    ) -> Optional[InterviewEvaluation]:
        """Return the evaluation for a specific session, or None."""
        return (
            db.query(InterviewEvaluation)
            .filter(InterviewEvaluation.session_id == session_id)
            .first()
        )

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[InterviewEvaluation]:
        """Return all evaluations for a user, newest first."""
        return (
            db.query(InterviewEvaluation)
            .filter(InterviewEvaluation.user_id == user_id)
            .order_by(InterviewEvaluation.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Latest
    # ------------------------------------------------------------------

    def get_latest_by_user(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Optional[InterviewEvaluation]:
        """Return the most recent evaluation for a user, or None."""
        return (
            db.query(InterviewEvaluation)
            .filter(InterviewEvaluation.user_id == user_id)
            .order_by(InterviewEvaluation.created_at.desc())
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
    ) -> List[InterviewEvaluation]:
        """Search evaluations by summary or recommendation content."""
        search_pattern = f"%{query}%"
        return (
            db.query(InterviewEvaluation)
            .filter(
                InterviewEvaluation.user_id == user_id,
                (
                    InterviewEvaluation.evaluation_summary.ilike(search_pattern)
                    | InterviewEvaluation.recommendation.ilike(search_pattern)
                ),
            )
            .order_by(InterviewEvaluation.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Analytics & Statistics
    # ------------------------------------------------------------------

    def average_scores(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Dict[str, Optional[float]]:
        """Return average scores across all evaluations for a user."""
        result = (
            db.query(
                func.avg(InterviewEvaluation.overall_score).label("avg_overall"),
                func.avg(InterviewEvaluation.technical_score).label("avg_technical"),
                func.avg(InterviewEvaluation.communication_score).label("avg_communication"),
                func.avg(InterviewEvaluation.problem_solving_score).label("avg_problem_solving"),
                func.avg(InterviewEvaluation.confidence_score).label("avg_confidence"),
                func.avg(InterviewEvaluation.behavioral_score).label("avg_behavioral"),
                func.avg(InterviewEvaluation.coding_score).label("avg_coding"),
            )
            .filter(InterviewEvaluation.user_id == user_id)
            .first()
        )

        if not result:
            return {}

        return {
            "average_overall_score": float(result.avg_overall) if result.avg_overall else None,
            "average_technical_score": float(result.avg_technical) if result.avg_technical else None,
            "average_communication_score": float(result.avg_communication) if result.avg_communication else None,
            "average_problem_solving_score": float(result.avg_problem_solving) if result.avg_problem_solving else None,
            "average_confidence_score": float(result.avg_confidence) if result.avg_confidence else None,
            "average_behavioral_score": float(result.avg_behavioral) if result.avg_behavioral else None,
            "average_coding_score": float(result.avg_coding) if result.avg_coding else None,
        }

    def common_items(
        self,
        db: Session,
        *,
        user_id: str,
        field: str,
        limit: int = 5,
    ) -> List[str]:
        """Return the most common values in a JSON list field.

        Args:
            db: Database session.
            user_id: User to filter by.
            field: Column name (e.g. 'strengths', 'weaknesses').
            limit: Max number of items to return.

        Returns:
            List of most frequently occurring string values.
        """
        column = getattr(InterviewEvaluation, field, None)
        if column is None:
            return []

        records = (
            db.query(column)
            .filter(
                InterviewEvaluation.user_id == user_id,
                column.isnot(None),
            )
            .all()
        )

        freq: Dict[str, int] = {}
        for (json_list,) in records:
            if isinstance(json_list, list):
                for item in json_list:
                    if isinstance(item, str):
                        freq[item] = freq.get(item, 0) + 1

        sorted_items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [item for item, _ in sorted_items[:limit]]

    def count_by_user(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> int:
        """Return the total number of evaluations for a user."""
        return (
            db.query(InterviewEvaluation)
            .filter(InterviewEvaluation.user_id == user_id)
            .count()
        )

    def statistics(
        self,
        db: Session,
        *,
        user_id: str,
    ) -> Dict:
        """Return comprehensive statistics for a user's evaluations."""
        return {
            "total_evaluations": self.count_by_user(db=db, user_id=user_id),
            **self.average_scores(db=db, user_id=user_id),
            "most_common_strengths": self.common_items(
                db=db, user_id=user_id, field="strengths"
            ),
            "most_common_weaknesses": self.common_items(
                db=db, user_id=user_id, field="weaknesses"
            ),
        }


interview_evaluation_crud = CRUDInterviewEvaluation(InterviewEvaluation)
