from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ProgressBase(BaseModel):
    """Shared fields for user progress snapshots."""
    completed_interviews: int = Field(0, ge=0, description="Total completed sessions")
    average_score: Optional[int] = Field(None, ge=0, le=100, description="Running average score")
    current_level: str = Field(
        "beginner",
        max_length=50,
        description="Level: 'beginner', 'intermediate', 'advanced'",
    )
    weak_topics: Optional[List[str]] = Field(None, description="Low-scoring topics")
    strong_topics: Optional[List[str]] = Field(None, description="High-scoring topics")


class ProgressCreate(ProgressBase):
    """Schema for creating a progress record."""
    user_id: str = Field(..., description="Owner's user UUID")


class ProgressUpdate(BaseModel):
    """Schema for updating progress. All fields optional."""
    completed_interviews: Optional[int] = Field(None, ge=0)
    average_score: Optional[int] = Field(None, ge=0, le=100)
    current_level: Optional[str] = Field(None, max_length=50)
    weak_topics: Optional[List[str]] = None
    strong_topics: Optional[List[str]] = None


class ProgressResponse(ProgressBase):
    """Schema for progress data returned to clients."""
    id: str = Field(..., description="UUID primary key")
    user_id: str = Field(..., description="Owner's user UUID")
    updated_at: datetime = Field(..., description="Last progress snapshot timestamp")

    model_config = {"from_attributes": True}
