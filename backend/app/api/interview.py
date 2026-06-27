"""Mock Interview Multi-Agent System API router.

Provides endpoints for the full interview lifecycle:

- `POST /api/interview/start` — Start a new interview session
- `POST /api/interview/answer` — Submit an answer and get the next question
- `POST /api/interview/end` — End an interview session
- `GET /api/interview/{session_id}` — Get session details
- `GET /api/interview/history` — List past sessions for the user
- `GET /api/interview/transcript/{session_id}` — Get full conversation transcript

Every step is logged: request receipt, database lookups, Gemini request &
response, database save, and any errors.
"""

import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.models.models import InterviewSession
from backend.app.models.resume_analysis_adk import ResumeAnalysisADK
from backend.app.models.ats_score import AtsScore
from backend.app.models.interview_question import InterviewQuestion
from backend.app.schemas.interview_turn import (
    InterviewAgentTurn,
    InterviewTurnCreate,
    InterviewTurnResponse,
    InterviewStartRequest,
    InterviewStartResponse,
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewEndRequest,
    InterviewSessionSummary,
    InterviewTurnConversation,
)
from backend.app.crud.crud_interview_turn import interview_turn_crud
from backend.app.services.agents.interview_agent import (
    InterviewAgent,
    InterviewAgentError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["interview"])

# --- Singleton service instances ---
_agent = InterviewAgent()


