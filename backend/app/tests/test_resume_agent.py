"""Unit tests for the Google ADK Resume Analysis Agent.

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

from backend.app.schemas.resume_analysis_adk import (
    ResumeData,
    Education,
    Experience,
    Project,
)
from backend.app.services.agents.resume_agent import ResumeAnalysisError

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
# Sample ResumeData for mocking
# ---------------------------------------------------------------------------

_SAMPLE_RESUME_DATA = ResumeData(
    full_name="Jane Doe",
    email="jane.doe@example.com",
    phone="+1-555-123-4567",
    linkedin="https://linkedin.com/in/janedoe",
    github="https://github.com/janedoe",
    portfolio="https://janedoe.dev",
    skills=["Python", "FastAPI", "Kubernetes", "Leadership"],
    technical_skills=["Python", "FastAPI", "Kubernetes", "Docker", "PostgreSQL"],
    soft_skills=["Leadership", "Communication", "Problem-solving"],
    education=[
        Education(
            institution="MIT",
            degree="BSc",
            field="Computer Science",
            start_date="Sep 2018",
            end_date="Jun 2022",
        )
    ],
    experience=[
        Experience(
            company="Tech Corp",
            role="Software Engineer",
            start_date="Jul 2022",
            end_date="Present",
            description="Built microservices.",
            highlights=["Scaled API to 10k QPS", "Led team of 3"],
        )
    ],
    projects=[
        Project(
            name="Open Source Tool",
            description="A CLI tool for DevOps.",
            technologies=["Python", "Click"],
            link="https://github.com/janedoe/tool",
        )
    ],
    certifications=["AWS Certified Solutions Architect"],
    languages=["English", "Spanish"],
)

_SAMPLE_EXTRACTED_JSON = _SAMPLE_RESUME_DATA.model_dump()
_SAMPLE_RESUME_TEXT = (
    "Jane Doe\njane.doe@example.com\n+1-555-123-4567\n"
    "Experienced software engineer skilled in Python, FastAPI, Kubernetes.\n"
)


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


# ===================================================================
# ResumeAnalysisAgent unit tests
# ===================================================================


@pytest.mark.asyncio
class TestResumeAnalysisAgent:
    """Unit tests for ``ResumeAnalysisAgent.analyze()``.

    All tests are ``async`` because ``analyze()`` awaits the ADK runner.
    """

    async def test_analyze_success(self):
        """Happy path: valid resume text returns a populated ``ResumeData``."""
        with patch(
            "backend.app.services.agents.resume_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event(json.dumps(_SAMPLE_EXTRACTED_JSON))
            ]

            from backend.app.services.agents.resume_agent import ResumeAnalysisAgent

            agent = ResumeAnalysisAgent()
            result = await agent.analyze(_SAMPLE_RESUME_TEXT)

            assert isinstance(result, ResumeData)
            assert result.full_name == "Jane Doe"
            assert result.email == "jane.doe@example.com"
            assert result.phone == "+1-555-123-4567"
            assert "Python" in result.skills
            assert len(result.education) == 1
            assert len(result.experience) == 1
            assert len(result.projects) == 1
            assert "AWS Certified Solutions Architect" in result.certifications
            assert "English" in result.languages

    async def test_analyze_empty_text_raises_error(self):
        """Empty text raises ``ResumeAnalysisError`` immediately (no API call)."""
        from backend.app.services.agents.resume_agent import ResumeAnalysisAgent

        agent = ResumeAnalysisAgent()

        with pytest.raises(ResumeAnalysisError, match="Resume text is empty"):
            await agent.analyze("")

        with pytest.raises(ResumeAnalysisError, match="Resume text is empty"):
            await agent.analyze("   ")

    async def test_analyze_gemini_timeout_raises_error(self):
        """When ``run_debug`` raises, a ``ResumeAnalysisError`` is raised."""
        with patch(
            "backend.app.services.agents.resume_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.side_effect = Exception("Gemini API timeout")

            from backend.app.services.agents.resume_agent import ResumeAnalysisAgent

            agent = ResumeAnalysisAgent()
            with pytest.raises(ResumeAnalysisError, match="Resume analysis service is temporarily unavailable"):
                await agent.analyze(_SAMPLE_RESUME_TEXT)

    async def test_analyze_malformed_json_raises_error(self):
        """Non-JSON text from Gemini raises ``ResumeAnalysisError``."""
        with patch(
            "backend.app.services.agents.resume_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event("This is not JSON at all")
            ]

            from backend.app.services.agents.resume_agent import ResumeAnalysisAgent

            agent = ResumeAnalysisAgent()
            with pytest.raises(ResumeAnalysisError, match="Failed to parse Gemini"):
                await agent.analyze(_SAMPLE_RESUME_TEXT)

    async def test_analyze_no_final_event_raises_error(self):
        """No event with ``is_final_response() == True`` raises an error."""
        with patch(
            "backend.app.services.agents.resume_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event("intermediate", is_final=False)
            ]

            from backend.app.services.agents.resume_agent import ResumeAnalysisAgent

            agent = ResumeAnalysisAgent()
            with pytest.raises(ResumeAnalysisError, match="no valid structured response"):
                await agent.analyze(_SAMPLE_RESUME_TEXT)

    async def test_analyze_empty_events_list_raises_error(self):
        """An empty event list raises ``ResumeAnalysisError``."""
        with patch(
            "backend.app.services.agents.resume_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = []

            from backend.app.services.agents.resume_agent import ResumeAnalysisAgent

            agent = ResumeAnalysisAgent()
            with pytest.raises(ResumeAnalysisError, match="no valid structured response"):
                await agent.analyze(_SAMPLE_RESUME_TEXT)


# ===================================================================
# API endpoint integration tests
# ===================================================================


@pytest.mark.asyncio
class TestAnalyzeResumeEndpoint:
    """Integration tests for ``POST /api/resumes/analyze``.

    The ADK agent's ``_runner.run_debug`` is mocked so no real API calls.
    """

    @patch(
        "backend.app.services.agents.resume_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_analyze_pdf_success(self, mock_run, client):
        """Upload a valid PDF and receive a structured analysis."""
        mock_run.return_value = [
            _make_fake_event(json.dumps(_SAMPLE_EXTRACTED_JSON))
        ]

        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            b"/Contents 4 0 R /Resources << /Font << >> >> >>\nendobj\n"
            b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td "
            b"(Hello World) Tj ET\nendstream\nendobj\n"
            b"xref\n5 0 obj\n<< /Type /XRef /Size 5 /W [1 1 1] /Root 1 0 R >>\n"
            b"stream\n...\nendstream\nendobj\n"
            b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n120\n%%%%EOF"
        )

        response = client.post(
            "/api/resumes/analyze",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["resume_filename"] == "resume.pdf"
        assert data["extracted_json"]["full_name"] == "Jane Doe"
        assert data["extracted_json"]["email"] == "jane.doe@example.com"
        assert data["id"] is not None
        assert data["user_id"] is not None
        assert "created_at" in data

    @patch(
        "backend.app.services.agents.resume_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_analyze_text_file_success(self, mock_run, client):
        """Upload a plain-text resume and receive a structured analysis."""
        mock_run.return_value = [
            _make_fake_event(json.dumps(_SAMPLE_EXTRACTED_JSON))
        ]

        text_content = "John Smith\njohn@example.com\n+1-555-987-6543"
        response = client.post(
            "/api/resumes/analyze",
            files={"file": ("resume.txt", text_content, "text/plain")},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["resume_filename"] == "resume.txt"
        assert data["extracted_json"]["full_name"] == "Jane Doe"

    async def test_analyze_empty_file_rejected(self, client):
        """Uploading an empty file returns 400."""
        response = client.post(
            "/api/resumes/analyze",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert response.status_code == 400
        assert "empty" in response.text.lower()

    @patch(
        "backend.app.services.agents.resume_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_analyze_agent_failure_returns_500(self, mock_run, client):
        """When the ADK agent fails, the API returns 500."""
        mock_run.side_effect = Exception("Gemini timeout")

        response = client.post(
            "/api/resumes/analyze",
            files={"file": ("resume.txt", "Some text content", "text/plain")},
        )
        assert response.status_code == 500
        assert "analysis failed" in response.text.lower()


# ===================================================================
# Pydantic schema tests
# ===================================================================


class TestResumeDataSchema:
    """Verify that ``ResumeData`` validates correctly."""

    def test_full_population(self):
        """A fully populated dict produces the correct model."""
        data = {
            "full_name": "Alice",
            "email": "a@b.com",
            "phone": "123",
            "linkedin": "",
            "github": "",
            "portfolio": "",
            "skills": ["A"],
            "technical_skills": ["B"],
            "soft_skills": ["C"],
            "education": [],
            "experience": [],
            "projects": [],
            "certifications": [],
            "languages": [],
        }
        model = ResumeData(**data)
        assert model.full_name == "Alice"

    def test_defaults_for_missing_fields(self):
        """Missing optional fields default to empty strings / lists."""
        data = {
            "full_name": "Bob",
            "email": "b@c.com",
            "phone": "456",
        }
        model = ResumeData(**data)
        assert model.linkedin == ""
        assert model.skills == []
        assert model.education == []

    def test_nested_education(self):
        """Education entries are validated as ``Education`` models."""
        data = {
            "full_name": "Test",
            "email": "t@t.com",
            "phone": "000",
            "education": [
                {
                    "institution": "Stanford",
                    "degree": "MSc",
                    "field": "AI",
                    "start_date": "2020",
                    "end_date": "2022",
                }
            ],
        }
        model = ResumeData(**data)
        assert len(model.education) == 1
        assert model.education[0].institution == "Stanford"
        assert model.education[0].degree == "MSc"
