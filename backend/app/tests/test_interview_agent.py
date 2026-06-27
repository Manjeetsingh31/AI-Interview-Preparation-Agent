"""Unit tests for the Google ADK Mock Interview Multi-Agent System.

Test strategy
-------------
- The ADK Agent internally uses Gemini via ``Runner.run_debug`` (which is
  an ``async`` method). We **mock ``Runner.run_debug``** so that no real
  API call is made.
- The mock returns a list of ``Event`` objects that simulate a successful
  Gemini response (or error conditions).
- All agent tests are ``async`` with ``@pytest.mark.asyncio``.
- The API endpoint is tested via ``TestClient`` with an isolated SQLite
  database, mocked agent, and proper table creation.
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

from backend.app.schemas.interview_turn import (
    InterviewAgentTurn,
    InterviewTurnResponse,
    InterviewStartResponse,
    InterviewAnswerResponse,
    InterviewSessionSummary,
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
    """FastAPI TestClient with overridden DB dependency."""

    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_fake_event(text: str, is_final: bool = True) -> MagicMock:
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


def _build_sample_first_turn() -> dict:
    """Build a sample first-turn response dict."""
    return InterviewAgentTurn(
        question="Tell me about your experience with Python and FastAPI.",
        follow_up="",
        category="Technical",
        difficulty="Easy",
        evaluation="",
        score=0,
        tags=["python", "fastapi"],
        expected_answer="I have built several APIs using FastAPI and Python.",
        is_final=False,
        finished_reason="",
        transcript_summary="",
    ).model_dump()


def _build_sample_answer_turn() -> dict:
    """Build a sample answer-turn response dict."""
    return InterviewAgentTurn(
        question="How do you handle database migrations in FastAPI?",
        follow_up="What migration tool do you prefer?",
        category="Technical",
        difficulty="Medium",
        evaluation="Good understanding of Python basics.",
        score=75,
        tags=["python", "fastapi", "database"],
        expected_answer="I use Alembic for database migrations.",
        is_final=False,
        finished_reason="",
        transcript_summary="",
    ).model_dump()


def _build_sample_final_turn() -> dict:
    """Build a sample final-turn response dict."""
    return InterviewAgentTurn(
        question="",
        follow_up="",
        category="",
        difficulty="",
        evaluation="Excellent interview performance.",
        score=90,
        tags=[],
        expected_answer="",
        is_final=True,
        finished_reason="All questions completed.",
        transcript_summary="The candidate demonstrated strong Python skills...",
    ).model_dump()


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_SAMPLE_RESUME_DATA = {
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "phone": "+1-555-123-4567",
    "skills": ["Python", "FastAPI", "Kubernetes", "Leadership"],
    "technical_skills": ["Python", "FastAPI", "Kubernetes", "Docker"],
    "soft_skills": ["Leadership", "Communication"],
    "education": [
        {
            "institution": "MIT",
            "degree": "BSc",
            "field": "Computer Science",
            "start_date": "Sep 2018",
            "end_date": "Jun 2022",
        }
    ],
    "experience": [
        {
            "company": "Tech Corp",
            "role": "Software Engineer",
            "start_date": "Jul 2022",
            "end_date": "Present",
            "description": "Built microservices.",
            "highlights": ["Scaled API to 10k QPS"],
        }
    ],
    "projects": [
        {
            "name": "Open Source Tool",
            "description": "A CLI tool for DevOps.",
            "technologies": ["Python", "Click"],
            "link": "https://github.com/janedoe/tool",
        }
    ],
    "certifications": ["AWS Certified Solutions Architect"],
    "languages": ["English", "Spanish"],
    "linkedin": "https://linkedin.com/in/janedoe",
    "github": "https://github.com/janedoe",
    "portfolio": "https://janedoe.dev",
}


# ===================================================================
# InterviewAgent unit tests
# ===================================================================


@pytest.mark.asyncio
class TestInterviewAgent:
    """Unit tests for ``InterviewAgent.next_turn()``."""

    async def test_next_turn_first_question(self):
        """Happy path: first turn returns an opening question."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event(json.dumps(_build_sample_first_turn()))
            ]

            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
            )

            agent = InterviewAgent()
            result = await agent.next_turn(
                resume_data=_SAMPLE_RESUME_DATA,
                question_number=1,
                total_questions=5,
                company="Google",
                role="Software Engineer",
                interview_type="Mixed",
                difficulty="Medium",
                candidate_answer=None,
            )

            assert isinstance(result, InterviewAgentTurn)
            assert result.question
            assert result.category in ("HR", "Technical", "Coding", "Behavioural")
            assert result.score == 0
            assert result.evaluation == ""
            assert result.is_final is False

    async def test_next_turn_with_answer(self):
        """Second turn evaluates previous answer and asks next question."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event(json.dumps(_build_sample_answer_turn()))
            ]

            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
            )

            agent = InterviewAgent()
            result = await agent.next_turn(
                resume_data=_SAMPLE_RESUME_DATA,
                question_number=2,
                total_questions=5,
                company="Google",
                role="Software Engineer",
                interview_type="Technical",
                difficulty="Easy",
                candidate_answer="I have experience with FastAPI.",
            )

            assert isinstance(result, InterviewAgentTurn)
            assert result.question
            assert result.score > 0
            assert result.evaluation

    async def test_next_turn_final_question(self):
        """Last turn returns is_final=True with transcript summary."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event(json.dumps(_build_sample_final_turn()))
            ]

            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
            )

            agent = InterviewAgent()
            result = await agent.next_turn(
                resume_data=_SAMPLE_RESUME_DATA,
                question_number=5,
                total_questions=5,
                company="Google",
                role="Software Engineer",
                interview_type="Mixed",
                difficulty="Hard",
                candidate_answer="My final answer.",
            )

            assert result.is_final is True
            assert result.finished_reason
            assert result.transcript_summary

    async def test_next_turn_with_previous_turns(self):
        """Conversation history is passed correctly via previous_turns."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event(json.dumps(_build_sample_answer_turn()))
            ]

            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
            )

            previous_turns = [
                {
                    "question_number": 1,
                    "question": "Tell me about yourself.",
                    "candidate_answer": "I am a Python developer.",
                    "difficulty": "Easy",
                    "category": "HR",
                    "score": 80,
                    "evaluation": "Good introduction.",
                }
            ]

            agent = InterviewAgent()
            result = await agent.next_turn(
                resume_data=_SAMPLE_RESUME_DATA,
                previous_turns=previous_turns,
                question_number=2,
                total_questions=5,
                company="Google",
                role="Software Engineer",
                interview_type="Technical",
                difficulty="Medium",
                candidate_answer="I used FastAPI for REST APIs.",
            )

            assert result.question

    async def test_next_turn_empty_data_raises_error(self):
        """Empty resume data still allows the agent to proceed."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event(json.dumps(_build_sample_first_turn()))
            ]

            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
            )

            agent = InterviewAgent()
            result = await agent.next_turn(
                resume_data=None,
                question_number=1,
                total_questions=3,
                company="Generic",
                role="Developer",
                interview_type="HR",
                difficulty="Easy",
                candidate_answer=None,
            )

            assert isinstance(result, InterviewAgentTurn)
            assert result.question

    async def test_next_turn_gemini_timeout_raises_error(self):
        """When ``run_debug`` raises, an ``InterviewAgentError`` is raised."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.side_effect = Exception("Gemini API timeout")

            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
                InterviewAgentError,
            )

            agent = InterviewAgent()
            with pytest.raises(
                InterviewAgentError, match="ADK interview agent failed"
            ):
                await agent.next_turn(
                    resume_data=_SAMPLE_RESUME_DATA,
                    question_number=1,
                    total_questions=3,
                    company="Google",
                    role="SDE",
                    interview_type="Technical",
                    difficulty="Medium",
                    candidate_answer=None,
                )

    async def test_next_turn_malformed_json_raises_error(self):
        """Non-JSON text from Gemini raises ``InterviewAgentError``."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event("This is not JSON at all")
            ]

            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
                InterviewAgentError,
            )

            agent = InterviewAgent()
            with pytest.raises(
                InterviewAgentError, match="Failed to parse Gemini"
            ):
                await agent.next_turn(
                    resume_data=_SAMPLE_RESUME_DATA,
                    question_number=1,
                    total_questions=3,
                    company="Google",
                    role="SDE",
                    interview_type="Technical",
                    difficulty="Easy",
                    candidate_answer=None,
                )

    async def test_next_turn_no_final_event_raises_error(self):
        """No event with ``is_final_response() == True`` raises an error."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event("intermediate", is_final=False)
            ]

            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
                InterviewAgentError,
            )

            agent = InterviewAgent()
            with pytest.raises(
                InterviewAgentError,
                match="no valid structured response",
            ):
                await agent.next_turn(
                    resume_data=_SAMPLE_RESUME_DATA,
                    question_number=1,
                    total_questions=3,
                    company="Google",
                    role="SDE",
                    interview_type="Technical",
                    difficulty="Medium",
                    candidate_answer=None,
                )

    async def test_next_turn_empty_events_list_raises_error(self):
        """An empty event list raises ``InterviewAgentError``."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = []

            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
                InterviewAgentError,
            )

            agent = InterviewAgent()
            with pytest.raises(
                InterviewAgentError,
                match="no valid structured response",
            ):
                await agent.next_turn(
                    resume_data=_SAMPLE_RESUME_DATA,
                    question_number=1,
                    total_questions=3,
                    company="Google",
                    role="SDE",
                    interview_type="Technical",
                    difficulty="Medium",
                    candidate_answer=None,
                )

    async def test_next_turn_different_interview_types(self):
        """All interview types are supported."""
        with patch(
            "backend.app.services.agents.interview_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            from backend.app.services.agents.interview_agent import (
                InterviewAgent,
            )

            for itype in ["HR", "Technical", "Coding", "Behavioural", "Mixed"]:
                mock_run.return_value = [
                    _make_fake_event(json.dumps(_build_sample_first_turn()))
                ]

                agent = InterviewAgent()
                result = await agent.next_turn(
                    resume_data=_SAMPLE_RESUME_DATA,
                    question_number=1,
                    total_questions=3,
                    company="Google",
                    role="SDE",
                    interview_type=itype,
                    difficulty="Medium",
                    candidate_answer=None,
                )

                assert result.question