def _get_current_user_id(db: Session = Depends(get_db)) -> str:
    user = db.query(User).filter(User.email == "candidate@example.com").first()
    if not user:
        user = User(
            email="candidate@example.com",
            password_hash=hashlib.sha256(b"password123").hexdigest(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created default mock user: id=%s", user.id)
    return user.id


def _turn_to_response(turn) -> InterviewTurnResponse:
    return InterviewTurnResponse(
        id=turn.id,
        user_id=turn.user_id,
        session_id=turn.session_id,
        resume_analysis_id=turn.resume_analysis_id,
        question_number=turn.question_number,
        question=turn.question,
        candidate_answer=turn.candidate_answer,
        follow_up=turn.follow_up,
        difficulty=turn.difficulty,
        category=turn.category,
        tags=turn.tags,
        expected_answer=turn.expected_answer,
        evaluation=turn.evaluation,
        score=turn.score,
        response_time=turn.response_time,
        created_at=turn.created_at,
    )

@router.post(
    "/start",
    response_model=InterviewStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new mock interview session",
)
async def start_interview(
    request: InterviewStartRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
) -> InterviewStartResponse:
    logger.info(
        "Interview Started — user=%s, analysis=%s, company=%s, " +
        "role=%s, type=%s, difficulty=%s, n=%d",
        user_id,
        request.resume_analysis_id,
        request.company,
        request.role,
        request.interview_type,
        request.difficulty,
        request.number_of_questions,
    )

    adk_record = db.query(ResumeAnalysisADK).filter(
        ResumeAnalysisADK.id == request.resume_analysis_id
    ).first()

    if not adk_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume analysis {request.resume_analysis_id} not found.",
        )

    if not adk_record.extracted_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume analysis has no extracted JSON data. Run analysis first.",
        )

    ats_record = db.query(AtsScore).filter(
        AtsScore.resume_analysis_adk_id == request.resume_analysis_id
    ).first()
    ats_data = None
    if ats_record:
        ats_data = {
            "overall_score": ats_record.overall_score,
            "strengths": ats_record.strengths,
            "weaknesses": ats_record.weaknesses,
            "missing_technical_skills": ats_record.missing_technical_skills,
            "skill_gap_analysis": ats_record.skill_gap_analysis,
        }

    generated_questions = []
    db_questions = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.resume_analysis_id == request.resume_analysis_id,
            InterviewQuestion.user_id == user_id,
        )
        .all()
    )
    for q in db_questions:
        generated_questions.append({
            "type": q.question_type,
            "question": q.question,
            "expected_answer": q.expected_answer,
            "difficulty": q.difficulty,
            "category": q.interview_type,
        })

    new_session = InterviewSession(
        user_id=user_id,
        role=request.role,
        company=request.company,
        interview_type=request.interview_type,
        status="active",
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    session_id = new_session.id

    try:
        turn: InterviewAgentTurn = await _agent.next_turn(
            resume_data=adk_record.extracted_json,
            ats_data=ats_data,
            generated_questions=generated_questions,
            previous_turns=None,
            question_number=1,
            total_questions=request.number_of_questions,
            company=request.company,
            role=request.role,
            interview_type=request.interview_type,
            difficulty=request.difficulty,
            candidate_answer=None,
        )
    except InterviewAgentError as exc:
        db.delete(new_session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Interview agent failed: {exc}",
        ) from exc

    turn_record = InterviewTurnCreate(
        user_id=user_id,
        session_id=session_id,
        resume_analysis_id=request.resume_analysis_id,
        question_number=1,
        question=turn.question,
        follow_up=turn.follow_up if turn.follow_up else None,
        difficulty=turn.difficulty,
        category=turn.category,
        tags=turn.tags,
        expected_answer=turn.expected_answer if turn.expected_answer else None,
        evaluation=turn.evaluation if turn.evaluation else None,
        score=turn.score if turn.score else None,
    )
    interview_turn_crud.create(db=db, obj_in=turn_record)

    logger.info("Interview started: session=%s, first_question_cat=%s", session_id, turn.category)

    return InterviewStartResponse(
        session_id=session_id,
        question=turn.question,
        question_number=1,
        category=turn.category,
        difficulty=turn.difficulty,
    )


@router.post(
    "/answer",
    response_model=InterviewAnswerResponse,
    summary="Submit an answer and get the next question",
)
async def submit_answer(
    request: InterviewAnswerRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
) -> InterviewAnswerResponse:
    session = db.query(InterviewSession).filter(
        InterviewSession.id == request.session_id,
        InterviewSession.user_id == user_id,
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not active.",
        )

    latest_turn = interview_turn_crud.get_latest_turn(db=db, session_id=request.session_id)
    if not latest_turn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active question found. Start a new interview first.",
        )

    if latest_turn.candidate_answer is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This question has already been answered.",
        )

    resume_analysis_id = latest_turn.resume_analysis_id
    adk_record = None
    ats_data = None
    if resume_analysis_id:
        adk_record = db.query(ResumeAnalysisADK).filter(
            ResumeAnalysisADK.id == resume_analysis_id
        ).first()
        ats_record = db.query(AtsScore).filter(
            AtsScore.resume_analysis_adk_id == resume_analysis_id
        ).first()
        if ats_record:
            ats_data = {
                "overall_score": ats_record.overall_score,
                "strengths": ats_record.strengths,
                "weaknesses": ats_record.weaknesses,
                "missing_technical_skills": ats_record.missing_technical_skills,
                "skill_gap_analysis": ats_record.skill_gap_analysis,
            }

    previous_turns = interview_turn_crud.get_session_turns(
        db=db, session_id=request.session_id
    )

    total_questions = 10
    next_q_no = len(previous_turns) + 1

    turn_dicts = []
    for t in previous_turns:
        turn_dicts.append({
            "question_number": t.question_number,
            "question": t.question,
            "candidate_answer": t.candidate_answer,
            "follow_up": t.follow_up,
            "difficulty": t.difficulty,
            "category": t.category,
            "tags": t.tags,
            "expected_answer": t.expected_answer,
            "evaluation": t.evaluation,
            "score": t.score,
        })

    try:
        turn: InterviewAgentTurn = await _agent.next_turn(
            resume_data=adk_record.extracted_json if adk_record else None,
            ats_data=ats_data,
            generated_questions=None,
            previous_turns=turn_dicts,
            question_number=next_q_no,
            total_questions=total_questions,
            company=session.company or "Generic",
            role=session.role,
            interview_type=session.interview_type,
            difficulty=latest_turn.difficulty,
            candidate_answer=request.answer,
            response_time=request.response_time,
        )
    except InterviewAgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Interview agent failed: {exc}",
        ) from exc

    interview_turn_crud.update_answer(
        db=db,
        turn_id=latest_turn.id,
        candidate_answer=request.answer,
        evaluation=turn.evaluation if turn.evaluation else None,
        score=turn.score if turn.score else None,
        follow_up=turn.follow_up if turn.follow_up else None,
        response_time=request.response_time,
    )

    if turn.is_final:
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        db.add(session)
        db.commit()

        return InterviewAnswerResponse(
            session_id=request.session_id,
            question_number=next_q_no,
            question="",
            follow_up=None,
            category="",
            difficulty="",
            tags=[],
            evaluation=turn.evaluation,
            score=turn.score,
            is_final=True,
            finished_reason=turn.finished_reason,
            transcript_summary=turn.transcript_summary,
        )

    turn_record = InterviewTurnCreate(
        user_id=user_id,
        session_id=request.session_id,
        resume_analysis_id=resume_analysis_id,
        question_number=next_q_no,
        question=turn.question,
        follow_up=None,
        difficulty=turn.difficulty,
        category=turn.category,
        tags=turn.tags,
        expected_answer=turn.expected_answer if turn.expected_answer else None,
        evaluation=None,
        score=None,
    )
    interview_turn_crud.create(db=db, obj_in=turn_record)

    return InterviewAnswerResponse(
        session_id=request.session_id,
        question_number=next_q_no,
        question=turn.question,
        follow_up=turn.follow_up if turn.follow_up else None,
        category=turn.category,
        difficulty=turn.difficulty,
        tags=turn.tags or [],
        evaluation=turn.evaluation,
        score=turn.score,
        is_final=False,
        finished_reason="",
        transcript_summary="",
    )


