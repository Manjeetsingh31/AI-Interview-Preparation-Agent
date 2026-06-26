import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.crud.base import CRUDBase
from backend.app.models.question import Question
from backend.app.schemas.question import QuestionCreate, QuestionUpdate

logger = logging.getLogger(__name__)


class CRUDQuestion(CRUDBase[Question, QuestionCreate, QuestionUpdate]):
    """CRUD operations for the Question bank.

    Supports filtering by category, difficulty, and tags.
    """

    def get_by_category(
        self,
        db: Session,
        *,
        category: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Question]:
        """Retrieve questions belonging to a category."""
        return (
            db.query(Question)
            .filter(Question.category == category)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_difficulty(
        self,
        db: Session,
        *,
        difficulty: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Question]:
        """Retrieve questions at a specific difficulty level."""
        return (
            db.query(Question)
            .filter(Question.difficulty == difficulty)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_random(
        self,
        db: Session,
        *,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: int = 1,
    ) -> List[Question]:
        """Retrieve random question(s), optionally filtered.

        Uses SQLAlchemy's func.random() for ordering — works with SQLite.
        """
        from sqlalchemy import func

        query = db.query(Question)
        if category:
            query = query.filter(Question.category == category)
        if difficulty:
            query = query.filter(Question.difficulty == difficulty)
        return query.order_by(func.random()).limit(limit).all()


question = CRUDQuestion(Question)
