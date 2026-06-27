"""API router for the Production AI Evaluation & Feedback Agent.

Endpoints
---------
- ``POST /evaluate`` — Generate an evaluation for a completed session.
- ``GET /evaluations/session/{session_id}`` — Get evaluation by session.
- ``GET /evaluations/{evaluation_id}`` — Get evaluation by ID.
- ``GET /evaluations`` — List evaluations for the current user.
- ``GET /evaluations/statistics`` — Aggregated evaluation statistics.
- ``DELETE /evaluations/{evaluation_id}`` — Delete an evaluation.
"""

import hashlib
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.interview_evaluation import (
    InterviewEvaluationAnalytics,
    InterviewEvaluationDashboard,
    InterviewEvaluationGenerateRequest,
    InterviewEvaluationResponse,
)
from backend.app.crud.crud_interview_evaluation import interview_evaluation_crud
from backend.app.crud.crud_interview_session import interview_session_crud
from backend.app.services.agents.evaluation_agent import (
    EVALUATION_AGENT_DESCRIPTION,
    run_evaluation_agent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["evaluations"])


def _get_current_user_id(db: Session = Depends(get_db)) -> str:
    """Mock auth: returns the default user's ID."""
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


# ---------------------------------------------------------------------------
# Generate evaluation
# ---------------------------------------------------------------------------


@router.post(
    "/evaluate",
    response_model=InterviewEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate evaluation for a completed session",
    description=(
        f"{EVALUATION_AGENT_DESCRIPTION} "
        "The session must be in 'completed' status."
    ),
)
async def evaluate_session(
    request: InterviewEvaluationGenerateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Run the AI Evaluation Agent and persist the result."""
    session = interview_session_crud.get(db=db, id=request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found",
        )
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session",
        )
    if session.status not in ("completed", "closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Session status is '{session.status}'. "
                "Only completed sessions can be evaluated."
            ),
        )

    existing = interview_evaluation_crud.get_by_session(
        db=db, session_id=request.session_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session already has an evaluation",
        )

    evaluation = await run_evaluation_agent(
        db=db,
        session_id=request.session_id,
        user_id=user_id,
    )
    return evaluation


# ---------------------------------------------------------------------------
# Read (fixed paths before parameterized paths for correct routing)
# ---------------------------------------------------------------------------


@router.get(
    "/evaluations/session/{session_id}",
    response_model=InterviewEvaluationResponse,
    summary="Get evaluation by session ID",
)
def get_evaluation_by_session(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return the evaluation for a specific interview session."""
    evaluation = interview_evaluation_crud.get_by_session(
        db=db, session_id=session_id
    )
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No evaluation found for session {session_id}",
        )
    if evaluation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this evaluation",
        )
    return evaluation


@router.get(
    "/evaluations",
    response_model=List[InterviewEvaluationResponse],
    summary="List evaluations for the current user",
)
def list_evaluations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return all evaluations for the current user, newest first."""
    return interview_evaluation_crud.get_by_user(
        db=db, user_id=user_id, skip=skip, limit=limit
    )


@router.get(
    "/evaluations/search",
    response_model=List[InterviewEvaluationResponse],
    summary="Search evaluations by text",
)
def search_evaluations(
    q: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Search evaluations by evaluation summary or recommendation text."""
    return interview_evaluation_crud.search(
        db=db, user_id=user_id, query=q, skip=skip, limit=limit
    )


@router.get(
    "/evaluations/statistics",
    response_model=InterviewEvaluationAnalytics,
    summary="Get aggregated evaluation statistics",
)
def get_evaluation_statistics(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return aggregated statistics across all evaluations for the user."""
    stats = interview_evaluation_crud.statistics(db=db, user_id=user_id)
    return InterviewEvaluationAnalytics(**stats)


@router.get(
    "/evaluations/dashboard",
    response_model=InterviewEvaluationDashboard,
    summary="Get evaluation dashboard data",
)
def get_evaluation_dashboard(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return dashboard data including latest evaluation and analytics."""
    latest = interview_evaluation_crud.get_latest_by_user(
        db=db, user_id=user_id
    )
    recent = interview_evaluation_crud.get_by_user(
        db=db, user_id=user_id, limit=5
    )
    stats = interview_evaluation_crud.statistics(db=db, user_id=user_id)

    return InterviewEvaluationDashboard(
        latest_evaluation=(
            InterviewEvaluationResponse.model_validate(latest)
            if latest
            else None
        ),
        analytics=InterviewEvaluationAnalytics(**stats),
        recent_evaluations=[
            InterviewEvaluationResponse.model_validate(e) for e in recent
        ],
    )


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=InterviewEvaluationResponse,
    summary="Get evaluation by ID",
)
def get_evaluation_by_id(
    evaluation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return a specific evaluation by its UUID."""
    evaluation = interview_evaluation_crud.get(db=db, id=evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found",
        )
    if evaluation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this evaluation",
        )
    return evaluation


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@router.delete(
    "/evaluations/{evaluation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an evaluation",
)
def delete_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Delete a specific evaluation by its UUID."""
    evaluation = interview_evaluation_crud.get(db=db, id=evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found",
        )
    if evaluation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this evaluation",
        )
    interview_evaluation_crud.remove(db=db, id=evaluation_id)
