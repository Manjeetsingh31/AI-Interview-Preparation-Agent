"""Unit tests for the Production Personalized Study Plan AI Agent.

Test strategy
-------------
- The ADK Agent internally uses Gemini via ``Runner.run_debug`` (an
  ``async`` method). Since ``google.adk`` is not available in the test
  environment, all agent executions fall through to the local fallback
  (``_fallback_study_plan``).
- Agent unit tests are ``async`` with ``@pytest.mark.asyncio``.
- API endpoint tests use ``TestClient`` with an isolated SQLite database
  and mocked user dependencies.
- CRUD tests verify persistence, queries, progress tracking, and statistics.
"""

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, get_db
from backend.app.main import app

from backend.app.schemas.study_plan_ai import (
    StudyPlanOutput,
    StudyPlanAICreate,
    StudyPlanAIUpdate,
    StudyPlanAIResponse,
)
from backend.app.schemas.interview_evaluation import (
    InterviewEvaluationCreate,
)
from backend.app.crud.crud_study_plan_ai import study_plan_ai_crud
from backend.app.crud.crud_interview_evaluation import (
    interview_evaluation_crud,
)
from backend.app.crud.crud_interview_session import (
    interview_session_crud,
)
from backend.app.schemas.interview_session import InterviewSessionCreate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_create(user_id: str = "test-user") -> InterviewSessionCreate:
    """Create an InterviewSessionCreate with the given user_id."""
    return InterviewSessionCreate(
        role="Software Engineer",
        interview_type="technical",
        company="Standard",
        status="active",
        user_id=user_id,
    )


