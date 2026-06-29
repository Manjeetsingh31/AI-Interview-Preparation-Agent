import sqlite3

path = "D:\\AI_ project\\backend\\interview_agent.db"
conn = sqlite3.connect(path)
c = conn.cursor()

c.execute("SELECT id, user_id, role, company, interview_type, status FROM interview_sessions")
sessions = c.fetchall()
print(f"Sessions: {len(sessions)}")
for s in sessions:
    print(f"  {s}")

c.execute("SELECT * FROM users")
users = c.fetchall()
print(f"\nUsers: {len(users)}")
for u in users:
    print(f"  {u}")

c.execute("SELECT * FROM interview_turns")
turns = c.fetchall()
print(f"\nTurns: {len(turns)}")

c.execute("SELECT * FROM interview_evaluations")
evals = c.fetchall()
print(f"Evaluations: {len(evals)}")

conn.close()
