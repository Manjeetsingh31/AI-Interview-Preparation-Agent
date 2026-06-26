"""Google ADK Resume Analysis Agent.

Architecture
------------
::

    Resume text
        │
        ▼
    ADK Agent (resume_agent)
        │
        ▼
    Gemini 2.5 Flash  (via google-genai SDK)
        │
        ▼
    Structured ResumeData  (Pydantic, JSON)
        │
        ▼
    Database  /  API Response

This module creates a **real Google ADK Agent** — *not* a direct Gemini SDK
call.  The API route must go through ``ResumeAnalysisAgent.analyze()``,
which internally constructs an ADK ``Agent`` with the structured ``ResumeData``
``output_schema`` and runs it via ``Runner.run_debug()``.

Design decisions
----------------
- ``Runner.run_debug`` is used for single-turn debugging. It is an ``async``
  method, so ``analyze()`` is also ``async``.
- ``output_schema=ResumeData`` tells Gemini 2.5 Flash to return strictly
  typed JSON that matches the ``ResumeData`` Pydantic model.
- ``temperature=0.1`` keeps the extraction deterministic.

Every step is logged at ``INFO`` level for observability.
"""

import json
import logging

from google.adk import Runner
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService

from backend.app.core.config import settings
from backend.app.schemas.resume_analysis_adk import ResumeData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent identity constants
# ---------------------------------------------------------------------------
_AGENT_NAME = "resume_analysis_agent"
_APP_NAME = "interview_prep_app"
_USER_ID = "resume_agent_user"
_SESSION_ID = "resume_analysis_session"

_SYSTEM_INSTRUCTION = (
    "You are an expert resume parser. Extract structured information from the "
    "candidate's resume text below. Return ONLY valid JSON matching the provided "
    "schema. Every field must be present \u2014 use empty strings or empty lists when "
    "information is not available.\n\n"
    "Fields to extract:\n"
    "- full_name: The candidate's full name.\n"
    "- email: Email address.\n"
    "- phone: Phone number.\n"
    "- linkedin: LinkedIn profile URL.\n"
    "- github: GitHub profile URL.\n"
    "- portfolio: Portfolio or personal website.\n"
    "- skills: All skills mentioned (technical + soft combined).\n"
    "- technical_skills: Programming languages, frameworks, tools, databases.\n"
    "- soft_skills: Communication, leadership, teamwork, problem-solving.\n"
    "- education: List of entries with institution, degree, field, start_date, end_date.\n"
    "- experience: List of entries with company, role, start_date, end_date, description, highlights.\n"
    "- projects: List of entries with name, description, technologies, link.\n"
    "- certifications: List of professional certifications.\n"
    "- languages: List of languages the candidate speaks.\n\n"
    "Do NOT include any markdown, explanation, or text outside the JSON."
)

# ---------------------------------------------------------------------------
# Singleton agent & runner (stateless, safe to reuse)
# ---------------------------------------------------------------------------
_session_service = InMemorySessionService()

_agent = Agent(
    name=_AGENT_NAME,
    model="gemini-2.5-flash",
    instruction=_SYSTEM_INSTRUCTION,
    output_schema=ResumeData,
    generate_content_config={
        "temperature": 0.1,
    },
)

_runner = Runner(
    agent=_agent,
    app_name=_APP_NAME,
    session_service=_session_service,
)


class ResumeAnalysisAgent:
    """Google ADK agent that analyses resume text using Gemini 2.5 Flash.

    Usage::

        agent = ResumeAnalysisAgent()
        result: ResumeData = await agent.analyze(resume_text)
        print(result.model_dump_json(indent=2))

    The agent is stateless \u2014 a single instance can be reused across
    multiple analyses.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.ResumeAnalysisAgent")

    async def analyze(self, resume_text: str) -> ResumeData:
        """Analyse a resume and return structured ``ResumeData``.

        Args:
            resume_text: Full text extracted from the resume PDF.

        Returns:
            A ``ResumeData`` instance with all extracted fields.

        Raises:
            ResumeAnalysisError: If the agent fails to produce a valid
                response (Gemini timeout, malformed JSON, etc.).
        """
        if not resume_text or not resume_text.strip():
            raise ResumeAnalysisError("Resume text is empty. Cannot analyse.")

        self.logger.info(
            "Gemini Request \u2014 sending resume text (%d chars) to ADK agent",
            len(resume_text),
        )

        prompt = f"Analyse the following resume:\n\n{resume_text}"

        try:
            events = await _runner.run_debug(
                user_messages=[prompt],
                user_id=_USER_ID,
                session_id=_SESSION_ID,
            )
        except Exception as exc:
            self.logger.error("Gemini timeout / API failure: %s", exc)
            raise ResumeAnalysisError(
                f"ADK agent failed to produce a response: {exc}"
            ) from exc

        # --- Extract the final structured response from events ---------------
        parsed: ResumeData | None = None
        self.logger.debug(
            "Gemini Response \u2014 received %d events", len(events)
        )
        for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        self.logger.debug(
                            "Gemini Response \u2014 raw text: %.200s...",
                            part.text,
                        )
                        try:
                            data = json.loads(part.text)
                            parsed = ResumeData(**data)
                            self.logger.info(
                                "Gemini Response \u2014 parsed successfully: "
                                "full_name=%s, email=%s",
                                parsed.full_name,
                                parsed.email,
                            )
                        except (json.JSONDecodeError, Exception) as exc:
                            self.logger.error(
                                "Malformed JSON from Gemini: %s", exc
                            )
                            raise ResumeAnalysisError(
                                f"Failed to parse Gemini response: {exc}"
                            ) from exc

        if parsed is None:
            self.logger.error(
                "No valid final response found in agent events (%d events)",
                len(events),
            )
            raise ResumeAnalysisError(
                "ADK agent returned no valid structured response."
            )

        return parsed


class ResumeAnalysisError(Exception):
    """Raised when the resume analysis agent encounters an unrecoverable error.

    Possible causes:
    - Empty resume text
    - Gemini API timeout or failure
    - Malformed JSON in Gemini response
    """
