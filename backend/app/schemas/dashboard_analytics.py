"""Pydantic schemas for the Production Analytics Dashboard.

Layers of schema:
1. Domain-specific analytics (SkillAnalytics, InterviewAnalytics, etc.)
2. Aggregated wrappers (DashboardStatistics, DashboardSummary)
3. Top-level response (DashboardResponse)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Domain-specific analytics schemas
# ---------------------------------------------------------------------------


class ResumeAnalytics(BaseModel):
    """Resume upload and analysis summary."""

    resume_uploaded: bool = False
    resume_analysed: bool = False
    resume_count: int = 0
    ats_score: Optional[float] = None
    skills_count: int = 0
    missing_skills_count: int = 0
    strengths_count: int = 0
    weaknesses_count: int = 0
    last_analysed: Optional[datetime] = None


class ATSAnalytics(BaseModel):
    """ATS score history and keyword analysis."""

    current_score: Optional[float] = None
    previous_score: Optional[float] = None
    improvement: Optional[float] = None
    total_analyses: int = 0
    keyword_coverage: Optional[float] = None
    missing_keywords: List[str] = Field(default_factory=list)
    formatting_score: Optional[float] = None
    section_scores: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)


class InterviewAnalytics(BaseModel):
    """Interview session and turn analytics."""

    total_sessions: int = 0
    completed_sessions: int = 0
    average_score: Optional[float] = None
    best_score: Optional[int] = None
    worst_score: Optional[int] = None
    questions_answered: int = 0
    average_response_time: Optional[float] = None
    difficulty_distribution: Dict[str, int] = Field(default_factory=dict)
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    technical_percentage: Optional[float] = None
    hr_percentage: Optional[float] = None
    behavioural_percentage: Optional[float] = None
    coding_percentage: Optional[float] = None


class EvaluationAnalytics(BaseModel):
    """Evaluation-specific aggregated scores."""

    total_evaluations: int = 0
    average_overall_score: Optional[float] = None
    average_technical_score: Optional[float] = None
    average_communication_score: Optional[float] = None
    average_problem_solving_score: Optional[float] = None
    average_confidence_score: Optional[float] = None
    average_behavioral_score: Optional[float] = None
    average_coding_score: Optional[float] = None
    strongest_topics: List[str] = Field(default_factory=list)
    weakest_topics: List[str] = Field(default_factory=list)
    hire_decision_distribution: Dict[str, int] = Field(default_factory=dict)
    improvement_rate: Optional[float] = None


class StudyAnalytics(BaseModel):
    """Study plan progress and task tracking."""

    total_plans: int = 0
    active_plans: int = 0
    completed_plans: int = 0
    tasks_completed: int = 0
    tasks_pending: int = 0
    completion_percentage: Optional[float] = None
    coding_hours: Optional[float] = None
    learning_hours: Optional[float] = None
    practice_sessions: int = 0
    revision_sessions: int = 0


class SkillAnalytics(BaseModel):
    """Comprehensive skill analysis."""

    top_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    weak_skills: List[str] = Field(default_factory=list)
    strong_skills: List[str] = Field(default_factory=list)
    skill_coverage: Optional[float] = None
    skill_frequency: Dict[str, int] = Field(default_factory=dict)
    skill_improvement: Optional[float] = None


class TimelineAnalytics(BaseModel):
    """Timeline progress data."""

    daily: List[Dict[str, Any]] = Field(default_factory=list)
    weekly: List[Dict[str, Any]] = Field(default_factory=list)
    monthly: List[Dict[str, Any]] = Field(default_factory=list)


class ProgressAnalytics(BaseModel):
    """Overall progress tracking."""

    total_sessions: int = 0
    completed_sessions: int = 0
    average_ats_score: Optional[float] = None
    average_interview_score: Optional[float] = None
    average_evaluation_score: Optional[float] = None
    best_score: Optional[int] = None
    worst_score: Optional[int] = None
    improvement_rate: Optional[float] = None
    completed_study_tasks: int = 0
    pending_study_tasks: int = 0
    overall_readiness_score: Optional[int] = None


# ---------------------------------------------------------------------------
# Aggregated response schemas
# ---------------------------------------------------------------------------


class DashboardSummary(BaseModel):
    """Brief dashboard overview for header display."""

    resume_uploaded: bool = False
    resume_analysed: bool = False
    ats_score: Optional[float] = None
    total_sessions: int = 0
    completed_sessions: int = 0
    average_score: Optional[float] = None
    study_completion: Optional[float] = None
    overall_readiness_score: Optional[int] = None


class DashboardStatistics(BaseModel):
    """Full numeric statistics for the dashboard."""

    resume: ResumeAnalytics = Field(default_factory=ResumeAnalytics)
    ats: ATSAnalytics = Field(default_factory=ATSAnalytics)
    interview: InterviewAnalytics = Field(default_factory=InterviewAnalytics)
    evaluation: EvaluationAnalytics = Field(default_factory=EvaluationAnalytics)
    study: StudyAnalytics = Field(default_factory=StudyAnalytics)
    skills: SkillAnalytics = Field(default_factory=SkillAnalytics)
    progress: ProgressAnalytics = Field(default_factory=ProgressAnalytics)
    timeline: TimelineAnalytics = Field(default_factory=TimelineAnalytics)


class DashboardResponse(BaseModel):
    """Top-level dashboard response containing all analytics."""

    summary: DashboardSummary = Field(default_factory=DashboardSummary)
    statistics: DashboardStatistics = Field(default_factory=DashboardStatistics)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# CRUD persistence schemas
# ---------------------------------------------------------------------------


class DashboardAnalyticsBase(BaseModel):
    """Shared fields for dashboard analytics records."""

    resume_stats: Optional[Dict[str, Any]] = None
    ats_stats: Optional[Dict[str, Any]] = None
    interview_stats: Optional[Dict[str, Any]] = None
    evaluation_stats: Optional[Dict[str, Any]] = None
    study_stats: Optional[Dict[str, Any]] = None
    skill_stats: Optional[Dict[str, Any]] = None
    daily_activity: Optional[List[Dict[str, Any]]] = None
    weekly_activity: Optional[List[Dict[str, Any]]] = None
    monthly_activity: Optional[List[Dict[str, Any]]] = None
    total_sessions: int = 0
    average_ats_score: Optional[float] = None
    average_interview_score: Optional[float] = None
    average_evaluation_score: Optional[float] = None
    best_score: Optional[int] = None
    worst_score: Optional[int] = None
    improvement_rate: Optional[float] = None
    completed_study_tasks: int = 0
    pending_study_tasks: int = 0
    overall_readiness_score: Optional[int] = None


class DashboardAnalyticsCreate(DashboardAnalyticsBase):
    """Schema for creating a new dashboard analytics record."""

    user_id: str


class DashboardAnalyticsUpdate(BaseModel):
    """Schema for updating dashboard analytics.

    All fields are optional — only provided fields will be patched.
    """

    resume_stats: Optional[Dict[str, Any]] = None
    ats_stats: Optional[Dict[str, Any]] = None
    interview_stats: Optional[Dict[str, Any]] = None
    evaluation_stats: Optional[Dict[str, Any]] = None
    study_stats: Optional[Dict[str, Any]] = None
    skill_stats: Optional[Dict[str, Any]] = None
    daily_activity: Optional[List[Dict[str, Any]]] = None
    weekly_activity: Optional[List[Dict[str, Any]]] = None
    monthly_activity: Optional[List[Dict[str, Any]]] = None
    total_sessions: Optional[int] = None
    average_ats_score: Optional[float] = None
    average_interview_score: Optional[float] = None
    average_evaluation_score: Optional[float] = None
    best_score: Optional[int] = None
    worst_score: Optional[int] = None
    improvement_rate: Optional[float] = None
    completed_study_tasks: Optional[int] = None
    pending_study_tasks: Optional[int] = None
    overall_readiness_score: Optional[int] = None


class DashboardAnalyticsResponse(DashboardAnalyticsBase):
    """Schema for dashboard analytics data returned to API clients."""

    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
