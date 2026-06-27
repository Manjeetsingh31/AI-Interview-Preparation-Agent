"""API router for the Production Analytics Dashboard.

Endpoints
---------
- ``GET /api/dashboard`` — Full dashboard (all analytics).
- ``GET /api/dashboard/summary`` — Brief summary for header display.
- ``GET /api/dashboard/statistics`` — All numeric statistics.
- ``GET /api/dashboard/interview`` — Interview-specific analytics.
- ``GET /api/dashboard/ats`` — ATS-specific analytics.
- ``GET /api/dashboard/study`` — Study plan analytics.
- ``GET /api/dashboard/skills`` — Skill analytics.
- ``GET /api/dashboard/timeline`` — Timeline activity data.
- ``GET /api/dashboard/readiness`` — Readiness score breakdown.
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.dashboard_analytics import (
    DashboardResponse,
    DashboardSummary,
    DashboardStatistics,
)
from backend.app.services.dashboard_service import (
    DASHBOARD_SERVICE_DESCRIPTION,
    generate_dashboard,
)
from backend.app.crud.crud_dashboard_analytics import (
    dashboard_analytics_crud,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


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
# Full dashboard
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Get full dashboard analytics",
    description=DASHBOARD_SERVICE_DESCRIPTION,
)
async def get_dashboard(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Generate and return the complete dashboard with all analytics."""
    logger.info("GET /api/dashboard for user %s", user_id)
    try:
        result = await generate_dashboard(db, user_id)
        logger.info("Dashboard returned for user %s", user_id)
        return result
    except Exception as e:
        logger.error("Dashboard generation failed for user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard generation failed: {e}",
        )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get dashboard summary",
)
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return a brief dashboard overview for header display."""
    result = await generate_dashboard(db, user_id)
    return result.summary


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


@router.get(
    "/statistics",
    response_model=DashboardStatistics,
    summary="Get all dashboard statistics",
)
async def get_dashboard_statistics(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return all numeric and categorical statistics."""
    result = await generate_dashboard(db, user_id)
    return result.statistics


# ---------------------------------------------------------------------------
# Interview analytics
# ---------------------------------------------------------------------------


@router.get(
    "/interview",
    response_model=Dict[str, Any],
    summary="Get interview analytics",
)
async def get_interview_analytics(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return interview-specific analytics."""
    result = await generate_dashboard(db, user_id)
    return result.statistics.interview.model_dump()


# ---------------------------------------------------------------------------
# ATS analytics
# ---------------------------------------------------------------------------


@router.get(
    "/ats",
    response_model=Dict[str, Any],
    summary="Get ATS analytics",
)
async def get_ats_analytics(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return ATS-specific analytics."""
    result = await generate_dashboard(db, user_id)
    return result.statistics.ats.model_dump()


# ---------------------------------------------------------------------------
# Study analytics
# ---------------------------------------------------------------------------


@router.get(
    "/study",
    response_model=Dict[str, Any],
    summary="Get study plan analytics",
)
async def get_study_analytics(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return study plan analytics."""
    result = await generate_dashboard(db, user_id)
    return result.statistics.study.model_dump()


# ---------------------------------------------------------------------------
# Skills analytics
# ---------------------------------------------------------------------------


@router.get(
    "/skills",
    response_model=Dict[str, Any],
    summary="Get skill analytics",
)
async def get_skill_analytics(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return comprehensive skill analytics."""
    result = await generate_dashboard(db, user_id)
    return result.statistics.skills.model_dump()


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


@router.get(
    "/timeline",
    response_model=Dict[str, Any],
    summary="Get timeline activity data",
)
async def get_timeline_analytics(
    period: Optional[str] = Query(
        None, description="Filter: daily, weekly, monthly"
    ),
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return timeline activity (daily / weekly / monthly)."""
    result = await generate_dashboard(db, user_id)
    timeline = result.statistics.timeline
    if period == "daily":
        return {"daily": timeline.daily}
    elif period == "weekly":
        return {"weekly": timeline.weekly}
    elif period == "monthly":
        return {"monthly": timeline.monthly}
    return timeline.model_dump()


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------


@router.get(
    "/readiness",
    response_model=Dict[str, Any],
    summary="Get readiness score breakdown",
)
async def get_readiness_score(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    """Return overall readiness score with per-pillar breakdown."""
    result = await generate_dashboard(db, user_id)
    readiness = result.summary.overall_readiness_score

    from backend.app.services.dashboard_service import _readiness_contributions

    breakdown = _readiness_contributions(result)

    return {
        "overall_readiness_score": readiness,
        "breakdown": breakdown,
        "formula": (
            "readiness = (resume * 0.15) + (ats * 0.20) + "
            "(interview * 0.25) + (evaluation * 0.25) + (study * 0.15)"
        ),
    }
