import sqlite3

def check_db(path):
    print(f"\n=== DB: {path} ===")
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in c.fetchall()]
    print(f"Tables ({len(tables)}): {tables}")
    
    if "interview_sessions" in tables:
        c.execute("SELECT * FROM interview_sessions")
        rows = c.fetchall()
        print(f"Sessions: {len(rows)}")
        for r in rows:
            print(f"  {r}")
    
    if "interview_turns" in tables:
        c.execute("SELECT * FROM interview_turns")
        rows = c.fetchall()
        print(f"Turns: {len(rows)}")
        for r in rows:
            print(f"  {r}")
    
    if "interview_evaluations" in tables:
        c.execute("SELECT * FROM interview_evaluations")
        rows = c.fetchall()
        print(f"Evaluations: {len(rows)}")
        for r in rows:
            print(f"  ID={r[0]}, Session={r[1]}, Score={r[7]}")
            print(f"  Summary preview: {str(r[-2])[:200]}")
            print()

    conn.close()

check_db("D:\\AI_ project\\interview_agent.db")
check_db("D:\\AI_ project\\backend\\interview_agent.db")
