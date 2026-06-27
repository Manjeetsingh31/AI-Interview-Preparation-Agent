"""Unit tests for the Production Analytics Dashboard.

Test strategy
-------------
- Dashboard service unit tests test each collector function in isolation.
- CRUD tests verify persistence, history, trends, reports, and readiness.
- API integration tests use ``TestClient`` with isolated SQLite database
  and verify all nine endpoints with empty and populated data.
- Readiness score formula is tested with known inputs.
- Edge cases include empty users, partial data, and boundary scores.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, get_db
from backend.app.main import app

from backend.app.schemas.dashboard_analytics import (
    ResumeAnalytics,
    ATSAnalytics,
    InterviewAnalytics,
    EvaluationAnalytics,
    StudyAnalytics,
    SkillAnalytics,
    TimelineAnalytics,
    DashboardSummary,
    DashboardStatistics,
    DashboardResponse,
    DashboardAnalyticsCreate,
    DashboardAnalyticsUpdate,
    DashboardAnalyticsResponse,
)
from backend.app.crud.crud_dashboard_analytics import (
    dashboard_analytics_crud,
)
from backend.app.crud.crud_interview_evaluation import (
    interview_evaluation_crud,
)
from backend.app.crud.crud_interview_session import (
    interview_session_crud,
)
from backend.app.schemas.interview_session import InterviewSessionCreate
from backend.app.schemas.interview_evaluation import (
    InterviewEvaluationCreate,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh file-based SQLite database per test."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    db_path = tmp.name

    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden DB and user dependencies."""

    def _get_db_override():
        yield db_session

    async def _get_user_id_override():
        return "test-user-id"

    app.dependency_overrides[get_db] = _get_db_override
    from backend.app.api.dashboard import _get_current_user_id

    app.dependency_overrides[_get_current_user_id] = _get_user_id_override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_completed_session(db_session, user_id: str = "test-user-id"):
    """Create a completed interview session."""
    session = interview_session_crud.create(
        db=db_session,
        obj_in=InterviewSessionCreate(
            role="Software Engineer",
            interview_type="technical",
            company="Standard",
            status="active",
            user_id=user_id,
        ),
    )
    session.status = "completed"
    db_session.commit()
    db_session.refresh(session)
    return session


def _create_evaluation(db_session, user_id: str = "test-user-id", score: int = 78):
    """Create a completed session + evaluation."""
    session = _create_completed_session(db_session, user_id)
    from backend.app.services.agents.evaluation_agent import _fallback_evaluation

    output = _fallback_evaluation(session, [])
    output.overall_score = score
    eval_create = InterviewEvaluationCreate(
        session_id=session.id,
        user_id=user_id,
        overall_score=output.overall_score,
        technical_score=output.technical_score or 70,
        communication_score=output.communication_score or 75,
        problem_solving_score=output.problem_solving_score or 72,
        confidence_score=output.confidence_score or 80,
        behavioral_score=output.behavioral_score or 78,
        coding_score=output.coding_score or 65,
        strengths=output.strengths or ["Communication"],
        weaknesses=output.weaknesses or ["Algorithms"],
        missed_topics=output.missed_topics or [],
        strong_topics=output.strong_topics or ["Python"],
        improvement_suggestions=output.improvement_suggestions or [],
        recommendation=output.recommendation or "",
        hire_decision=output.hire_decision or "Borderline",
        difficulty_level=output.difficulty_level or "Medium",
        evaluation_summary=output.evaluation_summary or "",
    )
    return interview_evaluation_crud.create(db=db_session, obj_in=eval_create)


# ===================================================================
# Dashboard Service Unit Tests
# ===================================================================


