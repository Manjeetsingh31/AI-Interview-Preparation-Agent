"""Dashboard Service — aggregates analytics from all modules.

This service is the central aggregation engine for the Production
Analytics Dashboard. It queries every data source (Resume, ATS,
Interview, Evaluation, Study Plan) and computes unified statistics,
trends, and the overall readiness score.

Responsibilities
----------------
1. Collect raw data from all five domains.
2. Compute per-domain analytics (resume, ATS, interview, evaluation, study).
3. Compute skill analytics from resume skills and evaluation topics.
4. Generate timeline activity (daily / weekly / monthly).
5. Calculate the overall readiness score (0–100).
6. Persist the aggregated result to ``DashboardAnalytics``.
7. Return a ``DashboardResponse`` for API consumption.

Readiness Score Formula
-----------------------
The overall readiness score (0–100) is a weighted composite of five
sub-scores:

    readiness = (resume * 0.15) + (ats * 0.20) + (interview * 0.25)
              + (evaluation * 0.25) + (study * 0.15)

Each sub-score is normalised to 0–100:
    - **resume**: 50 if the user has any resume analysis, +10 per skill
      (capped at 100).
    - **ats**: the latest ATS overall_score (directly).
    - **interview**: average of all evaluation overall_score values
      (0 if none).
    - **evaluation**: same as interview score pillar (weighted together).
    - **study**: the completion_percentage of the latest active study plan
      (0 if none).
"""

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.crud.crud_dashboard_analytics import (
    dashboard_analytics_crud,
)
from backend.app.models.ats_score import AtsScore
from backend.app.models.interview_evaluation import InterviewEvaluation
from backend.app.models.interview_turn import InterviewTurn
from backend.app.models.resume_analysis import ResumeAnalysis
from backend.app.models.study_plan_ai import StudyPlanAI
from backend.app.models.models import InterviewSession
from backend.app.schemas.dashboard_analytics import (
    ATSAnalytics,
    DashboardResponse,
    DashboardStatistics,
    DashboardSummary,
    EvaluationAnalytics,
    InterviewAnalytics,
    ProgressAnalytics,
    ResumeAnalytics,
    SkillAnalytics,
    StudyAnalytics,
    TimelineAnalytics,
    DashboardAnalyticsCreate,
)

logger = logging.getLogger(__name__)

# Readiness score weights
WEIGHT_RESUME = 0.15
WEIGHT_ATS = 0.20
WEIGHT_INTERVIEW = 0.25
WEIGHT_EVALUATION = 0.25
WEIGHT_STUDY = 0.15


# ---------------------------------------------------------------------------
# Domain collectors
# ---------------------------------------------------------------------------


def _collect_resume_data(db: Session, user_id: str) -> ResumeAnalytics:
    """Collect resume upload and analysis statistics."""
    analyses = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == user_id)
        .order_by(ResumeAnalysis.created_at.desc())
        .all()
    )
    if not analyses:
        return ResumeAnalytics()

    latest = analyses[0]
    all_skills = set()
    all_missing = set()
    all_strengths = set()
    all_weaknesses = set()
    for a in analyses:
        if a.skills:
            all_skills.update(a.skills)
        if a.missing_skills:
            all_missing.update(a.missing_skills)
        if a.strengths:
            all_strengths.update(a.strengths)
        if a.weaknesses:
            all_weaknesses.update(a.weaknesses)

    return ResumeAnalytics(
        resume_uploaded=True,
        resume_analysed=True,
        resume_count=len(analyses),
        ats_score=latest.ats_score,
        skills_count=len(all_skills),
        missing_skills_count=len(all_missing),
        strengths_count=len(all_strengths),
        weaknesses_count=len(all_weaknesses),
        last_analysed=latest.created_at,
    )


