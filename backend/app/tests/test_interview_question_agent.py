"""Unit tests for the Google ADK Interview Question Generator Agent.

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

from backend.app.schemas.interview_question import (
    InterviewQuestionItem,
    InterviewQuestionList,
    InterviewQuestionResponse,
)
from backend.app.services.agents.interview_question_agent import (
    InterviewQuestionError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh file-based SQLite database per test.

    Uses a temporary file instead of ``:memory:`` so that connections
    made from different threads (e.g. FastAPI ``TestClient`` running
    sync dependencies in a thread pool) all see the same database.
    """
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


def _build_sample_question_list(n: int = 3) -> dict:
    """Build a sample InterviewQuestionList dict for mocking."""
    questions = []
    for i in range(n):
        questions.append(
            InterviewQuestionItem(
                type="Technical" if i % 2 == 0 else "HR",
                question=f"Sample question {i+1}",
                expected_answer=f"Expected answer for question {i+1}",
                hints=[f"Hint {i+1}a", f"Hint {i+1}b"],
                follow_up=f"Follow-up for question {i+1}",
                tags=[f"tag{i+1}a", f"tag{i+1}b"],
            ).model_dump()
        )
    return InterviewQuestionList(questions=questions).model_dump()


# ===================================================================
# InterviewQuestionAgent unit tests
# ===================================================================


