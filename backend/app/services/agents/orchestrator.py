from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.models.models import InterviewSession, Transcript, Evaluation, Resume
from backend.app.services.agents.interviewer import InterviewerAgent
from backend.app.services.agents.evaluator import EvaluationAgent
from backend.app.schemas.schemas import ChatTurnResponse, EvaluationOut

MAX_INTERVIEW_TURNS = 5  # Limit the conversation to 5 question-answer exchanges for testing/capstone

class InterviewOrchestrator:
    def __init__(self):
        self.interviewer = InterviewerAgent()
        self.evaluator = EvaluationAgent()

    def process_turn(self, db: Session, session_id: str, candidate_message: str = None) -> ChatTurnResponse:
        """
        Processes a single conversational turn.
        - Records the candidate response if provided.
        - Determines if the interview should wrap up and triggers the evaluation.
        - Generates the next interviewer question.
        """
        # 1. Fetch Session and Resume
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        
        resume_data = None
        if session.resume:
            resume_data = session.resume.parsed_data

        # 2. Record Candidate response in Database
        if candidate_message:
            candidate_transcript = Transcript(
                session_id=session_id,
                sender="candidate",
                message=candidate_message,
                timestamp=datetime.utcnow()
            )
            db.add(candidate_transcript)
            db.commit()

        # 3. Pull entire transcript history for context
        transcripts = db.query(Transcript).filter(Transcript.session_id == session_id).order_by(Transcript.timestamp.asc()).all()
        history = [{"sender": t.sender, "message": t.message} for t in transcripts]

        # 4. Count the number of candidate answers to enforce the length limit
        candidate_turns = sum(1 for t in history if t["sender"] == "candidate")

        # 5. Check if we should wrap up
        should_wrap_up = candidate_turns >= MAX_INTERVIEW_TURNS
        
        if should_wrap_up:
            # Complete the session
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            db.commit()

            # Generate final evaluation
            eval_data = self.evaluator.evaluate_session(
                role=session.role,
                company=session.company,
                interview_type=session.interview_type,
                resume_data=resume_data,
                transcript_history=history
            )

            # Save evaluation
            evaluation = Evaluation(
                session_id=session_id,
                overall_score=eval_data.overall_score,
                feedback_summary=eval_data.feedback_summary,
                criteria_scores=eval_data.criteria_scores,
                recommendations=eval_data.recommendations,
                created_at=datetime.utcnow()
            )
            db.add(evaluation)
            
            # Record interviewer final goodbye
            wrap_up_message = "Thank you so much for participating in this mock interview. I've compiled your feedback and evaluation report which is now available on your dashboard."
            interviewer_transcript = Transcript(
                session_id=session_id,
                sender="interviewer",
                message=wrap_up_message,
                timestamp=datetime.utcnow()
            )
            db.add(interviewer_transcript)
            db.commit()

            # Format result
            eval_out = EvaluationOut(
                id=evaluation.id,
                session_id=evaluation.session_id,
                overall_score=evaluation.overall_score,
                feedback_summary=evaluation.feedback_summary,
                criteria_scores=evaluation.criteria_scores,
                recommendations=evaluation.recommendations,
                created_at=evaluation.created_at
            )

            return ChatTurnResponse(
                status="completed",
                message=wrap_up_message,
                evaluation=eval_out
            )

        # 6. Generate next interviewer response
        next_turn = self.interviewer.get_next_turn(
            role=session.role,
            company=session.company,
            interview_type=session.interview_type,
            resume_data=resume_data,
            transcript_history=history
        )

        # Save interviewer's response
        interviewer_transcript = Transcript(
            session_id=session_id,
            sender="interviewer",
            message=next_turn.message,
            timestamp=datetime.utcnow()
        )
        db.add(interviewer_transcript)
        db.commit()

        return ChatTurnResponse(
            status="active",
            message=next_turn.message,
            evaluation=None
        )