def _collect_ats_data(db: Session, user_id: str) -> ATSAnalytics:
    """Collect ATS score history and keyword analysis."""
    records = (
        db.query(AtsScore)
        .filter(AtsScore.user_id == user_id)
        .order_by(AtsScore.created_at.desc())
        .all()
    )
    if not records:
        return ATSAnalytics()

    latest = records[0]
    previous = records[1] if len(records) > 1 else None
    missing_keywords = set()
    suggestions = set()
    for r in records:
        if r.missing_keywords:
            missing_keywords.update(r.missing_keywords)
        if r.improvement_suggestions:
            suggestions.update(r.improvement_suggestions)

    improvement = None
    if previous and latest.overall_score is not None and previous.overall_score is not None:
        if previous.overall_score > 0:
            improvement = round(
                ((latest.overall_score - previous.overall_score)
                 / previous.overall_score) * 100,
                1,
            )

    section_scores = {}
    if latest.section_scores:
        section_scores = latest.section_scores

    return ATSAnalytics(
        current_score=latest.overall_score,
        previous_score=previous.overall_score if previous else None,
        improvement=improvement,
        total_analyses=len(records),
        keyword_coverage=None,
        missing_keywords=sorted(missing_keywords),
        formatting_score=latest.resume_structure_score,
        section_scores=section_scores,
        suggestions=sorted(suggestions),
    )


def _collect_interview_data(db: Session, user_id: str) -> InterviewAnalytics:
    """Collect interview session and turn analytics."""
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    if not sessions:
        return InterviewAnalytics()

    completed = [s for s in sessions if s.status == "completed"]
    total_completed = len(completed)

    # Evaluation scores from InterviewEvaluation
    evaluations = (
        db.query(InterviewEvaluation)
        .filter(InterviewEvaluation.user_id == user_id)
        .all()
    )
    scores = [e.overall_score for e in evaluations if e.overall_score is not None]

    # Turn data
    turns = (
        db.query(InterviewTurn)
        .filter(InterviewTurn.user_id == user_id)
        .all()
    )
    total_turns = len(turns)
    scored_turns = [t for t in turns if t.score is not None]
    response_times = [t.response_time for t in turns if t.response_time is not None]

    avg_response = None
    if response_times:
        avg_response = round(sum(response_times) / len(response_times), 1)

    difficulty_dist: Dict[str, int] = {}
    category_dist: Dict[str, int] = {}
    for t in turns:
        if t.difficulty:
            difficulty_dist[t.difficulty] = difficulty_dist.get(t.difficulty, 0) + 1
        if t.category:
            category_dist[t.category] = category_dist.get(t.category, 0) + 1

    total_categorized = sum(category_dist.values()) or 1
    tech_pct = round((category_dist.get("Technical", 0) / total_categorized) * 100, 1)
    hr_pct = round((category_dist.get("HR", 0) / total_categorized) * 100, 1)
    behav_pct = round((category_dist.get("Behavioral", 0) / total_categorized) * 100, 1)
    coding_pct = round((category_dist.get("Coding", 0) / total_categorized) * 100, 1)

    avg_score = None
    if scores:
        avg_score = round(sum(scores) / len(scores), 1)

    return InterviewAnalytics(
        total_sessions=len(sessions),
        completed_sessions=total_completed,
        average_score=avg_score,
        best_score=max(scores) if scores else None,
        worst_score=min(scores) if scores else None,
        questions_answered=total_turns,
        average_response_time=avg_response,
        difficulty_distribution=difficulty_dist,
        category_distribution=category_dist,
        technical_percentage=tech_pct,
        hr_percentage=hr_pct,
        behavioural_percentage=behav_pct,
        coding_percentage=coding_pct,
    )


