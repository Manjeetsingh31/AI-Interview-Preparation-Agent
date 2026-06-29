import sqlite3

path = "D:\\AI_ project\\interview_agent.db"
conn = sqlite3.connect(path)
c = conn.cursor()

# Check interview_sessions
c.execute("SELECT id, status, created_at FROM interview_sessions")
print("=== Sessions ===")
for r in c.fetchall():
    print(f"  {r}")

# Check interview_turns - which sessions have them
c.execute("SELECT session_id, COUNT(*) FROM interview_turns GROUP BY session_id")
print("\n=== Turns by session ===")
for r in c.fetchall():
    print(f"  Session {r[0]}: {r[1]} turns")

# Check transcripts
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcripts'")
if c.fetchone():
    c.execute("SELECT COUNT(*) FROM transcripts")
    count = c.fetchone()[0]
    print(f"\n=== Transcripts: {count} rows ===")
    if count > 0:
        c.execute("SELECT session_id, COUNT(*) FROM transcripts GROUP BY session_id")
        for r in c.fetchall():
            print(f"  Session {r[0]}: {r[1]} transcript messages")

# Check evaluations
c.execute("SELECT id, session_id, overall_score, hire_decision FROM interview_evaluations")
print("\n=== Evaluations ===")
for r in c.fetchall():
    print(f"  Eval {r[0]}: Session={r[1]}, Score={r[2]}, Decision={r[3]}")

# For each evaluation session, check if there are turns
evals = c.execute("SELECT session_id FROM interview_evaluations").fetchall()
for e in evals:
    sid = e[0]
    c.execute("SELECT COUNT(*) FROM interview_turns WHERE session_id=?", (sid,))
    turn_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM transcripts WHERE session_id=?", (sid,))
    trans_count = c.fetchone()[0]
    print(f"\n  Session {sid}: {turn_count} turns, {trans_count} transcript messages")

conn.close()
