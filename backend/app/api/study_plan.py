"""API router for the Production Personalized Study Plan AI Agent.

Endpoints
---------
- ``POST /api/study-plan/generate`` — Generate a new study plan.
- ``GET /api/study-plan/{plan_id}`` — Get plan by ID.
- ``GET /api/study-plan/history`` — List plans for the user.
- ``GET /api/study-plan/progress`` — Get progress for a plan.
- ``GET /api/study-plan/dashboard`` — Dashboard with aggregated stats.
- ``PUT /api/study-plan/update`` — Update plan progress.
- ``DELETE /api/study-plan/{plan_id}`` — Delete a plan.
"""

import hashlib
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.study_plan_ai import (
    StudyPlanAIResponse,
    StudyPlanAICreate,
    StudyPlanAIUpdate,
    StudyPlanSummary,
    StudyPlanHistory,
    StudyPlanProgress,
    StudyPlanDashboard,
    StudyPlanGenerateRequest,
    StudyPlanProgressUpdateRequest,
)
from backend.app.crud.crud_study_plan_ai import study_plan_ai_crud
from backend.app.services.agents.study_plan_agent import (
    STUDY_PLAN_AGENT_DESCRIPTION,
    run_study_plan_agent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/study-plan", tags=["study-plan"])


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
# Generate
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=StudyPlanAIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new personalized study plan",
    description=STUDY_PLAN_AGENT_DESCRIPTION,
)
async def generate_study_plan(
    request: StudyPlanGenerateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Generate a new study plan using the AI agent."""
    if request.study_duration not in (7, 15, 30, 60):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="study_duration must be 7, 15, 30, or 60",
        )

    if request.evaluation_id:
        from backend.app.models.interview_evaluation import InterviewEvaluation

        evaluation = db.query(InterviewEvaluation).filter(
            InterviewEvaluation.id == request.evaluation_id,
            InterviewEvaluation.user_id == user_id,
        ).first()
        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evaluation {request.evaluation_id} not found",
            )

    plan = await run_study_plan_agent(
        db=db,
        user_id=user_id,
        evaluation_id=request.evaluation_id,
        target_role=request.target_role,
        target_company=request.target_company,
        study_duration=request.study_duration,
    )
    return plan


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


@router.get(
    "/{plan_id}",
    response_model=StudyPlanAIResponse,
    summary="Get study plan by ID",
)
def get_study_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return a specific study plan by its UUID."""
    plan = study_plan_ai_crud.get(db=db, id=plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan {plan_id} not found",
        )
    if plan.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this study plan",
        )
    return plan


@router.get(
    "/history/all",
    response_model=StudyPlanHistory,
    summary="List study plans for the current user",
)
def list_study_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return all study plans for the current user, newest first."""
    plans = study_plan_ai_crud.get_by_user(
        db=db, user_id=user_id, skip=skip, limit=limit
    )
    total = study_plan_ai_crud.count_by_user(db=db, user_id=user_id)
    return StudyPlanHistory(
        plans=[StudyPlanSummary(
            id=p.id,
            target_role=p.target_role,
            target_company=p.target_company,
            study_duration=p.study_duration,
            completion_percentage=p.completion_percentage,
            status=p.status,
            created_at=p.created_at,
            updated_at=p.updated_at,
        ) for p in plans],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/progress/{plan_id}",
    response_model=StudyPlanProgress,
    summary="Get progress for a study plan",
)
def get_study_plan_progress(
    plan_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return detailed progress for a specific study plan."""
    plan = study_plan_ai_crud.get(db=db, id=plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan {plan_id} not found",
        )
    if plan.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this study plan",
        )

    progress = study_plan_ai_crud.get_progress(db=db, plan_id=plan_id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress not available",
        )
    return StudyPlanProgress(**progress)


@router.get(
    "/dashboard/data",
    response_model=StudyPlanDashboard,
    summary="Get study plan dashboard data",
)
def get_study_plan_dashboard(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return dashboard data including active plan and statistics."""
    active = study_plan_ai_crud.get_active_by_user(db=db, user_id=user_id)
    recent = study_plan_ai_crud.get_by_user(db=db, user_id=user_id, limit=5)
    total = study_plan_ai_crud.count_by_user(db=db, user_id=user_id)
    avg_completion = study_plan_ai_crud.average_completion(
        db=db, user_id=user_id
    )
    by_status = study_plan_ai_crud.plans_by_status(db=db, user_id=user_id)

    return StudyPlanDashboard(
        active_plan=(
            StudyPlanSummary(
                id=active.id,
                target_role=active.target_role,
                target_company=active.target_company,
                study_duration=active.study_duration,
                completion_percentage=active.completion_percentage,
                status=active.status,
                created_at=active.created_at,
                updated_at=active.updated_at,
            )
            if active
            else None
        ),
        recent_plans=[
            StudyPlanSummary(
                id=p.id,
                target_role=p.target_role,
                target_company=p.target_company,
                study_duration=p.study_duration,
                completion_percentage=p.completion_percentage,
                status=p.status,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in recent
        ],
        total_plans=total,
        average_completion=avg_completion,
        plans_by_status=by_status,
    )


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@router.put(
    "/update/{plan_id}",
    response_model=StudyPlanAIResponse,
    summary="Update a study plan",
)
def update_study_plan(
    plan_id: str,
    update_data: StudyPlanAIUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Update a study plan's fields or progress."""
    plan = study_plan_ai_crud.get(db=db, id=plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan {plan_id} not found",
        )
    if plan.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this study plan",
        )

    updated = study_plan_ai_crud.update(db=db, db_obj=plan, obj_in=update_data)
    return updated


@router.put(
    "/progress/{plan_id}",
    response_model=StudyPlanProgress,
    summary="Update study plan progress",
)
def update_study_plan_progress(
    plan_id: str,
    progress_data: StudyPlanProgressUpdateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Update the completion percentage and status of a plan."""
    plan = study_plan_ai_crud.get(db=db, id=plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan {plan_id} not found",
        )
    if plan.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this study plan",
        )

    updated = study_plan_ai_crud.update_progress(
        db=db,
        plan_id=plan_id,
        completion_percentage=progress_data.completion_percentage,
        status=progress_data.status,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update progress",
        )

    progress = study_plan_ai_crud.get_progress(db=db, plan_id=plan_id)
    return StudyPlanProgress(**progress)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a study plan",
)
def delete_study_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Delete a specific study plan by its UUID."""
    plan = study_plan_ai_crud.get(db=db, id=plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan {plan_id} not found",
        )
    if plan.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this study plan",
        )
    study_plan_ai_crud.remove(db=db, id=plan_id)