def _collect_evaluation_data(
    db: Session, user_id: str
) -> Tuple[EvaluationAnalytics, int, int]:
    """Collect evaluation-specific aggregated scores.

    Returns:
        Tuple of (EvaluationAnalytics, best_score, worst_score).
    """
    evaluations = (
        db.query(InterviewEvaluation)
        .filter(InterviewEvaluation.user_id == user_id)
        .order_by(InterviewEvaluation.created_at.desc())
        .all()
    )
    if not evaluations:
        return EvaluationAnalytics(), None, None

    scores = [e.overall_score for e in evaluations if e.overall_score is not None]
    n = len(scores)
    avg_overall = round(sum(scores) / n, 1) if n else None

    tech_scores = [e.technical_score for e in evaluations if e.technical_score is not None]
    comm_scores = [e.communication_score for e in evaluations if e.communication_score is not None]
    prob_scores = [e.problem_solving_score for e in evaluations if e.problem_solving_score is not None]
    conf_scores = [e.confidence_score for e in evaluations if e.confidence_score is not None]
    behav_scores = [e.behavioral_score for e in evaluations if e.behavioral_score is not None]
    coding_scores = [e.coding_score for e in evaluations if e.coding_score is not None]

    all_strong: List[str] = []
    all_weak: List[str] = []
    hire_dist: Dict[str, int] = {}
    for e in evaluations:
        if e.strong_topics:
            all_strong.extend(e.strong_topics)
        if e.weaknesses:
            all_weak.extend(e.weaknesses)
        if e.hire_decision:
            hire_dist[e.hire_decision] = hire_dist.get(e.hire_decision, 0) + 1

    strong_counter = Counter(all_strong)
    weak_counter = Counter(all_weak)

    # Improvement rate: compare first half vs second half
    improvement_rate = None
    if n >= 4:
        mid = n // 2
        first_half = sum(scores[:mid]) / mid
        second_half = sum(scores[mid:]) / (n - mid)
        if first_half > 0:
            improvement_rate = round(
                ((second_half - first_half) / first_half) * 100, 1
            )

    best_score = max(scores) if scores else None
    worst_score = min(scores) if scores else None

    return (
        EvaluationAnalytics(
            total_evaluations=len(evaluations),
            average_overall_score=avg_overall,
            average_technical_score=round(sum(tech_scores) / len(tech_scores), 1)
            if tech_scores else None,
            average_communication_score=round(sum(comm_scores) / len(comm_scores), 1)
            if comm_scores else None,
            average_problem_solving_score=round(sum(prob_scores) / len(prob_scores), 1)
            if prob_scores else None,
            average_confidence_score=round(sum(conf_scores) / len(conf_scores), 1)
            if conf_scores else None,
            average_behavioral_score=round(sum(behav_scores) / len(behav_scores), 1)
            if behav_scores else None,
            average_coding_score=round(sum(coding_scores) / len(coding_scores), 1)
            if coding_scores else None,
            strongest_topics=[t for t, _ in strong_counter.most_common(5)],
            weakest_topics=[t for t, _ in weak_counter.most_common(5)],
            hire_decision_distribution=hire_dist,
            improvement_rate=improvement_rate,
        ),
        best_score,
        worst_score,
    )


def _collect_study_data(db: Session, user_id: str) -> StudyAnalytics:
    """Collect study plan progress and task tracking."""
    plans = (
        db.query(StudyPlanAI)
        .filter(StudyPlanAI.user_id == user_id)
        .order_by(StudyPlanAI.created_at.desc())
        .all()
    )
    if not plans:
        return StudyAnalytics()

    active_count = sum(1 for p in plans if p.status == "active")
    completed_count = sum(1 for p in plans if p.status == "completed")

    total_completed_tasks = 0
    total_pending_tasks = 0
    completion_pcts = []
    for p in plans:
        completion_pcts.append(p.completion_percentage or 0)
        daily = p.daily_tasks or []
        n_done = int((p.completion_percentage or 0) / 100 * len(daily))
        total_completed_tasks += n_done
        total_pending_tasks += len(daily) - n_done

    avg_completion = round(sum(completion_pcts) / len(completion_pcts), 1)

    return StudyAnalytics(
        total_plans=len(plans),
        active_plans=active_count,
        completed_plans=completed_count,
        tasks_completed=total_completed_tasks,
        tasks_pending=total_pending_tasks,
        completion_percentage=avg_completion,
        coding_hours=None,
        learning_hours=None,
        practice_sessions=0,
        revision_sessions=0,
    )


