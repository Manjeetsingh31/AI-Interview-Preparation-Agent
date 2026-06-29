"""Google ADK Multi-Agent Mock Interview Agent.

Architecture
------------
::

    Resume Analysis + ATS + Generated Questions + Previous Turns
         │
         ▼
    ADK Agent (interview_agent)
         │
         ▼
    Gemini 2.5 Flash  (via google.adk SDK)
         │
         ▼
    Structured InterviewAgentTurn  (Pydantic, JSON)
         │
         ▼
    Database  /  API Response

This module creates a **real Google ADK Agent** that conducts a complete
mock interview like a real interviewer. It supports HR, Technical, Coding,
Behavioural, and Mixed interview types.

Design decisions
----------------
- ``output_schema=InterviewAgentTurn`` tells Gemini 2.5 Flash to return
  strictly typed JSON matching the ``InterviewAgentTurn`` Pydantic model.
- ``temperature=0.3`` balances consistency with conversational naturalness.
- The system instruction covers all interview types, difficulty progression,
  follow-up logic, and company-specific expectations.
- The agent is stateless — all conversation memory is passed in the prompt
  from the database.
"""

import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import List, Optional


from google.adk import Runner
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService

from backend.app.core.config import settings
from backend.app.schemas.interview_turn import InterviewAgentTurn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent identity constants
# ---------------------------------------------------------------------------
_AGENT_NAME = "interview_agent"
_APP_NAME = "interview_prep_app"
_USER_ID = "interview_agent_user"
_SESSION_ID = "interview_mock_session"

_INTERVIEW_TYPES = ("HR", "Technical", "Coding", "Behavioural", "Mixed")

_COMPANY_LIST = (
    "Generic, Google, Microsoft, Amazon, Meta, Apple, Netflix, "
    "Oracle, IBM, Adobe, TCS, Infosys, Wipro, Accenture, Capgemini, "
    "Deloitte, Cognizant"
)

_SYSTEM_INSTRUCTION = (
    "You are an expert Senior Technical Interviewer conducting a mock interview. "
    "Your goal is to simulate a real interview experience exactly like a human "
    "interviewer would.\n\n"
    "INTERVIEW TYPES:\n"
    "- HR: Focus on cultural fit, motivation, career goals, teamwork\n"
    "- Technical: Focus on system design, architecture, technology choices\n"
    "- Coding: Focus on algorithms, data structures, code quality, problem-solving\n"
    "- Behavioural: Focus on past experiences, leadership, conflict resolution\n"
    "- Mixed: Blend of all types as appropriate\n\n"
    "SUPPORTED COMPANIES:\n"
    f"{_COMPANY_LIST}\n\n"
    "QUESTION SOURCES (use in this order of priority):\n"
    "1. Resume projects — ask about implementation details, challenges, decisions\n"
    "2. ATS weaknesses — probe areas where the candidate is weak\n"
    "3. Skills — test depth of listed skills\n"
    "4. Previous answers — build on what the candidate said\n"
    "5. Education — relevant academic background\n"
    "6. Company & Role — tailor to the target company\n"
    "7. Interview type — follow the type guidelines\n\n"
    "DIFFICULTY PROGRESSION:\n"
    "- Questions must start at the requested difficulty level\n"
    "- Increase difficulty every 3-4 questions if the candidate answers correctly\n"
    "- Decrease difficulty if the candidate struggles (score < 40)\n"
    "- Never ask two questions of the same category consecutively\n"
    "- Switch categories automatically to cover all relevant areas\n\n"
    "FOLLOW-UP LOGIC:\n"
    "- If answer is weak (score < 40): Ask a clarification question\n"
    "- If answer is strong (score >= 80): Ask a deeper, more challenging question\n"
    "- If answer is partially correct (score 40-79): Ask one follow-up that probes the gap\n"
    "- Never ask unrelated follow-up questions\n"
    "- Never ask more than one follow-up per question\n\n"
    "RULES:\n"
    "1. Ask ONLY ONE question per turn.\n"
    "2. Never repeat a question that was already asked.\n"
    "3. Never repeat a topic that was already thoroughly covered.\n"
    "4. Use the candidate's resume skills, projects, and experience.\n"
    "5. Use ATS weaknesses to probe weak areas.\n"
    "6. Use previous answers to build a coherent conversation.\n"
    "7. Increase difficulty gradually as the candidate performs well.\n"
    "8. Track interview progress and finish after the configured number of questions.\n"
    "9. Provide a score (0-100) and evaluation for every answer.\n"
    "10. Provide the expected answer for every question you ask.\n"
    "11. When it is the last question, set is_final=True and provide a transcript_summary.\n"
    "12. Be professional, encouraging, and constructive — like a real interviewer.\n"
    "13. When no previous answer exists (first turn), set evaluation='' and score=0.\n\n"
    "CATEGORIES: HR, Technical, Coding, Behavioural\n\n"
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
    model=settings.GEMINI_MODEL,
    instruction=_SYSTEM_INSTRUCTION,
    output_schema=InterviewAgentTurn,
    generate_content_config={
        "temperature": 0.3,
    },
)

