import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class InterviewHistory(Base):
    """Records a single Q&A turn from a mock interview session.

    Each row captures one question asked by the AI interviewer and the
    candidate's answer together with an optional score. The interview_type
    discriminates between behavioural, coding, system-design, etc.

    Relationships:
        user: The candidate being interviewed.
    """
    __tablename__ = "interview_histories"

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
    interview_type = Column(
        String(50),
        nullable=False,
        comment="Category of interview: 'behavioral', 'coding', 'system_design'",
    )
    question = Column(
        Text,
        nullable=False,
        comment="The interview question posed to the candidate",
    )
    answer = Column(
        Text,
        nullable=True,
        comment="The candidate's spoken or typed answer",
    )
    score = Column(
        Integer,
        nullable=True,
        comment="Score out of 100 assigned by the evaluator agent",
    )
    feedback = Column(
        Text,
        nullable=True,
        comment="Qualitative feedback on this specific answer",
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="interview_histories")

    def __repr__(self) -> str:
        return f"<InterviewHistory(id={self.id}, type={self.interview_type})>"