def _collect_skill_data(db: Session, user_id: str) -> SkillAnalytics:
    """Collect skill analytics from resume analysis and evaluations."""
    resume_analyses = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.user_id == user_id)
        .order_by(ResumeAnalysis.created_at.desc())
        .all()
    )
    evaluations = (
        db.query(InterviewEvaluation)
        .filter(InterviewEvaluation.user_id == user_id)
        .all()
    )

    # Resume skills
    has_skills = set()
    missing_skills = set()
    strengths = set()
    weaknesses = set()
    for r in resume_analyses:
        if r.skills:
            has_skills.update(r.skills)
        if r.missing_skills:
            missing_skills.update(r.missing_skills)
        if r.strengths:
            strengths.update(r.strengths)
        if r.weaknesses:
            weaknesses.update(r.weaknesses)

    # Evaluation topics
    strong_topics = []
    weak_topics = []
    for e in evaluations:
        if e.strong_topics:
            strong_topics.extend(e.strong_topics)
        if e.weaknesses:
            weak_topics.extend(e.weaknesses)

    strong_counter = Counter(strong_topics)
    weak_counter = Counter(weak_topics)

    top_skills = sorted(has_skills)[:10] if has_skills else []
    strong_skills = [s for s in top_skills if s in strengths] or list(has_skills)[:5]
    weak_skills = [s for s in top_skills if s in weaknesses] or list(missing_skills)[:5]

    # Frequency
    freq: Dict[str, int] = {}
    for s in has_skills:
        freq[s] = freq.get(s, 0) + 1

    coverage = None
    total_known = len(has_skills) + len(missing_skills)
    if total_known > 0:
        coverage = round((len(has_skills) / total_known) * 100, 1)

    return SkillAnalytics(
        top_skills=top_skills,
        missing_skills=sorted(missing_skills)[:10],
        weak_skills=weak_skills[:10],
        strong_skills=strong_skills[:10],
        skill_coverage=coverage,
        skill_frequency=freq,
        skill_improvement=None,
    )


def _collect_timeline_data(
    db: Session, user_id: str
) -> TimelineAnalytics:
    """Generate daily / weekly / monthly timeline data."""
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.created_at.asc())
        .all()
    )
    evaluations = (
        db.query(InterviewEvaluation)
        .filter(InterviewEvaluation.user_id == user_id)
        .order_by(InterviewEvaluation.created_at.asc())
        .all()
    )

    daily_map: Dict[str, Dict[str, Any]] = {}
    weekly_map: Dict[str, Dict[str, Any]] = {}
    monthly_map: Dict[str, Dict[str, Any]] = {}

    def _week_key(dt: datetime) -> str:
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    def _month_key(dt: datetime) -> str:
        return dt.strftime("%Y-%m")

    for s in sessions:
        date_key = s.created_at.strftime("%Y-%m-%d")
        wk = _week_key(s.created_at)
        mo = _month_key(s.created_at)

        for mapping, key in [(daily_map, date_key), (weekly_map, wk), (monthly_map, mo)]:
            if key not in mapping:
                mapping[key] = {
                    "period": key,
                    "sessions": 0,
                    "completed": 0,
                    "evaluations": 0,
                }
            mapping[key]["sessions"] += 1
            if s.status == "completed":
                mapping[key]["completed"] += 1

    for e in evaluations:
        date_key = e.created_at.strftime("%Y-%m-%d")
        wk = _week_key(e.created_at)
        mo = _month_key(e.created_at)
        for mapping, key in [(daily_map, date_key), (weekly_map, wk), (monthly_map, mo)]:
            if key not in mapping:
                mapping[key] = {
                    "period": key,
                    "sessions": 0,
                    "completed": 0,
                    "evaluations": 0,
                }
            mapping[key]["evaluations"] += 1

    def _sorted(amap):
        return [amap[k] for k in sorted(amap.keys())]

    return TimelineAnalytics(
        daily=_sorted(daily_map),
        weekly=_sorted(weekly_map),
        monthly=_sorted(monthly_map),
    )


# ---------------------------------------------------------------------------
# Readiness score
# ---------------------------------------------------------------------------


def _compute_readiness_score(
    resume: ResumeAnalytics,
    ats: ATSAnalytics,
    interview: InterviewAnalytics,
    evaluation: EvaluationAnalytics,
    study: StudyAnalytics,
) -> int:
    """Compute overall readiness score (0–100) using weighted formula.

    Each sub-score is normalised to 0–100 before weighting.
    """
    # Resume sub-score
    resume_score = 0
    if resume.resume_uploaded:
        resume_score = 50
        resume_score += min(resume.skills_count * 10, 50)

    # ATS sub-score
    ats_score_val = ats.current_score if ats.current_score is not None else 0

    # Interview sub-score
    interview_score_val = interview.average_score if interview.average_score is not None else 0

    # Evaluation sub-score
    eval_score_val = evaluation.average_overall_score if evaluation.average_overall_score is not None else 0
    # Weight interview and evaluation together
    combined_interview_eval = (interview_score_val + eval_score_val) / 2

    # Study sub-score
    study_score_val = study.completion_percentage if study.completion_percentage is not None else 0

    readiness = (
        resume_score * WEIGHT_RESUME
        + ats_score_val * WEIGHT_ATS
        + combined_interview_eval * WEIGHT_INTERVIEW
        + eval_score_val * WEIGHT_EVALUATION
        + study_score_val * WEIGHT_STUDY
    )

    return min(max(round(readiness), 0), 100)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

