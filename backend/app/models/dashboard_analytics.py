"""DashboardAnalytics database model.

Stores pre-computed analytics snapshots for the candidate's interview
preparation journey. Each row contains aggregated statistics from
Resume Analysis, ATS, Interview Sessions, Evaluations, and Study Plans.

The model uses JSON columns to store structured sub-documents so that
the schema stays flexible as new metrics are added.

Relationships:
    user: The candidate who owns this dashboard data.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class DashboardAnalytics(Base):
    """Aggregated analytics snapshot for a user's dashboard.

    Attributes:
        id: UUID primary key.
        user_id: FK to the owning user (one row per user).

        resume_stats: JSON — resume upload/analysis summary.
        ats_stats: JSON — ATS score history and keyword coverage.
        interview_stats: JSON — session counts, scores, distributions.
        evaluation_stats: JSON — evaluation scores, strengths, weaknesses.
        study_stats: JSON — study plan completion and task tracking.
        skill_stats: JSON — skill analytics (top, missing, weak, strong).

        daily_activity: JSON — list of daily activity records.
        weekly_activity: JSON — list of weekly activity records.
        monthly_activity: JSON — list of monthly activity records.

        total_sessions: Total interview sessions count.
        average_ats_score: Average ATS score across all analyses.
        average_interview_score: Average interview performance score.
        average_evaluation_score: Average evaluation score.
        best_score: Highest evaluation score achieved.
        worst_score: Lowest evaluation score achieved.
        improvement_rate: Percentage improvement over time.

        completed_study_tasks: Number of completed study tasks.
        pending_study_tasks: Number of pending study tasks.

        overall_readiness_score: Composite readiness score (0-100).

        created_at: UTC timestamp.
        updated_at: UTC timestamp of last update.
    """

    __tablename__ = "dashboard_analytics"

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
        unique=True,
    )

    # JSON statistics blobs
    resume_stats = Column(JSON, nullable=True, comment="Resume analysis summary")
    ats_stats = Column(JSON, nullable=True, comment="ATS score analytics")
    interview_stats = Column(JSON, nullable=True, comment="Interview session analytics")
    evaluation_stats = Column(JSON, nullable=True, comment="Evaluation score analytics")
    study_stats = Column(JSON, nullable=True, comment="Study plan progress analytics")
    skill_stats = Column(JSON, nullable=True, comment="Skill coverage and analytics")

    # Timeline activity
    daily_activity = Column(JSON, nullable=True, comment="Daily activity records")
    weekly_activity = Column(JSON, nullable=True, comment="Weekly activity records")
    monthly_activity = Column(JSON, nullable=True, comment="Monthly activity records")

    # Numeric roll-ups
    total_sessions = Column(Integer, default=0, nullable=False)
    average_ats_score = Column(Float, nullable=True)
    average_interview_score = Column(Float, nullable=True)
    average_evaluation_score = Column(Float, nullable=True)
    best_score = Column(Integer, nullable=True)
    worst_score = Column(Integer, nullable=True)
    improvement_rate = Column(Float, nullable=True, comment="Percentage improvement")

    completed_study_tasks = Column(Integer, default=0, nullable=False)
    pending_study_tasks = Column(Integer, default=0, nullable=False)

    overall_readiness_score = Column(
        Integer, nullable=True, comment="Composite readiness 0-100"
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", backref="dashboard_analytics")

    def __repr__(self) -> str:
        return (
            f"<DashboardAnalytics(id={self.id}, user={self.user_id}, "
            f"readiness={self.overall_readiness_score})>"
        )
