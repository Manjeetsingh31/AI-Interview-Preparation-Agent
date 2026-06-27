"""ATS Scoring Engine API router.

Provides three endpoints for ATS (Applicant Tracking System) scoring:

- ``POST /api/ats/analyze`` — Run ATS scoring on an existing ADK resume
  analysis.  The agent consumes the structured JSON already produced by
  the Resume Analysis Agent (never raw PDFs or text).
- ``GET  /api/ats/{id}`` — Retrieve a single ATS score by its ID.
- ``GET  /api/ats/history`` — List all ATS scores for the authenticated user.

Architecture
------------
::

    Client  ──POST──►  FastAPI Route  ──►  ADK ATS Agent  ──►  Gemini 2.5 Flash
                           │                        │
                           ▼                        ▼
                     Database (ResumeADK)    Structured AtsOutput
                           │
                           ▼
                     Database (AtsScore)
                           │
                           ▼
                     JSON Response

Every step is logged: request receipt, database lookups, Gemini request &
response, database save, and any errors.
"""

import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.models.resume_analysis_adk import ResumeAnalysisADK
from backend.app.schemas.ats_score import (
    AtsOutput,
    AtsScoreCreate,
    AtsScoreResponse,
    AtsAnalyzeRequest,
)
from backend.app.crud.crud_ats_score import ats_score_crud as crud
from backend.app.services.agents.ats_agent import (
    AtsScoringAgent,
    AtsScoringError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ats", tags=["ats"])

# --- Singleton service instances -------------------------------------------
_agent = AtsScoringAgent()


# --- Auth dependency (mirrors main.py logic) --------------------------------
def _get_current_user_id(db: Session = Depends(get_db)) -> str:
    """Return the ID of the default mock user.

    Uses the same logic as ``main.py``: if the mock user does not exist
    yet, it is created on the fly.
    """
    user = db.query(User).filter(User.email == "candidate@example.com").first()
    if not user:
        user = User(
            email="candidate@example.com",
            password_hash=hashlib.sha256(b"password123").hexdigest(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created default mock user: id=%s", user.id)
    return user.id


# --- Endpoints --------------------------------------------------------------


@router.post(
    "/analyze",
    response_model=AtsScoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run ATS scoring on a resume analysis",
    description=(
        "Takes the ID of an existing ADK resume analysis and runs the ATS "
        "Scoring Engine (powered by Gemini 2.5 Flash) on its structured data. "
        "Returns section scores, job match percentages, skill gap analysis, "
        "and improvement suggestions."
    ),
)
async def analyze_ats(
    request: AtsAnalyzeRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
) -> AtsScoreResponse:
    """Run ATS scoring on a previously analysed resume.

    Args:
        request: Contains the ``resume_analysis_adk_id`` to score.
        db: Database session (injected by FastAPI).
        user_id: Authenticated user ID (injected by auth dependency).

    Returns:
        ``AtsScoreResponse`` with the full scoring breakdown.

    Raises:
        HTTPException 404: Resume analysis not found.
        HTTPException 400: Resume analysis has no extracted data.
        HTTPException 500: Agent failure or database error.
    """
    logger.info(
        "ATS Started — user=%s, resume_analysis_adk_id=%s",
        user_id,
        request.resume_analysis_adk_id,
    )

    # --- Step 1: Load the ADK resume analysis --------------------------------
    adk_record = db.query(ResumeAnalysisADK).filter(
        ResumeAnalysisADK.id == request.resume_analysis_adk_id
    ).first()

    if not adk_record:
        logger.error("Resume analysis not found: id=%s", request.resume_analysis_adk_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume analysis {request.resume_analysis_adk_id} not found.",
        )

    if not adk_record.extracted_json:
        logger.error("Resume analysis has no extracted data: id=%s", request.resume_analysis_adk_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume analysis has no extracted JSON data. Run analysis first.",
        )

    logger.info(
        "Resume Received — file=%s, user_id=%s",
        adk_record.resume_filename,
        user_id,
    )

    # --- Step 2: Run ATS scoring via ADK agent ------------------------------
    try:
        ats_result: AtsOutput = await _agent.analyze(adk_record.extracted_json)
    except AtsScoringError as exc:
        logger.error("ATS Agent failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ATS scoring failed: {exc}",
        ) from exc

    logger.info("ATS scoring complete — overall_score=%d", ats_result.overall_score)

    # --- Step 3: Build section_scores dict -----------------------------------
    section_scores = {
        "contact_information": ats_result.contact_info_score.model_dump(),
        "professional_summary": ats_result.professional_summary_score.model_dump(),
        "education": ats_result.education_section_score.model_dump(),
        "experience": ats_result.experience_section_score.model_dump(),
        "projects": ats_result.projects_section_score.model_dump(),
        "technical_skills": ats_result.technical_skills_section_score.model_dump(),
        "soft_skills": ats_result.soft_skills_section_score.model_dump(),
        "certifications": ats_result.certifications_section_score.model_dump(),
        "languages": ats_result.languages_section_score.model_dump(),
        "achievements": ats_result.achievements_section_score.model_dump(),
        "overall_formatting": ats_result.overall_formatting_section_score.model_dump(),
    }

    # --- Step 4: Build job_match dict ----------------------------------------
    job_match = {
        "Python Developer": ats_result.python_developer_match,
        "Backend Developer": ats_result.backend_developer_match,
        "AI Engineer": ats_result.ai_engineer_match,
        "Machine Learning Engineer": ats_result.machine_learning_engineer_match,
        "Data Analyst": ats_result.data_analyst_match,
        "Software Engineer": ats_result.software_engineer_match,
        "Full Stack Developer": ats_result.full_stack_developer_match,
    }

    # --- Step 5: Save to database --------------------------------------------
    try:
        obj_in = AtsScoreCreate(
            user_id=user_id,
            resume_analysis_adk_id=request.resume_analysis_adk_id,
            overall_score=ats_result.overall_score,
            section_scores=section_scores,
            job_match=job_match,
            strengths=ats_result.strengths,
            weaknesses=ats_result.weaknesses,
            missing_technical_skills=ats_result.missing_technical_skills,
            missing_soft_skills=ats_result.missing_soft_skills,
            missing_keywords=ats_result.missing_keywords,
            resume_structure_score=ats_result.resume_structure_score,
            grammar_score=ats_result.grammar_score,
            project_quality_score=ats_result.project_quality_score,
            education_score=ats_result.education_score,
            experience_score=ats_result.experience_score,
            certification_score=ats_result.certification_score,
            skill_gap_analysis=ats_result.skill_gap_analysis.model_dump(),
            improvement_suggestions=ats_result.improvement_suggestions,
        )
        db_obj = crud.create(db=db, obj_in=obj_in)
        logger.info(
            "Database save complete — id=%s, overall_score=%d",
            db_obj.id,
            ats_result.overall_score,
        )
    except Exception as exc:
        logger.error("Database save failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save ATS score to the database.",
        ) from exc

    # --- Step 6: Return structured response ----------------------------------
    return AtsScoreResponse(
        id=db_obj.id,
        user_id=db_obj.user_id,
        resume_analysis_adk_id=db_obj.resume_analysis_adk_id,
        overall_score=db_obj.overall_score,
        section_scores=db_obj.section_scores,
        job_match=db_obj.job_match,
        strengths=db_obj.strengths,
        weaknesses=db_obj.weaknesses,
        missing_technical_skills=db_obj.missing_technical_skills,
        missing_soft_skills=db_obj.missing_soft_skills,
        missing_keywords=db_obj.missing_keywords,
        resume_structure_score=db_obj.resume_structure_score,
        grammar_score=db_obj.grammar_score,
        project_quality_score=db_obj.project_quality_score,
        education_score=db_obj.education_score,
        experience_score=db_obj.experience_score,
        certification_score=db_obj.certification_score,
        skill_gap_analysis=db_obj.skill_gap_analysis,
        improvement_suggestions=db_obj.improvement_suggestions,
        created_at=db_obj.created_at,
    )


@router.get(
    "/history",
    response_model=list[AtsScoreResponse],
    summary="List ATS score history",
    description="Return all ATS scoring results for the authenticated user, "
    "ordered by most recent first.",
)
def get_ats_history(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
    skip: int = 0,
    limit: int = 100,
) -> list:
    """Return all ATS scores for the current user, newest first.

    Args:
        db: Database session (injected by FastAPI).
        user_id: Authenticated user ID (injected by auth dependency).
        skip: Number of records to skip (offset).
        limit: Maximum records to return.

    Returns:
        A list of ``AtsScoreResponse`` objects.
    """
    scores = crud.get_by_user(db=db, user_id=user_id, skip=skip, limit=limit)
    return [
        AtsScoreResponse(
            id=s.id,
            user_id=s.user_id,
            resume_analysis_adk_id=s.resume_analysis_adk_id,
            overall_score=s.overall_score,
            section_scores=s.section_scores,
            job_match=s.job_match,
            strengths=s.strengths,
            weaknesses=s.weaknesses,
            missing_technical_skills=s.missing_technical_skills,
            missing_soft_skills=s.missing_soft_skills,
            missing_keywords=s.missing_keywords,
            resume_structure_score=s.resume_structure_score,
            grammar_score=s.grammar_score,
            project_quality_score=s.project_quality_score,
            education_score=s.education_score,
            experience_score=s.experience_score,
            certification_score=s.certification_score,
            skill_gap_analysis=s.skill_gap_analysis,
            improvement_suggestions=s.improvement_suggestions,
            created_at=s.created_at,
        )
        for s in scores
    ]


@router.get(
    "/{id}",
    response_model=AtsScoreResponse,
    summary="Retrieve a single ATS score",
    description="Fetch a complete ATS scoring result by its unique ID.",
)
def get_ats_score(
    id: str,
    db: Session = Depends(get_db),
) -> AtsScoreResponse:
    """Retrieve a single ATS scoring result by ID.

    Args:
        id: The ATS score UUID.
        db: Database session (injected by FastAPI).

    Returns:
        ``AtsScoreResponse`` with the full scoring breakdown.

    Raises:
        HTTPException 404: Score not found.
    """
    db_obj = crud.get(db=db, id=id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ATS score {id} not found.",
        )
    return AtsScoreResponse(
        id=db_obj.id,
        user_id=db_obj.user_id,
        resume_analysis_adk_id=db_obj.resume_analysis_adk_id,
        overall_score=db_obj.overall_score,
        section_scores=db_obj.section_scores,
        job_match=db_obj.job_match,
        strengths=db_obj.strengths,
        weaknesses=db_obj.weaknesses,
        missing_technical_skills=db_obj.missing_technical_skills,
        missing_soft_skills=db_obj.missing_soft_skills,
        missing_keywords=db_obj.missing_keywords,
        resume_structure_score=db_obj.resume_structure_score,
        grammar_score=db_obj.grammar_score,
        project_quality_score=db_obj.project_quality_score,
        education_score=db_obj.education_score,
        experience_score=db_obj.experience_score,
        certification_score=db_obj.certification_score,
        skill_gap_analysis=db_obj.skill_gap_analysis,
        improvement_suggestions=db_obj.improvement_suggestions,
        created_at=db_obj.created_at,
    )
