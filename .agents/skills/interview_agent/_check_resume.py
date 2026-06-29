import sqlite3

path = "D:\\AI_ project\\backend\\interview_agent.db"
conn = sqlite3.connect(path)
c = conn.cursor()

for table in ['resume_analyses', 'resume_analyses_adk', 'resumes', 'ats_scores']:
    c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    if c.fetchone():
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"{table}: {count} rows")
        if count > 0:
            c.execute(f"SELECT * FROM {table} LIMIT 1")
            cols = [d[0] for d in c.description]
            print(f"  Columns: {cols}")

conn.close()
