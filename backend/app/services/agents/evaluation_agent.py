"""Production AI Evaluation & Feedback Agent.

An ADK Agent that performs a comprehensive post-interview evaluation
of a completed mock interview session. It consumes the full transcript,
resume analysis, and ATS scores to produce a structured evaluation.

The agent uses ``google.adk.agents.Agent`` with an ``output_schema``
set to :class:`InterviewEvaluationOutput`, ensuring Gemini returns
strictly typed JSON conforming to the schema.

Usage
-----
The primary entry point is :func:`run_evaluation_agent`, which is an
``async`` function that:
1. Builds a context string from the session data.
2. Runs the ADK Agent via ``Runner.run_debug``.
3. Parses the final response into an ``InterviewEvaluationOutput``.
4. Persists the result to the database via ``CRUDInterviewEvaluation``.

The agent is a **singleton** — it is created once at module import
time and reused across requests.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.schemas.interview_evaluation import (
    InterviewEvaluationOutput,
    InterviewEvaluationCreate,
    InterviewEvaluationResponse,
)
from backend.app.crud.crud_interview_evaluation import interview_evaluation_crud
from backend.app.models.models import InterviewSession
from backend.app.models.interview_turn import InterviewTurn
from backend.app.models.question import Question
from backend.app.models.resume_analysis import ResumeAnalysis
from backend.app.models.ats_score import AtsScore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ADK Agent singleton
# ---------------------------------------------------------------------------

_EVALUATION_AGENT = None
_EVALUATION_SERVICE = None


def _get_evaluation_agent():
    """Lazy-initialise and return the ADK Evaluation Agent singleton.

    The agent is configured with the Gemini model and the
    ``InterviewEvaluationOutput`` as its ``output_schema``.
    """
    global _EVALUATION_AGENT, _EVALUATION_SERVICE

    if _EVALUATION_AGENT is not None:
        return _EVALUATION_AGENT, _EVALUATION_SERVICE

    try:
        from google.adk.agents import Agent
        from google.adk.sessions import InMemorySessionService

        _EVALUATION_SERVICE = InMemorySessionService()

        _EVALUATION_AGENT = Agent(
            name="evaluation_agent",
            model=settings.GEMINI_MODEL,
            instruction=(
                "You are an expert interview evaluator. Your task is to "
                "evaluate a candidate's performance in a mock interview.\n\n"
                "You will receive:\n"
                "1. The interview transcript (questions and answers).\n"
                "2. The resume analysis (if available).\n"
                "3. The ATS score (if available).\n\n"
                "Analyse the candidate's performance and return a structured "
                "evaluation covering:\n"
                "- Section scores: technical, communication, problem-solving, "
                "confidence, behavioural, and coding (each 0-100).\n"
                "- An overall composite score (0-100).\n"
                "- Identified strengths and weaknesses.\n"
                "- Topics the candidate missed or excelled in.\n"
                "- Actionable improvement suggestions.\n"
                "- A detailed recommendation.\n"
                "- A hire decision (Strong Hire / Hire / Borderline / Reject).\n"
                "- An overall difficulty level (Easy / Medium / Hard).\n"
                "- A human-readable evaluation summary.\n\n"
                "Be objective, specific, and constructive in your feedback."
            ),
            output_schema=InterviewEvaluationOutput,
        )
        logger.info("Evaluation Agent initialised successfully.")
    except ImportError as e:
        logger.warning(
            "google.adk not available — using fallback evaluation agent. "
            "Install with: uv pip install google-adk. Error: %s",
            e,
        )
        _EVALUATION_AGENT = None
        _EVALUATION_SERVICE = None
    except Exception as e:
        logger.error("Failed to initialise Evaluation Agent: %s", e)
        _EVALUATION_AGENT = None
        _EVALUATION_SERVICE = None

    return _EVALUATION_AGENT, _EVALUATION_SERVICE


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------


def _build_evaluation_context(
    session: InterviewSession,
    turns: list[InterviewTurn],
    questions: list[Question],
    resume_analysis: Optional[dict] = None,
    ats_score: Optional[dict] = None,
) -> str:
    """Build a detailed context string from the interview data.

    This string is passed as the user prompt to the ADK Agent.
    """
    context_parts = [
        "# Mock Interview Evaluation Request",
        "",
        "## Session Information",
        f"- Job Title: {session.role or 'Not specified'}",
        f"- Company: {session.company or 'Not specified'}",
        f"- Interview Type: {session.interview_type or 'Not specified'}",
        f"- Status: {session.status}",
        "",
    ]

    if resume_analysis:
        context_parts.extend([
            "## Resume Analysis",
            json.dumps(resume_analysis, indent=2, default=str),
            "",
        ])

    if ats_score:
        context_parts.extend([
            "## ATS Score",
            json.dumps(ats_score, indent=2, default=str),
            "",
        ])

    context_parts.append("## Transcript (Questions & Answers)")
    context_parts.append("")

    for i, turn in enumerate(turns, 1):
        context_parts.append(f"### Q{i}: {turn.question or 'N/A'}")
        context_parts.append(f"- Category: {turn.category or 'General'}")
        context_parts.append(f"- Difficulty: {turn.difficulty or 'Medium'}")
        context_parts.append(f"- Answer: {turn.candidate_answer or 'No answer provided'}")
        context_parts.append(f"- Score: {turn.score or 0}/10")
        context_parts.append(f"- Evaluation: {turn.evaluation or 'Not evaluated'}")
        context_parts.append("")

    context_parts.append(
        "Please evaluate the candidate's overall performance and return "
        "a structured evaluation."
    )

    return "\n".join(context_parts)


# ---------------------------------------------------------------------------
# Fallback evaluation (used when ADK is unavailable)
# ---------------------------------------------------------------------------


def _fallback_evaluation(
    session: InterviewSession,
    turns: list[InterviewTurn],
) -> InterviewEvaluationOutput:
    """Produce a basic evaluation when the ADK agent is not available.

    This uses simple heuristics to avoid breaking the interview flow
    during development or when google-adk is not installed.
    """
    total_score = 0
    answered = 0
    categories: dict[str, list[int]] = {}

    for turn in turns:
        if turn.score is not None:
            normalized = turn.score * 10
            total_score += normalized
            answered += 1
        if turn.category:
            categories.setdefault(turn.category, []).append(
                (turn.score or 0) * 10
            )

    avg_overall = total_score // answered if answered > 0 else 50
    avg_overall = max(0, min(100, avg_overall))

    tech_scores = categories.get("Technical", []) or [50]
    comm_scores = categories.get("Communication", []) or [50]

    strengths = []
    weaknesses = []
    total_turns = len(turns) if turns else 1

    if avg_overall >= 70:
        strengths.append("Good overall performance")
        strengths.append("Answered most questions thoroughly")
    else:
        weaknesses.append("Overall performance needs improvement")

    if sum(tech_scores) // len(tech_scores) >= 60:
        strengths.append("Demonstrated technical knowledge")
    else:
        weaknesses.append("Technical knowledge needs strengthening")

    if sum(comm_scores) // len(comm_scores) >= 60:
        strengths.append("Good communication skills")
    else:
        weaknesses.append("Communication could be clearer")

    if avg_overall >= 80:
        hire_decision = "Hire"
    elif avg_overall >= 60:
        hire_decision = "Borderline"
    else:
        hire_decision = "Reject"

    difficulty = "Medium"

    return InterviewEvaluationOutput(
        overall_score=avg_overall,
        technical_score=sum(tech_scores) // len(tech_scores),
        communication_score=sum(comm_scores) // len(comm_scores),
        problem_solving_score=avg_overall,
        confidence_score=avg_overall,
        behavioral_score=avg_overall,
        coding_score=avg_overall,
        strengths=strengths,
        weaknesses=weaknesses,
        missed_topics=[],
        strong_topics=[],
        improvement_suggestions=[
            "Practice more mock interviews",
            "Review technical fundamentals",
        ],
        recommendation=(
            f"Candidate scored {avg_overall}/100 overall. "
            f"Recommendation: {hire_decision}."
        ),
        hire_decision=hire_decision,
        difficulty_level=difficulty,
        evaluation_summary=(
            f"Candidate completed {total_turns} questions with an "
            f"average score of {avg_overall}/100. "
            f"Hire decision: {hire_decision}."
        ),
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

EVALUATION_AGENT_DESCRIPTION = (
    "Evaluates a completed mock interview session and generates a "
    "structured, multi-dimensional assessment of the candidate's "
    "performance."
)


async def run_evaluation_agent(
    db: Session,
    session_id: str,
    user_id: str,
) -> InterviewEvaluationResponse:
    """Run the Evaluation Agent for a completed session and persist results.

    This function:
    1. Loads the session, turns, questions, resume analysis, and ATS score.
    2. Builds a prompt context from all data.
    3. Calls the ADK Agent (or fallback).
    4. Parses the structured ``InterviewEvaluationOutput``.
    5. Persists the evaluation to the database.

    Args:
        db: Active database session.
        session_id: The interview session to evaluate.
        user_id: The owner of the session.

    Returns:
        The persisted evaluation as an ``InterviewEvaluationResponse``.

    Raises:
        ValueError: If the session is not found or not completed.
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
    ).first()

    if not session:
        raise ValueError(f"Session {session_id} not found for user {user_id}")

    if session.status not in ("completed", "closed"):
        raise ValueError(
            f"Session {session_id} has status '{session.status}'. "
            "Only completed sessions can be evaluated."
        )

    turns = (
        db.query(InterviewTurn)
        .filter(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.created_at)
        .all()
    )

    questions = []
    resume_analysis_data = None
    resume_analysis = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == user_id)
        .order_by(ResumeAnalysis.created_at.desc())
        .first()
    )
    if resume_analysis:
        resume_analysis_data = {
            "total_score": resume_analysis.ats_score or 0,
            "skills_match_score": resume_analysis.ats_score or 0,
            "experience_score": 0,
            "education_score": 0,
            "matched_skills": resume_analysis.skills or [],
            "missing_skills": resume_analysis.missing_skills or [],
            "ats_friendly": False,
            "recommendations": resume_analysis.recommendations or [],
        }

    ats_score_data = None
    ats_record = (
        db.query(AtsScore)
        .filter(AtsScore.user_id == user_id)
        .order_by(AtsScore.created_at.desc())
        .first()
    )
    if ats_record:
        ats_score_data = {
            "overall_score": ats_record.overall_score,
            "strengths": ats_record.strengths,
            "weaknesses": ats_record.weaknesses,
            "missing_keywords": ats_record.missing_keywords,
            "resume_structure_score": ats_record.resume_structure_score,
            "grammar_score": ats_record.grammar_score,
            "section_scores": ats_record.section_scores,
            "project_quality_score": ats_record.project_quality_score,
            "education_score": ats_record.education_score,
            "experience_score": ats_record.experience_score,
            "certification_score": ats_record.certification_score,
            "improvement_suggestions": ats_record.improvement_suggestions,
        }

    context = _build_evaluation_context(
        session=session,
        turns=turns,
        questions=questions,
        resume_analysis=resume_analysis_data,
        ats_score=ats_score_data,
    )

    agent, _ = _get_evaluation_agent()
    if agent is not None:
        try:
            result = await _run_adk_agent(agent, context)
        except Exception as e:
            exc_type = type(e).__name__
            http_status = getattr(e, "code", None)
            if http_status is None:
                cause = getattr(e, "__cause__", None)
                http_status = getattr(cause, "code", None) if cause is not None else None
            logger.error(
                "ADK agent failed — exception=%s, http_status=%s, message=%s. "
                "Falling back to heuristic evaluation.",
                exc_type,
                http_status if http_status is not None else "N/A",
                str(e),
            )
            result = _fallback_evaluation(session, turns)
    else:
        logger.info("ADK agent not available, using fallback evaluation")
        result = _fallback_evaluation(session, turns)

    evaluation_create = InterviewEvaluationCreate(
        session_id=session_id,
        user_id=user_id,
        overall_score=result.overall_score,
        technical_score=result.technical_score,
        communication_score=result.communication_score,
        problem_solving_score=result.problem_solving_score,
        confidence_score=result.confidence_score,
        behavioral_score=result.behavioral_score,
        coding_score=result.coding_score,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        missed_topics=result.missed_topics,
        strong_topics=result.strong_topics,
        improvement_suggestions=result.improvement_suggestions,
        recommendation=result.recommendation,
        hire_decision=result.hire_decision,
        difficulty_level=result.difficulty_level,
        evaluation_summary=result.evaluation_summary,
    )

    saved = interview_evaluation_crud.create(db, obj_in=evaluation_create)
    logger.info(
        "Evaluation created for session %s with score %d",
        session_id,
        result.overall_score,
    )

    return InterviewEvaluationResponse.model_validate(saved)


