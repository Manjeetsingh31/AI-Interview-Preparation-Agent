"""
Add turns to the existing session in the backend DB, end it, and evaluate.
"""
import sys
import json
import urllib.request
import urllib.error

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
        return {"_error": e.code, "_detail": json.loads(e.read())}

# Add turns directly via SQLAlchemy (not API, since the API requires interview flow)
# We'll add them to the backend DB and then verify via the API
import sqlite3

db_path = "D:\\AI_ project\\backend\\interview_agent.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

session_id = "571769d1-f4dd-4399-90f8-72d5484d93fc"
user_id = "2cd0b524-21a9-4f16-9373-e213269ce81c"

# First, delete any existing turns for this session
c.execute("DELETE FROM interview_turns WHERE session_id=?", (session_id,))

# Add 3 InterviewTurn rows directly
turns_data = [
    (None, session_id, user_id, None, 1,
     "Tell me about your experience with Python.",
     "I have 3 years of experience with Python, building web APIs and data processing pipelines.",
     None, "Medium", "Technical",
     '["Python", "Experience"]',
     "A detailed description of Python experience.",
     "Good answer demonstrating relevant experience.", 80, 45,
     "2026-06-29 14:00:00.000000"),
    (None, session_id, user_id, None, 2,
     "How would you design a scalable REST API?",
     "I would use FastAPI with async endpoints, connection pooling, and Redis caching.",
     None, "Hard", "System Design",
     '["API", "System Design"]',
     "Discussion of scalability patterns and best practices.",
     "Solid understanding of API design with good technical depth.", 85, 60,
     "2026-06-29 14:01:00.000000"),
    (None, session_id, user_id, None, 3,
     "Describe a challenging bug you fixed.",
     "I debugged a memory leak in a production microservice using Python's tracemalloc and fixed it.",
     None, "Medium", "Behavioral",
     '["Debugging", "Production"]',
     "STAR method response expected.",
     "Good debugging approach with clear methodology.", 75, 50,
     "2026-06-29 14:02:00.000000"),
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
          ("2026-06-29 14:03:00.000000", session_id))

conn.commit()
conn.close()

print(f"Added 3 turns to session {session_id}")
print("Session marked as completed")

# Now evaluate via API
print("\n=== Calling /api/evaluate ===")
result = req("POST", "/api/evaluate", {"session_id": session_id})
if "_error" in result:
    print(f"ERROR {result['_error']}: {result['_detail']}")
else:
    print(f"Success! Score={result.get('overall_score')}")
    print(f"Hire={result.get('hire_decision')}")
    print(f"Summary={result.get('evaluation_summary')[:200] if result.get('evaluation_summary') else 'N/A'}")
    print(f"Strengths={result.get('strengths')}")
    print(f"Weaknesses={result.get('weaknesses')}")
    print(f"Missed topics={result.get('missed_topics')}")
    print(f"Strong topics={result.get('strong_topics')}")
