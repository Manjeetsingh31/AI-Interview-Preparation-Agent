"""Google ADK Interview Question Generator Agent.

Architecture
------------
::

    Resume Analysis JSON  +  Parameters (company, role, type, difficulty)
         │
         ▼
    ADK Agent (interview_question_agent)
         │
         ▼
    Gemini 2.5 Flash  (via google.adk SDK)
         │
         ▼
    Structured InterviewQuestionList  (Pydantic, JSON)
         │
         ▼
    Database  /  API Response

This module creates a **real Google ADK Agent** that generates personalised
interview questions based on the candidate's analysed resume, target company,
role, interview type, and difficulty level.

Design decisions
----------------
- ``output_schema=InterviewQuestionList`` tells Gemini 2.5 Flash to return
  strictly typed JSON matching the ``InterviewQuestionList`` Pydantic model.
- ``temperature=0.4`` balances creativity with consistency for question
  generation.
- The system instruction enforces question variety (HR, Technical, Coding,
  Resume), progressive difficulty, and JSON-only output.
"""

import json
import logging
from typing import List, Optional

from google.adk import Runner
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService

from backend.app.schemas.interview_question import (
    InterviewQuestionList,
    InterviewQuestionItem,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent identity constants
# ---------------------------------------------------------------------------
_AGENT_NAME = "interview_question_agent"
_APP_NAME = "interview_prep_app"
_USER_ID = "interview_q_agent_user"
_SESSION_ID = "interview_question_session"

_SYSTEM_INSTRUCTION = (
    "You are an experienced Senior Software Engineering Interviewer.\n\n"
    "Generate realistic interview questions based on the candidate's resume.\n"
    "Balance HR, Technical, Coding and Resume questions.\n"
    "Questions must become progressively harder.\n\n"
    "QUESTION TYPES (use the 'type' field):\n"
    "- HR: General human resources / fit questions\n"
    "- Technical: Technology and architecture knowledge\n"
    "- Coding: Code writing or algorithm questions\n"
    "- Behavioral: Past behaviour and situational questions\n"
    "- Resume: Questions about specific items on the resume\n"
    "- System Design: Architecture and scalability questions\n"
    "- Project Discussion: Deep dive into listed projects\n\n"
    "RULES:\n"
    "1. Use resume projects and skills to ask personalised questions.\n"
    "2. Ask project-specific questions that probe real implementation details.\n"
    "3. Generate company-specific questions relevant to the target company.\n"
    "4. Include coding questions appropriate for the role.\n"
    "5. Always provide a meaningful follow-up question.\n"
    "6. Generate realistic expected answers.\n"
    "7. Provide 2-4 actionable hints per question.\n"
    "8. Add 2-4 relevant tags per question.\n"
    "9. Never repeat the same question.\n"
    "10. Questions must progress from easier to harder.\n\n"
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
    output_schema=InterviewQuestionList,
    generate_content_config={
        "temperature": 0.4,
    },
)

_runner = Runner(
    agent=_agent,
    app_name=_APP_NAME,
    session_service=_session_service,
)


class InterviewQuestionAgent:
    """Google ADK agent that generates interview questions using Gemini 2.5 Flash.

    The agent consumes structured resume data (``ResumeAnalysisADK.extracted_json``)
    alongside interview parameters (company, role, type, difficulty) and produces
    a list of personalised interview questions.

    Usage::

        agent = InterviewQuestionAgent()
        result: InterviewQuestionList = await agent.generate(
            resume_data={...},
            company="Google",
            role="Software Engineer",
            interview_type="Mixed",
            difficulty="Medium",
            number_of_questions=10,
        )
        print(result.model_dump_json(indent=2))

    The agent is stateless — a single instance can be reused across
    multiple generations.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.InterviewQuestionAgent")

    async def generate(
        self,
        resume_data: dict,
        company: str,
        role: str,
        interview_type: str,
        difficulty: str,
        number_of_questions: int = 10,
    ) -> InterviewQuestionList:
        """Generate interview questions based on resume analysis and parameters.

        Args:
            resume_data: Structured resume data dict (from
                ``ResumeAnalysisADK.extracted_json``).
            company: Target company name.
            role: Target job role / title.
            interview_type: One of HR, Technical, Coding, Mixed.
            difficulty: One of Easy, Medium, Hard.
            number_of_questions: How many questions to generate (1-50).

        Returns:
            An ``InterviewQuestionList`` instance with all generated questions.

        Raises:
            InterviewQuestionError: If the agent fails to produce a valid
                response (Gemini timeout, malformed JSON, etc.).
        """
        if not resume_data:
            raise InterviewQuestionError(
                "Resume data is empty. Cannot generate questions."
            )

        self.logger.info(
            "Generation Request — company=%s, role=%s, type=%s, "
            "difficulty=%s, n=%d",
            company,
            role,
            interview_type,
            difficulty,
            number_of_questions,
        )

        prompt = (
            f"Generate {number_of_questions} interview questions for a "
            f"{role} position at {company}.\n\n"
            f"Interview Type: {interview_type}\n"
            f"Difficulty Level: {difficulty}\n\n"
            f"Candidate's Resume Data:\n"
            f"{json.dumps(resume_data, indent=2)}\n\n"
            f"Remember the rules: use resume projects, skills, and experience. "
            f"Balance question types. Progress from easier to harder. "
            f"Never repeat questions."
        )

        try:
            events = await _runner.run_debug(
                user_messages=[prompt],
                user_id=_USER_ID,
                session_id=_SESSION_ID,
            )
        except Exception as exc:
            self.logger.error("Gemini timeout / API failure: %s", exc)
            raise InterviewQuestionError(
                f"ADK agent failed to produce a response: {exc}"
            ) from exc

        # --- Extract the final structured response from events ---------------
        parsed: InterviewQuestionList | None = None
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
                            parsed = InterviewQuestionList(**data)
                            self.logger.info(
                                "Gemini Response — parsed successfully: "
                                "%d questions generated",
                                len(parsed.questions),
                            )
                        except (json.JSONDecodeError, Exception) as exc:
                            self.logger.error(
                                "Malformed JSON from Gemini: %s", exc
                            )
                            raise InterviewQuestionError(
                                f"Failed to parse Gemini response: {exc}"
                            ) from exc

        if parsed is None:
            self.logger.error(
                "No valid final response found in agent events (%d events)",
                len(events),
            )
            raise InterviewQuestionError(
                "ADK agent returned no valid structured response."
            )

        return parsed


class InterviewQuestionError(Exception):
    """Raised when the interview question generator encounters an error.

    Possible causes:
    - Empty resume data
    - Gemini API timeout or failure
    - Malformed JSON in Gemini response
    """
