from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StudyPlanBase(BaseModel):
    """Shared fields for study plan day entries."""
    day: int = Field(..., ge=1, description="Day number within the plan (1-based)")
    topic: str = Field(..., max_length=255, description="Subject area for the day")
    task: str = Field(..., description="Concrete task description")
    status: str = Field(
        "pending",
        max_length=20,
        description="Status: 'pending', 'in_progress', 'completed'",
    )


class StudyPlanCreate(StudyPlanBase):
    """Schema for adding a new study plan entry."""
    user_id: str = Field(..., description="Owner's user UUID")


class StudyPlanUpdate(BaseModel):
    """Schema for updating a study plan entry."""
    day: Optional[int] = Field(None, ge=1)
    topic: Optional[str] = Field(None, max_length=255)
    task: Optional[str] = None
    status: Optional[str] = Field(None, max_length=20)


class StudyPlanResponse(StudyPlanBase):
    """Schema for study plan data returned to clients."""
    id: str = Field(..., description="UUID primary key")
    user_id: str = Field(..., description="Owner's user UUID")
    created_at: datetime = Field(..., description="When the entry was created")

    model_config = {"from_attributes": True}