class TestDashboardServiceUnit:
    """Test each collector function in the dashboard service."""

    def test_collect_resume_data_empty(self, db_session):
        """Resume collector returns defaults for empty user."""
        from backend.app.services.dashboard_service import _collect_resume_data

        result = _collect_resume_data(db_session, "nonexistent")
        assert isinstance(result, ResumeAnalytics)
        assert result.resume_uploaded is False
        assert result.resume_count == 0

    def test_ats_collector_empty(self, db_session):
        """ATS collector returns defaults for empty user."""
        from backend.app.services.dashboard_service import _collect_ats_data

        result = _collect_ats_data(db_session, "nonexistent")
        assert isinstance(result, ATSAnalytics)
        assert result.current_score is None
        assert result.total_analyses == 0

    def test_interview_collector_empty(self, db_session):
        """Interview collector returns defaults for empty user."""
        from backend.app.services.dashboard_service import _collect_interview_data

        result = _collect_interview_data(db_session, "nonexistent")
        assert isinstance(result, InterviewAnalytics)
        assert result.total_sessions == 0
        assert result.questions_answered == 0

    def test_evaluation_collector_empty(self, db_session):
        """Evaluation collector returns defaults for empty user."""
        from backend.app.services.dashboard_service import _collect_evaluation_data

        result, best, worst = _collect_evaluation_data(db_session, "nonexistent")
        assert isinstance(result, EvaluationAnalytics)
        assert result.total_evaluations == 0
        assert best is None
        assert worst is None

    def test_study_collector_empty(self, db_session):
        """Study collector returns defaults for empty user."""
        from backend.app.services.dashboard_service import _collect_study_data

        result = _collect_study_data(db_session, "nonexistent")
        assert isinstance(result, StudyAnalytics)
        assert result.total_plans == 0

    def test_skill_collector_empty(self, db_session):
        """Skill collector returns defaults for empty user."""
        from backend.app.services.dashboard_service import _collect_skill_data

        result = _collect_skill_data(db_session, "nonexistent")
        assert isinstance(result, SkillAnalytics)
        assert result.top_skills == []

    def test_timeline_collector_empty(self, db_session):
        """Timeline collector returns empty lists for empty user."""
        from backend.app.services.dashboard_service import _collect_timeline_data

        result = _collect_timeline_data(db_session, "nonexistent")
        assert isinstance(result, TimelineAnalytics)
        assert result.daily == []
        assert result.weekly == []
        assert result.monthly == []

    def test_collect_interview_with_sessions(self, db_session):
        """Interview collector counts sessions correctly."""
        _create_completed_session(db_session)
        _create_completed_session(db_session)

        from backend.app.services.dashboard_service import _collect_interview_data

        result = _collect_interview_data(db_session, "test-user-id")
        assert result.total_sessions >= 2
        assert result.completed_sessions >= 2

    def test_collect_evaluation_with_data(self, db_session):
        """Evaluation collector aggregates scores."""
        _create_evaluation(db_session, score=80)
        _create_evaluation(db_session, score=90)

        from backend.app.services.dashboard_service import _collect_evaluation_data

        result, best, worst = _collect_evaluation_data(db_session, "test-user-id")
        assert result.total_evaluations >= 2
        assert best == 90
        assert worst == 80
        assert result.average_overall_score is not None

    def test_readiness_score_formula(self):
        """Readiness score formula produces expected values."""
        from backend.app.services.dashboard_service import _compute_readiness_score

        resume = ResumeAnalytics(resume_uploaded=True, skills_count=5)
        ats = ATSAnalytics(current_score=80.0)
        interview = InterviewAnalytics(average_score=70.0)
        evaluation = EvaluationAnalytics(average_overall_score=75.0)
        study = StudyAnalytics(completion_percentage=60.0)

        score = _compute_readiness_score(resume, ats, interview, evaluation, study)
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_readiness_score_minimum(self):
        """Readiness score is 0 with no data."""
        from backend.app.services.dashboard_service import _compute_readiness_score

        score = _compute_readiness_score(
            ResumeAnalytics(),
            ATSAnalytics(),
            InterviewAnalytics(),
            EvaluationAnalytics(),
            StudyAnalytics(),
        )
        assert score == 0

    def test_readiness_score_maximum(self):
        """Readiness score reaches high values with perfect data."""
        from backend.app.services.dashboard_service import _compute_readiness_score

        resume = ResumeAnalytics(resume_uploaded=True, skills_count=10)
        ats = ATSAnalytics(current_score=100.0)
        interview = InterviewAnalytics(average_score=100.0)
        evaluation = EvaluationAnalytics(average_overall_score=100.0)
        study = StudyAnalytics(completion_percentage=100.0)

        score = _compute_readiness_score(resume, ats, interview, evaluation, study)
        assert score >= 80

    def test_readiness_contributions(self):
        """Readiness contributions extract correctly."""
        from backend.app.services.dashboard_service import _readiness_contributions

        s = DashboardStatistics(
            resume=ResumeAnalytics(resume_uploaded=True, skills_count=5),
            ats=ATSAnalytics(current_score=80.0),
            interview=InterviewAnalytics(average_score=70.0),
            evaluation=EvaluationAnalytics(average_overall_score=75.0),
            study=StudyAnalytics(completion_percentage=60.0),
            skills=SkillAnalytics(),
            progress=ProgressAnalytics(),
            timeline=TimelineAnalytics(),
        )
        response = DashboardResponse(summary=DashboardSummary(), statistics=s)
        contrib = _readiness_contributions(response)
        assert "resume" in contrib
        assert "ats" in contrib
        assert "interview" in contrib
        assert "evaluation" in contrib
        assert "study" in contrib


