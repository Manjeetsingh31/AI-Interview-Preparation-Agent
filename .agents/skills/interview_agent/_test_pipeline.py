"""
Test the evaluation pipeline directly against the backend DB.
This creates a session, adds turns, then runs the evaluation agent 
and prints the context to verify the transcript is present.
"""
import sys
import os
import uuid
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, "D:\\AI_ project")

from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal, engine, Base
from backend.app.models.models import InterviewSession
from backend.app.models.interview_turn import InterviewTurn
from backend.app.models.user import User
from backend.app.models.resume_analysis_adk import ResumeAnalysisADK
from backend.app.models.ats_score import AtsScore
from backend.app.services.agents.evaluation_agent import (
    _build_evaluation_context,
    run_evaluation_agent,
    _fallback_evaluation,
)

def main():
    db = SessionLocal()
    
    try:
        # Check what user exists
        user = db.query(User).filter(User.email == "candidate@example.com").first()
        if not user:
            user = User(
                email="candidate@example.com",
                password_hash="test_hash",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        print(f"User: id={user.id}, email={user.email}")
        
        # Create a new session
        session = InterviewSession(
            user_id=user.id,
            role="Software Engineer",
            company="Google",
            interview_type="Technical",
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
        print(f"\nCreated session: {session_id}")
        
        # Create InterviewTurn rows
        turns_data = [
            {
                "question_number": 1,
                "question": "Tell me about your experience with Python.",
                "candidate_answer": "I have 3 years of experience with Python, working on web development and data analysis projects.",
                "difficulty": "Medium",
                "category": "Technical",
                "tags": ["Python", "Experience"],
                "expected_answer": "A detailed description of Python experience.",
                "evaluation": "Good answer with relevant experience.",
                "score": 80,
            },
            {
                "question_number": 2,
                "question": "How would you design a scalable REST API?",
                "candidate_answer": "I would use FastAPI with async endpoints, database connection pooling, and caching with Redis.",
                "difficulty": "Hard",
                "category": "System Design",
                "tags": ["API", "System Design"],
                "expected_answer": "Discussion of scalability patterns.",
                "evaluation": "Solid understanding of API design principles.",
                "score": 85,
            },
            {
                "question_number": 3,
                "question": "Describe a challenging bug you fixed.",
                "candidate_answer": "I debugged a memory leak in a production service using Python's tracemalloc.",
                "difficulty": "Medium",
                "category": "Behavioral",
                "tags": ["Debugging", "Production"],
                "expected_answer": "STAR method response.",
                "evaluation": "Good debugging approach demonstrated.",
                "score": 75,
            },
        ]
        
        for td in turns_data:
            turn = InterviewTurn(
                session_id=session_id,
                user_id=user.id,
                question_number=td["question_number"],
                question=td["question"],
                candidate_answer=td["candidate_answer"],
                difficulty=td["difficulty"],
                category=td["category"],
                tags=td["tags"],
                expected_answer=td["expected_answer"],
                evaluation=td["evaluation"],
                score=td["score"],
            )
            db.add(turn)
        
        db.commit()
        print(f"Created {len(turns_data)} InterviewTurn rows")
        
        # Verify turns are in DB
        turns = db.query(InterviewTurn).filter(
            InterviewTurn.session_id == session_id
        ).order_by(InterviewTurn.question_number).all()
        print(f"Verified turns in DB: {len(turns)}")
        for t in turns:
            print(f"  Q{t.question_number}: {t.question[:50]}...")
        
        # Now test _build_evaluation_context
        print("\n" + "="*60)
        print("TESTING _build_evaluation_context()")
        print("="*60)
        context = _build_evaluation_context(
            session=session,
            turns=turns,
            questions=[],
            resume_analysis=None,
            ats_score=None,
        )
        print("\nCONTENT:")
        print(context)
        
        # Check if transcript is present
        has_transcript = "## Transcript" in context
        has_q1 = "Q1:" in context
        has_q2 = "Q2:" in context
        has_q3 = "Q3:" in context
        has_answers = "I have 3 years of experience" in context
        print(f"\nTRANSCRIPT ANALYSIS:")
        print(f"  '## Transcript' section present: {has_transcript}")
        print(f"  Q1 present: {has_q1}")
        print(f"  Q2 present: {has_q2}")
        print(f"  Q3 present: {has_q3}")
        print(f"  Candidate answers present: {has_answers}")
        
        # Test fallback evaluation
        print("\n" + "="*60)
        print("TESTING _fallback_evaluation()")
        print("="*60)
        fb = _fallback_evaluation(session, turns)
        print(f"  Overall score: {fb.overall_score}")
        print(f"  Hire decision: {fb.hire_decision}")
        print(f"  Summary: {fb.evaluation_summary[:100]}...")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