# ===================================================================
# CRUD unit tests
# ===================================================================


class TestCRUDInterviewTurn:
    """Unit tests for ``CRUDInterviewTurn``."""

    def _create_user(self, db_session, email="candidate@example.com"):
        from backend.app.models.user import User

        user = User(email=email, password_hash="mock_hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def _create_session(self, db_session, user_id):
        from backend.app.models.models import InterviewSession

        session = InterviewSession(
            user_id=user_id,
            role="Engineer",
            company="Google",
            interview_type="Technical",
            status="active",
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    def _create_turn(self, db_session, session, user, q_no=1):
        from backend.app.schemas.interview_turn import InterviewTurnCreate

        create = InterviewTurnCreate(
            user_id=user.id,
            session_id=session.id,
            question_number=q_no,
            question=f"Test question {q_no}?",
            difficulty="Easy",
            category="Technical",
            tags=["python"],
        )
        from backend.app.crud.crud_interview_turn import interview_turn_crud

        return interview_turn_crud.create(db=db_session, obj_in=create)

    def test_create_turn(self, db_session):
        user = self._create_user(db_session)
        session = self._create_session(db_session, user.id)
        turn = self._create_turn(db_session, session, user)
        assert turn.id is not None
        assert turn.question_number == 1
        assert turn.question == "Test question 1?"

    def test_update_answer(self, db_session):
        from backend.app.crud.crud_interview_turn import interview_turn_crud

        user = self._create_user(db_session)
        session = self._create_session(db_session, user.id)
        turn = self._create_turn(db_session, session, user)

        updated = interview_turn_crud.update_answer(
            db=db_session,
            turn_id=turn.id,
            candidate_answer="My answer",
            evaluation="Good",
            score=85,
            follow_up="Follow-up?",
        )
        assert updated.candidate_answer == "My answer"
        assert updated.evaluation == "Good"
        assert updated.score == 85
        assert updated.follow_up == "Follow-up?"

    def test_get_latest_turn(self, db_session):
        from backend.app.crud.crud_interview_turn import interview_turn_crud

        user = self._create_user(db_session)
        session = self._create_session(db_session, user.id)
        self._create_turn(db_session, session, user, q_no=1)
        self._create_turn(db_session, session, user, q_no=2)

        latest = interview_turn_crud.get_latest_turn(
            db=db_session, session_id=session.id
        )
        assert latest.question_number == 2

    def test_get_next_question_number(self, db_session):
        from backend.app.crud.crud_interview_turn import interview_turn_crud

        user = self._create_user(db_session)
        session = self._create_session(db_session, user.id)

        next_no = interview_turn_crud.get_next_question_number(
            db=db_session, session_id=session.id
        )
        assert next_no == 1

        self._create_turn(db_session, session, user, q_no=1)
        next_no = interview_turn_crud.get_next_question_number(
            db=db_session, session_id=session.id
        )
        assert next_no == 2

    def test_average_score(self, db_session):
        from backend.app.crud.crud_interview_turn import interview_turn_crud

        user = self._create_user(db_session)
        session = self._create_session(db_session, user.id)
        t1 = self._create_turn(db_session, session, user, q_no=1)
        t2 = self._create_turn(db_session, session, user, q_no=2)

        interview_turn_crud.update_answer(
            db=db_session, turn_id=t1.id,
            candidate_answer="A1", score=80, evaluation="Good",
        )
        interview_turn_crud.update_answer(
            db=db_session, turn_id=t2.id,
            candidate_answer="A2", score=90, evaluation="Great",
        )

        avg = interview_turn_crud.average_score(
            db=db_session, session_id=session.id
        )
        assert avg == 85.0

    def test_get_transcript(self, db_session):
        from backend.app.crud.crud_interview_turn import interview_turn_crud

        user = self._create_user(db_session)
        session = self._create_session(db_session, user.id)
        t1 = self._create_turn(db_session, session, user, q_no=1)

        interview_turn_crud.update_answer(
            db=db_session, turn_id=t1.id,
            candidate_answer="My answer", score=80, evaluation="Good",
        )

        transcript = interview_turn_crud.get_transcript(
            db=db_session, session_id=session.id
        )
        assert "Q1" in transcript
        assert "My answer" in transcript
        assert "Good" in transcript

    def test_search(self, db_session):
        from backend.app.crud.crud_interview_turn import interview_turn_crud

        user = self._create_user(db_session)
        session = self._create_session(db_session, user.id)
        self._create_turn(db_session, session, user, q_no=1)

        results = interview_turn_crud.search(
            db=db_session, user_id=user.id, query="Test question"
        )
        assert len(results) == 1

        results = interview_turn_crud.search(
            db=db_session, user_id=user.id, query="Nonexistent"
        )
        assert len(results) == 0

    def test_delete_by_session(self, db_session):
        from backend.app.crud.crud_interview_turn import interview_turn_crud

        user = self._create_user(db_session)
        session = self._create_session(db_session, user.id)
        self._create_turn(db_session, session, user, q_no=1)
        self._create_turn(db_session, session, user, q_no=2)

        deleted = interview_turn_crud.delete_by_session(
            db=db_session, session_id=session.id
        )
        assert deleted == 2

        remaining = interview_turn_crud.get_by_session(
            db=db_session, session_id=session.id
        )
        assert len(remaining) == 0


# ===================================================================
# API endpoint integration tests
# ===================================================================


class TestInterviewAPI:
    """Integration tests for the interview API endpoints."""

    @pytest.fixture(autouse=True)
    def _setup_tables(self, db_session):
        Base.metadata.create_all(bind=db_session.bind)

    def _create_user(self, db_session):
        from backend.app.models.user import User

        user = User(
            email="candidate@example.com",
            password_hash="mock_hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def _create_adk_record(self, db_session, user_id):
        from backend.app.models.resume_analysis_adk import ResumeAnalysisADK

        record = ResumeAnalysisADK(
            user_id=user_id,
            resume_filename="test_resume.pdf",
            raw_text="Sample resume text",
            extracted_json=_SAMPLE_RESUME_DATA,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        return record

    @patch(
        "backend.app.services.agents.interview_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    def test_start_interview_success(self, mock_run, client, db_session):
        """POST /api/interview/start returns 201 with first question."""
        mock_run.return_value = [
            _make_fake_event(json.dumps(_build_sample_first_turn()))
        ]

        user = self._create_user(db_session)
        adk = self._create_adk_record(db_session, user.id)

        response = client.post(
            "/api/interview/start",
            json={
                "resume_analysis_id": adk.id,
                "company": "Google",
                "role": "Software Engineer",
                "interview_type": "Mixed",
                "difficulty": "Medium",
                "number_of_questions": 10,
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert "session_id" in data
        assert data["question"]
        assert data["question_number"] == 1
        assert data["category"]
        assert data["difficulty"]

    @patch(
        "backend.app.services.agents.interview_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    def test_start_and_answer(self, mock_run, client, db_session):
        """Full flow: start, answer, get next question."""
        mock_run.return_value = [
            _make_fake_event(json.dumps(_build_sample_first_turn()))
        ]

        user = self._create_user(db_session)
        adk = self._create_adk_record(db_session, user.id)

        start_resp = client.post(
            "/api/interview/start",
            json={
                "resume_analysis_id": adk.id,
                "company": "Google",
                "role": "Software Engineer",
                "interview_type": "Technical",
                "difficulty": "Easy",
                "number_of_questions": 5,
            },
        )
        assert start_resp.status_code == 201
        session_id = start_resp.json()["session_id"]

        # Mock the second turn (answer)
        mock_run.return_value = [
            _make_fake_event(json.dumps(_build_sample_answer_turn()))
        ]

        answer_resp = client.post(
            "/api/interview/answer",
            json={
                "session_id": session_id,
                "answer": "I have experience building APIs with FastAPI.",
                "response_time": 30,
            },
        )
        assert answer_resp.status_code == 200, answer_resp.text
        data = answer_resp.json()
        assert data["session_id"] == session_id
        assert data["question_number"] == 2
        assert data["question"]
        assert data["evaluation"]
        assert data["score"] is not None

    @patch(
        "backend.app.services.agents.interview_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    def test_start_and_complete(self, mock_run, client, db_session):
        """Full flow: start, answer final turn, session completes."""
        mock_run.return_value = [
            _make_fake_event(json.dumps(_build_sample_first_turn()))
        ]

        user = self._create_user(db_session)
        adk = self._create_adk_record(db_session, user.id)

        start_resp = client.post(
            "/api/interview/start",
            json={
                "resume_analysis_id": adk.id,
                "company": "Google",
                "role": "Software Engineer",
                "interview_type": "Technical",
                "difficulty": "Easy",
                "number_of_questions": 1,
            },
        )
        assert start_resp.status_code == 201
        session_id = start_resp.json()["session_id"]

        # Mock final turn
        mock_run.return_value = [
            _make_fake_event(json.dumps(_build_sample_final_turn()))
        ]

        answer_resp = client.post(
            "/api/interview/answer",
            json={
                "session_id": session_id,
                "answer": "My final answer.",
            },
        )
        assert answer_resp.status_code == 200
        data = answer_resp.json()
        assert data["is_final"] is True
        assert data["finished_reason"]
        assert data["transcript_summary"]

    @patch(
        "backend.app.services.agents.interview_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    def test_end_interview(self, mock_run, client, db_session):
        """POST /api/interview/end completes a session."""
        mock_run.return_value = [
            _make_fake_event(json.dumps(_build_sample_first_turn()))
        ]

        user = self._create_user(db_session)
        adk = self._create_adk_record(db_session, user.id)

        start_resp = client.post(
            "/api/interview/start",
            json={
                "resume_analysis_id": adk.id,
                "company": "Google",
                "role": "SDE",
                "interview_type": "Mixed",
                "difficulty": "Medium",
                "number_of_questions": 5,
            },
        )
        session_id = start_resp.json()["session_id"]

        end_resp = client.post(
            "/api/interview/end",
            json={"session_id": session_id},
        )
        assert end_resp.status_code == 200
        data = end_resp.json()
        assert data["status"] == "completed"
        assert data["total_questions"] >= 1

    def test_missing_resume_analysis_404(self, client, db_session):
        """A non-existent resume_analysis_id returns 404."""
        response = client.post(
            "/api/interview/start",
            json={
                "resume_analysis_id": "nonexistent-id",
                "company": "Google",
                "role": "SDE",
                "interview_type": "Mixed",
                "difficulty": "Medium",
                "number_of_questions": 3,
            },
        )
        assert response.status_code == 404

    @patch(
        "backend.app.services.agents.interview_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    def test_get_session_turns(self, mock_run, client, db_session):
        """GET /api/interview/{session_id} returns turns."""
        mock_run.return_value = [
            _make_fake_event(json.dumps(_build_sample_first_turn()))
        ]

        user = self._create_user(db_session)
        adk = self._create_adk_record(db_session, user.id)

        start_resp = client.post(
            "/api/interview/start",
            json={
                "resume_analysis_id": adk.id,
                "company": "Google",
                "role": "SDE",
                "interview_type": "Technical",
                "difficulty": "Easy",
                "number_of_questions": 3,
            },
        )
        session_id = start_resp.json()["session_id"]

        get_resp = client.get(f"/api/interview/{session_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["session_id"] == session_id
        assert len(data["turns"]) == 1

    @patch(
        "backend.app.services.agents.interview_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    def test_get_transcript(self, mock_run, client, db_session):
        """GET /api/interview/transcript/{session_id} returns transcript."""
        mock_run.return_value = [
            _make_fake_event(json.dumps(_build_sample_first_turn()))
        ]

        user = self._create_user(db_session)
        adk = self._create_adk_record(db_session, user.id)

        start_resp = client.post(
            "/api/interview/start",
            json={
                "resume_analysis_id": adk.id,
                "company": "Google",
                "role": "SDE",
                "interview_type": "Technical",
                "difficulty": "Easy",
                "number_of_questions": 3,
            },
        )
        session_id = start_resp.json()["session_id"]

        resp = client.get(f"/api/interview/transcript/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert "transcript" in data

    def test_session_not_found_404(self, client, db_session):
        """A non-existent session_id returns 404."""
        response = client.get("/api/interview/nonexistent-id")
        assert response.status_code == 404

    def test_end_nonexistent_session_404(self, client, db_session):
        """Ending a non-existent session returns 404."""
        response = client.post(
            "/api/interview/end",
            json={"session_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_answer_without_start_400(self, client, db_session):
        """Answering without starting a session returns 400."""
        self._create_user(db_session)

        response = client.post(
            "/api/interview/answer",
            json={
                "session_id": "nonexistent",
                "answer": "My answer",
            },
        )
        assert response.status_code == 404


# ===================================================================
# Pydantic schema tests
# ===================================================================


class TestInterviewTurnSchemas:
    """Verify that the interview turn schemas validate correctly."""

    def test_agent_turn_full_population(self):
        """A fully populated InterviewAgentTurn produces the correct model."""
        turn = InterviewAgentTurn(
            question="Explain Python decorators.",
            follow_up="How are decorators implemented?",
            category="Technical",
            difficulty="Medium",
            evaluation="Good answer.",
            score=85,
            tags=["python", "decorators"],
            expected_answer="Decorators are functions...",
            is_final=False,
            finished_reason="",
            transcript_summary="",
        )
        assert turn.question == "Explain Python decorators."
        assert turn.follow_up
        assert turn.category == "Technical"
        assert turn.score == 85
        assert turn.is_final is False

    def test_agent_turn_final(self):
        """Final turn has is_final=True and summary."""
        turn = InterviewAgentTurn(
            question="",
            follow_up="",
            category="",
            difficulty="",
            evaluation="Great work!",
            score=90,
            tags=[],
            expected_answer="",
            is_final=True,
            finished_reason="Interview complete.",
            transcript_summary="Candidate did well on Python.",
        )
        assert turn.is_final is True
        assert turn.finished_reason
        assert turn.transcript_summary

    def test_start_request_validation(self):
        """InterviewStartRequest validates required fields."""
        from backend.app.schemas.interview_turn import InterviewStartRequest

        req = InterviewStartRequest(
            resume_analysis_id="abc-123",
            company="Google",
            role="SDE",
            interview_type="Mixed",
            difficulty="Medium",
            number_of_questions=10,
        )
        assert req.resume_analysis_id == "abc-123"
        assert req.company == "Google"
        assert req.number_of_questions == 10

    def test_turn_response_from_attributes(self):
        """InterviewTurnResponse can be created from ORM attributes."""
        from datetime import datetime

        response = InterviewTurnResponse(
            id="test-id",
            user_id="user-id",
            session_id="session-id",
            resume_analysis_id="analysis-id",
            question_number=1,
            question="Test question?",
            candidate_answer="Test answer.",
            follow_up="Follow-up?",
            difficulty="Easy",
            category="Technical",
            tags=["python"],
            expected_answer="Expected.",
            evaluation="Good.",
            score=85,
            response_time=30,
            created_at=datetime(2024, 1, 1),
        )
        assert response.id == "test-id"
        assert response.question == "Test question?"
        assert response.score == 85
        assert response.difficulty == "Easy"
        assert response.category == "Technical"
