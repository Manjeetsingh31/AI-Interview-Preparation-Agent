from typing import Optional, List
from pydantic import BaseModel, Field


class QuestionBase(BaseModel):
    """Shared fields for the interview question bank."""
    category: str = Field(..., max_length=100, description="Topic bucket")
    difficulty: str = Field(
        ...,
        max_length=20,
        description="Difficulty: 'easy', 'medium', 'hard'",
    )
    question: str = Field(..., description="The interview question text")
    expected_answer: Optional[str] = Field(None, description="Ideal answer for evaluation rubrics")
    tags: Optional[List[str]] = Field(None, description="Filterable topic tags")


class QuestionCreate(QuestionBase):
    """Schema for adding a new question to the bank."""


class QuestionUpdate(BaseModel):
    """Schema for updating a question. All fields optional."""
    category: Optional[str] = Field(None, max_length=100)
    difficulty: Optional[str] = Field(None, max_length=20)
    question: Optional[str] = None
    expected_answer: Optional[str] = None
    tags: Optional[List[str]] = None


class QuestionResponse(QuestionBase):
    """Schema for question data returned to clients."""
    id: str = Field(..., description="UUID primary key")

    model_config = {"from_attributes": True}
