import uuid
from sqlalchemy import Column, String, Text, JSON
from backend.app.core.database import Base


class Question(Base):
    """Pre-seeded question bank for mock interviews.

    This table is populated at setup time with curated questions organised by
    category and difficulty. It is read-only from the application perspective
    — questions are never modified during normal operation. The tags column
    enables filtering by topic (e.g. 'python', 'leadership', 'algorithms').

    Note:
        This model has NO foreign-key relationship to User because questions
        are shared across all candidates.
    """
    __tablename__ = "questions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    category = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Topic bucket: 'behavioral', 'python', 'system_design', 'ml', etc.",
    )
    difficulty = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Difficulty level: 'easy', 'medium', 'hard'",
    )
    question = Column(
        Text,
        nullable=False,
        comment="The interview question text",
    )
    expected_answer = Column(
        Text,
        nullable=True,
        comment="Ideal/expected answer used as a rubric by the evaluator",
    )
    tags = Column(
        JSON,
        nullable=True,
        comment="Arbitrary tags for advanced filtering, e.g. ['python', 'oop']",
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, category={self.category}, diff={self.difficulty})>"
