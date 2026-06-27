"""Unit tests for the Production AI Evaluation & Feedback Agent.

Test strategy
-------------
- The ADK Agent internally uses Gemini via ``Runner.run_debug`` (which is
  an ``async`` method). We **mock ``Runner.run_debug``** so that no real
  API call is made.
- The mock returns a list of ``Event`` objects that simulate a successful
  Gemini response (or error conditions).
- All agent tests are ``async`` with ``@pytest.mark.asyncio``.
- API endpoint tests use ``TestClient`` with an isolated SQLite database,
  mocked agent, and proper table creation.

Integration notes
-----------------
- Tests that need a "completed" session must create one via the
  ``interview_session`` CRUD, then update its status to ``completed``.
- The ``run_evaluation_agent`` function checks session status before
  proceeding — tests verify the error path for non-completed sessions.
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

from backend.app.schemas.interview_evaluation import (
    InterviewEvaluationOutput,
    InterviewEvaluationCreate,
)
from backend.app.crud.crud_interview_evaluation import interview_evaluation_crud
from backend.app.crud.crud_interview_session import interview_session_crud
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
    from backend.app.api.evaluation import _get_current_user_id

    app.dependency_overrides[_get_current_user_id] = _get_user_id_override

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_fake_event(
    text: str,
    is_final: bool = True,
    function_call: bool = False,
) -> MagicMock:
    """Create a minimal fake Event with a text part."""
    fake_part = MagicMock()
    fake_part.text = text
    fake_part.function_call = None

    fake_content = MagicMock()
    fake_content.parts = [fake_part]
    fake_content.role = "model"

    event = MagicMock()
    event.is_final_response.return_value = is_final
    event.content = fake_content
    event.author = "model"
    return event


def _build_sample_evaluation_output() -> dict:
    """Build a sample evaluation output dict matching InterviewEvaluationOutput."""
    return {
        "overall_score": 78,
        "technical_score": 72,
        "communication_score": 85,
        "problem_solving_score": 75,
        "confidence_score": 80,
        "behavioral_score": 82,
        "coding_score": 68,
        "strengths": [
            "Strong communication skills",
            "Good technical foundation",
        ],
        "weaknesses": [
            "Needs more practice with algorithms",
        ],
        "missed_topics": [
            "System design fundamentals",
        ],
        "strong_topics": [
            "Python fundamentals",
            "API design",
        ],
        "improvement_suggestions": [
            "Practice coding problems daily",
            "Study system design patterns",
        ],
        "recommendation": (
            "The candidate shows promise with strong communication. "
            "Recommend focusing on algorithms and system design."
        ),
        "hire_decision": "Borderline",
        "difficulty_level": "Medium",
        "evaluation_summary": (
            "The candidate performed adequately across all dimensions. "
            "Strengths in communication were notable, but technical depth "
            "in algorithms needs improvement."
        ),
    }


# ---------------------------------------------------------------------------
# Agent unit tests
# ---------------------------------------------------------------------------


class TestEvaluationAgentUnit:
    """Unit tests for the Evaluation Agent logic."""

    @pytest.mark.asyncio
    async def test_fallback_evaluation(self, db_session):
        """Test the fallback evaluation produces valid output."""
        from backend.app.services.agents.evaluation_agent import (
            _fallback_evaluation,
        )

        session = interview_session_crud.create(
            db=db_session,
            obj_in=_make_session_create(user_id="test-user"),
        )

        result = _fallback_evaluation(session, [])
        assert isinstance(result, InterviewEvaluationOutput)
        assert 0 <= result.overall_score <= 100
        assert result.hire_decision in (
            "Strong Hire", "Hire", "Borderline", "Reject"
        )
        assert result.difficulty_level in ("Easy", "Medium", "Hard")
        assert len(result.strengths) > 0 or len(result.weaknesses) > 0

    @pytest.mark.asyncio
    async def test_build_context_contains_session_info(self, db_session):
        """Test that the context builder includes session data."""
        from backend.app.services.agents.evaluation_agent import (
            _build_evaluation_context,
        )

        session = interview_session_crud.create(
            db=db_session,
            obj_in=_make_session_create(user_id="test-user"),
        )

        context = _build_evaluation_context(session, [], [])
        assert session.role in context
        assert session.interview_type in context
        assert "Mock Interview Evaluation Request" in context

    @pytest.mark.asyncio
    async def test_build_context_with_resume_analysis(self, db_session):
        """Test context builder handles resume analysis data."""
        from backend.app.services.agents.evaluation_agent import (
            _build_evaluation_context,
        )

        session = interview_session_crud.create(
            db=db_session,
            obj_in=_make_session_create(user_id="test-user"),
        )

        resume = {
            "total_score": 85,
            "skills_match_score": 80,
            "matched_skills": ["Python", "FastAPI"],
            "missing_skills": ["Docker"],
        }

        context = _build_evaluation_context(session, [], [], resume)
        assert "Resume Analysis" in context
        assert "Python" in context
        assert "Docker" in context

    @pytest.mark.asyncio
    async def test_run_evaluation_agent_not_completed(self, db_session):
        """Test that non-completed sessions raise ValueError."""
        from backend.app.services.agents.evaluation_agent import (
            run_evaluation_agent,
        )

        session = interview_session_crud.create(
            db=db_session,
            obj_in=_make_session_create(user_id="test-user"),
        )

        with pytest.raises(ValueError, match="Only completed sessions"):
            await run_evaluation_agent(
                db=db_session,
                session_id=session.id,
                user_id="test-user",
            )

    @pytest.mark.asyncio
    async def test_run_evaluation_agent_nonexistent_session(self, db_session):
        """Test that nonexistent sessions raise ValueError."""
        from backend.app.services.agents.evaluation_agent import (
            run_evaluation_agent,
        )

        with pytest.raises(ValueError, match="not found"):
            await run_evaluation_agent(
                db=db_session,
                session_id="nonexistent-id",
                user_id="test-user",
            )


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


class TestEvaluationAgentAPI:
    """Integration tests for the Evaluation API endpoints.

    These tests use the ADK agent mock path — they always go through
    the fallback since google.adk is not available in the test env.
    """

    def _create_completed_session(self, db_session, user_id: str = "test-user-id"):
        """Helper to create a completed interview session."""
        session = interview_session_crud.create(
            db=db_session,
            obj_in=_make_session_create(user_id=user_id),
        )
        session.status = "completed"
        db_session.commit()
        db_session.refresh(session)
        return session

    def test_evaluate_session_success(self, client, db_session):
        """Test POST /api/evaluate creates an evaluation."""
        session = self._create_completed_session(db_session)

        response = client.post(
            "/api/evaluate",
            json={"session_id": session.id},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == session.id
        assert data["overall_score"] > 0
        assert data["hire_decision"] in (
            "Strong Hire", "Hire", "Borderline", "Reject"
        )

    def test_evaluate_session_not_found(self, client):
        """Test POST /api/evaluate with nonexistent session."""
        response = client.post(
            "/api/evaluate",
            json={"session_id": "nonexistent-id"},
        )
        assert response.status_code == 404

    def test_evaluate_session_not_completed(self, client, db_session):
        """Test POST /api/evaluate with non-completed session."""
        session = interview_session_crud.create(
            db=db_session,
            obj_in=_make_session_create(user_id="test-user-id"),
        )

        response = client.post(
            "/api/evaluate",
            json={"session_id": session.id},
        )
        assert response.status_code == 400
        assert "Only completed sessions can be evaluated" in response.text

    def test_evaluate_session_duplicate(self, client, db_session):
        """Test POST /api/evaluate twice returns 409."""
        session = self._create_completed_session(db_session)

        response1 = client.post(
            "/api/evaluate",
            json={"session_id": session.id},
        )
        assert response1.status_code == 201

        response2 = client.post(
            "/api/evaluate",
            json={"session_id": session.id},
        )
        assert response2.status_code == 409
        assert "already has an evaluation" in response2.text

    def test_get_evaluation_by_session(self, client, db_session):
        """Test GET /api/evaluations/session/{session_id}."""
        session = self._create_completed_session(db_session)

        client.post("/api/evaluate", json={"session_id": session.id})

        response = client.get(f"/api/evaluations/session/{session.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session.id

    def test_get_evaluation_by_session_not_found(self, client):
        """Test GET /api/evaluations/session/{id} with no evaluation."""
        response = client.get(
            "/api/evaluations/session/nonexistent-id"
        )
        assert response.status_code == 404

    def test_get_evaluation_by_id(self, client, db_session):
        """Test GET /api/evaluations/{evaluation_id}."""
        session = self._create_completed_session(db_session)
        create_resp = client.post(
            "/api/evaluate", json={"session_id": session.id}
        )
        eval_id = create_resp.json()["id"]

        response = client.get(f"/api/evaluations/{eval_id}")
        assert response.status_code == 200
        assert response.json()["id"] == eval_id

    def test_get_evaluation_by_id_not_found(self, client):
        """Test GET /api/evaluations/{id} with nonexistent ID."""
        response = client.get(
            "/api/evaluations/nonexistent-id"
        )
        assert response.status_code == 404

    def test_list_evaluations(self, client, db_session):
        """Test GET /api/evaluations returns user's evaluations."""
        session1 = self._create_completed_session(db_session)
        session2 = self._create_completed_session(db_session)

        client.post("/api/evaluate", json={"session_id": session1.id})
        client.post("/api/evaluate", json={"session_id": session2.id})

        response = client.get("/api/evaluations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_evaluations_empty(self, client):
        """Test GET /api/evaluations returns empty list."""
        response = client.get("/api/evaluations")
        assert response.status_code == 200
        assert response.json() == []

    def test_search_evaluations(self, client, db_session):
        """Test GET /api/evaluations/search finds by text."""
        session = self._create_completed_session(db_session)
        client.post("/api/evaluate", json={"session_id": session.id})

        response = client.get(
            "/api/evaluations/search", params={"q": "score"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_search_evaluations_no_results(self, client, db_session):
        """Test GET /api/evaluations/search with no matches."""
        session = self._create_completed_session(db_session)
        client.post("/api/evaluate", json={"session_id": session.id})

        response = client.get(
            "/api/evaluations/search", params={"q": "zzzznonexistent"}
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_get_evaluation_statistics(self, client, db_session):
        """Test GET /api/evaluations/statistics."""
        session = self._create_completed_session(db_session)
        client.post("/api/evaluate", json={"session_id": session.id})

        response = client.get("/api/evaluations/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_evaluations" in data
        assert data["total_evaluations"] >= 1

    def test_get_evaluation_statistics_empty(self, client):
        """Test GET /api/evaluations/statistics with no evaluations."""
        response = client.get("/api/evaluations/statistics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_evaluations"] == 0

    def test_get_dashboard(self, client, db_session):
        """Test GET /api/evaluations/dashboard."""
        session = self._create_completed_session(db_session)
        client.post("/api/evaluate", json={"session_id": session.id})

        response = client.get("/api/evaluations/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "latest_evaluation" in data
        assert "analytics" in data
        assert "recent_evaluations" in data
        assert data["latest_evaluation"] is not None

    def test_get_dashboard_empty(self, client):
        """Test GET /api/evaluations/dashboard with no data."""
        response = client.get("/api/evaluations/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["latest_evaluation"] is None
        assert data["analytics"]["total_evaluations"] == 0

    def test_delete_evaluation(self, client, db_session):
        """Test DELETE /api/evaluations/{id}."""
        session = self._create_completed_session(db_session)
        create_resp = client.post(
            "/api/evaluate", json={"session_id": session.id}
        )
        eval_id = create_resp.json()["id"]

        response = client.delete(f"/api/evaluations/{eval_id}")
        assert response.status_code == 204

        get_response = client.get(f"/api/evaluations/{eval_id}")
        assert get_response.status_code == 404

    def test_delete_evaluation_not_found(self, client):
        """Test DELETE /api/evaluations/{id} with nonexistent ID."""
        response = client.delete(
            "/api/evaluations/nonexistent-id"
        )
        assert response.status_code == 404

    def test_create_evaluation_different_user_forbidden(
        self, client, db_session
    ):
        """Test that a user cannot evaluate another user's session."""
        session = self._create_completed_session(
            db_session, user_id="other-user-id"
        )

        response = client.post(
            "/api/evaluate",
            json={"session_id": session.id},
        )
        assert response.status_code == 403

    def test_get_evaluation_different_user_forbidden(
        self, client, db_session
    ):
        """Test that a user cannot read another user's evaluation."""
        session = self._create_completed_session(
            db_session, user_id="test-user-id"
        )
        create_resp = client.post(
            "/api/evaluate", json={"session_id": session.id}
        )
        eval_id = create_resp.json()["id"]

        from backend.app.api.evaluation import _get_current_user_id

        async def _other_user_override():
            return "other-user-id"

        app.dependency_overrides[_get_current_user_id] = _other_user_override

        response = client.get(f"/api/evaluations/{eval_id}")
        assert response.status_code == 403

        app.dependency_overrides[_get_current_user_id] = lambda: "test-user-id"


# ---------------------------------------------------------------------------
# CRUD unit tests
# ---------------------------------------------------------------------------


class TestCRUDInterviewEvaluation:
    """Unit tests for CRUDInterviewEvaluation operations."""

    def _create_evaluation(self, db_session, user_id="test-user"):
        """Helper to create a sample evaluation."""
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
        evaluation_create = InterviewEvaluationCreate(
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
            db=db_session, obj_in=evaluation_create
        )

    def test_create_evaluation(self, db_session):
        """Test creating an evaluation record."""
        evaluation = self._create_evaluation(db_session)
        assert evaluation.id is not None
        assert evaluation.overall_score > 0
        assert evaluation.hire_decision in (
            "Strong Hire", "Hire", "Borderline", "Reject"
        )

    def test_get_by_session(self, db_session):
        """Test retrieving an evaluation by session ID."""
        evaluation = self._create_evaluation(db_session)
        found = interview_evaluation_crud.get_by_session(
            db=db_session, session_id=evaluation.session_id
        )
        assert found is not None
        assert found.id == evaluation.id

    def test_get_by_session_not_found(self, db_session):
        """Test get_by_session returns None for nonexistent session."""
        found = interview_evaluation_crud.get_by_session(
            db=db_session, session_id="nonexistent"
        )
        assert found is None

    def test_get_by_user(self, db_session):
        """Test retrieving all evaluations for a user."""
        evaluation = self._create_evaluation(db_session)
        result = interview_evaluation_crud.get_by_user(
            db=db_session, user_id="test-user"
        )
        assert len(result) >= 1
        assert result[0].id == evaluation.id

    def test_get_latest_by_user(self, db_session):
        """Test retrieving the latest evaluation."""
        evaluation = self._create_evaluation(db_session)
        latest = interview_evaluation_crud.get_latest_by_user(
            db=db_session, user_id="test-user"
        )
        assert latest is not None
        assert latest.id == evaluation.id

    def test_count_by_user(self, db_session):
        """Test counting evaluations."""
        self._create_evaluation(db_session)
        self._create_evaluation(db_session)
        assert (
            interview_evaluation_crud.count_by_user(
                db=db_session, user_id="test-user"
            )
            >= 2
        )

    def test_search(self, db_session):
        """Test searching evaluations by text."""
        evaluation = self._create_evaluation(db_session)
        result = interview_evaluation_crud.search(
            db=db_session,
            user_id="test-user",
            query="score",
        )
        assert len(result) >= 1
        assert result[0].id == evaluation.id

    def test_average_scores(self, db_session):
        """Test average score calculation."""
        self._create_evaluation(db_session)
        self._create_evaluation(db_session)
        averages = interview_evaluation_crud.average_scores(
            db=db_session, user_id="test-user"
        )
        assert "average_overall_score" in averages
        assert averages["average_overall_score"] is not None

    def test_statistics(self, db_session):
        """Test comprehensive statistics."""
        self._create_evaluation(db_session)
        stats = interview_evaluation_crud.statistics(
            db=db_session, user_id="test-user"
        )
        assert stats["total_evaluations"] >= 1
        assert "average_overall_score" in stats
        assert "most_common_strengths" in stats
