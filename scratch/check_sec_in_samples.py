import csv
import json

with open("dataset/sample_output.csv", encoding="utf-8") as f:
    expected = {r["case_id"]: json.loads(r["steps_json"]) for r in csv.DictReader(f)}

for cid, steps in expected.items():
    sec_steps = [s for s in steps if s['system_id'] == 'security_service']
    print(f"{cid}: has_security={len(sec_steps) > 0}")
