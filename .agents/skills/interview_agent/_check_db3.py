import sqlite3

def check_db(path, label):
    print(f"\n=== {label}: {path} ===")
    conn = sqlite3.connect(path)
    c = conn.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in c.fetchall()]
    print(f"Tables ({len(tables)}): {tables}")
    
    for table in ["interview_sessions", "interview_turns", "interview_evaluations"]:
        if table in tables:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            count = c.fetchone()[0]
            c.execute(f"SELECT * FROM {table} LIMIT 1")
            cols = [d[0] for d in c.description]
            print(f"\n  {table}: {count} rows")
            print(f"  Columns: {cols}")
            if count > 0:
                row = c.fetchone()
                print(f"  Sample: {row}")
    
    conn.close()

check_db("D:\\AI_ project\\interview_agent.db", "Root DB")
check_db("D:\\AI_ project\\backend\\interview_agent.db", "Backend DB")