@router.post(
    "/end",
    response_model=InterviewSessionSummary,
    summary="End an interview session",
)
async def end_interview(
    request: InterviewEndRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
) -> InterviewSessionSummary:
    session = db.query(InterviewSession).filter(
        InterviewSession.id == request.session_id,
        InterviewSession.user_id == user_id,
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already completed.",
        )

    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()

    transcript = interview_turn_crud.get_transcript(db=db, session_id=request.session_id)
    avg_score = interview_turn_crud.average_score(db=db, session_id=request.session_id)
    total_q = interview_turn_crud.count_by_session(db=db, session_id=request.session_id)

    logger.info("Interview ended: session=%s, questions=%d, avg_score=%s", request.session_id, total_q, avg_score)

    return InterviewSessionSummary(
        session_id=request.session_id,
        status="completed",
        total_questions=total_q,
        average_score=avg_score,
        transcript_summary=transcript,
    )


@router.get(
    "/{session_id}",
    response_model=InterviewTurnConversation,
    summary="Get all turns for a session",
)
def get_session_turns(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
) -> InterviewTurnConversation:
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    turns = interview_turn_crud.get_session_turns(db=db, session_id=session_id)

    return InterviewTurnConversation(
        session_id=session_id,
        turns=[_turn_to_response(t) for t in turns],
    )


@router.get(
    "/history",
    response_model=list[InterviewTurnResponse],
    summary="List interview turn history for the current user",
)
def get_interview_history(
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
    skip: int = 0,
    limit: int = 100,
) -> list:
    turns = interview_turn_crud.get_by_user(db=db, user_id=user_id, skip=skip, limit=limit)
    return [_turn_to_response(t) for t in turns]


@router.get(
    "/transcript/{session_id}",
    summary="Get full conversation transcript",
)
def get_transcript(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(_get_current_user_id),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    transcript = interview_turn_crud.get_transcript(db=db, session_id=session_id)

    return {
        "session_id": session_id,
        "transcript": transcript,
    }