async def _run_adk_agent(
    agent,
    context: str,
) -> InterviewEvaluationOutput:
    """Run the ADK Agent and parse its output.

    Uses ``Runner.run_debug`` to send the context to the agent and
    collect the structured ``output_schema`` response.

    Args:
        agent: The ADK Agent instance.
        context: Prompt string built from interview data.

    Returns:
        A validated ``InterviewEvaluationOutput`` instance.

    Raises:
        RuntimeError: If the agent returns no output or malformed data.
    """
    from google.adk.runners import Runner

    session_service = _EVALUATION_SERVICE
    runner = Runner(
        agent=agent,
        app_name="evaluation_agent",
        session_service=session_service,
    )

    events = await runner.run_debug(
        user_messages=[context],
        user_id="evaluation_user",
        session_id="evaluation_session",
    )

    if not events:
        raise RuntimeError("Evaluation Agent returned no events")

    final_event = events[-1]
    if not final_event.content or not final_event.content.parts:
        raise RuntimeError("Evaluation Agent returned empty content")

    final_part = final_event.content.parts[-1]
    output_text = None

    if final_part.text:
        output_text = final_part.text
    elif final_part.function_call:
        logger.warning("Agent returned function call instead of text output")
        try:
            output_text = json.dumps(final_part.function_call.args)
        except Exception:
            pass

    if not output_text:
        raise RuntimeError("Evaluation Agent returned no parsable output")

    try:
        parsed = json.loads(output_text)
        return InterviewEvaluationOutput(**parsed)
    except (json.JSONDecodeError, Exception) as e:
        raise RuntimeError(
            f"Failed to parse evaluation output: {e}. "
            f"Raw output: {output_text[:500]}"
        )