@pytest.mark.asyncio
class TestInterviewQuestionAgent:
    """Unit tests for ``InterviewQuestionAgent.generate()``.

    All tests are ``async`` because ``generate()`` awaits the ADK runner.
    """

    async def test_generate_success(self):
        """Happy path: valid resume data returns a populated question list."""
        with patch(
            "backend.app.services.agents.interview_question_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event(
                    json.dumps(_build_sample_question_list(3))
                )
            ]

            from backend.app.services.agents.interview_question_agent import (
                InterviewQuestionAgent,
            )

            agent = InterviewQuestionAgent()
            result = await agent.generate(
                resume_data=_SAMPLE_RESUME_DATA,
                company="Google",
                role="Software Engineer",
                interview_type="Mixed",
                difficulty="Medium",
                number_of_questions=3,
            )

            assert isinstance(result, InterviewQuestionList)
            assert len(result.questions) == 3
            for q in result.questions:
                assert q.question
                assert q.expected_answer
                assert q.type in (
                    "HR", "Technical", "Coding", "Behavioral",
                    "Resume", "System Design", "Project Discussion",
                )

    async def test_generate_with_different_counts(self):
        """Different question counts are handled correctly."""
        with patch(
            "backend.app.services.agents.interview_question_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            for n in [1, 5, 10]:
                mock_run.return_value = [
                    _make_fake_event(
                        json.dumps(_build_sample_question_list(n))
                    )
                ]

                from backend.app.services.agents.interview_question_agent import (
                    InterviewQuestionAgent,
                )

                agent = InterviewQuestionAgent()
                result = await agent.generate(
                    resume_data=_SAMPLE_RESUME_DATA,
                    company="Google",
                    role="Software Engineer",
                    interview_type="Mixed",
                    difficulty="Medium",
                    number_of_questions=n,
                )

                assert len(result.questions) == n

    async def test_generate_empty_data_raises_error(self):
        """Empty resume data raises ``InterviewQuestionError`` immediately."""
        from backend.app.services.agents.interview_question_agent import (
            InterviewQuestionAgent,
        )

        agent = InterviewQuestionAgent()

        with pytest.raises(
            InterviewQuestionError, match="Resume data is empty"
        ):
            await agent.generate(
                resume_data={},
                company="Google",
                role="SDE",
                interview_type="Technical",
                difficulty="Medium",
            )

    async def test_generate_gemini_timeout_raises_error(self):
        """When ``run_debug`` raises, an ``InterviewQuestionError`` is raised."""
        with patch(
            "backend.app.services.agents.interview_question_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.side_effect = Exception("Gemini API timeout")

            from backend.app.services.agents.interview_question_agent import (
                InterviewQuestionAgent,
            )

            agent = InterviewQuestionAgent()
            with pytest.raises(
                InterviewQuestionError, match="ADK agent failed"
            ):
                await agent.generate(
                    resume_data=_SAMPLE_RESUME_DATA,
                    company="Google",
                    role="SDE",
                    interview_type="Technical",
                    difficulty="Hard",
                )

    async def test_generate_malformed_json_raises_error(self):
        """Non-JSON text from Gemini raises ``InterviewQuestionError``."""
        with patch(
            "backend.app.services.agents.interview_question_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event("This is not JSON at all")
            ]

            from backend.app.services.agents.interview_question_agent import (
                InterviewQuestionAgent,
            )

            agent = InterviewQuestionAgent()
            with pytest.raises(
                InterviewQuestionError, match="Failed to parse Gemini"
            ):
                await agent.generate(
                    resume_data=_SAMPLE_RESUME_DATA,
                    company="Google",
                    role="SDE",
                    interview_type="Technical",
                    difficulty="Easy",
                )

    async def test_generate_no_final_event_raises_error(self):
        """No event with ``is_final_response() == True`` raises an error."""
        with patch(
            "backend.app.services.agents.interview_question_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event("intermediate", is_final=False)
            ]

            from backend.app.services.agents.interview_question_agent import (
                InterviewQuestionAgent,
            )

            agent = InterviewQuestionAgent()
            with pytest.raises(
                InterviewQuestionError,
                match="no valid structured response",
            ):
                await agent.generate(
                    resume_data=_SAMPLE_RESUME_DATA,
                    company="Google",
                    role="SDE",
                    interview_type="Technical",
                    difficulty="Medium",
                )

    async def test_generate_empty_events_list_raises_error(self):
        """An empty event list raises ``InterviewQuestionError``."""
        with patch(
            "backend.app.services.agents.interview_question_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = []

            from backend.app.services.agents.interview_question_agent import (
                InterviewQuestionAgent,
            )

            agent = InterviewQuestionAgent()
            with pytest.raises(
                InterviewQuestionError,
                match="no valid structured response",
            ):
                await agent.generate(
                    resume_data=_SAMPLE_RESUME_DATA,
                    company="Google",
                    role="SDE",
                    interview_type="Technical",
                    difficulty="Medium",
                )

    async def test_generate_different_difficulties(self):
        """Questions are generated for all difficulty levels."""
        with patch(
            "backend.app.services.agents.interview_question_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            from backend.app.services.agents.interview_question_agent import (
                InterviewQuestionAgent,
            )

            for diff in ["Easy", "Medium", "Hard"]:
                mock_run.return_value = [
                    _make_fake_event(
                        json.dumps(_build_sample_question_list(3))
                    )
                ]

                agent = InterviewQuestionAgent()
                result = await agent.generate(
                    resume_data=_SAMPLE_RESUME_DATA,
                    company="Google",
                    role="SDE",
                    interview_type="Mixed",
                    difficulty=diff,
                    number_of_questions=3,
                )

                assert len(result.questions) == 3

    async def test_generate_different_interview_types(self):
        """Questions are generated for all interview types."""
        with patch(
            "backend.app.services.agents.interview_question_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            from backend.app.services.agents.interview_question_agent import (
                InterviewQuestionAgent,
            )

            for itype in ["HR", "Technical", "Coding", "Mixed"]:
                mock_run.return_value = [
                    _make_fake_event(
                        json.dumps(_build_sample_question_list(2))
                    )
                ]

                agent = InterviewQuestionAgent()
                result = await agent.generate(
                    resume_data=_SAMPLE_RESUME_DATA,
                    company="Google",
                    role="SDE",
                    interview_type=itype,
                    difficulty="Medium",
                    number_of_questions=2,
                )

                assert len(result.questions) == 2


# ===================================================================
# API endpoint integration tests
# ===================================================================


@pytest.mark.asyncio
class TestGenerateQuestionsEndpoint:
    """Integration tests for ``POST /api/interview/questions/generate``.

    The ADK agent's ``_runner.run_debug`` is mocked so no real API calls.
    """

    @pytest.fixture(autouse=True)
    def _setup_tables(self, db_session):
        """Ensure all relevant tables exist for each test."""
        Base.metadata.create_all(bind=db_session.bind)

    def _create_adk_record(
        self, db_session, user_id: str, resume_data: dict = None
    ):
        """Insert a test ResumeAnalysisADK record and return its ID."""
        from backend.app.models.resume_analysis_adk import ResumeAnalysisADK

        record = ResumeAnalysisADK(
            user_id=user_id,
            resume_filename="test_resume.pdf",
            raw_text="Sample resume text",
            extracted_json=resume_data or _SAMPLE_RESUME_DATA,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        return record.id

    @patch(
        "backend.app.services.agents.interview_question_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_generate_success(self, mock_run, client, db_session):
        """POST with valid data returns 201 with questions."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(_build_sample_question_list(3))
            )
        ]

        from backend.app.models.user import User

        user = User(
            email="candidate@example.com",
            password_hash="mock_hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        adk_id = self._create_adk_record(db_session, user.id)

        response = client.post(
            "/api/interview/questions/generate",
            json={
                "resume_analysis_id": adk_id,
                "company": "Google",
                "role": "Software Engineer",
                "interview_type": "Mixed",
                "difficulty": "Medium",
                "number_of_questions": 3,
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) == 3
        for q in data["questions"]:
            assert q["id"] is not None
            assert q["question"]
            assert q["expected_answer"]
            assert q["question_type"]
            assert q["user_id"] == user.id
            assert q["resume_analysis_id"] == adk_id
            assert q["company"] == "Google"
            assert q["role"] == "Software Engineer"
            assert q["interview_type"] == "Mixed"
            assert q["difficulty"] == "Medium"

    @patch(
        "backend.app.services.agents.interview_question_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_generate_ten_questions(
        self, mock_run, client, db_session
    ):
        """Generate 10 questions successfully."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(_build_sample_question_list(10))
            )
        ]

        from backend.app.models.user import User

        user = User(
            email="candidate@example.com",
            password_hash="mock_hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        adk_id = self._create_adk_record(db_session, user.id)

        response = client.post(
            "/api/interview/questions/generate",
            json={
                "resume_analysis_id": adk_id,
                "company": "Google",
                "role": "Software Engineer",
                "interview_type": "Technical",
                "difficulty": "Hard",
                "number_of_questions": 10,
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert len(data["questions"]) == 10

    @patch(
        "backend.app.services.agents.interview_question_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_generate_hr_interview(
        self, mock_run, client, db_session
    ):
        """HR interview type generates questions."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(_build_sample_question_list(2))
            )
        ]

        from backend.app.models.user import User

        user = User(
            email="candidate@example.com",
            password_hash="mock_hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        adk_id = self._create_adk_record(db_session, user.id)

        response = client.post(
            "/api/interview/questions/generate",
            json={
                "resume_analysis_id": adk_id,
                "company": "Amazon",
                "role": "Product Manager",
                "interview_type": "HR",
                "difficulty": "Easy",
                "number_of_questions": 2,
            },
        )
        assert response.status_code == 201

    @patch(
        "backend.app.services.agents.interview_question_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_generate_coding_interview(
        self, mock_run, client, db_session
    ):
        """Coding interview type generates questions."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(_build_sample_question_list(4))
            )
        ]

        from backend.app.models.user import User

        user = User(
            email="candidate@example.com",
            password_hash="mock_hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        adk_id = self._create_adk_record(db_session, user.id)

        response = client.post(
            "/api/interview/questions/generate",
            json={
                "resume_analysis_id": adk_id,
                "company": "Microsoft",
                "role": "Backend Engineer",
                "interview_type": "Coding",
                "difficulty": "Hard",
                "number_of_questions": 4,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["questions"]) == 4

    async def test_generate_missing_resume_404(self, client, db_session):
        """A non-existent resume_analysis_id returns 404."""
        response = client.post(
            "/api/interview/questions/generate",
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
        assert "not found" in response.text.lower()

    def _create_user_and_empty_adk(self, db_session):
        """Helper: create a user and an ADK record with null extracted_json."""
        from backend.app.models.user import User
        from backend.app.models.resume_analysis_adk import ResumeAnalysisADK

        user = User(
            email="candidate@example.com",
            password_hash="mock_hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        record = ResumeAnalysisADK(
            user_id=user.id,
            resume_filename="empty.pdf",
            raw_text="",
            extracted_json=None,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        return record.id

    async def test_generate_invalid_resume_400(self, client, db_session):
        """A resume analysis with no extracted_json returns 400."""
        adk_id = self._create_user_and_empty_adk(db_session)

        response = client.post(
            "/api/interview/questions/generate",
            json={
                "resume_analysis_id": adk_id,
                "company": "Google",
                "role": "SDE",
                "interview_type": "Mixed",
                "difficulty": "Medium",
                "number_of_questions": 3,
            },
        )
        assert response.status_code == 400
        assert "extracted" in response.text.lower()

    @patch(
        "backend.app.services.agents.interview_question_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_generate_agent_failure_500(
        self, mock_run, client, db_session
    ):
        """When the ADK agent fails, the API returns 500."""
        mock_run.side_effect = Exception("Gemini timeout")

        from backend.app.models.user import User

        user = User(
            email="candidate@example.com",
            password_hash="mock_hash",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        adk_id = self._create_adk_record(db_session, user.id)

        response = client.post(
            "/api/interview/questions/generate",
            json={
                "resume_analysis_id": adk_id,
                "company": "Google",
                "role": "SDE",
                "interview_type": "Mixed",
                "difficulty": "Medium",
                "number_of_questions": 3,
            },
        )
        assert response.status_code == 500
        assert "failed" in response.text.lower()


# ===================================================================
# Pydantic schema tests
# ===================================================================


class TestInterviewQuestionSchemas:
    """Verify that the interview question schemas validate correctly."""

    def test_question_item_full_population(self):
        """A fully populated InterviewQuestionItem produces the correct model."""
        item = InterviewQuestionItem(
            type="Technical",
            question="Explain Python decorators.",
            expected_answer=(
                "Decorators are functions that modify other functions."
            ),
            hints=["Functions", "Closures", "Wrappers"],
            follow_up="How are decorators implemented internally?",
            tags=["python", "decorators", "functions"],
        )
        assert item.type == "Technical"
        assert item.question == "Explain Python decorators."
        assert len(item.hints) == 3
        assert item.follow_up
        assert len(item.tags) == 3

    def test_question_item_defaults(self):
        """Missing optional fields default to empty values."""
        item = InterviewQuestionItem(
            type="HR",
            question="Tell me about yourself.",
            expected_answer="A summary of background.",
        )
        assert item.hints == []
        assert item.follow_up == ""
        assert item.tags == []

    def test_question_list_population(self):
        """InterviewQuestionList wraps items correctly."""
        items = [
            InterviewQuestionItem(
                type="Technical",
                question="Q1",
                expected_answer="A1",
            ),
            InterviewQuestionItem(
                type="HR",
                question="Q2",
                expected_answer="A2",
            ),
        ]
        qlist = InterviewQuestionList(questions=items)
        assert len(qlist.questions) == 2
        assert qlist.questions[0].type == "Technical"
        assert qlist.questions[1].type == "HR"

    def test_question_response_from_attributes(self):
        """InterviewQuestionResponse can be created from ORM attributes."""
        from datetime import datetime

        response = InterviewQuestionResponse(
            id="test-id",
            user_id="user-id",
            resume_analysis_id="analysis-id",
            company="Google",
            role="SDE",
            interview_type="Mixed",
            difficulty="Medium",
            question_type="Technical",
            question="Test question?",
            expected_answer="Test answer.",
            hints=["Hint 1"],
            follow_up="Follow-up?",
            tags=["tag1"],
            created_at=datetime(2024, 1, 1),
        )
        assert response.id == "test-id"
        assert response.company == "Google"
        assert response.question_type == "Technical"
        assert response.hints == ["Hint 1"]
        assert response.tags == ["tag1"]
