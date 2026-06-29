"""
Final test: use scores in 0-10 range to avoid fallback normalization bug,
verify transcript appears in evaluation.
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
session_id = str(uuid.uuid4())
now = datetime.now(timezone.utc).isoformat()

# Create session - active first, then we'll transition to completed
c.execute(
    """INSERT INTO interview_sessions 
    (id, user_id, role, company, interview_type, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)""",
    (session_id, user_id, "Software Engineer", "Google", "Technical", "active", now)
)

# Add turns with scores 0-10 (to avoid fallback *10 bug exceeding 100)
# The scores 0-10 will be normalized to 0-100 by the *10 factor in fallback
turns_data = [
    (str(uuid.uuid4()), session_id, user_id, None, 1,
     "What is your experience with Python?",
     "I have 3 years building web APIs and data pipelines with Python.",
     None, "Medium", "Technical",
     json.dumps(["Python"]),
     "Detailed Python experience expected.",
     "Good answer.", 8, 45, now),
    (str(uuid.uuid4()), session_id, user_id, None, 2,
     "How would you design a scalable REST API?",
     "FastAPI with async endpoints, connection pooling, and Redis caching.",
     None, "Hard", "System Design",
     json.dumps(["API", "Design"]),
     "Scalability patterns expected.",
     "Solid understanding.", 9, 60, now),
    (str(uuid.uuid4()), session_id, user_id, None, 3,
     "Describe a challenging bug you fixed.",
     "I debugged a memory leak in production using Python tracemalloc.",
     None, "Medium", "Behavioral",
     json.dumps(["Debugging"]),
     "STAR method.",
     "Good approach.", 7, 50, now),
    (str(uuid.uuid4()), session_id, user_id, None, 4,
     "Explain the difference between SQL and NoSQL databases.",
     "SQL has fixed schemas and ACID compliance; NoSQL is flexible and scalable.",
     None, "Medium", "Technical",
     json.dumps(["Database"]),
     "Technical comparison expected.",
     "Clear explanation.", 8, 30, now),
]

c.executemany(
    """INSERT INTO interview_turns 
    (id, session_id, user_id, resume_analysis_id, question_number,
     question, candidate_answer, follow_up, difficulty, category,
     tags, expected_answer, evaluation, score, response_time, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    turns_data
)

# Mark as completed
c.execute("UPDATE interview_sessions SET status='completed', completed_at=? WHERE id=?",
          (now, session_id))

conn.commit()
conn.close()

print(f"=== Created session: {session_id} ===")
print(f"4 turns with scores 0-10, marked completed")

# Evaluate via API
print("\n=== Calling /api/evaluate ===")
result = req("POST", "/api/evaluate", {"session_id": session_id})
if "_error" in result:
    print(f"ERROR {result['_error']}: {result['_detail']}")
else:
    print(f"SUCCESS!")
    summary = result.get('evaluation_summary', '')
    print(f"  Score: {result.get('overall_score')}")
    print(f"  Technical: {result.get('technical_score')}")
    print(f"  Communication: {result.get('communication_score')}")
    print(f"  Hire: {result.get('hire_decision')}")
    print(f"  Summary ({len(summary)} chars): {summary[:400]}")
    print(f"  Strengths: {result.get('strengths')}")
    print(f"  Weaknesses: {result.get('weaknesses')}")
    
    # KEY CHECK: Does the summary mention the transcript?
    transcript_keywords = ['Python', 'scalable', 'memory leak', 'FastAPI', 'Redis', 'SQL', 'NoSQL', 'database', 'tracemalloc']
    found_keywords = [k for k in transcript_keywords if k.lower() in summary.lower() or any(k.lower() in str(result.get(f, '')).lower() for f in ['strengths', 'weaknesses', 'recommendation', 'evaluation_summary'])]
    print(f"\n  Transcript keywords found in evaluation: {found_keywords}")
    print(f"  Transcript evidence: {'YES - evaluation references interview content' if len(found_keywords) > 2 else 'NO - evaluation does not reference interview content'}")
