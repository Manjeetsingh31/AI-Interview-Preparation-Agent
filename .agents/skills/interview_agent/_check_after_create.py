import sqlite3

path = "D:\\AI_ project\\interview_agent.db"
conn = sqlite3.connect(path)
c = conn.cursor()

c.execute("SELECT id, user_id, role, status FROM interview_sessions ORDER BY created_at DESC LIMIT 3")
sessions = c.fetchall()
print("Root DB - Latest sessions:")
for s in sessions:
    print(f"  {s}")

c.execute("SELECT * FROM users")
users = c.fetchall()
print(f"\nRoot DB - Users ({len(users)}):")
for u in users:
    print(f"  {u}")

conn.close()

# Check backend DB too
path2 = "D:\\AI_ project\\backend\\interview_agent.db"
conn2 = sqlite3.connect(path2)
c2 = conn2.cursor()

c2.execute("SELECT id, user_id, role, status FROM interview_sessions ORDER BY created_at DESC LIMIT 3")
sessions2 = c2.fetchall()
print("\nBackend DB - Latest sessions:")
for s in sessions2:
    print(f"  {s}")

conn2.close()
