"""
Full pipeline test: create a session via the new API, answer questions, 
end the session, and evaluate.
"""
import sys
import os
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

# First check what the current user is
print("=== Check existing sessions ===")
sessions = req("GET", "/api/interview/sessions")
print(f"Sessions: {len(sessions)}")
for s in sessions:
    print(f"  {s.get('id')}: {s.get('role')} - {s.get('status')}")

# Check evaluations
print("\n=== Check existing evaluations ===")
evals = req("GET", "/api/evaluations")
print(f"Evaluations: {len(evals)}")

# Check if there are resume analyses available
print("\n=== Check resume analyses ===")
# There should be none in the backend DB

# Let's check what happened with the test session created via direct DB
# The session ID was 0d66387d-7969-4aea-acd7-bd029a752593
# But that was created with a different DB session, it might not be visible via the API

# Check the session via the old API
print("\n=== Check session via old API ===")
s = req("GET", f"/api/sessions/571769d1-f4dd-4399-90f8-72d5484d93fc")
print(f"Session from old API: id={s.get('id')}, role={s.get('role')}, status={s.get('status')}, user_id={s.get('user_id')}")

# Call the evaluation endpoint for a session that exists
# We need a completed session. Let's end the one we created.
print("\n=== End the session ===")
try:
    end_result = req("POST", "/api/interview/end", {
        "session_id": "571769d1-f4dd-4399-90f8-72d5484d93fc",
    })
    print(f"End result: {end_result}")
except Exception as e:
    print(f"End error: {e}")

# Try to evaluate it (no turns exist, so this should show if fallback handles empty turns)
print("\n=== Evaluate session ===")
try:
    eval_result = req("POST", "/api/evaluate", {
        "session_id": "571769d1-f4dd-4399-90f8-72d5484d93fc",
    })
    print(f"Evaluate result:")
    print(f"  Score: {eval_result.get('overall_score')}")
    print(f"  Hire: {eval_result.get('hire_decision')}")
    print(f"  Summary: {eval_result.get('evaluation_summary')}")
    print(f"  Strengths: {eval_result.get('strengths')}")
    print(f"  Weaknesses: {eval_result.get('weaknesses')}")
except Exception as e:
    print(f"Evaluate error: {e}")
