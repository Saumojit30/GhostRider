import csv
import json

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    reqs = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    samples = list(csv.DictReader(f))

for row in samples:
    cid = row['case_id']
    st = row['deletion_status']
    steps = json.loads(row['steps_json'])
    req = reqs[cid]
    print(f"=== {cid} [{st}] ({len(steps)} steps) email={req['email']} audit_at={req['audit_at']} ===")
    for s in steps:
        print(f"  {s['phase']:<12} {s['operation']:<25} {s['system_id']:<20} {s['resource_id']:<20} {s['state']:<10} {s['evidence_id']}")
