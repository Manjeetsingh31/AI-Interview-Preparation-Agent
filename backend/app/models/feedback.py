import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Feedback(Base):
    """Aggregated performance feedback for a completed interview round.

    Unlike InterviewHistory (per-question), Feedback is a post-interview
    summary covering communication, technical depth, and confidence. Storing
    structured scores in dedicated columns makes analytical queries
    (AVG, WHERE filters) efficient without JSON parsing.

    Relationships:
        user: The candidate who received this feedback.
    """
    __tablename__ = "feedbacks"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    communication_score = Column(
        Integer,
        nullable=True,
        comment="Clarity, articulation, and structure of responses (0-100)",
    )
    technical_score = Column(
        Integer,
        nullable=True,
        comment="Accuracy and depth of technical answers (0-100)",
    )
    confidence_score = Column(
        Integer,
        nullable=True,
        comment="Perceived confidence and composure (0-100)",
    )
    overall_score = Column(
        Integer,
        nullable=True,
        comment="Weighted composite score (0-100)",
    )
    strengths = Column(
        JSON,
        nullable=True,
        comment="List of observed strong areas",
    )
    weaknesses = Column(
        JSON,
        nullable=True,
        comment="List of areas needing improvement",
    )
    suggestions = Column(
        JSON,
        nullable=True,
        comment="Actionable improvement suggestions",
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="feedbacks")

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, overall={self.overall_score})>"
