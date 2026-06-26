from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FeedbackBase(BaseModel):
    """Shared fields for interview performance feedback."""
    communication_score: Optional[int] = Field(None, ge=0, le=100, description="Clarity score 0-100")
    technical_score: Optional[int] = Field(None, ge=0, le=100, description="Technical accuracy 0-100")
    confidence_score: Optional[int] = Field(None, ge=0, le=100, description="Confidence score 0-100")
    overall_score: Optional[int] = Field(None, ge=0, le=100, description="Weighted composite 0-100")
    strengths: Optional[List[str]] = Field(None, description="Observed strong areas")
    weaknesses: Optional[List[str]] = Field(None, description="Areas needing improvement")
    suggestions: Optional[List[str]] = Field(None, description="Actionable improvement tips")


class FeedbackCreate(FeedbackBase):
    """Schema for creating a new feedback record."""
    user_id: str = Field(..., description="Owner's user UUID")


class FeedbackUpdate(BaseModel):
    """Schema for updating feedback. All fields optional."""
    communication_score: Optional[int] = Field(None, ge=0, le=100)
    technical_score: Optional[int] = Field(None, ge=0, le=100)
    confidence_score: Optional[int] = Field(None, ge=0, le=100)
    overall_score: Optional[int] = Field(None, ge=0, le=100)
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None


class FeedbackResponse(FeedbackBase):
    """Schema for feedback data returned to clients."""
    id: str = Field(..., description="UUID primary key")
    user_id: str = Field(..., description="Owner's user UUID")
    created_at: datetime = Field(..., description="When feedback was recorded")

    model_config = {"from_attributes": True}
