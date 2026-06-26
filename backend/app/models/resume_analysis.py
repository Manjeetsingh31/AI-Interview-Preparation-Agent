import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class ResumeAnalysis(Base):
    """Stores the output of parsing and analysing a candidate's resume.

    Each row represents a single uploaded resume and its ATS (Applicant
    Tracking System) evaluation. Skills, strengths, and recommendations are
    stored as JSON lists for schema flexibility — they vary per resume.

    Relationships:
        user: The candidate who owns this resume.
    """
    __tablename__ = "resume_analyses"

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
        comment="FK — cascading delete removes analyses when user is deleted",
    )
    resume_filename = Column(
        String(255),
        nullable=False,
        comment="Original uploaded filename for display purposes",
    )
    ats_score = Column(
        Integer,
        nullable=True,
        comment="ATS compatibility score out of 100 (nullable until parsed)",
    )
    skills = Column(
        JSON,
        nullable=True,
        comment="List of detected skills, e.g. ['Python', 'Kubernetes']",
    )
    missing_skills = Column(
        JSON,
        nullable=True,
        comment="Skills the job description expected but the resume lacks",
    )
    strengths = Column(
        JSON,
        nullable=True,
        comment="Key strengths identified in the resume",
    )
    weaknesses = Column(
        JSON,
        nullable=True,
        comment="Areas where the resume could be improved",
    )
    recommendations = Column(
        JSON,
        nullable=True,
        comment="Actionable suggestions for resume improvement",
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="When this analysis was performed",
    )

    user = relationship("User", back_populates="resume_analyses")

    def __repr__(self) -> str:
        return f"<ResumeAnalysis(id={self.id}, file={self.resume_filename})>"
