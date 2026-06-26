from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ResumeAnalysisBase(BaseModel):
    """Shared fields for resume analysis records."""
    resume_filename: str = Field(..., max_length=255, description="Original uploaded filename")
    ats_score: Optional[int] = Field(None, ge=0, le=100, description="ATS compatibility score 0-100")
    skills: Optional[List[str]] = Field(None, description="Detected skills list")
    missing_skills: Optional[List[str]] = Field(None, description="Skills the resume lacks")
    strengths: Optional[List[str]] = Field(None, description="Identified strengths")
    weaknesses: Optional[List[str]] = Field(None, description="Areas for improvement")
    recommendations: Optional[List[str]] = Field(None, description="Actionable suggestions")


class ResumeAnalysisCreate(ResumeAnalysisBase):
    """Schema for creating a new resume analysis.

    user_id is typically injected from the authenticated request context.
    """
    user_id: str = Field(..., description="Owner's user UUID")


class ResumeAnalysisUpdate(BaseModel):
    """Schema for updating an existing resume analysis.

    All fields optional — only provided fields will be patched.
    """
    resume_filename: Optional[str] = Field(None, max_length=255)
    ats_score: Optional[int] = Field(None, ge=0, le=100)
    skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None


class ResumeAnalysisResponse(ResumeAnalysisBase):
    """Schema for resume analysis data returned to clients."""
    id: str = Field(..., description="UUID primary key")
    user_id: str = Field(..., description="Owner's user UUID")
    created_at: datetime = Field(..., description="When the analysis was performed")

    model_config = {"from_attributes": True}
