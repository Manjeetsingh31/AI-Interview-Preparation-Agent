"""Pydantic schemas for the InterviewSession model.

The InterviewSession model (from models.py) stores metadata about each
mock interview session: role, company, interview type, and status.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InterviewSessionBase(BaseModel):
    """Shared fields for interview session records."""

    role: str = Field(..., description="Job role for the interview")
    company: Optional[str] = Field("Standard", description="Target company")
    interview_type: str = Field(..., description="Technical, behavioral, etc.")
    status: Optional[str] = Field("active", description="Session status")


class InterviewSessionCreate(InterviewSessionBase):
    """Schema for creating a new interview session record."""

    user_id: str = Field(..., description="Owner's user UUID")
    resume_id: Optional[str] = Field(None, description="FK to resume")


class InterviewSessionUpdate(BaseModel):
    """Schema for updating an interview session.

    All fields are optional.
    """

    role: Optional[str] = None
    company: Optional[str] = None
    interview_type: Optional[str] = None
    status: Optional[str] = None


class InterviewSessionResponse(InterviewSessionBase):
    """Schema for interview session data returned to API clients."""

    id: str
    user_id: str
    resume_id: Optional[str]
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
