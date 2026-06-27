"""InterviewTurn database model.

Stores each Q&A turn from the Multi-Agent Mock Interview System.
Each row represents a single question asked by the AI interviewer
along with the candidate's answer, evaluation, and metadata.

Relationships:
    session: The InterviewSession this turn belongs to.
    user: The candidate who answered.
    resume_analysis: The ResumeAnalysisADK used for context.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class InterviewTurn(Base):
    """A single Q&A turn in a mock interview session.

    Attributes:
        id: UUID primary key.
        session_id: FK to the interview session.
        user_id: FK to the owning user.
        resume_analysis_id: FK to the ADK resume analysis used for context.
        question_number: Sequential number of this question in the session.
        question: The interview question text.
        candidate_answer: The candidate's answer text.
        follow_up: Follow-up question asked after the answer.
        difficulty: Difficulty level (Easy, Medium, Hard).
        category: Question category (HR, Technical, Coding, Behavioral).
        tags: JSON list of keyword tags.
        expected_answer: Expected or ideal answer.
        evaluation: AI evaluation of the candidate's answer.
        score: Score out of 100 for the answer.
        response_time: Time taken to answer in seconds.
        created_at: UTC timestamp.
    """

    __tablename__ = "interview_turns"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id = Column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_analysis_id = Column(
        String(36),
        ForeignKey("resume_analyses_adk.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question_number = Column(
        Integer,
        nullable=False,
    )
    question = Column(
        Text,
        nullable=False,
    )
    candidate_answer = Column(
        Text,
        nullable=True,
    )
    follow_up = Column(
        Text,
        nullable=True,
    )
    difficulty = Column(
        String(20),
        nullable=False,
    )
    category = Column(
        String(50),
        nullable=False,
    )
    tags = Column(
        JSON,
        nullable=True,
    )
    expected_answer = Column(
        Text,
        nullable=True,
    )
    evaluation = Column(
        Text,
        nullable=True,
    )
    score = Column(
        Integer,
        nullable=True,
    )
    response_time = Column(
        Integer,
        nullable=True,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    session = relationship("InterviewSession", backref="interview_turns")
    user = relationship("User", backref="interview_turns")
    resume_analysis = relationship("ResumeAnalysisADK", backref="interview_turns")

    def __repr__(self) -> str:
        return (
            f"<InterviewTurn(id={self.id}, session={self.session_id}, "
            f"q_no={self.question_number}, cat={self.category})>"
        )
