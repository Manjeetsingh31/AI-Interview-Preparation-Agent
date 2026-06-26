"""ADK Resume Analysis model.

Stores the output of the Google ADK Resume Analysis Agent.
Each row represents a single resume analysed by the ADK agent.
The raw resume text and the structured JSON extracted by Gemini
are both persisted for auditability and reprocessing.

Relationships:
    user: The candidate who owns this analysis.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class ResumeAnalysisADK(Base):
    """Structured resume analysis produced by the Google ADK agent.

    Stores the raw resume text alongside the structured JSON extraction
    so that the analysis can be audited or re-run without re-uploading.

    Attributes:
        id: UUID primary key.
        user_id: FK to the owning user.
        resume_filename: Original uploaded filename.
        raw_text: Full text extracted from the resume PDF.
        extracted_json: Structured JSON returned by Gemini via the ADK agent.
        created_at: UTC timestamp of when the analysis was saved.
    """

    __tablename__ = "resume_analyses_adk"

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
    resume_filename = Column(
        String(255),
        nullable=False,
    )
    raw_text = Column(
        Text,
        nullable=True,
    )
    extracted_json = Column(
        JSON,
        nullable=True,
    )
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<ResumeAnalysisADK(id={self.id}, file={self.resume_filename})>"
