"""Pydantic schemas for the ATS Scoring Engine.

Three layers of schema:
1. ``SectionScoreDetail`` / ``SkillGapAnalysis`` — nested models for the
   structured Gemini output.
2. ``AtsOutput`` — top-level schema that Gemini is instructed to return.
   This is passed as ``output_schema`` to the ADK Agent.
3. ``AtsScoreCreate`` / ``AtsScoreResponse`` — database persistence schemas
   following the project convention.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Nested schemas for the structured Gemini output
# ---------------------------------------------------------------------------


class SectionScoreDetail(BaseModel):
    """Score, rationale, and recommendation for a single resume section."""

    score: int = Field(
        ..., ge=0, le=100, description="Section score out of 100"
    )
    reason: str = Field(
        ..., description="Explanation of why this score was assigned"
    )
    recommendation: str = Field(
        ..., description="Actionable advice to improve this section"
    )


class SkillGapAnalysis(BaseModel):
    """Categorised skill gaps identified in the resume."""

    missing_technologies: List[str] = Field(
        default_factory=list,
        description="Missing technologies (e.g. Docker, Kubernetes, Git)",
    )
    missing_programming_languages: List[str] = Field(
        default_factory=list,
        description="Missing programming languages (e.g. Python, Java, Go)",
    )
    missing_frameworks: List[str] = Field(
        default_factory=list,
        description="Missing frameworks (e.g. FastAPI, Django, React)",
    )
    missing_cloud_skills: List[str] = Field(
        default_factory=list,
        description="Missing cloud skills (e.g. AWS, GCP, Azure)",
    )
    missing_devops_skills: List[str] = Field(
        default_factory=list,
        description="Missing DevOps skills (e.g. CI/CD, Terraform, Jenkins)",
    )
    missing_databases: List[str] = Field(
        default_factory=list,
        description="Missing databases (e.g. PostgreSQL, MongoDB, Redis)",
    )
    missing_soft_skills: List[str] = Field(
        default_factory=list,
        description="Missing soft skills (e.g. Leadership, Communication)",
    )


# ---------------------------------------------------------------------------
# ADK Agent output schema
# ---------------------------------------------------------------------------


class AtsOutput(BaseModel):
    """Top-level ATS scoring result that Gemini returns.

    This schema is used as the ADK Agent's ``output_schema`` so that
    Gemini 2.5 Flash returns strictly typed JSON matching these fields.
    """

    overall_score: int = Field(
        ..., ge=0, le=100, description="Composite ATS score out of 100"
    )

    # ---- Section-wise scores ----
    contact_info_score: SectionScoreDetail = Field(
        ..., description="Contact Information section evaluation"
    )
    professional_summary_score: SectionScoreDetail = Field(
        ..., description="Professional Summary section evaluation"
    )
    education_section_score: SectionScoreDetail = Field(
        ..., description="Education section evaluation"
    )
    experience_section_score: SectionScoreDetail = Field(
        ..., description="Experience section evaluation"
    )
    projects_section_score: SectionScoreDetail = Field(
        ..., description="Projects section evaluation"
    )
    technical_skills_section_score: SectionScoreDetail = Field(
        ..., description="Technical Skills section evaluation"
    )
    soft_skills_section_score: SectionScoreDetail = Field(
        ..., description="Soft Skills section evaluation"
    )
    certifications_section_score: SectionScoreDetail = Field(
        ..., description="Certifications section evaluation"
    )
    languages_section_score: SectionScoreDetail = Field(
        ..., description="Languages section evaluation"
    )
    achievements_section_score: SectionScoreDetail = Field(
        ..., description="Achievements section evaluation"
    )
    overall_formatting_section_score: SectionScoreDetail = Field(
        ..., description="Overall Formatting evaluation"
    )

    # ---- Resume strengths & weaknesses ----
    strengths: List[str] = Field(
        default_factory=list,
        description="Identified resume strengths",
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="Identified resume weaknesses",
    )

    # ---- Missing skills & keywords ----
    missing_technical_skills: List[str] = Field(
        default_factory=list,
        description="Technical skills the resume should have",
    )
    missing_soft_skills: List[str] = Field(
        default_factory=list,
        description="Soft skills the resume should have",
    )
    missing_keywords: List[str] = Field(
        default_factory=list,
        description="ATS keywords missing from the resume",
    )

    # ---- Component scores ----
    resume_structure_score: int = Field(
        ..., ge=0, le=100, description="Resume structure quality score"
    )
    grammar_score: int = Field(
        ..., ge=0, le=100, description="Grammar and readability score"
    )
    project_quality_score: int = Field(
        ..., ge=0, le=100, description="Project quality assessment score"
    )
    education_score: int = Field(
        ..., ge=0, le=100, description="Education relevance score"
    )
    experience_score: int = Field(
        ..., ge=0, le=100, description="Work experience quality score"
    )
    certification_score: int = Field(
        ..., ge=0, le=100, description="Certification relevance score"
    )

    # ---- Job match percentages ----
    python_developer_match: int = Field(
        ..., ge=0, le=100, description="Match % for Python Developer role"
    )
    backend_developer_match: int = Field(
        ..., ge=0, le=100, description="Match % for Backend Developer role"
    )
    ai_engineer_match: int = Field(
        ..., ge=0, le=100, description="Match % for AI Engineer role"
    )
    machine_learning_engineer_match: int = Field(
        ..., ge=0, le=100,
        description="Match % for Machine Learning Engineer role",
    )
    data_analyst_match: int = Field(
        ..., ge=0, le=100, description="Match % for Data Analyst role"
    )
    software_engineer_match: int = Field(
        ..., ge=0, le=100, description="Match % for Software Engineer role"
    )
    full_stack_developer_match: int = Field(
        ..., ge=0, le=100,
        description="Match % for Full Stack Developer role",
    )

    # ---- Skill gap & improvement ----
    skill_gap_analysis: SkillGapAnalysis = Field(
        ..., description="Categorised skill gap analysis"
    )
    improvement_suggestions: List[str] = Field(
        default_factory=list,
        description="Actionable resume improvement suggestions",
    )


# ---------------------------------------------------------------------------
# CRUD schemas (follow existing project convention)
# ---------------------------------------------------------------------------


class AtsScoreBase(BaseModel):
    """Shared fields for ATS score records."""

    resume_analysis_adk_id: str = Field(..., description="FK to the ADK resume analysis")
    overall_score: int = Field(..., ge=0, le=100)
    section_scores: Optional[dict] = Field(None)
    job_match: Optional[dict] = Field(None)
    strengths: Optional[List[str]] = Field(None)
    weaknesses: Optional[List[str]] = Field(None)
    missing_technical_skills: Optional[List[str]] = Field(None)
    missing_soft_skills: Optional[List[str]] = Field(None)
    missing_keywords: Optional[List[str]] = Field(None)
    resume_structure_score: Optional[int] = Field(None, ge=0, le=100)
    grammar_score: Optional[int] = Field(None, ge=0, le=100)
    project_quality_score: Optional[int] = Field(None, ge=0, le=100)
    education_score: Optional[int] = Field(None, ge=0, le=100)
    experience_score: Optional[int] = Field(None, ge=0, le=100)
    certification_score: Optional[int] = Field(None, ge=0, le=100)
    skill_gap_analysis: Optional[dict] = Field(None)
    improvement_suggestions: Optional[List[str]] = Field(None)


class AtsScoreCreate(AtsScoreBase):
    """Schema for creating a new ATS score record."""

    user_id: str


class AtsScoreUpdate(BaseModel):
    """Schema for updating an existing ATS score record.

    All fields are optional — only provided fields will be patched.
    """

    overall_score: Optional[int] = Field(None, ge=0, le=100)
    section_scores: Optional[dict] = None
    job_match: Optional[dict] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    missing_technical_skills: Optional[List[str]] = None
    missing_soft_skills: Optional[List[str]] = None
    missing_keywords: Optional[List[str]] = None
    resume_structure_score: Optional[int] = Field(None, ge=0, le=100)
    grammar_score: Optional[int] = Field(None, ge=0, le=100)
    project_quality_score: Optional[int] = Field(None, ge=0, le=100)
    education_score: Optional[int] = Field(None, ge=0, le=100)
    experience_score: Optional[int] = Field(None, ge=0, le=100)
    certification_score: Optional[int] = Field(None, ge=0, le=100)
    skill_gap_analysis: Optional[dict] = None
    improvement_suggestions: Optional[List[str]] = None


class AtsScoreResponse(AtsScoreBase):
    """Schema for ATS score data returned to API clients."""

    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AtsAnalyzeRequest(BaseModel):
    """Request body for triggering an ATS evaluation on an existing analysis."""

    resume_analysis_adk_id: str = Field(
        ..., description="ID of the ADK resume analysis to score"
    )
