import sqlite3

path = "D:\\AI_ project\\interview_agent.db"
conn = sqlite3.connect(path)
c = conn.cursor()

c.execute("PRAGMA table_info(users)")
cols = c.fetchall()
print("User columns:")
for col in cols:
    print(f"  {col}")

c.execute("SELECT * FROM users")
users = c.fetchall()
print(f"\nUsers: {len(users)}")
for u in users:
    print(f"  {u}")

conn.close()