_runner = Runner(
    agent=_agent,
    app_name=_APP_NAME,
    session_service=_session_service,
)


class InterviewAgent:
    """Google ADK agent that conducts a complete mock interview.

    The agent consumes resume analysis, ATS analysis, generated questions,
    and previous interview turns to produce the next interview question,
    evaluate answers, and manage the interview flow.

    Usage::

        agent = InterviewAgent()
        result: InterviewAgentTurn = await agent.next_turn(
            resume_data={...},
            ats_data={...},
            generated_questions=[...],
            previous_turns=[...],
            question_number=1,
            total_questions=10,
            company="Google",
            role="Software Engineer",
            interview_type="Mixed",
            difficulty="Medium",
            candidate_answer=None,  # None on first turn
        )
        print(result.model_dump_json(indent=2))

    The agent is stateless — conversation memory is managed externally
    via the ``previous_turns`` parameter.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.InterviewAgent")
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2),
        reraise=True,
    )
    async def _run_with_retry(self, prompt: str):
        return await _runner.run_debug(
            user_messages=[prompt],
            user_id=_USER_ID,
            session_id=_SESSION_ID,
        )

    async def next_turn(
        self,
        *,
        resume_data: Optional[dict] = None,
        ats_data: Optional[dict] = None,
        generated_questions: Optional[List[dict]] = None,
        previous_turns: Optional[List[dict]] = None,
        question_number: int = 1,
        total_questions: int = 10,
        company: str = "Generic",
        role: str = "Software Engineer",
        interview_type: str = "Mixed",
        difficulty: str = "Medium",
        candidate_answer: Optional[str] = None,
        response_time: Optional[int] = None,
    ) -> InterviewAgentTurn:
        """Generate the next interview turn.

        Args:
            resume_data: Structured resume data dict.
            ats_data: Structured ATS analysis dict.
            generated_questions: Previously generated questions for reference.
            previous_turns: List of previous turn dicts (conversation memory).
            question_number: Current question number (1-based).
            total_questions: Total number of questions configured.
            company: Target company name.
            role: Target job role.
            interview_type: One of HR, Technical, Coding, Behavioural, Mixed.
            difficulty: One of Easy, Medium, Hard.
            candidate_answer: The candidate's previous answer (None for first turn).
            response_time: Time taken for the answer in seconds.

        Returns:
            An ``InterviewAgentTurn`` instance with the next question or
            final transcript.

        Raises:
            InterviewAgentError: If the agent fails to produce a valid
                response (Gemini timeout, malformed JSON, etc.).
        """
        self.logger.info(
            "Interview Turn — q_no=%d/%d, type=%s, company=%s, role=%s, "
            "difficulty=%s",
            question_number,
            total_questions,
            interview_type,
            company,
            role,
            difficulty,
        )

        # --- Build the prompt ---
        prompt = self._build_prompt(
            resume_data=resume_data,
            ats_data=ats_data,
            generated_questions=generated_questions,
            previous_turns=previous_turns,
            question_number=question_number,
            total_questions=total_questions,
            company=company,
            role=role,
            interview_type=interview_type,
            difficulty=difficulty,
            candidate_answer=candidate_answer,
            response_time=response_time,
        )

        # --- Call the ADK agent ---
        try:
            events = await self._run_with_retry(prompt)
        except Exception as exc:
            self.logger.exception("Gemini API failed after retries")
            raise InterviewAgentError(
                "Interview service is temporarily unavailable. Please try again in a few minutes."
            ) from exc

        # --- Extract structured response ---
        parsed: InterviewAgentTurn | None = None
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
                            parsed = InterviewAgentTurn(**data)
                            self.logger.info(
                                "Gemini Response — parsed: category=%s, "
                                "difficulty=%s, is_final=%s",
                                parsed.category,
                                parsed.difficulty,
                                parsed.is_final,
                            )
                        except json.JSONDecodeError as exc:
                            self.logger.error("Malformed JSON from Gemini: %s", exc)
                            raise InterviewAgentError(
                                f"Failed to parse Gemini response: {exc}"
                            ) from exc
                        except Exception as exc:
                            self.logger.exception("Unexpected error while parsing Gemini response")
                            raise InterviewAgentError(
                                "Unexpected error while processing the Gemini response."
                            ) from exc

        if parsed is None:
            self.logger.error(
                "No valid final response found in agent events (%d events)",
                len(events),
            )
            raise InterviewAgentError(
                "ADK interview agent returned no valid structured response."
            )

        return parsed

    def _build_prompt(
        self,
        *,
        resume_data: Optional[dict],
        ats_data: Optional[dict],
        generated_questions: Optional[List[dict]],
        previous_turns: Optional[List[dict]],
        question_number: int,
        total_questions: int,
        company: str,
        role: str,
        interview_type: str,
        difficulty: str,
        candidate_answer: Optional[str],
        response_time: Optional[int],
    ) -> str:
        """Build the prompt for the ADK agent."""
        lines = [
            f"You are interviewing a candidate for the {role} position at {company}.",
            f"Interview Type: {interview_type}",
            f"Current Difficulty: {difficulty}",
            f"Question {question_number} of {total_questions}",
            "",
        ]

        if resume_data:
            lines.append("=== CANDIDATE RESUME DATA ===")
            lines.append(json.dumps(resume_data, indent=2))
            lines.append("")

        if ats_data:
            lines.append("=== ATS ANALYSIS ===")
            # Only include relevant fields
            ats_prompt = {}
            if "strengths" in ats_data:
                ats_prompt["strengths"] = ats_data["strengths"]
            if "weaknesses" in ats_data:
                ats_prompt["weaknesses"] = ats_data["weaknesses"]
            if "missing_technical_skills" in ats_data:
                ats_prompt["missing_technical_skills"] = ats_data["missing_technical_skills"]
            if "skill_gap_analysis" in ats_data:
                ats_prompt["skill_gap_analysis"] = ats_data["skill_gap_analysis"]
            if "overall_score" in ats_data:
                ats_prompt["overall_score"] = ats_data["overall_score"]
            if ats_prompt:
                lines.append(json.dumps(ats_prompt, indent=2))
                lines.append("")

        if generated_questions:
            lines.append("=== GENERATED QUESTIONS (for reference) ===")
            lines.append(json.dumps(generated_questions[:5], indent=2))
            lines.append("")

        if previous_turns:
            lines.append("=== PREVIOUS INTERVIEW TURNS (conversation history) ===")
            for idx, turn in enumerate(previous_turns, 1):
                lines.append(f"--- Turn {idx} ---")
                q_text = turn.get("question", "")
                a_text = turn.get("candidate_answer", "")
                ev_text = turn.get("evaluation", "")
                sc_text = turn.get("score", "")
                fu_text = turn.get("follow_up", "")
                cat_text = turn.get("category", "")
                diff_text = turn.get("difficulty", "")
                lines.append(f"Category: {cat_text}")
                lines.append(f"Difficulty: {diff_text}")
                lines.append(f"Question: {q_text}")
                if a_text:
                    lines.append(f"Candidate Answer: {a_text}")
                if ev_text:
                    lines.append(f"Evaluation: {ev_text}")
                if sc_text:
                    lines.append(f"Score: {sc_text}")
                if fu_text:
                    lines.append(f"Follow-up: {fu_text}")
                lines.append("")
        else:
            lines.append("This is the FIRST question of the interview. "
                         "There is no conversation history yet.")
            lines.append("")

        if candidate_answer is not None:
            lines.append("=== CANDIDATE'S ANSWER TO EVALUATE ===")
            lines.append(candidate_answer)
            if response_time:
                lines.append(f"(Response time: {response_time} seconds)")
            lines.append("")
            lines.append(
                "Please evaluate this answer, provide a score (0-100), "
                "and then ask the NEXT question (question_number + 1). "
                "Use the follow-up logic based on the score."
            )
        else:
            lines.append(
                "This is the first turn. Provide an opening question "
                "appropriate for this interview type and difficulty."
            )
            lines.append(
                "Set evaluation='' and score=0 for the first turn."
            )

        lines.append(
            "\nRemember: Ask ONLY ONE question. Never repeat questions. "
            "If this is the last question (question_number == total_questions), "
            "set is_final=True and provide a transcript_summary."
        )

        return "\n".join(lines)


class InterviewAgentError(Exception):
    """Raised when the interview agent encounters an unrecoverable error.

    Possible causes:
    - Empty input data
    - Gemini API timeout or failure
    - Malformed JSON in Gemini response
    """
