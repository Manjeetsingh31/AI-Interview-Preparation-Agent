import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Progress(Base):
    """Denormalised one-row-per-user progress snapshot.

    Aggregates overall interview performance data so the dashboard can display
    the user's current level, weak/strong topics, and completion stats without
    running expensive aggregate queries on every page load. Updated after each
    interview session.

    This is a one-to-one relationship — every user has exactly one Progress row
    (auto-created on first interview completion).

    Relationships:
        user: The candidate whose progress is tracked.
    """
    __tablename__ = "progress"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="One-to-one: each user has exactly one progress row",
    )
    completed_interviews = Column(
        Integer,
        default=0,
        comment="Total number of completed interview sessions",
    )
    average_score = Column(
        Integer,
        nullable=True,
        comment="Running average score across all completed interviews",
    )
    current_level = Column(
        String(50),
        default="beginner",
        comment="Proficiency level: 'beginner', 'intermediate', 'advanced'",
    )
    weak_topics = Column(
        JSON,
        nullable=True,
        comment="Topics the user consistently scores low on",
    )
    strong_topics = Column(
        JSON,
        nullable=True,
        comment="Topics the user consistently scores high on",
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Last time the progress snapshot was recalculated",
    )

    user = relationship("User", back_populates="progress")

    def __repr__(self) -> str:
        return f"<Progress(id={self.id}, level={self.current_level})>"
