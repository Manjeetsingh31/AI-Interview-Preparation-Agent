"""Pydantic schemas for the Interview Turn Multi-Agent System.

Layers of schema:
1. ``InterviewAgentTurn`` — ADK agent output schema (Gemini response_schema).
2. ``InterviewTurnBase/Create/Update/Response`` — CRUD persistence schemas.
3. ``InterviewTurnHistory/Conversation/SessionSummary`` — API response wrappers.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# ADK Agent output schema (Gemini response_schema)
# ---------------------------------------------------------------------------


class InterviewAgentTurn(BaseModel):
    """A single turn response from the Interview Agent.

    Returned by Gemini for every interaction — initial question, follow-up,
    or final transcript.
    """

    question: str = Field(
        ..., description="The interview question to ask the candidate"
    )
    follow_up: str = Field(
        "",
        description=(
            "Follow-up question probing deeper. Empty on the first turn "
            "or when no follow-up is needed."
        ),
    )
    category: str = Field(
        ...,
        description=(
            "Question category: HR, Technical, Coding, Behavioral"
        ),
    )
    difficulty: str = Field(
        ..., description="Current difficulty level: Easy, Medium, Hard"
    )
    evaluation: str = Field(
        "",
        description=(
            "Quality assessment of the candidate's previous answer. "
            "Empty on the first turn."
        ),
    )
    score: int = Field(
        0, ge=0, le=100,
        description="Score out of 100 for the previous answer. 0 on first turn.",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Keyword tags for this question",
    )
    expected_answer: str = Field(
        "",
        description="Expected or ideal answer for this question",
    )
    is_final: bool = Field(
        False,
        description="True when the interview is complete (all questions asked)",
    )
    finished_reason: str = Field(
        "",
        description="Reason for finishing when is_final is True",
    )
    transcript_summary: str = Field(
        "",
        description="Full interview transcript summary when is_final is True",
    )


# ---------------------------------------------------------------------------
# CRUD schemas (follow existing project convention)
# ---------------------------------------------------------------------------


class InterviewTurnBase(BaseModel):
    """Shared fields for interview turn records."""

    session_id: str = Field(..., description="FK to the interview session")
    resume_analysis_id: Optional[str] = Field(
        None, description="FK to the ADK resume analysis"
    )
    question_number: int = Field(..., description="Sequential question number")
    question: str = Field(..., description="The interview question text")
    candidate_answer: Optional[str] = Field(
        None, description="The candidate's answer text"
    )
    follow_up: Optional[str] = Field(
        None, description="Follow-up question asked"
    )
    difficulty: str = Field(
        ..., description="Difficulty level: Easy, Medium, Hard"
    )
    category: str = Field(
        ..., description="Category: HR, Technical, Coding, Behavioral"
    )
    tags: Optional[List[str]] = Field(None, description="Keyword tags")
    expected_answer: Optional[str] = Field(
        None, description="Expected or ideal answer"
    )
    evaluation: Optional[str] = Field(
        None, description="AI evaluation of the answer"
    )
    score: Optional[int] = Field(
        None, ge=0, le=100, description="Score out of 100"
    )
    response_time: Optional[int] = Field(
        None, description="Response time in seconds"
    )


class InterviewTurnCreate(InterviewTurnBase):
    """Schema for creating a new interview turn record."""

    user_id: str = Field(..., description="Owner's user UUID")


class InterviewTurnUpdate(BaseModel):
    """Schema for updating an interview turn (e.g. adding answer + evaluation).

    All fields are optional — only provided fields will be patched.
    """

    candidate_answer: Optional[str] = None
    follow_up: Optional[str] = None
    evaluation: Optional[str] = None
    score: Optional[int] = Field(None, ge=0, le=100)
    response_time: Optional[int] = None


class InterviewTurnResponse(InterviewTurnBase):
    """Schema for interview turn data returned to API clients."""

    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# API response schemas
# ---------------------------------------------------------------------------


class InterviewTurnHistory(BaseModel):
    """Paginated history of interview turns."""

    turns: List[InterviewTurnResponse] = Field(
        ..., description="List of interview turns"
    )
    total: int = Field(..., description="Total number of turns")
    skip: int = Field(0, description="Number of records skipped")
    limit: int = Field(100, description="Page size")


class InterviewTurnConversation(BaseModel):
    """Full conversation for a single session."""

    session_id: str = Field(..., description="Session UUID")
    turns: List[InterviewTurnResponse] = Field(
        ..., description="All turns in the session"
    )


class InterviewSessionSummary(BaseModel):
    """Aggregated summary of a completed interview session."""

    session_id: str = Field(..., description="Session UUID")
    status: str = Field(..., description="Session status")
    total_questions: int = Field(..., description="Number of questions asked")
    average_score: Optional[float] = Field(
        None, description="Average score across all answered questions"
    )
    transcript_summary: str = Field(
        "", description="Summary of the entire interview conversation"
    )


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class InterviewStartRequest(BaseModel):
    """Request body to start a new interview session."""

    resume_analysis_id: str = Field(
        ..., description="ID of the ADK resume analysis to base questions on"
    )
    company: str = Field(
        ..., max_length=255, description="Target company"
    )
    role: str = Field(
        ..., max_length=255, description="Target role / job title"
    )
    interview_type: str = Field(
        ...,
        description="Interview type: HR, Technical, Coding, Behavioral, or Mixed",
    )
    difficulty: str = Field(
        ..., description="Starting difficulty: Easy, Medium, or Hard"
    )
    number_of_questions: int = Field(
        10, ge=1, le=50,
        description="Total number of questions for this interview",
    )


class InterviewAnswerRequest(BaseModel):
    """Request body to submit an answer and get the next question."""

    session_id: str = Field(..., description="Session UUID")
    answer: str = Field(..., description="The candidate's answer text")
    response_time: Optional[int] = Field(
        None, description="Time taken to answer in seconds",
    )
    total_questions: Optional[int] = Field(
        None, ge=1, le=50, description="Total questions configured for this session",
    )


class InterviewEndRequest(BaseModel):
    """Request body to end an interview session."""

    session_id: str = Field(..., description="Session UUID")


class InterviewStartResponse(BaseModel):
    """Response after starting an interview."""

    session_id: str = Field(..., description="Session UUID")
    question: str = Field(..., description="First question")
    question_number: int = Field(1, description="Question number")
    category: str = Field(..., description="Question category")
    difficulty: str = Field(..., description="Current difficulty")


class InterviewAnswerResponse(BaseModel):
    """Response after submitting an answer."""

    session_id: str = Field(..., description="Session UUID")
    question_number: int = Field(..., description="Current question number")
    question: str = Field(..., description="Next question")
    follow_up: Optional[str] = Field(
        None, description="Follow-up question"
    )
    category: str = Field(..., description="Question category")
    difficulty: str = Field(..., description="Current difficulty")
    tags: List[str] = Field(
        default_factory=list, description="Keyword tags"
    )
    evaluation: Optional[str] = Field(
        None, description="Evaluation of previous answer"
    )
    score: Optional[int] = Field(
        None, ge=0, le=100, description="Score for previous answer"
    )
    is_final: bool = Field(
        False, description="True if this was the last question"
    )
    finished_reason: str = Field(
        "",
        description="Reason for finishing when is_final is True",
    )
    transcript_summary: str = Field(
        "",
        description="Full transcript when is_final is True",
    )
