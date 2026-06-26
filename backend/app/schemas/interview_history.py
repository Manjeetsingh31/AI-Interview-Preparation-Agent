from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class InterviewHistoryBase(BaseModel):
    """Shared fields for interview Q&A records."""
    interview_type: str = Field(
        ...,
        max_length=50,
        description="Type: 'behavioral', 'coding', 'system_design', etc.",
    )
    question: str = Field(..., description="The interview question text")
    answer: Optional[str] = Field(None, description="The candidate's answer text")
    score: Optional[int] = Field(None, ge=0, le=100, description="Score 0-100")
    feedback: Optional[str] = Field(None, description="Qualitative feedback on the answer")


class InterviewHistoryCreate(InterviewHistoryBase):
    """Schema for recording a new interview turn."""
    user_id: str = Field(..., description="Owner's user UUID")


class InterviewHistoryUpdate(BaseModel):
    """Schema for updating an interview record (e.g. adding score later)."""
    interview_type: Optional[str] = Field(None, max_length=50)
    question: Optional[str] = None
    answer: Optional[str] = None
    score: Optional[int] = Field(None, ge=0, le=100)
    feedback: Optional[str] = None


class InterviewHistoryResponse(InterviewHistoryBase):
    """Schema for interview history data returned to clients."""
    id: str = Field(..., description="UUID primary key")
    user_id: str = Field(..., description="Owner's user UUID")
    created_at: datetime = Field(..., description="When this turn was recorded")

    model_config = {"from_attributes": True}
