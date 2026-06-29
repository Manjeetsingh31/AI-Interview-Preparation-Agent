import sqlite3

path = "D:\\AI_ project\\backend\\interview_agent.db"
conn = sqlite3.connect(path)
c = conn.cursor()

# Check all tables that might contain interview data
tables = ['transcripts', 'interview_histories', 'questions', 'interview_questions']
for table in tables:
    c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    if c.fetchone():
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"{table}: {count} rows")
        if count > 0:
            c.execute(f"SELECT * FROM {table} LIMIT 2")
            cols = [d[0] for d in c.description]
            for row in c.fetchall():
                print(f"  Cols: {cols}")
                print(f"  Row: {row}")
    else:
        print(f"{table}: table does not exist")

conn.close()
