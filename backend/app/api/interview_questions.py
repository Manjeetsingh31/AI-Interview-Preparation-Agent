"""Interview Question Generator API router.

Provides the endpoint:

- ``POST /api/interview/questions/generate`` — Generate personalised interview
  questions based on an ADK resume analysis, target company, role, interview
  type, and difficulty level. Each question is persisted to the database and
  returned in the response.

Architecture
------------
::

    Client  ──POST──►  FastAPI Route  ──►  ADK Agent  ──►  Gemini 2.5 Flash
                           │                        │
                           ▼                        ▼
                     Database (ResumeADK)     Structured QuestionList
                           │
                           ▼
                     Database (InterviewQuestion × N)
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
from backend.app.schemas.interview_question import (
    InterviewQuestionCreate,
    InterviewQuestionGenerateRequest,
    InterviewQuestionGenerateResponse,
    InterviewQuestionItem,
    InterviewQuestionList,
    InterviewQuestionResponse,
)
from backend.app.crud.crud_interview_question import interview_question as crud
from backend.app.services.agents.interview_question_agent import (
    InterviewQuestionAgent,
    InterviewQuestionError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview/questions", tags=["interview"])

# --- Singleton service instances -------------------------------------------
_agent = InterviewQuestionAgent()


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
    "/generate",
    response_model=InterviewQuestionGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate personalised interview questions",
    description=(
        "Generate interview questions tailored to the candidate's resume, "
        "target company, role, interview type, and difficulty level. "
        "Uses the Google ADK Interview Question Agent powered by Gemini 2.5 Flash. "
        "All generated questions are persisted to the database."
    ),
)
async def generate_questions(
    request: InterviewQuestionGenerateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
) -> InterviewQuestionGenerateResponse:
    """Generate interview questions from a resume analysis.

    Args:
        request: Contains the resume analysis ID, company, role,
            interview type, difficulty, and number of questions.
        db: Database session (injected by FastAPI).
        user_id: Authenticated user ID (injected by auth dependency).

    Returns:
        ``InterviewQuestionGenerateResponse`` with the list of generated questions.

    Raises:
        HTTPException 404: Resume analysis not found.
        HTTPException 400: Resume analysis has no extracted data.
        HTTPException 500: Agent failure or database error.
    """
    logger.info(
        "Generation Started — user=%s, resume_analysis_id=%s, "
        "company=%s, role=%s, type=%s, difficulty=%s, n=%d",
        user_id,
        request.resume_analysis_id,
        request.company,
        request.role,
        request.interview_type,
        request.difficulty,
        request.number_of_questions,
    )

    # --- Step 1: Load the ADK resume analysis --------------------------------
    adk_record = db.query(ResumeAnalysisADK).filter(
        ResumeAnalysisADK.id == request.resume_analysis_id
    ).first()

    if not adk_record:
        logger.error(
            "Resume analysis not found: id=%s", request.resume_analysis_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume analysis {request.resume_analysis_id} not found.",
        )

    if not adk_record.extracted_json:
        logger.error(
            "Resume analysis has no extracted data: id=%s",
            request.resume_analysis_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Resume analysis has no extracted JSON data. "
                "Run analysis first."
            ),
        )

    logger.info(
        "Resume Loaded — file=%s, user_id=%s",
        adk_record.resume_filename,
        user_id,
    )

    # --- Step 2: Generate questions via ADK agent ---------------------------
    try:
        question_list: InterviewQuestionList = await _agent.generate(
            resume_data=adk_record.extracted_json,
            company=request.company,
            role=request.role,
            interview_type=request.interview_type,
            difficulty=request.difficulty,
            number_of_questions=request.number_of_questions,
        )
    except InterviewQuestionError as exc:
        logger.error("Interview Question Agent failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question generation failed: {exc}",
        ) from exc

    logger.info(
        "Generation complete — %d questions generated",
        len(question_list.questions),
    )

    # --- Step 3: Save each question to the database -------------------------
    try:
        create_schemas = [
            InterviewQuestionCreate(
                user_id=user_id,
                resume_analysis_id=request.resume_analysis_id,
                company=request.company,
                role=request.role,
                interview_type=request.interview_type,
                difficulty=request.difficulty,
                question_type=q.type,
                question=q.question,
                expected_answer=q.expected_answer,
                hints=q.hints,
                follow_up=q.follow_up if q.follow_up else None,
                tags=q.tags,
            )
            for q in question_list.questions
        ]
        db_objs = crud.create_in_bulk(db=db, questions_data=create_schemas)
        logger.info(
            "Database save complete — %d questions saved", len(db_objs)
        )
    except Exception as exc:
        logger.error("Database save failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save questions to the database.",
        ) from exc

    # --- Step 4: Return structured response ----------------------------------
    return InterviewQuestionGenerateResponse(
        questions=[
            InterviewQuestionResponse(
                id=q.id,
                user_id=q.user_id,
                resume_analysis_id=q.resume_analysis_id,
                company=q.company,
                role=q.role,
                interview_type=q.interview_type,
                difficulty=q.difficulty,
                question_type=q.question_type,
                question=q.question,
                expected_answer=q.expected_answer,
                hints=q.hints,
                follow_up=q.follow_up,
                tags=q.tags,
                created_at=q.created_at,
            )
            for q in db_objs
        ]
    )


@router.get(
    "/history",
    response_model=list[InterviewQuestionResponse],
    summary="List generated question history",
    description=(
        "Return all previously generated interview questions for the "
        "authenticated user, ordered by most recent first."
    ),
)
def get_question_history(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
    skip: int = 0,
    limit: int = 100,
) -> list:
    """Return all generated questions for the current user, newest first.

    Args:
        db: Database session (injected by FastAPI).
        user_id: Authenticated user ID (injected by auth dependency).
        skip: Number of records to skip (offset).
        limit: Maximum records to return.

    Returns:
        A list of ``InterviewQuestionResponse`` objects.
    """
    questions = crud.get_by_user(
        db=db, user_id=user_id, skip=skip, limit=limit
    )
    return [
        InterviewQuestionResponse(
            id=q.id,
            user_id=q.user_id,
            resume_analysis_id=q.resume_analysis_id,
            company=q.company,
            role=q.role,
            interview_type=q.interview_type,
            difficulty=q.difficulty,
            question_type=q.question_type,
            question=q.question,
            expected_answer=q.expected_answer,
            hints=q.hints,
            follow_up=q.follow_up,
            tags=q.tags,
            created_at=q.created_at,
        )
        for q in questions
    ]


@router.get(
    "/by-analysis/{resume_analysis_id}",
    response_model=list[InterviewQuestionResponse],
    summary="List questions for a specific resume analysis",
    description=(
        "Return all generated questions tied to a given resume analysis ID."
    ),
)
def get_questions_by_analysis(
    resume_analysis_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
) -> list:
    """Return all questions generated for a specific resume analysis.

    Args:
        resume_analysis_id: The ADK resume analysis UUID.
        db: Database session (injected by FastAPI).
        user_id: Authenticated user ID (injected by auth dependency).

    Returns:
        A list of ``InterviewQuestionResponse`` objects.

    Raises:
        HTTPException 404: No questions found for this analysis.
    """
    questions = crud.get_by_user_and_analysis(
        db=db,
        user_id=user_id,
        resume_analysis_id=resume_analysis_id,
    )
    if not questions:
        return []
    return [
        InterviewQuestionResponse(
            id=q.id,
            user_id=q.user_id,
            resume_analysis_id=q.resume_analysis_id,
            company=q.company,
            role=q.role,
            interview_type=q.interview_type,
            difficulty=q.difficulty,
            question_type=q.question_type,
            question=q.question,
            expected_answer=q.expected_answer,
            hints=q.hints,
            follow_up=q.follow_up,
            tags=q.tags,
            created_at=q.created_at,
        )
        for q in questions
    ]
