"""Production Personalized Study Plan AI Agent.

An ADK Agent that generates a personalized learning roadmap based on
the candidate's resume analysis, ATS scores, and interview evaluation.

The agent uses ``google.adk.agents.Agent`` with an ``output_schema``
set to :class:`StudyPlanOutput`, ensuring Gemini returns strictly typed
JSON conforming to the schema.

The agent supports generating plans of different durations:
- 7-Day Rapid Preparation Plan
- 15-Day Focused Preparation Plan
- 30-Day Comprehensive Preparation Plan
- 60-Day Placement Preparation Plan

Usage
-----
The primary entry point is :func:`run_study_plan_agent`, which is an
``async`` function that:
1. Loads the evaluation, resume analysis, and ATS data.
2. Builds a context string from all available data.
3. Runs the ADK Agent via ``Runner.run_debug``.
4. Parses the final response into a ``StudyPlanOutput``.
5. Persists the result to the database via ``CRUDStudyPlanAI``.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.schemas.study_plan_ai import (
    StudyPlanOutput,
    StudyPlanAICreate,
    StudyPlanAIResponse,
)
from backend.app.crud.crud_study_plan_ai import study_plan_ai_crud
from backend.app.models.interview_evaluation import InterviewEvaluation
from backend.app.models.resume_analysis import ResumeAnalysis
from backend.app.models.ats_score import AtsScore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ADK Agent singleton
# ---------------------------------------------------------------------------

_STUDY_PLAN_AGENT = None
_STUDY_PLAN_SERVICE = None


def _get_study_plan_agent():
    """Lazy-initialise and return the ADK Study Plan Agent singleton.

    The agent is configured with the Gemini model and the
    ``StudyPlanOutput`` as its ``output_schema``.
    """
    global _STUDY_PLAN_AGENT, _STUDY_PLAN_SERVICE

    if _STUDY_PLAN_AGENT is not None:
        return _STUDY_PLAN_AGENT, _STUDY_PLAN_SERVICE

    try:
        from google.adk.agents import Agent
        from google.adk.sessions import InMemorySessionService

        _STUDY_PLAN_SERVICE = InMemorySessionService()

        _STUDY_PLAN_AGENT = Agent(
            name="study_plan_agent",
            model=settings.GEMINI_MODEL,
            instruction=(
                "You are an expert career coach and study planner. Your task "
                "is to generate a personalized study plan for a job candidate.\n\n"
                "You will receive:\n"
                "1. Interview evaluation results (scores, strengths, weaknesses, "
                "missed topics, improvement suggestions).\n"
                "2. Resume analysis (skills, matched skills, missing skills).\n"
                "3. ATS score analysis (keyword matches, gaps).\n\n"
                "Based on this data, create a structured study plan covering:\n"
                "- A roadmap overview with weekly focus areas\n"
                "- Day-by-day tasks with topic, difficulty, estimated time, "
                "coding task, reading task, revision task, and goal\n"
                "- Weekly goals and milestones with mini-projects\n"
                "- Coding practice recommendations by platform and difficulty\n"
                "- Interview practice recommendations with questions and tips\n"
                "- Recommended projects to build missing skills\n"
                "- Recommended certifications for the target role\n"
                "- Learning resources (docs, books, videos, courses)\n\n"
                "Prioritize the candidate's weakest topics first. Build on "
                "their strong topics with advanced material.\n"
                "Be specific, practical, and actionable.\n"
                "The study_duration field must match the requested duration."
            ),
            output_schema=StudyPlanOutput,
        )
        logger.info("Study Plan Agent initialised successfully.")
    except ImportError as e:
        logger.warning(
            "google.adk not available — using fallback study plan agent. "
            "Install with: uv pip install google-adk. Error: %s",
            e,
        )
        _STUDY_PLAN_AGENT = None
        _STUDY_PLAN_SERVICE = None
    except Exception as e:
        logger.error("Failed to initialise Study Plan Agent: %s", e)
        _STUDY_PLAN_AGENT = None
        _STUDY_PLAN_SERVICE = None

    return _STUDY_PLAN_AGENT, _STUDY_PLAN_SERVICE


# ---------------------------------------------------------------------------
# Duration labels
# ---------------------------------------------------------------------------

_DURATION_LABELS = {
    7: "7-Day Rapid Preparation Plan",
    15: "15-Day Focused Preparation Plan",
    30: "30-Day Comprehensive Preparation Plan",
    60: "60-Day Placement Preparation Plan",
}


def _duration_label(days: int) -> str:
    return _DURATION_LABELS.get(days, f"{days}-Day Preparation Plan")


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------


def _build_study_plan_context(
    evaluation: Optional[InterviewEvaluation] = None,
    resume_analysis: Optional[dict] = None,
    ats_score: Optional[dict] = None,
    target_role: Optional[str] = None,
    target_company: Optional[str] = None,
    study_duration: int = 30,
) -> str:
    """Build a detailed context string from candidate data.

    This string is passed as the user prompt to the ADK Agent.
    """
    plan_label = _duration_label(study_duration)

    context_parts = [
        "# Personalized Study Plan Generation Request",
        "",
        f"## Plan Type: {plan_label}",
        f"- Duration: {study_duration} days",
        f"- Target Role: {target_role or 'Not specified'}",
        f"- Target Company: {target_company or 'Not specified'}",
        "",
    ]

    if evaluation:
        context_parts.extend([
            "## Interview Evaluation",
            f"- Overall Score: {evaluation.overall_score}/100",
            f"- Technical Score: {evaluation.technical_score or 'N/A'}/100",
            f"- Communication Score: {evaluation.communication_score or 'N/A'}/100",
            f"- Problem Solving Score: {evaluation.problem_solving_score or 'N/A'}/100",
            f"- Confidence Score: {evaluation.confidence_score or 'N/A'}/100",
            f"- Behavioral Score: {evaluation.behavioral_score or 'N/A'}/100",
            f"- Coding Score: {evaluation.coding_score or 'N/A'}/100",
            f"- Hire Decision: {evaluation.hire_decision or 'N/A'}",
            f"- Difficulty Level: {evaluation.difficulty_level or 'N/A'}",
            f"- Strengths: {json.dumps(evaluation.strengths or [])}",
            f"- Weaknesses: {json.dumps(evaluation.weaknesses or [])}",
            f"- Missed Topics: {json.dumps(evaluation.missed_topics or [])}",
            f"- Strong Topics: {json.dumps(evaluation.strong_topics or [])}",
            f"- Improvement Suggestions: {json.dumps(evaluation.improvement_suggestions or [])}",
            f"- Summary: {evaluation.evaluation_summary or 'N/A'}",
            "",
        ])

    if resume_analysis:
        context_parts.extend([
            "## Resume Analysis",
            json.dumps(resume_analysis, indent=2, default=str),
            "",
        ])

    if ats_score:
        context_parts.extend([
            "## ATS Score Analysis",
            json.dumps(ats_score, indent=2, default=str),
            "",
        ])

    context_parts.append(
        f"Please generate a comprehensive {study_duration}-day study plan "
        f"for the target role of '{target_role or 'the candidate'}'."
    )
    if target_company:
        context_parts.append(
            f"The plan should help the candidate prepare for interviews at "
            f"'{target_company}'."
        )
    context_parts.append(
        "\nPrioritize the candidate's weakest areas first, then build on "
        "their strengths with advanced material. Include specific, actionable "
        "tasks for each day."
    )

    return "\n".join(context_parts)


# ---------------------------------------------------------------------------
# Fallback plan (used when ADK is unavailable)
# ---------------------------------------------------------------------------


def _fallback_study_plan(
    target_role: str,
    target_company: Optional[str],
    study_duration: int,
    evaluation: Optional[InterviewEvaluation] = None,
) -> StudyPlanOutput:
    """Produce a basic study plan when the ADK agent is not available.

    Generates a simple day-by-day plan with general topics based on
    the target role and duration.
    """
    weak_topics = evaluation.weaknesses if evaluation and evaluation.weaknesses else []
    strong_topics = evaluation.strengths if evaluation and evaluation.strengths else []

    general_topics = [
        "Data Structures & Algorithms",
        "System Design",
        "Database Concepts",
        "Object-Oriented Programming",
        "Operating Systems",
        "Computer Networks",
    ]

    days = []
    for day_num in range(1, study_duration + 1):
        topic_idx = (day_num - 1) % len(general_topics)
        topic = general_topics[topic_idx]
        days.append({
            "day": day_num,
            "topic": topic,
            "difficulty": "Intermediate",
            "estimated_time": "2-3 hours",
            "coding_task": f"Solve 2 LeetCode problems on {topic}",
            "reading_task": f"Study {topic} fundamentals",
            "revision_task": f"Review notes from previous {min(3, day_num - 1)} days",
            "goal": f"Master core {topic} concepts",
        })

    return StudyPlanOutput(
        target_role=target_role,
        target_company=target_company,
        study_duration=study_duration,
        overview=(
            f"A {study_duration}-day study plan for {target_role} position. "
            f"Focus on {', '.join(weak_topics[:3]) if weak_topics else 'core concepts'}."
        ),
        weekly_focus=[f"Week {w+1}: {general_topics[w % len(general_topics)]}" for w in range(max(1, study_duration // 7))],
        weak_topics=weak_topics,
        strong_topics=strong_topics,
        daily_tasks=days,
        weekly_tasks=[
            {
                "week": w + 1,
                "focus_area": f"Week {w+1} Focus",
                "goals": [f"Complete daily tasks for week {w+1}"],
                "mini_project": None,
                "mock_interviews": 1 if w % 2 == 0 else 0,
            }
            for w in range(max(1, study_duration // 7))
        ],
        coding_practice=[
            {
                "topic": "Data Structures",
                "platform": "LeetCode",
                "problems": ["Arrays", "Strings", "Linked Lists"],
                "difficulty": "Medium",
            },
        ],
        interview_practice=[
            {
                "topic": "Technical",
                "questions": ["Tell me about yourself", "Why this role?"],
                "tips": ["Use STAR method", "Be specific"],
            },
        ],
        recommended_projects=[
            {
                "title": "Portfolio Project",
                "description": f"Build a project showcasing {target_role} skills",
                "skills_covered": [target_role],
                "difficulty": "Intermediate",
            },
        ],
        recommended_certifications=[
            {
                "name": "Relevant Certification",
                "provider": "Coursera",
                "description": f"Certification related to {target_role}",
                "estimated_time": "3 months",
            },
        ],
        recommended_resources=[
            {
                "title": f"{target_role} Interview Prep",
                "type": "Course",
                "url": None,
                "description": f"Comprehensive course for {target_role}",
            },
        ],
        roadmap_summary=(
            f"A {study_duration}-day roadmap for {target_role}. "
            f"Total of {len(days)} daily tasks across "
            f"{max(1, study_duration // 7)} weeks."
        ),
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

STUDY_PLAN_AGENT_DESCRIPTION = (
    "Generates a personalized, actionable study plan based on the "
    "candidate's resume analysis, ATS scores, and interview evaluation."
)


async def run_study_plan_agent(
    db: Session,
    user_id: str,
    evaluation_id: Optional[str] = None,
    target_role: Optional[str] = None,
    target_company: Optional[str] = None,
    study_duration: int = 30,
) -> StudyPlanAIResponse:
    """Run the Study Plan Agent and persist results.

    This function:
    1. Loads the evaluation (if provided), resume analysis, and ATS score.
    2. Builds a prompt context from all data.
    3. Calls the ADK Agent (or fallback).
    4. Parses the structured ``StudyPlanOutput``.
    5. Persists the plan to the database.

    Args:
        db: Active database session.
        user_id: The owner of the study plan.
        evaluation_id: Optional evaluation UUID to base the plan on.
        target_role: Override target role.
        target_company: Override target company.
        study_duration: Plan duration in days (7, 15, 30, or 60).

    Returns:
        The persisted plan as a ``StudyPlanAIResponse``.
    """
    logger.info("Study Plan started for user %s (duration=%d)", user_id, study_duration)

    evaluation = None
    resume_analysis_data = None
    ats_score_data = None
    resolved_role = target_role
    resolved_company = target_company

    if evaluation_id:
        evaluation = db.query(InterviewEvaluation).filter(
            InterviewEvaluation.id == evaluation_id,
            InterviewEvaluation.user_id == user_id,
        ).first()
        if not evaluation:
            raise ValueError(f"Evaluation {evaluation_id} not found for user {user_id}")
        resolved_role = resolved_role or evaluation.session.role if evaluation.session else None

    resume_analysis = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == user_id)
        .order_by(ResumeAnalysis.created_at.desc())
        .first()
    )
    if resume_analysis:
        resume_analysis_data = {
            "resume_filename": resume_analysis.resume_filename,
            "ats_score": resume_analysis.ats_score,
            "skills": resume_analysis.skills,
            "missing_skills": resume_analysis.missing_skills,
            "strengths": resume_analysis.strengths,
            "weaknesses": resume_analysis.weaknesses,
            "recommendations": resume_analysis.recommendations,
        }

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
            "missing_technical_skills": ats_record.missing_technical_skills,
            "missing_soft_skills": ats_record.missing_soft_skills,
            "missing_keywords": ats_record.missing_keywords,
            "improvement_suggestions": ats_record.improvement_suggestions,
        }

    resolved_role = resolved_role or resume_analysis_data.get("skills", ["Software Engineer"])[0] if resume_analysis_data else "Software Engineer"

    context = _build_study_plan_context(
        evaluation=evaluation,
        resume_analysis=resume_analysis_data,
        ats_score=ats_score_data,
        target_role=resolved_role,
        target_company=resolved_company,
        study_duration=study_duration,
    )

    agent, _ = _get_study_plan_agent()
    if agent is not None:
        try:
            result = await _run_adk_agent(agent, context)
        except Exception as e:
            logger.error("ADK agent failed, using fallback: %s", e)
            result = _fallback_study_plan(
                target_role=resolved_role,
                target_company=resolved_company,
                study_duration=study_duration,
                evaluation=evaluation,
            )
    else:
        logger.info("ADK agent not available, using fallback study plan")
        result = _fallback_study_plan(
            target_role=resolved_role,
            target_company=resolved_company,
            study_duration=study_duration,
            evaluation=evaluation,
        )

    daily_tasks_list = []
    if result.daily_tasks:
        daily_tasks_list = [t.model_dump() for t in result.daily_tasks]

    weekly_tasks_list = []
    if result.weekly_tasks:
        weekly_tasks_list = [t.model_dump() for t in result.weekly_tasks]

    coding_list = []
    if result.coding_practice:
        coding_list = [c.model_dump() for c in result.coding_practice]

    interview_list = []
    if result.interview_practice:
        interview_list = [i.model_dump() for i in result.interview_practice]

    projects_list = []
    if result.recommended_projects:
        projects_list = [p.model_dump() for p in result.recommended_projects]

    certs_list = []
    if result.recommended_certifications:
        certs_list = [c.model_dump() for c in result.recommended_certifications]

    resources_list = []
    if result.recommended_resources:
        resources_list = [r.model_dump() for r in result.recommended_resources]

    plan_create = StudyPlanAICreate(
        user_id=user_id,
        evaluation_id=evaluation_id,
        resume_analysis_id=evaluation.resume_analysis_id if evaluation else None,
        target_role=result.target_role,
        target_company=result.target_company,
        study_duration=result.study_duration,
        roadmap={
            "overview": result.overview,
            "weekly_focus": result.weekly_focus,
            "roadmap_summary": result.roadmap_summary,
        },
        daily_tasks=daily_tasks_list,
        weekly_tasks=weekly_tasks_list,
        weak_topics=result.weak_topics,
        strong_topics=result.strong_topics,
        coding_practice=coding_list,
        interview_practice=interview_list,
        recommended_projects=projects_list,
        recommended_certifications=certs_list,
        recommended_resources=resources_list,
        completion_percentage=0.0,
        status="active",
    )

    saved = study_plan_ai_crud.create(db, obj_in=plan_create)
    logger.info(
        "Study Plan created for user %s (role=%s, duration=%d)",
        user_id,
        result.target_role,
        result.study_duration,
    )

    return StudyPlanAIResponse.model_validate(saved)


async def _run_adk_agent(
    agent,
    context: str,
) -> StudyPlanOutput:
    """Run the ADK Agent and parse its output.

    Uses ``Runner.run_debug`` to send the context to the agent and
    collect the structured ``output_schema`` response.

    Args:
        agent: The ADK Agent instance.
        context: Prompt string built from candidate data.

    Returns:
        A validated ``StudyPlanOutput`` instance.

    Raises:
        RuntimeError: If the agent returns no output or malformed data.
    """
    from google.adk.runners import Runner

    session_service = _STUDY_PLAN_SERVICE
    runner = Runner(
        agent=agent,
        app_name="study_plan_agent",
        session_service=session_service,
    )

    events = []
    async for event in runner.run_debug(
        session_id="study_plan_session",
        user_content=context,
    ):
        events.append(event)
        if event.is_final_response():
            break

    if not events:
        raise RuntimeError("Study Plan Agent returned no events")

    final_event = events[-1]
    if not final_event.content or not final_event.content.parts:
        raise RuntimeError("Study Plan Agent returned empty content")

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
        raise RuntimeError("Study Plan Agent returned no parsable output")

    try:
        parsed = json.loads(output_text)
        return StudyPlanOutput(**parsed)
    except (json.JSONDecodeError, Exception) as e:
        raise RuntimeError(
            f"Failed to parse study plan output: {e}. "
            f"Raw output: {output_text[:500]}"
        )
