import sqlite3

path = "D:\\AI_ project\\interview_agent.db"
conn = sqlite3.connect(path)
c = conn.cursor()

c.execute("SELECT * FROM users")
users = c.fetchall()
print(f"Users: {len(users)}")
for u in users:
    print(f"  ID={u[0]}, Email={u[1]}")

c.execute("SELECT id, user_id FROM interview_sessions")
sessions = c.fetchall()
print(f"\nSessions: {len(sessions)}")
for s in sessions:
    print(f"  ID={s[0]}, user_id={s[1]}")

c.execute("SELECT id, user_id FROM interview_evaluations")
evals = c.fetchall()
print(f"\nEvaluations: {len(evals)}")
for e in evals:
    print(f"  ID={e[0]}, user_id={e[1]}")

conn.close()
