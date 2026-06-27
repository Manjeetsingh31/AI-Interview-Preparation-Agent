"""Google ADK ATS Scoring Agent.

Architecture
------------
::

    ResumeData JSON  (from ADK Resume Analysis Agent)
         │
         ▼
    ADK Agent (ats_agent)
         │
         ▼
    Gemini 2.5 Flash  (via google.adk SDK)
         │
         ▼
    Structured AtsOutput  (Pydantic, JSON)
         │
         ▼
    Database  /  API Response

This module creates a **real Google ADK Agent** — *not* a direct Gemini SDK
call.  The API route must go through ``AtsScoringAgent.analyze()``,
which internally constructs an ADK ``Agent`` with the structured ``AtsOutput``
``output_schema`` and runs it via ``Runner.run_debug()``.

The agent consumes ONLY the structured JSON output of the Resume Analysis
Agent (``ResumeData``). It does NOT parse PDFs or raw text.

Design decisions
----------------
- ``output_schema=AtsOutput`` tells Gemini 2.5 Flash to return strictly
  typed JSON that matches the ``AtsOutput`` Pydantic model.
- ``temperature=0.2`` provides a small amount of variability while keeping
  scoring consistent.
- The system instruction details the scoring weightage, section evaluation
  criteria, and job role matching requirements so every score is explainable.

Every step is logged at ``INFO`` level for observability.
"""

import json
import logging

from google.adk import Runner
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService

from backend.app.schemas.ats_score import AtsOutput

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent identity constants
# ---------------------------------------------------------------------------
_AGENT_NAME = "ats_scoring_agent"
_APP_NAME = "interview_prep_app"
_USER_ID = "ats_agent_user"
_SESSION_ID = "ats_scoring_session"

_SYSTEM_INSTRUCTION = (
    "You are an expert ATS (Applicant Tracking System) evaluator and senior "
    "technical recruiter. Your task is to evaluate the provided structured "
    "resume data and produce a comprehensive, explainable ATS score.\n\n"
    "SCORING WEIGHTAGE (total = 100 points):\n"
    "- Technical Skills ............ 30 points\n"
    "- Projects .................... 20 points\n"
    "- Experience .................. 15 points\n"
    "- Education ................... 10 points\n"
    "- Resume Structure ............ 10 points\n"
    "- Certifications .............. 5 points\n"
    "- Achievements ................ 5 points\n"
    "- Grammar & Readability ....... 5 points\n\n"
    "SECTION EVALUATION (score each section 0-100 with a reason and "
    "recommendation):\n"
    "1. Contact Information — check for email, phone, LinkedIn, GitHub, "
    "portfolio.\n"
    "2. Professional Summary — evaluate clarity, impact, and relevance.\n"
    "3. Education — assess degrees, fields, institutions, relevance.\n"
    "4. Experience — evaluate duration, relevance, career progression, "
    "impact.\n"
    "5. Projects — check complexity, technologies, descriptions, links.\n"
    "6. Technical Skills — evaluate breadth, depth, relevance.\n"
    "7. Soft Skills — look for evidence of communication, leadership, "
    "teamwork.\n"
    "8. Certifications — evaluate relevance, quantity, recency.\n"
    "9. Languages — consider multilingual ability.\n"
    "10. Achievements — evaluate measurable accomplishments.\n"
    "11. Overall Formatting — assess layout readability and consistency.\n\n"
    "JOB ROLE MATCHING (return 0-100 percentage for each):\n"
    "Evaluate the resume against each role's typical requirements:\n"
    "- Python Developer\n"
    "- Backend Developer\n"
    "- AI Engineer\n"
    "- Machine Learning Engineer\n"
    "- Data Analyst\n"
    "- Software Engineer\n"
    "- Full Stack Developer\n\n"
    "SKILL GAP ANALYSIS — categorise what is missing:\n"
    "- Missing Technologies (e.g., Docker, Kubernetes, Git)\n"
    "- Missing Programming Languages (e.g., Python, Java, Go)\n"
    "- Missing Frameworks (e.g., FastAPI, Django, React)\n"
    "- Missing Cloud Skills (e.g., AWS, GCP, Azure)\n"
    "- Missing DevOps Skills (e.g., CI/CD, Terraform, Jenkins)\n"
    "- Missing Databases (e.g., PostgreSQL, MongoDB, Redis)\n"
    "- Missing Soft Skills (e.g., Leadership, Communication)\n\n"
    "Return ONLY valid JSON matching the provided schema. "
    "Every field must be present. Use empty strings or empty lists when "
    "information is not available. Do NOT include any markdown, explanation, "
    "or text outside the JSON."
)

