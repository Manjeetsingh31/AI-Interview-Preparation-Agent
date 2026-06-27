"""Pydantic schemas for the Production Personalized Study Plan AI Agent.

Layers of schema:
1. ``StudyPlanOutput`` — ADK agent output schema (Gemini response_schema).
   Contains nested models for daily tasks, weekly goals, coding practice, etc.
2. ``StudyPlanAIBase/Create/Update/Response`` — CRUD persistence schemas.
3. ``StudyPlanSummary/History/Progress/Dashboard`` — API response wrappers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Nested schemas for the ADK output
# ---------------------------------------------------------------------------


class DailyTaskItem(BaseModel):
    """A single day's tasks within the study plan."""

    day: int = Field(..., description="Day number (1-indexed)")
    topic: str = Field(..., description="Main topic for the day")
    difficulty: str = Field(
        ..., description="Difficulty level: Beginner, Intermediate, Advanced"
    )
    estimated_time: str = Field(
        ..., description="Estimated time e.g. '2 hours', '3 hours'"
    )
    coding_task: str = Field(
        ..., description="Coding task or problem to solve"
    )
    reading_task: str = Field(
        ..., description="Reading or study material"
    )
    revision_task: str = Field(
        ..., description="Revision or recap task"
    )
    goal: str = Field(..., description="Daily learning goal")


class WeeklyTaskItem(BaseModel):
    """Weekly goals and milestones."""

    week: int = Field(..., description="Week number")
    focus_area: str = Field(..., description="Primary focus for the week")
    goals: List[str] = Field(
        default_factory=list, description="List of weekly goals"
    )
    mini_project: Optional[str] = Field(
        None, description="Mini project for the week"
    )
    mock_interviews: int = Field(
        0, description="Number of mock interviews this week"
    )


class CodingPracticeItem(BaseModel):
    """Coding practice recommendation."""

    topic: str = Field(..., description="Topic or area")
    platform: str = Field(
        ..., description="Platform: LeetCode, HackerRank, Codeforces, etc."
    )
    problems: List[str] = Field(
        default_factory=list, description="Recommended problems"
    )
    difficulty: str = Field(
        ..., description="Difficulty: Easy, Medium, Hard"
    )


class InterviewPracticeItem(BaseModel):
    """Interview practice recommendation."""

    topic: str = Field(..., description="Interview topic")
    questions: List[str] = Field(
        default_factory=list, description="Practice questions"
    )
    tips: List[str] = Field(
        default_factory=list, description="Tips for this area"
    )


class ProjectRecommendation(BaseModel):
    """Recommended project."""

    title: str = Field(..., description="Project title")
    description: str = Field(..., description="Project description")
    skills_covered: List[str] = Field(
        default_factory=list, description="Skills this project covers"
    )
    difficulty: str = Field(
        ..., description="Difficulty: Beginner, Intermediate, Advanced"
    )


class CertificationRecommendation(BaseModel):
    """Recommended certification."""

    name: str = Field(..., description="Certification name")
    provider: str = Field(
        ..., description="Provider: Google, Microsoft, AWS, etc."
    )
    description: str = Field(
        ..., description="Why this certification is recommended"
    )
    estimated_time: str = Field(
        ..., description="Estimated time to prepare"
    )


class ResourceRecommendation(BaseModel):
    """Recommended learning resource."""

    title: str = Field(..., description="Resource title")
    type: str = Field(
        ..., description="Type: Documentation, Book, Video, Course, Website"
    )
    url: Optional[str] = Field(None, description="URL (if applicable)")
    description: str = Field(..., description="Why this resource is useful")


# ---------------------------------------------------------------------------
# ADK Agent output schema (Gemini response_schema)
# ---------------------------------------------------------------------------


class StudyPlanOutput(BaseModel):
    """Top-level study plan result that Gemini returns.

    This schema is used as the ADK Agent's ``output_schema`` so that
    Gemini 2.5 Flash returns strictly typed JSON matching these fields.
    """

    target_role: str = Field(
        ..., description="Target job role for the plan"
    )
    target_company: Optional[str] = Field(
        None, description="Target company"
    )
    study_duration: int = Field(
        ..., description="Number of days: 7, 15, 30, or 60"
    )

    overview: str = Field(
        ..., description="Brief overview of the study plan"
    )
    weekly_focus: List[str] = Field(
        default_factory=list,
        description="Focus area for each week",
    )

    weak_topics: List[str] = Field(
        default_factory=list,
        description="Prioritized weak topics to focus on",
    )
    strong_topics: List[str] = Field(
        default_factory=list,
        description="Strong topics to build on",
    )

    daily_tasks: List[DailyTaskItem] = Field(
        default_factory=list,
        description="Day-by-day task breakdown",
    )
    weekly_tasks: List[WeeklyTaskItem] = Field(
        default_factory=list,
        description="Weekly goals and milestones",
    )

    coding_practice: List[CodingPracticeItem] = Field(
        default_factory=list,
        description="Coding practice recommendations",
    )
    interview_practice: List[InterviewPracticeItem] = Field(
        default_factory=list,
        description="Interview practice recommendations",
    )

    recommended_projects: List[ProjectRecommendation] = Field(
        default_factory=list,
        description="Recommended projects",
    )
    recommended_certifications: List[CertificationRecommendation] = Field(
        default_factory=list,
        description="Recommended certifications",
    )
    recommended_resources: List[ResourceRecommendation] = Field(
        default_factory=list,
        description="Recommended learning resources",
    )

    roadmap_summary: str = Field(
        ...,
        description="Full-text summary of the complete study roadmap",
    )


