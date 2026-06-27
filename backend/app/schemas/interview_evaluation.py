"""Pydantic schemas for the Production AI Evaluation & Feedback Agent.

Layers of schema:
1. ``InterviewEvaluationOutput`` — ADK agent output schema (Gemini response_schema).
2. ``InterviewEvaluationBase/Create/Update/Response`` — CRUD persistence schemas.
3. ``InterviewEvaluationSummary/History/Analytics/Dashboard`` — API response wrappers.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# ADK Agent output schema (Gemini response_schema)
# ---------------------------------------------------------------------------


class InterviewEvaluationOutput(BaseModel):
    """Top-level evaluation result that Gemini returns.

    This schema is used as the ADK Agent's ``output_schema`` so that
    Gemini 2.5 Flash returns strictly typed JSON matching these fields.
    """

    overall_score: int = Field(
        ..., ge=0, le=100, description="Composite overall score out of 100"
    )
    technical_score: int = Field(
        ..., ge=0, le=100, description="Technical knowledge score"
    )
    communication_score: int = Field(
        ..., ge=0, le=100, description="Communication clarity score"
    )
    problem_solving_score: int = Field(
        ..., ge=0, le=100, description="Problem-solving ability score"
    )
    confidence_score: int = Field(
        ..., ge=0, le=100, description="Confidence level score"
    )
    behavioral_score: int = Field(
        ..., ge=0, le=100, description="Behavioural competency score"
    )
    coding_score: int = Field(
        ..., ge=0, le=100, description="Coding skill score"
    )

    strengths: List[str] = Field(
        default_factory=list,
        description="Key strengths demonstrated during the interview",
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="Areas where the candidate needs improvement",
    )
    missed_topics: List[str] = Field(
        default_factory=list,
        description="Important topics the candidate missed or struggled with",
    )
    strong_topics: List[str] = Field(
        default_factory=list,
        description="Topics the candidate demonstrated strong knowledge in",
    )

    improvement_suggestions: List[str] = Field(
        default_factory=list,
        description="Actionable suggestions for improvement",
    )
    recommendation: str = Field(
        ...,
        description="Detailed hiring recommendation with rationale",
    )
    hire_decision: str = Field(
        ...,
        description="One of: Strong Hire, Hire, Borderline, Reject",
    )
    difficulty_level: str = Field(
        ...,
        description="Overall difficulty level: Easy, Medium, or Hard",
    )

    evaluation_summary: str = Field(
        ...,
        description="Full-text summary of the evaluation",
    )


# ---------------------------------------------------------------------------
# CRUD schemas (follow existing project convention)
# ---------------------------------------------------------------------------


class InterviewEvaluationBase(BaseModel):
    """Shared fields for interview evaluation records."""

    session_id: str = Field(..., description="FK to the interview session")
    resume_analysis_id: Optional[str] = Field(
        None, description="FK to the ADK resume analysis"
    )
    overall_score: int = Field(..., ge=0, le=100)
    technical_score: Optional[int] = Field(None, ge=0, le=100)
    communication_score: Optional[int] = Field(None, ge=0, le=100)
    problem_solving_score: Optional[int] = Field(None, ge=0, le=100)
    confidence_score: Optional[int] = Field(None, ge=0, le=100)
    behavioral_score: Optional[int] = Field(None, ge=0, le=100)
    coding_score: Optional[int] = Field(None, ge=0, le=100)
    strengths: Optional[List[str]] = Field(None)
    weaknesses: Optional[List[str]] = Field(None)
    missed_topics: Optional[List[str]] = Field(None)
    strong_topics: Optional[List[str]] = Field(None)
    improvement_suggestions: Optional[List[str]] = Field(None)
    recommendation: Optional[str] = Field(None)
    hire_decision: Optional[str] = Field(None)
    difficulty_level: Optional[str] = Field(None)
    evaluation_summary: Optional[str] = Field(None)


class InterviewEvaluationCreate(InterviewEvaluationBase):
    """Schema for creating a new interview evaluation record."""

    user_id: str = Field(..., description="Owner's user UUID")


class InterviewEvaluationUpdate(BaseModel):
    """Schema for updating an existing interview evaluation record.

    All fields are optional — only provided fields will be patched.
    """

    overall_score: Optional[int] = Field(None, ge=0, le=100)
    technical_score: Optional[int] = Field(None, ge=0, le=100)
    communication_score: Optional[int] = Field(None, ge=0, le=100)
    problem_solving_score: Optional[int] = Field(None, ge=0, le=100)
    confidence_score: Optional[int] = Field(None, ge=0, le=100)
    behavioral_score: Optional[int] = Field(None, ge=0, le=100)
    coding_score: Optional[int] = Field(None, ge=0, le=100)
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    missed_topics: Optional[List[str]] = None
    strong_topics: Optional[List[str]] = None
    improvement_suggestions: Optional[List[str]] = None
    recommendation: Optional[str] = None
    hire_decision: Optional[str] = None
    difficulty_level: Optional[str] = None
    evaluation_summary: Optional[str] = None


class InterviewEvaluationResponse(InterviewEvaluationBase):
    """Schema for interview evaluation data returned to API clients."""

    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# API response schemas
# ---------------------------------------------------------------------------


class InterviewEvaluationSummary(BaseModel):
    """Concise summary of an interview evaluation."""

    session_id: str = Field(..., description="Session UUID")
    overall_score: int = Field(..., description="Overall score out of 100")
    grade: str = Field(..., description="Letter grade: A+, A, B+, B, C, D")
    hire_decision: str = Field(..., description="Hiring recommendation")
    strengths_count: int = Field(..., description="Number of strengths identified")
    weaknesses_count: int = Field(..., description="Number of weaknesses identified")


class InterviewEvaluationHistory(BaseModel):
    """Paginated history of interview evaluations."""

    evaluations: List[InterviewEvaluationResponse] = Field(
        ..., description="List of evaluations"
    )
    total: int = Field(..., description="Total number of evaluations")
    skip: int = Field(0, description="Number of records skipped")
    limit: int = Field(100, description="Page size")


class InterviewEvaluationAnalytics(BaseModel):
    """Aggregated analytics across multiple evaluations."""

    total_evaluations: int = Field(..., description="Total number of evaluations")
    average_overall_score: Optional[float] = Field(
        None, description="Average overall score"
    )
    average_technical_score: Optional[float] = Field(
        None, description="Average technical score"
    )
    average_communication_score: Optional[float] = Field(
        None, description="Average communication score"
    )
    average_problem_solving_score: Optional[float] = Field(
        None, description="Average problem-solving score"
    )
    average_confidence_score: Optional[float] = Field(
        None, description="Average confidence score"
    )
    average_behavioral_score: Optional[float] = Field(
        None, description="Average behavioral score"
    )
    average_coding_score: Optional[float] = Field(
        None, description="Average coding score"
    )
    most_common_weaknesses: List[str] = Field(
        default_factory=list, description="Most frequently identified weaknesses"
    )
    most_common_strengths: List[str] = Field(
        default_factory=list, description="Most frequently identified strengths"
    )


class InterviewEvaluationDashboard(BaseModel):
    """Full dashboard data for a user's interview performance."""

    latest_evaluation: Optional[InterviewEvaluationResponse] = Field(
        None, description="Most recent evaluation"
    )
    analytics: InterviewEvaluationAnalytics = Field(
        ..., description="Aggregated analytics"
    )
    recent_evaluations: List[InterviewEvaluationResponse] = Field(
        default_factory=list, description="Recent evaluations"
    )


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class InterviewEvaluationGenerateRequest(BaseModel):
    """Request body to trigger evaluation generation."""

    session_id: str = Field(..., description="Session UUID to evaluate")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def compute_grade(score: int) -> str:
    """Convert a numeric score (0-100) to a letter grade."""
    if score >= 95:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 75:
        return "B+"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    return "D"
