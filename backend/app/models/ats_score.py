"""ATS Score database model.

Stores the output of the AI-powered ATS (Applicant Tracking System) scoring engine.
Each row represents a single resume scored by the ATS engine, consuming structured
data from the Resume Analysis ADK agent — never raw PDFs or text.

Relationships:
    user: The candidate who owns this score.
    resume_analysis_adk: The ADK analysis record that was scored.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class AtsScore(Base):
    """ATS scoring result for a single resume analysis.

    Attributes:
        id: UUID primary key.
        resume_analysis_adk_id: FK to the analysed resume record.
        user_id: FK to the owning user.
        overall_score: Composite ATS score out of 100.
        section_scores: JSON dict mapping section names to
            {score, reason, recommendation}.
        job_match: JSON dict mapping job role to match percentage (0-100).
        strengths: List of identified resume strengths.
        weaknesses: List of identified resume weaknesses.
        missing_technical_skills: Technical skills the resume lacks.
        missing_soft_skills: Soft skills the resume lacks.
        missing_keywords: Keywords missing from the resume.
        resume_structure_score: Structure quality score (0-100).
        grammar_score: Grammar and readability score (0-100).
        project_quality_score: Project quality score (0-100).
        education_score: Education relevance score (0-100).
        experience_score: Experience relevance score (0-100).
        certification_score: Certification score (0-100).
        skill_gap_analysis: JSON dict with categorised skill gaps.
        improvement_suggestions: List of actionable improvement suggestions.
        created_at: UTC timestamp of when the score was generated.
    """

    __tablename__ = "ats_scores"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    resume_analysis_adk_id = Column(
        String(36),
        ForeignKey("resume_analyses_adk.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_score = Column(
        Integer,
        nullable=False,
    )
    section_scores = Column(
        JSON,
        nullable=True,
    )
    job_match = Column(
        JSON,
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
    missing_technical_skills = Column(
        JSON,
        nullable=True,
    )
    missing_soft_skills = Column(
        JSON,
        nullable=True,
    )
    missing_keywords = Column(
        JSON,
        nullable=True,
    )
    resume_structure_score = Column(
        Integer,
        nullable=True,
    )
    grammar_score = Column(
        Integer,
        nullable=True,
    )
    project_quality_score = Column(
        Integer,
        nullable=True,
    )
    education_score = Column(
        Integer,
        nullable=True,
    )
    experience_score = Column(
        Integer,
        nullable=True,
    )
    certification_score = Column(
        Integer,
        nullable=True,
    )
    skill_gap_analysis = Column(
        JSON,
        nullable=True,
    )
    improvement_suggestions = Column(
        JSON,
        nullable=True,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", backref="ats_scores")
    resume_analysis_adk = relationship("ResumeAnalysisADK", backref="ats_scores")

    def __repr__(self) -> str:
        return f"<AtsScore(id={self.id}, score={self.overall_score})>"