# ---------------------------------------------------------------------------
# Singleton agent & runner (stateless, safe to reuse)
# ---------------------------------------------------------------------------
_session_service = InMemorySessionService()

_agent = Agent(
    name=_AGENT_NAME,
    model="gemini-2.5-flash",
    instruction=_SYSTEM_INSTRUCTION,
    output_schema=AtsOutput,
    generate_content_config={
        "temperature": 0.2,
    },
)

_runner = Runner(
    agent=_agent,
    app_name=_APP_NAME,
    session_service=_session_service,
)


class AtsScoringAgent:
    """Google ADK agent that scores a resume using Gemini 2.5 Flash.

    The agent consumes structured resume data (``ResumeData``) from the
    Resume Analysis ADK Agent and produces a comprehensive ATS evaluation
    including section scores, job matching, skill gap analysis, and
    improvement suggestions.

    Usage::

        agent = AtsScoringAgent()
        result: AtsOutput = await agent.analyze(resume_data_dict)
        print(result.model_dump_json(indent=2))

    The agent is stateless — a single instance can be reused across
    multiple analyses.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.AtsScoringAgent")

    async def analyze(self, resume_data: dict) -> AtsOutput:
        """Score a resume and return a structured ``AtsOutput``.

        Args:
            resume_data: Structured resume data dict (from ``ResumeData``).

        Returns:
            An ``AtsOutput`` instance with all scoring fields.

        Raises:
            AtsScoringError: If the agent fails to produce a valid
                response (Gemini timeout, malformed JSON, etc.).
        """
        if not resume_data:
            raise AtsScoringError("Resume data is empty. Cannot score.")

        self.logger.info(
            "ATS Request — sending resume data to ADK agent"
        )

        prompt = (
            "Evaluate the following structured resume data and produce "
            "a comprehensive ATS score.\n\n"
            f"{json.dumps(resume_data, indent=2)}"
        )

        try:
            events = await _runner.run_debug(
                user_messages=[prompt],
                user_id=_USER_ID,
                session_id=_SESSION_ID,
            )
        except Exception as exc:
            self.logger.error("Gemini timeout / API failure: %s", exc)
            raise AtsScoringError(
                f"ADK ATS agent failed to produce a response: {exc}"
            ) from exc

        # --- Extract the final structured response from events ---------------
        parsed: AtsOutput | None = None
        self.logger.debug(
            "Gemini Response — received %d events", len(events)
        )
        for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        self.logger.debug(
                            "Gemini Response — raw text: %.200s...",
                            part.text,
                        )
                        try:
                            data = json.loads(part.text)
                            parsed = AtsOutput(**data)
                            self.logger.info(
                                "Gemini Response — parsed successfully: "
                                "overall_score=%d",
                                parsed.overall_score,
                            )
                        except (json.JSONDecodeError, Exception) as exc:
                            self.logger.error(
                                "Malformed JSON from Gemini: %s", exc
                            )
                            raise AtsScoringError(
                                f"Failed to parse Gemini ATS response: {exc}"
                            ) from exc

        if parsed is None:
            self.logger.error(
                "No valid final response found in agent events (%d events)",
                len(events),
            )
            raise AtsScoringError(
                "ADK ATS agent returned no valid structured response."
            )

        return parsed


class AtsScoringError(Exception):
    """Raised when the ATS scoring agent encounters an unrecoverable error.

    Possible causes:
    - Empty resume data
    - Gemini API timeout or failure
    - Malformed JSON in Gemini response
    """
