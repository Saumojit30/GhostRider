import csv
import json

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_reqs = list(csv.DictReader(f))

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    expected = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

with open('dataset/evidence_files.csv', encoding='utf-8') as f:
    ev_files = {r['file_id']: r for r in csv.DictReader(f)}

for req in sample_reqs:
    cid = req['case_id']
    aat = req['audit_at']
    st, steps = expected[cid]
    cites = sorted(list(set(s['evidence_id'] for s in steps if s['evidence_id'])))
    cites_info = [f"{fid} ({ev_files[fid]['captured_at']})" for fid in cites if fid in ev_files]
    print(f"{cid:<8} audit_at={aat} cited={cites_info}")