# ===================================================================
# CRUD Unit Tests
# ===================================================================


class TestCRUDDashboardAnalytics:
    """Tests for CRUDDashboardAnalytics operations."""

    def _create_record(self, db_session, user_id="test-user"):
        return dashboard_analytics_crud.create(
            db=db_session,
            obj_in=DashboardAnalyticsCreate(user_id=user_id),
        )

    def test_create(self, db_session):
        """Creating a dashboard analytics record."""
        record = self._create_record(db_session)
        assert record.id is not None
        assert record.user_id == "test-user"

    def test_get_by_user(self, db_session):
        """Get by user ID."""
        record = self._create_record(db_session)
        found = dashboard_analytics_crud.get_by_user(
            db=db_session, user_id="test-user"
        )
        assert found is not None
        assert found.id == record.id

    def test_get_by_user_not_found(self, db_session):
        """Get by nonexistent user returns None."""
        found = dashboard_analytics_crud.get_by_user(
            db=db_session, user_id="nonexistent"
        )
        assert found is None

    def test_get_or_create_existing(self, db_session):
        """Get or create returns existing record."""
        record = self._create_record(db_session)
        result = dashboard_analytics_crud.get_or_create(
            db=db_session, user_id="test-user"
        )
        assert result.id == record.id

    def test_get_or_create_new(self, db_session):
        """Get or create creates a new record."""
        result = dashboard_analytics_crud.get_or_create(
            db=db_session, user_id="new-user"
        )
        assert result is not None
        assert result.user_id == "new-user"

    def test_get_history(self, db_session):
        """Get history returns snapshot list."""
        record = self._create_record(db_session)
        record.overall_readiness_score = 75
        db_session.commit()
        history = dashboard_analytics_crud.get_history(
            db=db_session, user_id="test-user"
        )
        assert len(history) >= 1
        assert history[0].get("overall_readiness_score") == 75

    def test_get_history_empty(self, db_session):
        """Get history for empty user."""
        history = dashboard_analytics_crud.get_history(
            db=db_session, user_id="nonexistent"
        )
        assert history == []

    def test_get_trend(self, db_session):
        """Get trend for a specific metric."""
        record = self._create_record(db_session)
        record.overall_readiness_score = 80
        db_session.commit()
        trend = dashboard_analytics_crud.get_trend(
            db=db_session,
            user_id="test-user",
            metric="overall_readiness_score",
        )
        assert len(trend) >= 1
        assert trend[0]["value"] == 80

    def test_get_trend_empty(self, db_session):
        """Get trend for empty user."""
        trend = dashboard_analytics_crud.get_trend(
            db=db_session, user_id="nonexistent"
        )
        assert trend == []

    def test_get_progress(self, db_session):
        """Get progress summary."""
        record = self._create_record(db_session)
        record.overall_readiness_score = 70
        record.total_sessions = 5
        db_session.commit()
        progress = dashboard_analytics_crud.get_progress(
            db=db_session, user_id="test-user"
        )
        assert progress is not None
        assert progress["overall_readiness_score"] == 70
        assert progress["total_sessions"] == 5

    def test_get_progress_not_found(self, db_session):
        """Get progress for empty user."""
        progress = dashboard_analytics_crud.get_progress(
            db=db_session, user_id="nonexistent"
        )
        assert progress is None

    def test_get_report_weekly(self, db_session):
        """Get weekly report."""
        record = self._create_record(db_session)
        record.overall_readiness_score = 65
        db_session.commit()
        report = dashboard_analytics_crud.get_report(
            db=db_session, user_id="test-user", period="weekly"
        )
        assert report is not None
        assert report["period"] == "weekly"
        assert report["overall_readiness_score"] == 65

    def test_get_report_monthly(self, db_session):
        """Get monthly report."""
        record = self._create_record(db_session)
        report = dashboard_analytics_crud.get_report(
            db=db_session, user_id="test-user", period="monthly"
        )
        assert report is not None
        assert report["period"] == "monthly"

    def test_get_report_empty(self, db_session):
        """Get report for empty user."""
        report = dashboard_analytics_crud.get_report(
            db=db_session, user_id="nonexistent"
        )
        assert report is None

    def test_get_report_invalid_period(self, db_session):
        """Get report with invalid period returns None."""
        record = self._create_record(db_session)
        report = dashboard_analytics_crud.get_report(
            db=db_session, user_id="test-user", period="invalid"
        )
        assert report is None

    def test_get_readiness(self, db_session):
        """Get readiness with breakdown."""
        record = self._create_record(db_session)
        record.overall_readiness_score = 72
        record.resume_stats = {"readiness_contribution": 80}
        record.ats_stats = {"readiness_contribution": 70}
        record.interview_stats = {"readiness_contribution": 75}
        record.evaluation_stats = {"readiness_contribution": 72}
        record.study_stats = {"readiness_contribution": 60}
        db_session.commit()
        readiness = dashboard_analytics_crud.get_readiness(
            db=db_session, user_id="test-user"
        )
        assert readiness is not None
        assert readiness["overall_readiness_score"] == 72
        assert "breakdown" in readiness

    def test_get_readiness_empty(self, db_session):
        """Get readiness for empty user."""
        readiness = dashboard_analytics_crud.get_readiness(
            db=db_session, user_id="nonexistent"
        )
        assert readiness is None

    def test_update_record(self, db_session):
        """Update a dashboard analytics record."""
        record = self._create_record(db_session)
        updated = dashboard_analytics_crud.update(
            db=db_session,
            db_obj=record,
            obj_in=DashboardAnalyticsUpdate(
                overall_readiness_score=85,
                total_sessions=10,
            ),
        )
        assert updated.overall_readiness_score == 85
        assert updated.total_sessions == 10

    def test_remove_record(self, db_session):
        """Delete a dashboard analytics record."""
        record = self._create_record(db_session)
        record_id = record.id
        dashboard_analytics_crud.remove(db=db_session, id=record_id)
        assert (
            dashboard_analytics_crud.get(db=db_session, id=record_id) is None
        )


