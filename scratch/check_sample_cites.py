import csv
import json

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_reqs = list(csv.DictReader(f))

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    expected = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

with open('dataset/evidence_files.csv', encoding='utf-8') as f:
    ev_files = {r['file_id']: r for r in csv.DictReader(f)}

print(f"{'Case':<8} {'audit_at':<22} {'Cited File':<12} {'captured_at':<22} {'File Path'}")
print("-" * 100)

for req in sample_reqs:
    cid = req['case_id']
    aat = req['audit_at']
    st, steps = expected[cid]
    cites = set(s['evidence_id'] for s in steps if s['evidence_id'])
    for fid in cites:
        ev = ev_files.get(fid, {})
        print(f"{cid:<8} {aat:<22} {fid:<12} {ev.get('captured_at', ''):<22} {ev.get('file_path', '')}")
