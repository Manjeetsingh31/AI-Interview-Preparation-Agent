"""InterviewEvaluation database model.

Stores the comprehensive AI evaluation of a completed mock interview
session. Each row represents a full evaluation produced by the
Evaluation Agent after the interview finishes.

The evaluation analyses the candidate's performance across multiple
dimensions: technical knowledge, communication, problem-solving,
confidence, behaviour, and coding skills. It also includes a hiring
recommendation and detailed improvement suggestions.

Relationships:
    session: The InterviewSession that was evaluated.
    user: The candidate who was evaluated.
    resume_analysis: The ResumeAnalysisADK used as context.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class InterviewEvaluation(Base):
    """Comprehensive evaluation of a completed mock interview session.

    Attributes:
        id: UUID primary key.
        session_id: FK to the interview session (unique — one eval per session).
        user_id: FK to the owning user.
        resume_analysis_id: FK to the ADK resume analysis used for context.

        overall_score: Composite score out of 100.
        technical_score: Technical knowledge score (0-100).
        communication_score: Communication clarity score (0-100).
        problem_solving_score: Problem-solving ability score (0-100).
        confidence_score: Confidence level score (0-100).
        behavioral_score: Behavioural competency score (0-100).
        coding_score: Coding skill score (0-100).

        strengths: JSON list of identified strengths.
        weaknesses: JSON list of identified weaknesses.
        missed_topics: JSON list of topics the candidate missed.
        strong_topics: JSON list of topics the candidate excelled at.

        improvement_suggestions: JSON list of actionable improvement suggestions.
        recommendation: Detailed hiring recommendation text.
        hire_decision: One of Strong Hire, Hire, Borderline, Reject.
        difficulty_level: Overall difficulty level of the interview.

        evaluation_summary: Full-text summary of the evaluation.

        created_at: UTC timestamp.
    """

    __tablename__ = "interview_evaluations"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id = Column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        unique=True,
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

    overall_score = Column(
        Integer,
        nullable=False,
    )
    technical_score = Column(
        Integer,
        nullable=True,
    )
    communication_score = Column(
        Integer,
        nullable=True,
    )
    problem_solving_score = Column(
        Integer,
        nullable=True,
    )
    confidence_score = Column(
        Integer,
        nullable=True,
    )
    behavioral_score = Column(
        Integer,
        nullable=True,
    )
    coding_score = Column(
        Integer,
        nullable=True,
    )

    strengths = Column(
        JSON,
        nullable=True,
    )
    weaknesses = Column(
        JSON,
        nullable=True,
    )
    missed_topics = Column(
        JSON,
        nullable=True,
    )
    strong_topics = Column(
        JSON,
        nullable=True,
    )

    improvement_suggestions = Column(
        JSON,
        nullable=True,
    )
    recommendation = Column(
        Text,
        nullable=True,
    )
    hire_decision = Column(
        String(20),
        nullable=True,
    )
    difficulty_level = Column(
        String(20),
        nullable=True,
    )

    evaluation_summary = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    session = relationship("InterviewSession", backref="interview_evaluation")
    user = relationship("User", backref="interview_evaluations")
    resume_analysis = relationship("ResumeAnalysisADK", backref="interview_evaluations")

    def __repr__(self) -> str:
        return (
            f"<InterviewEvaluation(id={self.id}, session={self.session_id}, "
            f"score={self.overall_score})>"
        )
