import sqlite3

conn = sqlite3.connect(":memory:")
with open("dataset/evidence/databases/customer_accounts_failover_replica_20260902.sql", "r", encoding="utf-8") as f:
    conn.executescript(f.read())

cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables in evidence_54:", tables)

for t in tables:
    cur = conn.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = cur.fetchone()[0]
    print(f"Table {t}: {cnt} rows")
    cur = conn.execute(f"SELECT * FROM {t}")
    for row in cur.fetchall()[:5]:
        print(f"  {row}")
