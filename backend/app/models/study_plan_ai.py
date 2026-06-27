"""StudyPlanAI database model.

Stores the AI-generated personalized study plan produced by the
Study Plan Agent after analyzing the candidate's resume, ATS score,
and interview evaluation.

Each row represents a complete learning roadmap for a specific target
role and company, including daily/weekly tasks, coding practice,
recommended projects, and certifications.

Relationships:
    user: The candidate who owns this study plan.
    evaluation: The interview evaluation this plan is based on.
    resume_analysis: The ADK resume analysis used as context.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class StudyPlanAI(Base):
    """Personalized AI-generated study plan.

    Attributes:
        id: UUID primary key.
        user_id: FK to the owning user.
        evaluation_id: FK to the interview evaluation used.
        resume_analysis_id: FK to the ADK resume analysis used.

        target_role: Job role the plan prepares for.
        target_company: Target company (optional).
        study_duration: Number of days the plan covers.

        roadmap: JSON — full structured roadmap (list of phases/weeks).
        daily_tasks: JSON — day-by-day breakdown of tasks.
        weekly_tasks: JSON — weekly goals and milestones.

        weak_topics: JSON list of prioritized weak topics.
        strong_topics: JSON list of strong topics to build on.

        coding_practice: JSON list of coding practice recommendations.
        interview_practice: JSON list of interview practice recommendations.

        recommended_projects: JSON list of recommended projects.
        recommended_certifications: JSON list of recommended certs.
        recommended_resources: JSON list of learning resources.

        completion_percentage: Float 0-100 tracking plan progress.
        status: One of active, completed, paused, archived.
        created_at: UTC timestamp.
        updated_at: UTC timestamp of last update.
    """

    __tablename__ = "study_plans_ai"

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
    evaluation_id = Column(
        String(36),
        ForeignKey("interview_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resume_analysis_id = Column(
        String(36),
        ForeignKey("resume_analyses_adk.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    target_role = Column(
        String(255),
        nullable=False,
    )
    target_company = Column(
        String(255),
        nullable=True,
    )
    study_duration = Column(
        Integer,
        nullable=False,
        comment="Number of days the plan covers (7, 15, 30, or 60)",
    )

    roadmap = Column(
        JSON,
        nullable=True,
        comment="Full structured roadmap as JSON",
    )
    daily_tasks = Column(
        JSON,
        nullable=True,
        comment="Day-by-day task breakdown",
    )
    weekly_tasks = Column(
        JSON,
        nullable=True,
        comment="Weekly goals and milestones",
    )

    weak_topics = Column(
        JSON,
        nullable=True,
        comment="Prioritized list of weak topics",
    )
    strong_topics = Column(
        JSON,
        nullable=True,
        comment="List of strong topics to build on",
    )

    coding_practice = Column(
        JSON,
        nullable=True,
        comment="Coding practice recommendations",
    )
    interview_practice = Column(
        JSON,
        nullable=True,
        comment="Interview practice recommendations",
    )

    recommended_projects = Column(
        JSON,
        nullable=True,
        comment="Recommended hands-on projects",
    )
    recommended_certifications = Column(
        JSON,
        nullable=True,
        comment="Recommended certifications",
    )
    recommended_resources = Column(
        JSON,
        nullable=True,
        comment="Recommended learning resources",
    )

    completion_percentage = Column(
        Float,
        default=0.0,
        nullable=False,
    )
    status = Column(
        String(20),
        default="active",
        nullable=False,
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

    user = relationship("User", backref="study_plans_ai")
    evaluation = relationship("InterviewEvaluation", backref="study_plans_ai")
    resume_analysis = relationship("ResumeAnalysisADK", backref="study_plans_ai")

    def __repr__(self) -> str:
        return (
            f"<StudyPlanAI(id={self.id}, role={self.target_role}, "
            f"duration={self.study_duration}d, status={self.status})>"
        )
