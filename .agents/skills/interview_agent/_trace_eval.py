"""
Trace the exact execution of run_evaluation_agent() to determine
why the fallback path is taken instead of the ADK agent.
"""
import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone

sys.path.insert(0, "D:\\AI_ project")

# Enable logging to see whatever the agent logs
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.models import InterviewSession
from backend.app.models.interview_turn import InterviewTurn
from backend.app.models.user import User
from backend.app.services.agents import evaluation_agent as eva

# Monkey-patch _get_evaluation_agent to trace what it returns
_original_get_agent = eva._get_evaluation_agent
def _traced_get_agent():
    result = _original_get_agent()
    agent, svc = result
    print(f"\n=== TRACE: _get_evaluation_agent() returned agent={agent is not None}, service={svc is not None} ===")
    if agent is None:
        print("=== TRACE: Agent is None - fallback WILL be used ===")
    else:
        print(f"=== TRACE: Agent type={type(agent).__name__}, name={agent.name} ===")
    return result
eva._get_evaluation_agent = _traced_get_agent

# Monkey-patch _run_adk_agent to trace if it's called
_original_run_adk = eva._run_adk_agent
async def _traced_run_adk(agent, context):
    print(f"\n=== TRACE: _run_adk_agent() CALLED ===")
    print(f"=== TRACE: Context length={len(context)} chars, first 200 chars: {context[:200]} ===")
    try:
        result = await _original_run_adk(agent, context)
        print(f"=== TRACE: _run_adk_agent() SUCCEEDED ===")
        print(f"=== TRACE: Result type={type(result).__name__}, score={result.overall_score} ===")
        return result
    except Exception as e:
        print(f"=== TRACE: _run_adk_agent() FAILED with exception: {type(e).__name__}: {e} ===")
        raise
eva._run_adk_agent = _traced_run_adk

# Monkey-patch _fallback_evaluation to trace if it's called
_original_fallback = eva._fallback_evaluation
def _traced_fallback(session, turns):
    print(f"\n=== TRACE: _fallback_evaluation() CALLED ===")
    print(f"=== TRACE: Number of turns: {len(turns)} ===")
    result = _original_fallback(session, turns)
    print(f"=== TRACE: Fallback result: score={result.overall_score}, decision={result.hire_decision} ===")
    return result
eva._fallback_evaluation = _traced_fallback

# Now monkey-patch run_evaluation_agent itself to trace the decision path
_original_run = eva.run_evaluation_agent
async def _traced_run(db, session_id, user_id):
    # Pre-trace: check what _get_evaluation_agent returns
    agent, svc = eva._get_evaluation_agent()
    print(f"\n=== TRACE: Pre-call check - agent is None? {agent is None} ===")
    
    if agent is None:
        print("=== TRACE: Path will be: FALLBACK (agent is None) ===")
    else:
        print("=== TRACE: Path will be: ADK AGENT ===")
    
    result = await _original_run(db, session_id, user_id)
    print(f"\n=== TRACE: run_evaluation_agent() RESULT: score={result.overall_score}, decision={result.hire_decision}, summary={result.evaluation_summary[:100]} ===")
    return result
eva.run_evaluation_agent = _traced_run

async def main():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "candidate@example.com").first()
        if not user:
            user = User(email="candidate@example.com", password_hash="test")
            db.add(user)
            db.commit()
            db.refresh(user)
        print(f"User: {user.id}")
        
        # Create session
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
        sid = session.id
        print(f"Session: {sid}")
        
        # Add 3 turns with realistic Q&A
        turns_data = [
            ("What is Python list comprehension?", 
             "List comprehension is a concise way to create lists. For example: [x**2 for x in range(10)].",
             "Medium", "Technical", 8),
            ("Explain the difference between REST and GraphQL.",
             "REST has fixed endpoints while GraphQL allows the client to specify what data it needs.",
             "Hard", "System Design", 7),
            ("Tell me about a time you had a conflict with a teammate.",
             "I had a disagreement about architecture but we resolved it by discussing tradeoffs and reaching consensus.",
             "Medium", "Behavioral", 8),
        ]
        for i, (q, a, diff, cat, score) in enumerate(turns_data, 1):
            turn = InterviewTurn(
                session_id=sid, user_id=user.id,
                question_number=i, question=q, candidate_answer=a,
                difficulty=diff, category=cat,
                tags=[], expected_answer="", evaluation="", score=score,
            )
            db.add(turn)
        db.commit()
        print(f"Added {len(turns_data)} turns")
        
        print("\n" + "=" * 60)
        print("CALLING run_evaluation_agent()")
        print("=" * 60)
        
        from backend.app.services.agents.evaluation_agent import run_evaluation_agent
        result = await run_evaluation_agent(db=db, session_id=sid, user_id=user.id)
        
        print("\n" + "=" * 60)
        print("FINAL RESULT")
        print("=" * 60)
        print(f"Score: {result.overall_score}")
        print(f"Technical: {result.technical_score}")
        print(f"Communication: {result.communication_score}")
        print(f"Hire: {result.hire_decision}")
        print(f"Summary: {result.evaluation_summary}")
        print(f"Strengths: {result.strengths}")
        print(f"Weaknesses: {result.weaknesses}")
        
    finally:
        db.close()

asyncio.run(main())