# ---------------------------------------------------------------------------
# CRUD schemas (follow existing project convention)
# ---------------------------------------------------------------------------


class StudyPlanAIBase(BaseModel):
    """Shared fields for study plan records."""

    evaluation_id: Optional[str] = Field(
        None, description="FK to interview evaluation"
    )
    resume_analysis_id: Optional[str] = Field(
        None, description="FK to ADK resume analysis"
    )
    target_role: str = Field(..., description="Target job role")
    target_company: Optional[str] = Field(None, description="Target company")
    study_duration: int = Field(..., description="Duration in days")

    roadmap: Optional[Dict[str, Any]] = Field(
        None, description="Full roadmap as dict"
    )
    daily_tasks: Optional[List[Dict[str, Any]]] = Field(
        None, description="Daily task list"
    )
    weekly_tasks: Optional[List[Dict[str, Any]]] = Field(
        None, description="Weekly task list"
    )

    weak_topics: Optional[List[str]] = Field(None)
    strong_topics: Optional[List[str]] = Field(None)

    coding_practice: Optional[List[Dict[str, Any]]] = Field(None)
    interview_practice: Optional[List[Dict[str, Any]]] = Field(None)

    recommended_projects: Optional[List[Dict[str, Any]]] = Field(None)
    recommended_certifications: Optional[List[Dict[str, Any]]] = Field(None)
    recommended_resources: Optional[List[Dict[str, Any]]] = Field(None)

    completion_percentage: Optional[float] = Field(0.0, ge=0.0, le=100.0)
    status: Optional[str] = Field("active")


class StudyPlanAICreate(StudyPlanAIBase):
    """Schema for creating a new study plan record."""

    user_id: str = Field(..., description="Owner's user UUID")


class StudyPlanAIUpdate(BaseModel):
    """Schema for updating an existing study plan.

    All fields are optional — only provided fields will be patched.
    """

    target_role: Optional[str] = None
    target_company: Optional[str] = None
    study_duration: Optional[int] = None
    roadmap: Optional[Dict[str, Any]] = None
    daily_tasks: Optional[List[Dict[str, Any]]] = None
    weekly_tasks: Optional[List[Dict[str, Any]]] = None
    weak_topics: Optional[List[str]] = None
    strong_topics: Optional[List[str]] = None
    coding_practice: Optional[List[Dict[str, Any]]] = None
    interview_practice: Optional[List[Dict[str, Any]]] = None
    recommended_projects: Optional[List[Dict[str, Any]]] = None
    recommended_certifications: Optional[List[Dict[str, Any]]] = None
    recommended_resources: Optional[List[Dict[str, Any]]] = None
    completion_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    status: Optional[str] = None


class StudyPlanAIResponse(StudyPlanAIBase):
    """Schema for study plan data returned to API clients."""

    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# API response schemas
# ---------------------------------------------------------------------------


class StudyPlanSummary(BaseModel):
    """Concise summary of a study plan for list views."""

    id: str
    target_role: str
    target_company: Optional[str]
    study_duration: int
    completion_percentage: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime]


class StudyPlanHistory(BaseModel):
    """Paginated study plan history."""

    plans: List[StudyPlanSummary]
    total: int
    skip: int = 0
    limit: int = 100


class StudyPlanProgress(BaseModel):
    """Detailed progress info for a study plan."""

    plan_id: str
    target_role: str
    completion_percentage: float
    status: str
    days_completed: int
    total_days: int
    daily_tasks_done: int
    daily_tasks_total: int

    progress_by_week: Optional[List[Dict[str, Any]]] = Field(
        None, description="Progress breakdown per week"
    )


class StudyPlanDashboard(BaseModel):
    """Dashboard-level aggregated data."""

    active_plan: Optional[StudyPlanSummary]
    recent_plans: List[StudyPlanSummary]
    total_plans: int
    average_completion: float
    plans_by_status: Dict[str, int]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class StudyPlanGenerateRequest(BaseModel):
    """Request body to generate a study plan."""

    evaluation_id: Optional[str] = Field(
        None, description="Evaluation UUID to base the plan on"
    )
    target_role: Optional[str] = Field(
        None, description="Override target role"
    )
    target_company: Optional[str] = Field(
        None, description="Override target company"
    )
    study_duration: int = Field(
        30, description="Duration: 7, 15, 30, or 60 days"
    )


class StudyPlanProgressUpdateRequest(BaseModel):
    """Request body to update study plan progress."""

    completion_percentage: float = Field(
        ..., ge=0.0, le=100.0, description="New completion percentage"
    )
    status: Optional[str] = Field(None, description="New status")
