"""
Fresh test: create a new session with turns, evaluate via API.
"""
import sys
import json
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE = "http://localhost:8765"

def req(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            detail = json.loads(body)
        except:
            detail = body.decode()
        return {"_error": e.code, "_detail": detail}

import sqlite3

db_path = "D:\\AI_ project\\backend\\interview_agent.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

user_id = "2cd0b524-21a9-4f16-9373-e213269ce81c"
new_session_id = str(uuid.uuid4())
now = datetime.now(timezone.utc).isoformat()

# Create a new session
c.execute(
    """INSERT INTO interview_sessions 
    (id, user_id, role, company, interview_type, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)""",
    (new_session_id, user_id, "Software Engineer", "Google", "Technical", "active", now)
)

# Add 3 InterviewTurn rows
turns_data = [
    (str(uuid.uuid4()), new_session_id, user_id, None, 1,
     "What is your experience with Python?",
     "I have 3 years of experience with Python building web APIs and data pipelines.",
     None, "Medium", "Technical",
     json.dumps(["Python", "Experience"]),
     "A detailed description of Python experience.",
     "Good answer.", 80, 45, now),
    (str(uuid.uuid4()), new_session_id, user_id, None, 2,
     "How would you design a scalable REST API?",
     "I would use FastAPI with async endpoints and Redis caching.",
     None, "Hard", "System Design",
     json.dumps(["API", "System Design"]),
     "Scalability discussion.",
     "Solid understanding.", 85, 60, now),
    (str(uuid.uuid4()), new_session_id, user_id, None, 3,
     "Describe a challenging bug you fixed.",
     "I debugged a memory leak in production using tracemalloc.",
     None, "Medium", "Behavioral",
     json.dumps(["Debugging", "Production"]),
     "STAR response.",
     "Good approach.", 75, 50, now),
]

c.executemany(
    """INSERT INTO interview_turns 
    (id, session_id, user_id, resume_analysis_id, question_number,
     question, candidate_answer, follow_up, difficulty, category,
     tags, expected_answer, evaluation, score, response_time, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    turns_data
)

# Mark session as completed
c.execute("UPDATE interview_sessions SET status='completed', completed_at=? WHERE id=?",
          (now, new_session_id))

conn.commit()
conn.close()

print(f"=== Created new session: {new_session_id} ===")
print(f"Added 3 turns, marked as completed")

# Verify through API - check new session
print("\n=== Check session via API ===")
s = req("GET", f"/api/interview/{new_session_id}")
print(f"Session: id={s.get('session_id')}, turns={len(s.get('turns', []))}" if "session_id" in s else f"Got: {s}")

# Now evaluate via API
print("\n=== Calling /api/evaluate ===")
result = req("POST", "/api/evaluate", {"session_id": new_session_id})
if "_error" in result:
    print(f"ERROR {result['_error']}: {result['_detail']}")
else:
    print(f"SUCCESS!")
    print(f"  Score: {result.get('overall_score')}")
    print(f"  Technical: {result.get('technical_score')}")
    print(f"  Communication: {result.get('communication_score')}")
    print(f"  Problem Solving: {result.get('problem_solving_score')}")
    print(f"  Confidence: {result.get('confidence_score')}")
    print(f"  Behavioral: {result.get('behavioral_score')}")
    print(f"  Coding: {result.get('coding_score')}")
    print(f"  Hire: {result.get('hire_decision')}")
    print(f"  Difficulty: {result.get('difficulty_level')}")
    print(f"  Summary: {result.get('evaluation_summary')}")
    print(f"  Strengths: {result.get('strengths')}")
    print(f"  Weaknesses: {result.get('weaknesses')}")
    print(f"  Missed topics: {result.get('missed_topics')}")
    print(f"  Strong topics: {result.get('strong_topics')}")
    print(f"  Improvement: {result.get('improvement_suggestions')}")
