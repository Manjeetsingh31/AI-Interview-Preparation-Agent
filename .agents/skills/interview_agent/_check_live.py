import sqlite3

path = "D:\\AI_ project\\interview_agent.db"
conn = sqlite3.connect(path)
c = conn.cursor()

c.execute("SELECT * FROM users")
users = c.fetchall()
print(f"Users: {len(users)}")
for u in users:
    print(f"  ID={u[0]}, Email={u[1]}")
