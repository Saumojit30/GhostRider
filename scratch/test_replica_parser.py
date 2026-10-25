import csv
import json
import sqlite3
import re
from pathlib import Path

# Test SQLite replica parser
conn = sqlite3.connect(":memory:")
with open("dataset/evidence/databases/customer_data_read_replica_20260921.sql", "r", encoding="utf-8") as f:
    conn.executescript(f.read())

cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables in replica:", tables)

cur = conn.execute("SELECT resource_id, origin_system, collection_name, record_json FROM customer_data_read_replica")
rows = cur.fetchall()
print(f"Total rows in replica: {len(rows)}")
for r in rows[:5]:
    rj = json.loads(r[3])
    print(r[0], r[1], r[2], list(rj.keys()))
