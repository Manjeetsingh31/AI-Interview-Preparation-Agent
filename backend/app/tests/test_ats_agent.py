"""Unit tests for the Google ADK ATS Scoring Agent.

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

from backend.app.schemas.ats_score import (
    AtsOutput,
    SectionScoreDetail,
    SkillGapAnalysis,
)
from backend.app.services.agents.ats_agent import AtsScoringError

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


def _make_section(score: int, reason: str, recommendation: str) -> dict:
    return {
        "score": score,
        "reason": reason,
        "recommendation": recommendation,
    }


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
# Sample ATS outputs
# ---------------------------------------------------------------------------

_SAMPLE_SECTION = SectionScoreDetail(
    score=85, reason="Good content", recommendation="Add more detail"
)

_SAMPLE_SKILL_GAP = SkillGapAnalysis(
    missing_technologies=["Kubernetes"],
    missing_programming_languages=["Go"],
    missing_frameworks=["Django"],
    missing_cloud_skills=["AWS"],
    missing_devops_skills=["CI/CD"],
    missing_databases=["PostgreSQL"],
    missing_soft_skills=["Leadership"],
)


def _build_ats_output(
    overall_score: int,
    strengths: list,
    weaknesses: list,
) -> dict:
    """Build a sample ATS output dict for mocking."""
    base = _make_section(overall_score, "Test reason", "Test recommendation")
    return AtsOutput(
        overall_score=overall_score,
        contact_info_score=_SAMPLE_SECTION,
        professional_summary_score=_SAMPLE_SECTION,
        education_section_score=_SAMPLE_SECTION,
        experience_section_score=_SAMPLE_SECTION,
        projects_section_score=_SAMPLE_SECTION,
        technical_skills_section_score=_SAMPLE_SECTION,
        soft_skills_section_score=_SAMPLE_SECTION,
        certifications_section_score=_SAMPLE_SECTION,
        languages_section_score=_SAMPLE_SECTION,
        achievements_section_score=_SAMPLE_SECTION,
        overall_formatting_section_score=_SAMPLE_SECTION,
        strengths=strengths,
        weaknesses=weaknesses,
        missing_technical_skills=[],
        missing_soft_skills=[],
        missing_keywords=[],
        resume_structure_score=overall_score,
        grammar_score=overall_score,
        project_quality_score=overall_score,
        education_score=overall_score,
        experience_score=overall_score,
        certification_score=overall_score,
        python_developer_match=overall_score,
        backend_developer_match=overall_score,
        ai_engineer_match=overall_score,
        machine_learning_engineer_match=overall_score,
        data_analyst_match=overall_score,
        software_engineer_match=overall_score,
        full_stack_developer_match=overall_score,
        skill_gap_analysis=_SAMPLE_SKILL_GAP,
        improvement_suggestions=["Improve summary", "Add more projects"],
    ).model_dump()


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
# AtsScoringAgent unit tests
# ===================================================================


@pytest.mark.asyncio
class TestAtsScoringAgent:
    """Unit tests for ``AtsScoringAgent.analyze()``.

    All tests are ``async`` because ``analyze()`` awaits the ADK runner.
    """

    async def test_analyze_success(self):
        """Happy path: valid resume data returns a populated ``AtsOutput``."""
        with patch(
            "backend.app.services.agents.ats_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event(
                    json.dumps(_build_ats_output(85, ["Strong Python"], []))
                )
            ]

            from backend.app.services.agents.ats_agent import AtsScoringAgent

            agent = AtsScoringAgent()
            result = await agent.analyze(_SAMPLE_RESUME_DATA)

            assert isinstance(result, AtsOutput)
            assert result.overall_score == 85
            assert "Strong Python" in result.strengths
            assert result.resume_structure_score == 85
            assert result.python_developer_match == 85

    async def test_analyze_excellent_resume(self):
        """An excellent resume gets a high score with strong strengths."""
        with patch(
            "backend.app.services.agents.ats_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            output = _build_ats_output(
                92,
                ["Strong Python", "Relevant experience", "Good projects"],
                [],
            )
            mock_run.return_value = [
                _make_fake_event(json.dumps(output))
            ]

            from backend.app.services.agents.ats_agent import AtsScoringAgent

            agent = AtsScoringAgent()
            result = await agent.analyze(_SAMPLE_RESUME_DATA)

            assert result.overall_score == 92
            assert len(result.strengths) == 3
            assert len(result.weaknesses) == 0

    async def test_analyze_average_resume(self):
        """An average resume gets a medium score with mixed feedback."""
        with patch(
            "backend.app.services.agents.ats_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            output = _build_ats_output(
                65,
                ["Good technical skills"],
                ["Weak projects", "Missing cloud experience"],
            )
            mock_run.return_value = [
                _make_fake_event(json.dumps(output))
            ]

            from backend.app.services.agents.ats_agent import AtsScoringAgent

            agent = AtsScoringAgent()
            result = await agent.analyze(_SAMPLE_RESUME_DATA)

            assert result.overall_score == 65
            assert "Weak projects" in result.weaknesses

    async def test_analyze_poor_resume(self):
        """A poor resume gets a low score with many weaknesses."""
        with patch(
            "backend.app.services.agents.ats_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            output = _build_ats_output(
                35,
                [],
                [
                    "No relevant experience",
                    "Missing technical skills",
                    "Poor formatting",
                    "No achievements",
                ],
            )
            mock_run.return_value = [
                _make_fake_event(json.dumps(output))
            ]

            from backend.app.services.agents.ats_agent import AtsScoringAgent

            agent = AtsScoringAgent()
            result = await agent.analyze(_SAMPLE_RESUME_DATA)

            assert result.overall_score == 35
            assert len(result.weaknesses) >= 3

    async def test_analyze_empty_data_raises_error(self):
        """Empty resume data raises ``AtsScoringError`` immediately."""
        from backend.app.services.agents.ats_agent import AtsScoringAgent

        agent = AtsScoringAgent()

        with pytest.raises(AtsScoringError, match="Resume data is empty"):
            await agent.analyze({})

    async def test_analyze_gemini_timeout_raises_error(self):
        """When ``run_debug`` raises, an ``AtsScoringError`` is raised."""
        with patch(
            "backend.app.services.agents.ats_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.side_effect = Exception("Gemini API timeout")

            from backend.app.services.agents.ats_agent import AtsScoringAgent

            agent = AtsScoringAgent()
            with pytest.raises(AtsScoringError, match="ADK ATS agent failed"):
                await agent.analyze(_SAMPLE_RESUME_DATA)

    async def test_analyze_malformed_json_raises_error(self):
        """Non-JSON text from Gemini raises ``AtsScoringError``."""
        with patch(
            "backend.app.services.agents.ats_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event("This is not JSON at all")
            ]

            from backend.app.services.agents.ats_agent import AtsScoringAgent

            agent = AtsScoringAgent()
            with pytest.raises(AtsScoringError, match="Failed to parse Gemini"):
                await agent.analyze(_SAMPLE_RESUME_DATA)

    async def test_analyze_no_final_event_raises_error(self):
        """No event with ``is_final_response() == True`` raises an error."""
        with patch(
            "backend.app.services.agents.ats_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_fake_event("intermediate", is_final=False)
            ]

            from backend.app.services.agents.ats_agent import AtsScoringAgent

            agent = AtsScoringAgent()
            with pytest.raises(
                AtsScoringError, match="no valid structured response"
            ):
                await agent.analyze(_SAMPLE_RESUME_DATA)

    async def test_analyze_empty_events_list_raises_error(self):
        """An empty event list raises ``AtsScoringError``."""
        with patch(
            "backend.app.services.agents.ats_agent._runner.run_debug",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = []

            from backend.app.services.agents.ats_agent import AtsScoringAgent

            agent = AtsScoringAgent()
            with pytest.raises(
                AtsScoringError, match="no valid structured response"
            ):
                await agent.analyze(_SAMPLE_RESUME_DATA)


# ===================================================================
# API endpoint integration tests
# ===================================================================


@pytest.mark.asyncio
class TestAnalyzeAtsEndpoint:
    """Integration tests for ``POST /api/ats/analyze``.

    The ADK agent's ``_runner.run_debug`` is mocked so no real API calls.
    We also need the ``ResumeAnalysisADK`` record to exist, and we ensure
    the ``ats_scores`` table is created before each test.
    """

    @pytest.fixture(autouse=True)
    def _setup_tables(self, db_session):
        """Ensure all relevant tables exist for each test."""
        Base.metadata.create_all(bind=db_session.bind)

    def _create_adk_record(self, db_session, user_id: str, resume_data: dict = None):
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
        "backend.app.services.agents.ats_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_analyze_success(self, mock_run, client, db_session):
        """POST /api/ats/analyze with valid data returns 201 with scores."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(_build_ats_output(85, ["Strong Python"], []))
            )
        ]

        user_id = client.app.dependency_overrides[
            get_db
        ]().__next__().query.__class__  # placeholder
        # Create a user first
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
            "/api/ats/analyze",
            json={"resume_analysis_adk_id": adk_id},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["overall_score"] == 85
        assert data["resume_analysis_adk_id"] == adk_id
        assert data["id"] is not None
        assert "section_scores" in data
        assert "job_match" in data
        assert "skill_gap_analysis" in data
        assert "improvement_suggestions" in data

    @patch(
        "backend.app.services.agents.ats_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_analyze_excellent_resume_score(
        self, mock_run, client, db_session
    ):
        """An excellent resume analysis returns a high overall score."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(_build_ats_output(92, ["Excellent"], []))
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
            "/api/ats/analyze",
            json={"resume_analysis_adk_id": adk_id},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["overall_score"] >= 90

    @patch(
        "backend.app.services.agents.ats_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_analyze_average_resume_score(
        self, mock_run, client, db_session
    ):
        """An average resume analysis returns a medium score."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(_build_ats_output(65, ["OK"], ["Weak"]))
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
            "/api/ats/analyze",
            json={"resume_analysis_adk_id": adk_id},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert 40 <= data["overall_score"] <= 80

    @patch(
        "backend.app.services.agents.ats_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_analyze_poor_resume_score(
        self, mock_run, client, db_session
    ):
        """A poor resume analysis returns a low score with weaknesses."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(
                    _build_ats_output(
                        35, [], ["Bad", "Missing skills", "No exp"]
                    )
                )
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
            "/api/ats/analyze",
            json={"resume_analysis_adk_id": adk_id},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["overall_score"] <= 40
        assert len(data["weaknesses"]) >= 1

    async def test_analyze_missing_resume_404(self, client, db_session):
        """A non-existent resume_analysis_adk_id returns 404."""
        response = client.post(
            "/api/ats/analyze",
            json={"resume_analysis_adk_id": "nonexistent-id"},
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

    async def test_analyze_invalid_resume_400(self, client, db_session):
        """A resume analysis with no extracted_json returns 400."""
        adk_id = self._create_user_and_empty_adk(db_session)

        response = client.post(
            "/api/ats/analyze",
            json={"resume_analysis_adk_id": adk_id},
        )
        assert response.status_code == 400
        assert "extracted" in response.text.lower()

    @patch(
        "backend.app.services.agents.ats_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_analyze_agent_failure_500(
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
            "/api/ats/analyze",
            json={"resume_analysis_adk_id": adk_id},
        )
        assert response.status_code == 500
        assert "failed" in response.text.lower()

    @patch(
        "backend.app.services.agents.ats_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_get_ats_score_by_id(self, mock_run, client, db_session):
        """GET /api/ats/{id} returns a previously created ATS score."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(_build_ats_output(85, ["A"], []))
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

        create_resp = client.post(
            "/api/ats/analyze",
            json={"resume_analysis_adk_id": adk_id},
        )
        assert create_resp.status_code == 201
        ats_id = create_resp.json()["id"]

        get_resp = client.get(f"/api/ats/{ats_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == ats_id
        assert data["overall_score"] == 85

    async def test_get_ats_score_not_found_404(self, client):
        """GET /api/ats/{id} returns 404 for non-existent score."""
        response = client.get("/api/ats/nonexistent-id")
        assert response.status_code == 404

    @patch(
        "backend.app.services.agents.ats_agent._runner.run_debug",
        new_callable=AsyncMock,
    )
    async def test_get_ats_history(self, mock_run, client, db_session):
        """GET /api/ats/history returns list of scores for the user."""
        mock_run.return_value = [
            _make_fake_event(
                json.dumps(_build_ats_output(75, ["B"], ["C"]))
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

        client.post(
            "/api/ats/analyze",
            json={"resume_analysis_adk_id": adk_id},
        )

        response = client.get("/api/ats/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["overall_score"] == 75


# ===================================================================
# Pydantic schema tests
# ===================================================================


class TestAtsOutputSchema:
    """Verify that ``AtsOutput`` validates correctly."""

    def _minimal_ats_output(self) -> dict:
        section = _make_section(80, "Good", "Keep improving")
        return {
            "overall_score": 80,
            "contact_info_score": section,
            "professional_summary_score": section,
            "education_section_score": section,
            "experience_section_score": section,
            "projects_section_score": section,
            "technical_skills_section_score": section,
            "soft_skills_section_score": section,
            "certifications_section_score": section,
            "languages_section_score": section,
            "achievements_section_score": section,
            "overall_formatting_section_score": section,
            "strengths": ["A"],
            "weaknesses": ["B"],
            "missing_technical_skills": [],
            "missing_soft_skills": [],
            "missing_keywords": [],
            "resume_structure_score": 80,
            "grammar_score": 80,
            "project_quality_score": 80,
            "education_score": 80,
            "experience_score": 80,
            "certification_score": 80,
            "python_developer_match": 80,
            "backend_developer_match": 70,
            "ai_engineer_match": 60,
            "machine_learning_engineer_match": 50,
            "data_analyst_match": 40,
            "software_engineer_match": 80,
            "full_stack_developer_match": 70,
            "skill_gap_analysis": {
                "missing_technologies": [],
                "missing_programming_languages": [],
                "missing_frameworks": [],
                "missing_cloud_skills": [],
                "missing_devops_skills": [],
                "missing_databases": [],
                "missing_soft_skills": [],
            },
            "improvement_suggestions": ["Add projects"],
        }

    def test_full_population(self):
        """A fully populated dict produces the correct model."""
        data = self._minimal_ats_output()
        model = AtsOutput(**data)
        assert model.overall_score == 80
        assert model.contact_info_score.score == 80
        assert model.python_developer_match == 80
        assert model.machine_learning_engineer_match == 50
        assert model.skill_gap_analysis.missing_technologies == []

    def test_nested_section_score_detail(self):
        """SectionScoreDetail validates nested fields correctly."""
        section = SectionScoreDetail(
            score=75,
            reason="Good coverage",
            recommendation="Add more depth",
        )
        assert section.score == 75
        assert section.reason == "Good coverage"
        assert section.recommendation == "Add more depth"

    def test_section_score_detail_bounds(self):
        """SectionScoreDetail enforces score 0-100."""
        with pytest.raises(ValueError):
            SectionScoreDetail(score=150, reason="x", recommendation="y")

    def test_job_match_bounds(self):
        """AtsOutput enforces job match 0-100."""
        data = self._minimal_ats_output()
        data["python_developer_match"] = -1
        with pytest.raises(ValueError):
            AtsOutput(**data)

    def test_improvement_suggestions_default(self):
        """Improvement suggestions default to empty list."""
        data = self._minimal_ats_output()
        data.pop("improvement_suggestions")
        model = AtsOutput(**data)
        assert model.improvement_suggestions == []