DASHBOARD_SERVICE_DESCRIPTION = (
    "Aggregates analytics from Resume, ATS, Interview, Evaluation, "
    "and Study Plan modules into a unified dashboard."
)


async def generate_dashboard(
    db: Session,
    user_id: str,
) -> DashboardResponse:
    """Generate a complete dashboard response for the given user.

    This is the primary entry point for the dashboard service. It:
    1. Collects data from all five domains.
    2. Computes aggregate statistics.
    3. Calculates the readiness score.
    4. Persists the snapshot to ``DashboardAnalytics``.
    5. Returns a ``DashboardResponse``.

    Args:
        db: Active database session.
        user_id: The target user's UUID.

    Returns:
        A fully populated ``DashboardResponse``.
    """
    logger.info("Dashboard request for user %s", user_id)

    # Collect domain data
    resume = _collect_resume_data(db, user_id)
    logger.debug("Collected resume analytics for user %s", user_id)

    ats = _collect_ats_data(db, user_id)
    logger.debug("Collected ATS analytics for user %s", user_id)

    interview = _collect_interview_data(db, user_id)
    logger.debug("Collected interview analytics for user %s", user_id)

    evaluation_analytics, best_score, worst_score = _collect_evaluation_data(db, user_id)
    logger.debug("Collected evaluation analytics for user %s", user_id)

    study = _collect_study_data(db, user_id)
    logger.debug("Collected study analytics for user %s", user_id)

    skills = _collect_skill_data(db, user_id)
    logger.debug("Collected skill analytics for user %s", user_id)

    timeline = _collect_timeline_data(db, user_id)
    logger.debug("Collected timeline analytics for user %s", user_id)

    # Readiness score
    readiness = _compute_readiness_score(resume, ats, interview, evaluation_analytics, study)
    logger.info("Readiness score computed for user %s: %d", user_id, readiness)

    # Improvement rate
    improvement_rate = evaluation_analytics.improvement_rate

    # Averages
    avg_interview_score = interview.average_score
    avg_evaluation_score = evaluation_analytics.average_overall_score

    # Build summary
    summary = DashboardSummary(
        resume_uploaded=resume.resume_uploaded,
        resume_analysed=resume.resume_analysed,
        ats_score=ats.current_score,
        total_sessions=interview.total_sessions,
        completed_sessions=interview.completed_sessions,
        average_score=avg_interview_score,
        study_completion=study.completion_percentage,
        overall_readiness_score=readiness,
    )

    # Build progress
    progress = ProgressAnalytics(
        total_sessions=interview.total_sessions,
        completed_sessions=interview.completed_sessions,
        average_ats_score=ats.current_score,
        average_interview_score=avg_interview_score,
        average_evaluation_score=avg_evaluation_score,
        best_score=best_score,
        worst_score=worst_score,
        improvement_rate=improvement_rate,
        completed_study_tasks=study.tasks_completed,
        pending_study_tasks=study.tasks_pending,
        overall_readiness_score=readiness,
    )

    # Build statistics
    statistics = DashboardStatistics(
        resume=resume,
        ats=ats,
        interview=interview,
        evaluation=evaluation_analytics,
        study=study,
        skills=skills,
        progress=progress,
        timeline=timeline,
    )

    response = DashboardResponse(
        summary=summary,
        statistics=statistics,
    )

    # Persist to database
    _persist_dashboard(db, user_id, response)
    logger.info("Dashboard generated and persisted for user %s", user_id)

    return response