def _build_sample_study_plan_output(
    target_role: str = "Software Engineer",
    duration: int = 30,
) -> StudyPlanOutput:
    """Build a fully populated StudyPlanOutput for unit-test assertions."""
    return StudyPlanOutput(
        target_role=target_role,
        target_company="Google",
        study_duration=duration,
        overview=f"A {duration}-day study plan for {target_role}",
        weekly_focus=["Week 1: DSA", "Week 2: System Design"],
        weak_topics=["Algorithms", "System Design"],
        strong_topics=["Python", "Communication"],
        daily_tasks=[
            {
                "day": 1,
                "topic": "Data Structures",
                "difficulty": "Intermediate",
                "estimated_time": "2 hours",
                "coding_task": "Solve 2 LeetCode problems",
                "reading_task": "Study arrays and strings",
                "revision_task": "Review notes",
                "goal": "Master basic data structures",
            }
        ],
        weekly_tasks=[
            {
                "week": 1,
                "focus_area": "DSA Foundation",
                "goals": ["Complete daily tasks"],
                "mini_project": None,
                "mock_interviews": 1,
            }
        ],
        coding_practice=[
            {
                "topic": "Data Structures",
                "platform": "LeetCode",
                "problems": ["Two Sum", "Valid Parentheses"],
                "difficulty": "Medium",
            }
        ],
        interview_practice=[
            {
                "topic": "Technical",
                "questions": ["Tell me about yourself"],
                "tips": ["Use STAR method"],
            }
        ],
        recommended_projects=[
            {
                "title": "REST API",
                "description": "Build a REST API",
                "skills_covered": ["Python", "FastAPI"],
                "difficulty": "Intermediate",
            }
        ],
        recommended_certifications=[
            {
                "name": "AWS Certified",
                "provider": "AWS",
                "description": "Cloud certification",
                "estimated_time": "3 months",
            }
        ],
        recommended_resources=[
            {
                "title": "System Design Interview",
                "type": "Book",
                "url": None,
                "description": "Great for system design prep",
            }
        ],
        roadmap_summary=f"{duration}-day roadmap for {target_role}",
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
    from backend.app.api.study_plan import _get_current_user_id

    app.dependency_overrides[_get_current_user_id] = _get_user_id_override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Agent unit tests
# ---------------------------------------------------------------------------


class TestStudyPlanAgentUnit:
    """Unit tests for the Study Plan Agent logic."""

    @pytest.mark.asyncio
    async def test_fallback_study_plan(self):
        """_fallback_study_plan produces valid output."""
        from backend.app.services.agents.study_plan_agent import (
            _fallback_study_plan,
        )

        result = _fallback_study_plan(
            target_role="Software Engineer",
            target_company="Google",
            study_duration=7,
        )
        assert isinstance(result, StudyPlanOutput)
        assert result.target_role == "Software Engineer"
        assert result.target_company == "Google"
        assert result.study_duration == 7
        assert len(result.daily_tasks) == 7
        assert result.overview is not None

    @pytest.mark.asyncio
    async def test_fallback_study_plan_15_days(self):
        """_fallback_study_plan with 15-day duration."""
        from backend.app.services.agents.study_plan_agent import (
            _fallback_study_plan,
        )

        result = _fallback_study_plan(
            target_role="Data Scientist",
            target_company=None,
            study_duration=15,
        )
        assert result.study_duration == 15
        assert len(result.daily_tasks) == 15

    @pytest.mark.asyncio
    async def test_fallback_study_plan_with_evaluation(self, db_session):
        """_fallback_study_plan uses evaluation data."""
        from backend.app.services.agents.study_plan_agent import (
            _fallback_study_plan,
        )

        session = interview_session_crud.create(
            db=db_session,
            obj_in=_make_session_create(user_id="test-user"),
        )
        session.status = "completed"
        db_session.commit()

        from backend.app.services.agents.evaluation_agent import (
            _fallback_evaluation,
        )

        output = _fallback_evaluation(session, [])
        eval_create = InterviewEvaluationCreate(
            session_id=session.id,
            user_id="test-user",
            overall_score=output.overall_score,
            technical_score=output.technical_score,
            communication_score=output.communication_score,
            problem_solving_score=output.problem_solving_score,
            confidence_score=output.confidence_score,
            behavioral_score=output.behavioral_score,
            coding_score=output.coding_score,
            strengths=output.strengths,
            weaknesses=output.weaknesses,
            missed_topics=output.missed_topics,
            strong_topics=output.strong_topics,
            improvement_suggestions=output.improvement_suggestions,
            recommendation=output.recommendation,
            hire_decision=output.hire_decision,
            difficulty_level=output.difficulty_level,
            evaluation_summary=output.evaluation_summary,
        )
        evaluation = interview_evaluation_crud.create(
            db=db_session, obj_in=eval_create
        )

        result = _fallback_study_plan(
            target_role="Software Engineer",
            target_company=None,
            study_duration=7,
            evaluation=evaluation,
        )
        assert len(result.weak_topics) > 0
        assert result.weak_topics == evaluation.weaknesses

    @pytest.mark.asyncio
    async def test_build_context_contains_role_and_duration(self):
        """Context builder includes target role and duration."""
        from backend.app.services.agents.study_plan_agent import (
            _build_study_plan_context,
        )

        context = _build_study_plan_context(
            target_role="Data Scientist",
            study_duration=15,
        )
        assert "Data Scientist" in context
        assert "15 days" in context
        assert "Study Plan Generation Request" in context

    @pytest.mark.asyncio
    async def test_build_context_with_evaluation(self, db_session):
        """Context builder includes evaluation data."""
        from backend.app.services.agents.study_plan_agent import (
            _build_study_plan_context,
        )

        session = interview_session_crud.create(
            db=db_session,
            obj_in=_make_session_create(user_id="test-user"),
        )
        session.status = "completed"
        db_session.commit()

        from backend.app.services.agents.evaluation_agent import (
            _fallback_evaluation,
        )

        output = _fallback_evaluation(session, [])
        eval_create = InterviewEvaluationCreate(
            session_id=session.id,
            user_id="test-user",
            overall_score=output.overall_score,
            technical_score=output.technical_score,
            communication_score=output.communication_score,
            problem_solving_score=output.problem_solving_score,
            confidence_score=output.confidence_score,
            behavioral_score=output.behavioral_score,
            coding_score=output.coding_score,
            strengths=output.strengths,
            weaknesses=output.weaknesses,
            missed_topics=output.missed_topics,
            strong_topics=output.strong_topics,
            improvement_suggestions=output.improvement_suggestions,
            recommendation=output.recommendation,
            hire_decision=output.hire_decision,
            difficulty_level=output.difficulty_level,
            evaluation_summary=output.evaluation_summary,
        )
        evaluation = interview_evaluation_crud.create(
            db=db_session, obj_in=eval_create
        )

        context = _build_study_plan_context(evaluation=evaluation)
        assert "Interview Evaluation" in context
        assert str(evaluation.overall_score) in context

    @pytest.mark.asyncio
    async def test_build_context_with_resume_ats_data(self):
        """Context builder includes resume and ATS data."""
        from backend.app.services.agents.study_plan_agent import (
            _build_study_plan_context,
        )

        resume = {
            "skills": ["Python", "FastAPI"],
            "missing_skills": ["Docker"],
            "strengths": ["Fast learner"],
            "weaknesses": ["System design"],
        }
        ats = {
            "overall_score": 82,
            "missing_keywords": ["Kubernetes"],
        }

        context = _build_study_plan_context(
            resume_analysis=resume,
            ats_score=ats,
            target_role="Backend Engineer",
        )
        assert "Resume Analysis" in context
        assert "ATS Score Analysis" in context
        assert "Python" in context
        assert "Kubernetes" in context

    @pytest.mark.asyncio
    async def test_run_study_plan_agent_nonexistent_evaluation(
        self, db_session
    ):
        """run_study_plan_agent raises ValueError for missing evaluation."""
        from backend.app.services.agents.study_plan_agent import (
            run_study_plan_agent,
        )

        with pytest.raises(ValueError, match="not found"):
            await run_study_plan_agent(
                db=db_session,
                user_id="test-user",
                evaluation_id="nonexistent-id",
            )

    @pytest.mark.asyncio
    async def test_duration_label_mapping(self):
        """Duration labels map correctly."""
        from backend.app.services.agents.study_plan_agent import (
            _duration_label,
        )

        assert "Rapid" in _duration_label(7)
        assert "Focused" in _duration_label(15)
        assert "Comprehensive" in _duration_label(30)
        assert "Placement" in _duration_label(60)
        assert "Day" in _duration_label(100)


# ---------------------------------------------------------------------------
# CRUD unit tests
# ---------------------------------------------------------------------------


class TestCRUDStudyPlanAI:
    """Unit tests for CRUDStudyPlanAI operations."""

    def _create_plan(
        self, db_session, user_id: str = "test-user"
    ) -> StudyPlanAIResponse:
        """Helper to create a sample study plan."""
        plan_create = StudyPlanAICreate(
            user_id=user_id,
            target_role="Software Engineer",
            target_company="Google",
            study_duration=30,
            roadmap={"overview": "Test roadmap"},
            daily_tasks=[
                {"day": 1, "topic": "DSA", "goal": "Learn DSA"}
            ],
            weekly_tasks=[{"week": 1, "focus_area": "DSA"}],
            weak_topics=["Algorithms"],
            strong_topics=["Python"],
            coding_practice=[
                {
                    "topic": "DSA",
                    "platform": "LeetCode",
                    "problems": [],
                    "difficulty": "Medium",
                }
            ],
            interview_practice=[
                {"topic": "Behavioral", "questions": [], "tips": []}
            ],
            recommended_projects=[
                {
                    "title": "Test Project",
                    "description": "Test",
                    "skills_covered": [],
                    "difficulty": "Beginner",
                }
            ],
            recommended_certifications=[
                {
                    "name": "Test Cert",
                    "provider": "Test",
                    "description": "Test",
                    "estimated_time": "1 month",
                }
            ],
            recommended_resources=[
                {
                    "title": "Test Resource",
                    "type": "Book",
                    "url": None,
                    "description": "Test",
                }
            ],
            completion_percentage=0.0,
            status="active",
        )
        return study_plan_ai_crud.create(db=db_session, obj_in=plan_create)

    def test_create_plan(self, db_session):
        """Creating a study plan returns a valid record."""
        plan = self._create_plan(db_session)
        assert plan.id is not None
        assert plan.target_role == "Software Engineer"
        assert plan.study_duration == 30
        assert plan.status == "active"
        assert plan.completion_percentage == 0.0

    def test_get_plan_by_id(self, db_session):
        """Get a plan by its ID."""
        plan = self._create_plan(db_session)
        found = study_plan_ai_crud.get(db=db_session, id=plan.id)
        assert found is not None
        assert found.id == plan.id

    def test_get_plan_not_found(self, db_session):
        """Get by nonexistent ID returns None."""
        found = study_plan_ai_crud.get(
            db=db_session, id="nonexistent-id"
        )
        assert found is None

    def test_get_by_user(self, db_session):
        """Get all plans for a user."""
        plan = self._create_plan(db_session)
        results = study_plan_ai_crud.get_by_user(
            db=db_session, user_id="test-user"
        )
        assert len(results) >= 1
        assert results[0].id == plan.id

    def test_get_by_user_empty(self, db_session):
        """Get by user with no plans returns empty list."""
        results = study_plan_ai_crud.get_by_user(
            db=db_session, user_id="nonexistent"
        )
        assert results == []

    def test_get_active_by_user(self, db_session):
        """Get the active plan for a user."""
        plan = self._create_plan(db_session)
        active = study_plan_ai_crud.get_active_by_user(
            db=db_session, user_id="test-user"
        )
        assert active is not None
        assert active.id == plan.id
        assert active.status == "active"

    def test_get_active_by_user_none(self, db_session):
        """Returns None when no active plan exists."""
        plan = self._create_plan(db_session)
        study_plan_ai_crud.update(
            db=db_session, db_obj=plan, obj_in=StudyPlanAIUpdate(status="completed")
        )
        active = study_plan_ai_crud.get_active_by_user(
            db=db_session, user_id="test-user"
        )
        assert active is None

    def test_get_latest_by_user(self, db_session):
        """Get the latest plan for a user."""
        plan = self._create_plan(db_session)
        latest = study_plan_ai_crud.get_latest_by_user(
            db=db_session, user_id="test-user"
        )
        assert latest is not None
        assert latest.id == plan.id

    def test_get_by_evaluation(self, db_session):
        """Get plan linked to an evaluation."""
        plan = self._create_plan(db_session)
        # Use a dummy evaluation_id since SQLite doesn't enforce FKs
        plan.evaluation_id = "eval-123"
        db_session.commit()
        found = study_plan_ai_crud.get_by_evaluation(
            db=db_session, evaluation_id="eval-123"
        )
        assert found is not None
        assert found.id == plan.id

    def test_get_by_evaluation_not_found(self, db_session):
        """Get by nonexistent evaluation returns None."""
        found = study_plan_ai_crud.get_by_evaluation(
            db=db_session, evaluation_id="nonexistent"
        )
        assert found is None

    def test_search(self, db_session):
        """Search plans by target role."""
        plan = self._create_plan(db_session)
        results = study_plan_ai_crud.search(
            db=db_session, user_id="test-user", query="Software"
        )
        assert len(results) >= 1
        assert results[0].id == plan.id

    def test_search_no_results(self, db_session):
        """Search with non-matching query returns empty list."""
        self._create_plan(db_session)
        results = study_plan_ai_crud.search(
            db=db_session, user_id="test-user", query="zzzznonexistent"
        )
        assert results == []

    def test_update_progress(self, db_session):
        """Update completion percentage keeps plan active."""
        plan = self._create_plan(db_session)
        updated = study_plan_ai_crud.update_progress(
            db=db_session,
            plan_id=plan.id,
            completion_percentage=50.0,
        )
        assert updated is not None
        assert updated.completion_percentage == 50.0
        assert updated.status == "active"

    def test_update_progress_completes_plan(self, db_session):
        """Reaching 100% completion sets status to completed."""
        plan = self._create_plan(db_session)
        updated = study_plan_ai_crud.update_progress(
            db=db_session,
            plan_id=plan.id,
            completion_percentage=100.0,
        )
        assert updated is not None
        assert updated.completion_percentage == 100.0
        assert updated.status == "completed"

    def test_update_progress_with_status_override(self, db_session):
        """Update progress with explicit status."""
        plan = self._create_plan(db_session)
        updated = study_plan_ai_crud.update_progress(
            db=db_session,
            plan_id=plan.id,
            completion_percentage=30.0,
            status="paused",
        )
        assert updated is not None
        assert updated.status == "paused"

    def test_update_progress_not_found(self, db_session):
        """Update progress on nonexistent plan returns None."""
        result = study_plan_ai_crud.update_progress(
            db=db_session,
            plan_id="nonexistent",
            completion_percentage=50.0,
        )
        assert result is None

    def test_get_progress(self, db_session):
        """Get progress returns detailed breakdown."""
        plan = self._create_plan(db_session)
        progress = study_plan_ai_crud.get_progress(
            db=db_session, plan_id=plan.id
        )
        assert progress is not None
        assert progress["plan_id"] == plan.id
        assert progress["total_days"] == 30
        assert progress["completion_percentage"] == 0.0
        assert progress["days_completed"] == 0

    def test_get_progress_not_found(self, db_session):
        """Get progress on nonexistent plan returns None."""
        progress = study_plan_ai_crud.get_progress(
            db=db_session, plan_id="nonexistent"
        )
        assert progress is None

    def test_count_by_user(self, db_session):
        """Count plans for a user."""
        self._create_plan(db_session)
        self._create_plan(db_session)
        count = study_plan_ai_crud.count_by_user(
            db=db_session, user_id="test-user"
        )
        assert count >= 2

    def test_average_completion(self, db_session):
        """Average completion percentage."""
        plan = self._create_plan(db_session)
        study_plan_ai_crud.update_progress(
            db=db_session, plan_id=plan.id, completion_percentage=50.0
        )
        avg = study_plan_ai_crud.average_completion(
            db=db_session, user_id="test-user"
        )
        assert avg > 0

    def test_plans_by_status(self, db_session):
        """Plans grouped by status."""
        self._create_plan(db_session)
        by_status = study_plan_ai_crud.plans_by_status(
            db=db_session, user_id="test-user"
        )
        assert "active" in by_status
        assert by_status["active"] >= 1

    def test_statistics(self, db_session):
        """Comprehensive statistics."""
        self._create_plan(db_session)
        stats = study_plan_ai_crud.statistics(
            db=db_session, user_id="test-user"
        )
        assert stats["total_plans"] >= 1
        assert "average_completion" in stats
        assert "plans_by_status" in stats

    def test_statistics_empty(self, db_session):
        """Statistics for user with no plans."""
        stats = study_plan_ai_crud.statistics(
            db=db_session, user_id="empty-user"
        )
        assert stats["total_plans"] == 0
        assert stats["average_completion"] == 0.0
        assert stats["plans_by_status"] == {}

    def test_dashboard(self, db_session):
        """Dashboard returns all components."""
        self._create_plan(db_session)
        dash = study_plan_ai_crud.dashboard(
            db=db_session, user_id="test-user"
        )
        assert dash["total_plans"] >= 1
        assert dash["active_plan"] is not None
        assert len(dash["recent_plans"]) >= 1
        assert dash["average_completion"] >= 0

    def test_dashboard_empty(self, db_session):
        """Dashboard for user with no plans."""
        dash = study_plan_ai_crud.dashboard(
            db=db_session, user_id="empty-user"
        )
        assert dash["total_plans"] == 0
        assert dash["active_plan"] is None
        assert dash["recent_plans"] == []

    def test_update_plan(self, db_session):
        """Update plan fields."""
        plan = self._create_plan(db_session)
        updated = study_plan_ai_crud.update(
            db=db_session,
            db_obj=plan,
            obj_in=StudyPlanAIUpdate(
                target_role="Senior Engineer", target_company="Microsoft"
            ),
        )
        assert updated.target_role == "Senior Engineer"
        assert updated.target_company == "Microsoft"

    def test_remove_plan(self, db_session):
        """Delete a plan."""
        plan = self._create_plan(db_session)
        plan_id = plan.id
        study_plan_ai_crud.remove(db=db_session, id=plan_id)
        assert (
            study_plan_ai_crud.get(db=db_session, id=plan_id) is None
        )


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


class TestStudyPlanAPI:
    """Integration tests for the Study Plan API endpoints.

    Since ``google.adk`` is not available in the test environment, all
    agent calls fall through to the local fallback implementation.
    """

    def _create_evaluation(
        self, db_session, user_id: str = "test-user-id"
    ):
        """Helper to create a completed session + evaluation."""
        session = interview_session_crud.create(
            db=db_session,
            obj_in=_make_session_create(user_id=user_id),
        )
        session.status = "completed"
        db_session.commit()

        from backend.app.services.agents.evaluation_agent import (
            _fallback_evaluation,
        )

        output = _fallback_evaluation(session, [])
        eval_create = InterviewEvaluationCreate(
            session_id=session.id,
            user_id=user_id,
            overall_score=output.overall_score,
            technical_score=output.technical_score,
            communication_score=output.communication_score,
            problem_solving_score=output.problem_solving_score,
            confidence_score=output.confidence_score,
            behavioral_score=output.behavioral_score,
            coding_score=output.coding_score,
            strengths=output.strengths,
            weaknesses=output.weaknesses,
            missed_topics=output.missed_topics,
            strong_topics=output.strong_topics,
            improvement_suggestions=output.improvement_suggestions,
            recommendation=output.recommendation,
            hire_decision=output.hire_decision,
            difficulty_level=output.difficulty_level,
            evaluation_summary=output.evaluation_summary,
        )
        return interview_evaluation_crud.create(
            db=db_session, obj_in=eval_create
        )

    # -- Generate -------------------------------------------------------

    def test_generate_plan_no_evaluation(self, client):
        """POST /api/study-plan/generate without evaluation_id."""
        response = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["target_role"] is not None
        assert data["study_duration"] == 7
        assert data["status"] == "active"

    def test_generate_plan_with_evaluation(self, client, db_session):
        """POST /api/study-plan/generate with valid evaluation_id."""
        evaluation = self._create_evaluation(db_session)
        response = client.post(
            "/api/study-plan/generate",
            json={
                "evaluation_id": evaluation.id,
                "target_role": "Data Scientist",
                "target_company": "Meta",
                "study_duration": 30,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["target_role"] is not None
        assert data["study_duration"] == 30
        assert data["status"] == "active"

    def test_generate_plan_invalid_duration(self, client):
        """POST /api/study-plan/generate with invalid duration."""
        response = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 100},
        )
        assert response.status_code == 400
        assert "study_duration must be 7, 15, 30, or 60" in response.text

    def test_generate_plan_evaluation_not_found(self, client):
        """POST /api/study-plan/generate with nonexistent evaluation."""
        response = client.post(
            "/api/study-plan/generate",
            json={
                "evaluation_id": "nonexistent-id",
                "study_duration": 15,
            },
        )
        assert response.status_code == 404

    def test_generate_plan_evaluation_wrong_user(self, client, db_session):
        """POST /api/study-plan/generate with another user's evaluation."""
        evaluation = self._create_evaluation(
            db_session, user_id="other-user"
        )
        response = client.post(
            "/api/study-plan/generate",
            json={
                "evaluation_id": evaluation.id,
                "study_duration": 15,
            },
        )
        assert response.status_code == 404

    # -- Get by ID ------------------------------------------------------

    def test_get_plan_by_id(self, client, db_session):
        """GET /api/study-plan/{plan_id}."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]
        response = client.get(f"/api/study-plan/{plan_id}")
        assert response.status_code == 200
        assert response.json()["id"] == plan_id

    def test_get_plan_not_found(self, client):
        """GET /api/study-plan/{plan_id} with nonexistent ID."""
        response = client.get("/api/study-plan/nonexistent-id")
        assert response.status_code == 404

    def test_get_plan_forbidden(self, client, db_session):
        """GET /api/study-plan/{plan_id} by another user."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]

        from backend.app.api.study_plan import _get_current_user_id

        async def _other_override():
            return "other-user-id"

        app.dependency_overrides[_get_current_user_id] = _other_override
        response = client.get(f"/api/study-plan/{plan_id}")
        assert response.status_code == 403
        app.dependency_overrides[
            _get_current_user_id
        ] = lambda: "test-user-id"

    # -- History --------------------------------------------------------

    def test_list_plans(self, client, db_session):
        """GET /api/study-plan/history returns user's plans."""
        client.post(
            "/api/study-plan/generate", json={"study_duration": 7}
        )
        client.post(
            "/api/study-plan/generate", json={"study_duration": 15}
        )
        response = client.get("/api/study-plan/history/all")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["plans"]) >= 2

    def test_list_plans_empty(self, client):
        """GET /api/study-plan/history when no plans exist."""
        response = client.get("/api/study-plan/history/all")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["plans"] == []

    # -- Progress -------------------------------------------------------

    def test_get_progress(self, client, db_session):
        """GET /api/study-plan/progress/{plan_id}."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 30},
        )
        plan_id = create_resp.json()["id"]
        response = client.get(f"/api/study-plan/progress/{plan_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == plan_id
        assert data["total_days"] == 30
        assert data["completion_percentage"] == 0.0

    def test_get_progress_not_found(self, client):
        """GET /api/study-plan/progress/{plan_id} with nonexistent ID."""
        response = client.get(
            "/api/study-plan/progress/nonexistent-id"
        )
        assert response.status_code == 404

    def test_get_progress_forbidden(self, client, db_session):
        """GET /api/study-plan/progress/{plan_id} by another user."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]

        from backend.app.api.study_plan import _get_current_user_id

        async def _other_override():
            return "other-user-id"

        app.dependency_overrides[_get_current_user_id] = _other_override
        response = client.get(f"/api/study-plan/progress/{plan_id}")
        assert response.status_code == 403
        app.dependency_overrides[
            _get_current_user_id
        ] = lambda: "test-user-id"

    # -- Dashboard ------------------------------------------------------

    def test_dashboard_with_data(self, client, db_session):
        """GET /api/study-plan/dashboard/data with plans."""
        client.post(
            "/api/study-plan/generate", json={"study_duration": 7}
        )
        response = client.get("/api/study-plan/dashboard/data")
        assert response.status_code == 200
        data = response.json()
        assert data["total_plans"] >= 1
        assert data["active_plan"] is not None
        assert isinstance(data["recent_plans"], list)

    def test_dashboard_empty(self, client):
        """GET /api/study-plan/dashboard/data with no plans."""
        response = client.get("/api/study-plan/dashboard/data")
        assert response.status_code == 200
        data = response.json()
        assert data["total_plans"] == 0
        assert data["active_plan"] is None
        assert data["average_completion"] == 0.0

    # -- Update ---------------------------------------------------------

    def test_update_plan(self, client, db_session):
        """PUT /api/study-plan/update/{plan_id}."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]
        response = client.put(
            f"/api/study-plan/update/{plan_id}",
            json={
                "target_role": "Updated Role",
                "target_company": "New Company",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["target_role"] == "Updated Role"
        assert data["target_company"] == "New Company"

    def test_update_plan_partial(self, client, db_session):
        """PUT /api/study-plan/update/{plan_id} with partial data."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]
        response = client.put(
            f"/api/study-plan/update/{plan_id}",
            json={"target_role": "Only Role Updated"},
        )
        assert response.status_code == 200
        assert response.json()["target_role"] == "Only Role Updated"

    def test_update_plan_not_found(self, client):
        """PUT /api/study-plan/update/{plan_id} with nonexistent ID."""
        response = client.put(
            "/api/study-plan/update/nonexistent-id",
            json={"target_role": "Test"},
        )
        assert response.status_code == 404

    def test_update_plan_forbidden(self, client, db_session):
        """PUT /api/study-plan/update/{plan_id} by another user."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]

        from backend.app.api.study_plan import _get_current_user_id

        async def _other_override():
            return "other-user-id"

        app.dependency_overrides[_get_current_user_id] = _other_override
        response = client.put(
            f"/api/study-plan/update/{plan_id}",
            json={"target_role": "Hacked"},
        )
        assert response.status_code == 403
        app.dependency_overrides[
            _get_current_user_id
        ] = lambda: "test-user-id"

    # -- Progress Update ------------------------------------------------

    def test_update_progress_api(self, client, db_session):
        """PUT /api/study-plan/progress/{plan_id}."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]
        response = client.put(
            f"/api/study-plan/progress/{plan_id}",
            json={"completion_percentage": 50.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completion_percentage"] == 50.0
        assert data["status"] == "active"

    def test_update_progress_completes_plan(self, client, db_session):
        """PUT /api/study-plan/progress/{plan_id} to 100%."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]
        response = client.put(
            f"/api/study-plan/progress/{plan_id}",
            json={"completion_percentage": 100.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completion_percentage"] == 100.0
        assert data["status"] == "completed"

    def test_update_progress_with_status(self, client, db_session):
        """PUT /api/study-plan/progress/{plan_id} with status override."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]
        response = client.put(
            f"/api/study-plan/progress/{plan_id}",
            json={
                "completion_percentage": 30.0,
                "status": "paused",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    def test_update_progress_not_found(self, client):
        """PUT /api/study-plan/progress/{plan_id} nonexistent."""
        response = client.put(
            "/api/study-plan/progress/nonexistent-id",
            json={"completion_percentage": 50.0},
        )
        assert response.status_code == 404

    def test_update_progress_forbidden(self, client, db_session):
        """PUT /api/study-plan/progress/{plan_id} by another user."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]

        from backend.app.api.study_plan import _get_current_user_id

        async def _other_override():
            return "other-user-id"

        app.dependency_overrides[_get_current_user_id] = _other_override
        response = client.put(
            f"/api/study-plan/progress/{plan_id}",
            json={"completion_percentage": 50.0},
        )
        assert response.status_code == 403
        app.dependency_overrides[
            _get_current_user_id
        ] = lambda: "test-user-id"

    # -- Delete ---------------------------------------------------------

    def test_delete_plan(self, client, db_session):
        """DELETE /api/study-plan/{plan_id}."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]
        response = client.delete(f"/api/study-plan/{plan_id}")
        assert response.status_code == 204

        get_resp = client.get(f"/api/study-plan/{plan_id}")
        assert get_resp.status_code == 404

    def test_delete_plan_not_found(self, client):
        """DELETE /api/study-plan/{plan_id} with nonexistent ID."""
        response = client.delete("/api/study-plan/nonexistent-id")
        assert response.status_code == 404

    def test_delete_plan_forbidden(self, client, db_session):
        """DELETE /api/study-plan/{plan_id} by another user."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]

        from backend.app.api.study_plan import _get_current_user_id

        async def _other_override():
            return "other-user-id"

        app.dependency_overrides[_get_current_user_id] = _other_override
        response = client.delete(f"/api/study-plan/{plan_id}")
        assert response.status_code == 403
        app.dependency_overrides[
            _get_current_user_id
        ] = lambda: "test-user-id"

    # -- Edge cases -----------------------------------------------------

    def test_generate_plan_15_days(self, client):
        """Study plan with 15-day duration."""
        response = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 15},
        )
        assert response.status_code == 201
        assert response.json()["study_duration"] == 15

    def test_generate_plan_60_days(self, client):
        """Study plan with 60-day duration."""
        response = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 60},
        )
        assert response.status_code == 201
        assert response.json()["study_duration"] == 60

    def test_duplicate_progress_update(self, client, db_session):
        """Multiple progress updates are cumulative."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]

        client.put(
            f"/api/study-plan/progress/{plan_id}",
            json={"completion_percentage": 30.0},
        )
        resp2 = client.put(
            f"/api/study-plan/progress/{plan_id}",
            json={"completion_percentage": 60.0},
        )
        assert resp2.status_code == 200
        assert resp2.json()["completion_percentage"] == 60.0

    def test_progress_update_invalid_percentage(self, client, db_session):
        """Progress update with invalid percentage returns 422."""
        create_resp = client.post(
            "/api/study-plan/generate",
            json={"study_duration": 7},
        )
        plan_id = create_resp.json()["id"]
        response = client.put(
            f"/api/study-plan/progress/{plan_id}",
            json={"completion_percentage": 150},
        )
        assert response.status_code == 422
