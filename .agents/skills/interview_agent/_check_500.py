import sqlite3

db_path = "D:\\AI_ project\\backend\\interview_agent.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

session_id = "67fa0943-b48a-44d8-9fb7-3eea0d7735a1"

# Check evaluations for this session
c.execute("SELECT * FROM interview_evaluations WHERE session_id=?", (session_id,))
evals = c.fetchall()
print(f"Evaluations for session: {len(evals)}")
for e in evals:
    cols = [d[0] for d in c.description]
    for i, col in enumerate(cols):
        print(f"  {col}: {e[i]}")

# Check turns
c.execute("SELECT question_number, question[:50], score FROM interview_turns WHERE session_id=?", (session_id,))
turns = c.fetchall()
print(f"\nTurns: {len(turns)}")
for t in turns:
    print(f"  Q{t[0]}: score={t[2]}")

conn.close()
