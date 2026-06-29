import sqlite3
conn = sqlite3.connect("interview_agent.db")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print("Tables:", [r[0] for r in c.fetchall()])

# Check interview_sessions
try:
    c.execute("SELECT * FROM interview_sessions")
    rows = c.fetchall()
    print("Sessions:", rows)
except Exception as e:
    print("No interview_sessions table:", e)

# Check interview_turns
try:
    c.execute("SELECT * FROM interview_turns")
    rows = c.fetchall()
    print("Turns:", rows)
except Exception as e:
    print("No interview_turns table:", e)

# Check interview_evaluations
try:
    c.execute("SELECT * FROM interview_evaluations")
    rows = c.fetchall()
    print("Evaluations:", rows)
except Exception as e:
    print("No interview_evaluations table:", e)

conn.close()
