"""Pydantic schemas for the ADK Resume Analysis Agent.

Three layers of schema:
1. ``Education`` / ``Experience`` / ``Project`` — nested models for the
   structured Gemini output.
2. ``ResumeData`` — top-level schema that Gemini is instructed to return.
   This is passed as ``output_schema`` to the ADK Agent.
3. ``ResumeAnalysisADKCreate`` / ``ResumeAnalysisADKResponse`` — database
   persistence schemas following the project convention.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Nested schemas for the structured Gemini response
# ---------------------------------------------------------------------------


class Education(BaseModel):
    """A single education entry extracted from the resume."""

    institution: str = Field("", description="School or university name")
    degree: str = Field("", description="Degree obtained, e.g. BSc, MSc")
    field: str = Field("", description="Field of study, e.g. Computer Science")
    start_date: str = Field("", description="Start date (free text, e.g. Sep 2018)")
    end_date: str = Field("", description="End date (free text, e.g. Jun 2022)")


class Experience(BaseModel):
    """A single work experience entry extracted from the resume."""

    company: str = Field("", description="Company or organisation name")
    role: str = Field("", description="Job title")
    start_date: str = Field("", description="Start date (free text)")
    end_date: str = Field("", description="End date or 'Present'")
    description: str = Field("", description="Overview of responsibilities")
    highlights: List[str] = Field(default_factory=list, description="Key achievements")


class Project(BaseModel):
    """A project entry extracted from the resume."""

    name: str = Field("", description="Project name")
    description: str = Field("", description="Brief description")
    technologies: List[str] = Field(default_factory=list, description="Tech stack used")
    link: str = Field("", description="Project URL (GitHub, live demo, etc.)")


class ResumeData(BaseModel):
    """Top-level structured resume data that Gemini returns.

    This schema is used as the ADK Agent's ``output_schema`` so that
    Gemini 2.5 Flash returns strictly typed JSON matching these fields.
    """

    full_name: str = Field("", description="Candidate's full name")
    email: str = Field("", description="Email address")
    phone: str = Field("", description="Phone number")
    linkedin: str = Field("", description="LinkedIn profile URL")
    github: str = Field("", description="GitHub profile URL")
    portfolio: str = Field("", description="Portfolio or personal website URL")
    skills: List[str] = Field(default_factory=list, description="All skills mentioned")
    technical_skills: List[str] = Field(
        default_factory=list, description="Technical / hard skills"
    )
    soft_skills: List[str] = Field(
        default_factory=list, description="Soft / interpersonal skills"
    )
    education: List[Education] = Field(
        default_factory=list, description="Education history"
    )
    experience: List[Experience] = Field(
        default_factory=list, description="Work experience"
    )
    projects: List[Project] = Field(
        default_factory=list, description="Notable projects"
    )
    certifications: List[str] = Field(
        default_factory=list, description="Professional certifications"
    )
    languages: List[str] = Field(
        default_factory=list, description="Languages spoken"
    )


# ---------------------------------------------------------------------------
# CRUD schemas (follow existing project convention)
# ---------------------------------------------------------------------------


class ResumeAnalysisADKBase(BaseModel):
    """Shared fields for ADK resume analysis records."""

    resume_filename: str = Field(..., max_length=255)
    raw_text: Optional[str] = Field(None)
    extracted_json: Optional[dict] = Field(None)


class ResumeAnalysisADKCreate(ResumeAnalysisADKBase):
    """Schema for creating a new ADK resume analysis record."""

    user_id: str


class ResumeAnalysisADKUpdate(BaseModel):
    """Schema for updating an existing ADK resume analysis record.

    All fields are optional — only provided fields will be patched.
    """

    resume_filename: Optional[str] = Field(None, max_length=255)
    raw_text: Optional[str] = None
    extracted_json: Optional[dict] = None


class ResumeAnalysisADKResponse(ResumeAnalysisADKBase):
    """Schema for ADK resume analysis data returned to API clients."""

    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