async def regenerate_dashboard(
    db: Session,
    user_id: str,
) -> DashboardResponse:
    """Force-regenerate dashboard data, overwriting existing cache."""
    return await generate_dashboard(db, user_id)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _persist_dashboard(
    db: Session,
    user_id: str,
    response: DashboardResponse,
) -> None:
    """Store the current dashboard snapshot to the database."""
    s = response.statistics

    readiness_contribution = _readiness_contributions(response)

    record = dashboard_analytics_crud.get_or_create(db=db, user_id=user_id)

    update_data = dict(
        resume_stats={
            "resume_uploaded": s.resume.resume_uploaded,
            "resume_analysed": s.resume.resume_analysed,
            "resume_count": s.resume.resume_count,
            "ats_score": s.resume.ats_score,
            "skills_count": s.resume.skills_count,
            "missing_skills_count": s.resume.missing_skills_count,
            "readiness_contribution": readiness_contribution["resume"],
        },
        ats_stats={
            "current_score": s.ats.current_score,
            "previous_score": s.ats.previous_score,
            "improvement": s.ats.improvement,
            "total_analyses": s.ats.total_analyses,
            "missing_keywords": s.ats.missing_keywords,
            "formatting_score": s.ats.formatting_score,
            "suggestions": s.ats.suggestions,
            "readiness_contribution": readiness_contribution["ats"],
        },
        interview_stats={
            "total_sessions": s.interview.total_sessions,
            "completed_sessions": s.interview.completed_sessions,
            "average_score": s.interview.average_score,
            "questions_answered": s.interview.questions_answered,
            "difficulty_distribution": s.interview.difficulty_distribution,
            "category_distribution": s.interview.category_distribution,
            "readiness_contribution": readiness_contribution["interview"],
        },
        evaluation_stats={
            "total_evaluations": s.evaluation.total_evaluations,
            "average_overall_score": s.evaluation.average_overall_score,
            "strongest_topics": s.evaluation.strongest_topics,
            "weakest_topics": s.evaluation.weakest_topics,
            "hire_decision_distribution": s.evaluation.hire_decision_distribution,
            "improvement_rate": s.evaluation.improvement_rate,
            "readiness_contribution": readiness_contribution["evaluation"],
        },
        study_stats={
            "total_plans": s.study.total_plans,
            "active_plans": s.study.active_plans,
            "completed_plans": s.study.completed_plans,
            "tasks_completed": s.study.tasks_completed,
            "tasks_pending": s.study.tasks_pending,
            "completion_percentage": s.study.completion_percentage,
            "readiness_contribution": readiness_contribution["study"],
        },
        skill_stats={
            "top_skills": s.skills.top_skills,
            "missing_skills": s.skills.missing_skills,
            "weak_skills": s.skills.weak_skills,
            "strong_skills": s.skills.strong_skills,
            "skill_coverage": s.skills.skill_coverage,
            "skill_frequency": s.skills.skill_frequency,
        },
        daily_activity=s.timeline.daily,
        weekly_activity=s.timeline.weekly,
        monthly_activity=s.timeline.monthly,
        total_sessions=s.progress.total_sessions,
        average_ats_score=s.progress.average_ats_score,
        average_interview_score=s.progress.average_interview_score,
        average_evaluation_score=s.progress.average_evaluation_score,
        best_score=s.progress.best_score,
        worst_score=s.progress.worst_score,
        improvement_rate=s.progress.improvement_rate,
        completed_study_tasks=s.progress.completed_study_tasks,
        pending_study_tasks=s.progress.pending_study_tasks,
        overall_readiness_score=s.progress.overall_readiness_score,
    )

    from backend.app.schemas.dashboard_analytics import (
        DashboardAnalyticsUpdate,
    )

    dashboard_analytics_crud.update(
        db=db, db_obj=record, obj_in=DashboardAnalyticsUpdate(**update_data)
    )
    logger.info("Dashboard snapshot persisted for user %s", user_id)


def _readiness_contributions(response: DashboardResponse) -> Dict[str, int]:
    """Extract per-pillar readiness sub-scores from the response.

    Returns:
        Dict with keys: resume, ats, interview, evaluation, study.
    """
    s = response.statistics
    resume_score = 0
    if s.resume.resume_uploaded:
        resume_score = 50 + min(s.resume.skills_count * 10, 50)

    ats_score = s.ats.current_score or 0
    interview_score = s.interview.average_score or 0
    eval_score = s.evaluation.average_overall_score or 0
    study_score = s.study.completion_percentage or 0

    return {
        "resume": min(resume_score, 100),
        "ats": min(ats_score, 100),
        "interview": min(interview_score, 100),
        "evaluation": min(eval_score, 100),
        "study": min(study_score, 100),
    }