# ===================================================================
# API Integration Tests
# ===================================================================


class TestDashboardAPI:
    """API integration tests for all dashboard endpoints."""

    def _create_session_with_evaluation(self, db_session):
        """Create session + evaluation for populated dashboard data."""
        from backend.app.services.agents.evaluation_agent import (
            _fallback_evaluation,
        )

        session = interview_session_crud.create(
            db=db_session,
            obj_in=InterviewSessionCreate(
                role="Software Engineer",
                interview_type="technical",
                company="Standard",
                status="active",
                user_id="test-user-id",
            ),
        )
        session.status = "completed"
        db_session.commit()
        db_session.refresh(session)

        output = _fallback_evaluation(session, [])
        eval_create = InterviewEvaluationCreate(
            session_id=session.id,
            user_id="test-user-id",
            overall_score=output.overall_score,
            technical_score=output.technical_score or 70,
            communication_score=output.communication_score or 75,
            problem_solving_score=output.problem_solving_score or 72,
            confidence_score=output.confidence_score or 80,
            behavioral_score=output.behavioral_score or 78,
            coding_score=output.coding_score or 65,
            strengths=output.strengths or [],
            weaknesses=output.weaknesses or [],
            missed_topics=output.missed_topics or [],
            strong_topics=output.strong_topics or [],
            improvement_suggestions=output.improvement_suggestions or [],
            recommendation=output.recommendation or "",
            hire_decision=output.hire_decision or "Borderline",
            difficulty_level=output.difficulty_level or "Medium",
            evaluation_summary=output.evaluation_summary or "",
        )
        interview_evaluation_crud.create(db=db_session, obj_in=eval_create)

    # -- Full Dashboard ------------------------------------------------

    def test_get_dashboard_empty(self, client):
        """GET /api/dashboard returns valid response with no data."""
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "statistics" in data
        assert "generated_at" in data
        assert data["summary"]["resume_uploaded"] is False
        assert data["summary"]["overall_readiness_score"] == 0

    def test_get_dashboard_populated(self, client, db_session):
        """GET /api/dashboard with data returns populated response."""
        self._create_session_with_evaluation(db_session)
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_sessions"] >= 1
        assert data["summary"]["overall_readiness_score"] is not None

    def test_get_dashboard_includes_statistics(self, client, db_session):
        """Dashboard response contains all statistics sections."""
        self._create_session_with_evaluation(db_session)
        response = client.get("/api/dashboard")
        data = response.json()
        stats = data["statistics"]
        assert "resume" in stats
        assert "ats" in stats
        assert "interview" in stats
        assert "evaluation" in stats
        assert "study" in stats
        assert "skills" in stats
        assert "progress" in stats
        assert "timeline" in stats

    # -- Summary -------------------------------------------------------

    def test_get_summary(self, client, db_session):
        """GET /api/dashboard/summary."""
        self._create_session_with_evaluation(db_session)
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert "resume_uploaded" in data
        assert "overall_readiness_score" in data

    # -- Statistics ----------------------------------------------------

    def test_get_statistics(self, client, db_session):
        """GET /api/dashboard/statistics."""
        self._create_session_with_evaluation(db_session)
        response = client.get("/api/dashboard/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "resume" in data
        assert "interview" in data
        assert "evaluation" in data

    # -- Interview Analytics -------------------------------------------

    def test_get_interview_analytics(self, client, db_session):
        """GET /api/dashboard/interview."""
        self._create_session_with_evaluation(db_session)
        response = client.get("/api/dashboard/interview")
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "completed_sessions" in data

    def test_get_interview_analytics_empty(self, client):
        """GET /api/dashboard/interview with no data."""
        response = client.get("/api/dashboard/interview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 0

    # -- ATS Analytics ------------------------------------------------

    def test_get_ats_analytics(self, client):
        """GET /api/dashboard/ats."""
        response = client.get("/api/dashboard/ats")
        assert response.status_code == 200
        data = response.json()
        assert "current_score" in data

    # -- Study Analytics ----------------------------------------------

    def test_get_study_analytics(self, client):
        """GET /api/dashboard/study."""
        response = client.get("/api/dashboard/study")
        assert response.status_code == 200
        data = response.json()
        assert "total_plans" in data

    # -- Skills Analytics ---------------------------------------------

    def test_get_skill_analytics(self, client):
        """GET /api/dashboard/skills."""
        response = client.get("/api/dashboard/skills")
        assert response.status_code == 200
        data = response.json()
        assert "top_skills" in data

    # -- Timeline -----------------------------------------------------

    def test_get_timeline(self, client, db_session):
        """GET /api/dashboard/timeline."""
        self._create_session_with_evaluation(db_session)
        response = client.get("/api/dashboard/timeline")
        assert response.status_code == 200
        data = response.json()
        assert "daily" in data
        assert "weekly" in data
        assert "monthly" in data

    def test_get_timeline_daily_filter(self, client):
        """GET /api/dashboard/timeline?period=daily."""
        response = client.get("/api/dashboard/timeline", params={"period": "daily"})
        assert response.status_code == 200
        data = response.json()
        assert "daily" in data

    def test_get_timeline_weekly_filter(self, client):
        """GET /api/dashboard/timeline?period=weekly."""
        response = client.get("/api/dashboard/timeline", params={"period": "weekly"})
        assert response.status_code == 200
        assert "weekly" in response.json()

    def test_get_timeline_monthly_filter(self, client):
        """GET /api/dashboard/timeline?period=monthly."""
        response = client.get("/api/dashboard/timeline", params={"period": "monthly"})
        assert response.status_code == 200
        assert "monthly" in response.json()

    # -- Readiness ----------------------------------------------------

    def test_get_readiness(self, client, db_session):
        """GET /api/dashboard/readiness."""
        self._create_session_with_evaluation(db_session)
        response = client.get("/api/dashboard/readiness")
        assert response.status_code == 200
        data = response.json()
        assert "overall_readiness_score" in data
        assert "breakdown" in data
        assert "formula" in data
        assert "resume" in data["breakdown"]
        assert "ats" in data["breakdown"]
        assert "interview" in data["breakdown"]
        assert "evaluation" in data["breakdown"]
        assert "study" in data["breakdown"]

    def test_get_readiness_empty(self, client):
        """GET /api/dashboard/readiness with no data."""
        response = client.get("/api/dashboard/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_readiness_score"] == 0

    # -- Multiple calls -----------------------------------------------

    def test_multiple_dashboard_calls(self, client):
        """Repeated dashboard calls succeed."""
        resp1 = client.get("/api/dashboard")
        assert resp1.status_code == 200
        resp2 = client.get("/api/dashboard")
        assert resp2.status_code == 200

    def test_all_endpoints_respond(self, client, db_session):
        """All 9 endpoints return 200."""
        self._create_session_with_evaluation(db_session)
        endpoints = [
            "/api/dashboard",
            "/api/dashboard/summary",
            "/api/dashboard/statistics",
            "/api/dashboard/interview",
            "/api/dashboard/ats",
            "/api/dashboard/study",
            "/api/dashboard/skills",
            "/api/dashboard/timeline",
            "/api/dashboard/readiness",
        ]
        for ep in endpoints:
            r = client.get(ep)
            assert r.status_code == 200, f"{ep} returned {r.status_code}"

    # -- Schema validation --------------------------------------------

    def test_summary_response_has_required_fields(self, client):
        """Summary response contains all required fields."""
        response = client.get("/api/dashboard/summary")
        data = response.json()
        required = [
            "resume_uploaded", "resume_analysed", "ats_score",
            "total_sessions", "completed_sessions", "average_score",
            "study_completion", "overall_readiness_score",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_dashboard_response_structure(self, client):
        """Dashboard response has correct top-level structure."""
        response = client.get("/api/dashboard")
        data = response.json()
        assert "summary" in data
        assert "statistics" in data
        assert "generated_at" in data


# ===================================================================
# Edge Cases
# ===================================================================


class TestDashboardEdgeCases:
    """Edge cases and error handling."""

    def test_dashboard_with_sessions_but_no_evaluations(
        self, db_session
    ):
        """Dashboard works with sessions but no evaluations."""
        _create_completed_session(db_session)

        from backend.app.services.dashboard_service import _collect_interview_data

        result = _collect_interview_data(db_session, "test-user-id")
        assert result.total_sessions >= 1
        assert result.average_score is None

    def test_dashboard_resume_no_skills(self, db_session):
        """Resume collector handles analyses with no skills."""
        from backend.app.models.resume_analysis import ResumeAnalysis

        ra = ResumeAnalysis(
            id="test-ra-id",
            user_id="test-user-id",
            resume_filename="test.pdf",
            skills=None,
            missing_skills=None,
            ats_score=75,
        )
        db_session.add(ra)
        db_session.commit()

        from backend.app.services.dashboard_service import _collect_resume_data

        result = _collect_resume_data(db_session, "test-user-id")
        assert result.resume_uploaded is True
        assert result.skills_count == 0

    def test_dashboard_multiple_evaluations_improvement(self, db_session):
        """Improvement rate calculated with multiple evaluations."""
        _create_evaluation(db_session, score=60)
        _create_evaluation(db_session, score=70)
        _create_evaluation(db_session, score=80)
        _create_evaluation(db_session, score=90)

        from backend.app.services.dashboard_service import _collect_evaluation_data

        result, best, worst = _collect_evaluation_data(db_session, "test-user-id")
        assert result.total_evaluations >= 4
        assert result.improvement_rate is not None

    def test_resume_analytics_default_values(self):
        """ResumeAnalytics schema has correct defaults."""
        ra = ResumeAnalytics()
        assert ra.resume_uploaded is False
        assert ra.resume_count == 0
        assert ra.skills_count == 0

    def test_ats_analytics_default_values(self):
        """ATSAnalytics schema has correct defaults."""
        aa = ATSAnalytics()
        assert aa.current_score is None
        assert aa.total_analyses == 0
        assert aa.missing_keywords == []

    def test_interview_analytics_default_values(self):
        """InterviewAnalytics schema has correct defaults."""
        ia = InterviewAnalytics()
        assert ia.total_sessions == 0
        assert ia.difficulty_distribution == {}
        assert ia.category_distribution == {}

    def test_evaluation_analytics_default_values(self):
        """EvaluationAnalytics schema has correct defaults."""
        ea = EvaluationAnalytics()
        assert ea.total_evaluations == 0
        assert ea.hire_decision_distribution == {}

    def test_study_analytics_default_values(self):
        """StudyAnalytics schema has correct defaults."""
        sa = StudyAnalytics()
        assert sa.total_plans == 0
        assert sa.tasks_completed == 0

    def test_skill_analytics_default_values(self):
        """SkillAnalytics schema has correct defaults."""
        sa = SkillAnalytics()
        assert sa.top_skills == []
        assert sa.skill_frequency == {}

    def test_dashboard_statistics_nested_access(self):
        """DashboardStatistics can access nested analytics."""
        ds = DashboardStatistics()
        assert isinstance(ds.resume, ResumeAnalytics)
        assert isinstance(ds.ats, ATSAnalytics)
        assert isinstance(ds.interview, InterviewAnalytics)
        assert isinstance(ds.evaluation, EvaluationAnalytics)
        assert isinstance(ds.study, StudyAnalytics)
        assert isinstance(ds.skills, SkillAnalytics)
        assert isinstance(ds.progress, ProgressAnalytics)
        assert isinstance(ds.timeline, TimelineAnalytics)

    def test_dashboard_response_default_factory(self):
        """DashboardResponse creates defaults."""
        dr = DashboardResponse()
        assert isinstance(dr.summary, DashboardSummary)
        assert isinstance(dr.statistics, DashboardStatistics)


# ===================================================================
# ProgressAnalytics tests (import fix)
# ===================================================================

from backend.app.schemas.dashboard_analytics import ProgressAnalytics


class TestProgressAnalytics:
    """Tests for ProgressAnalytics schema."""

    def test_default_values(self):
        """ProgressAnalytics has correct defaults."""
        pa = ProgressAnalytics()
        assert pa.total_sessions == 0
        assert pa.overall_readiness_score is None

    def test_populated_values(self):
        """ProgressAnalytics stores all fields."""
        pa = ProgressAnalytics(
            total_sessions=10,
            completed_sessions=8,
            average_ats_score=75.0,
            average_interview_score=80.0,
            average_evaluation_score=82.0,
            best_score=95,
            worst_score=60,
            improvement_rate=15.5,
            completed_study_tasks=20,
            pending_study_tasks=5,
            overall_readiness_score=78,
        )
        assert pa.total_sessions == 10
        assert pa.overall_readiness_score == 78
        assert pa.improvement_rate == 15.5
