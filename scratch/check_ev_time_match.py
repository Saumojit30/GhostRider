import csv

with open('dataset/evidence_files.csv', encoding='utf-8') as f:
    ev_files = {r['file_id']: r for r in csv.DictReader(f)}

# Map captured_at -> file_id
time_to_ev = {}
for fid, r in ev_files.items():
    t = r['captured_at']
    time_to_ev[t] = fid

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_reqs = list(csv.DictReader(f))

exact_ev_matches = 0
for req in sample_reqs:
    cid = req['case_id']
    aat = req['audit_at']
    matched_ev = time_to_ev.get(aat)
    print(f"{cid}: audit_at={aat} -> matched_ev={matched_ev}")
    if matched_ev:
        exact_ev_matches += 1

print(f"\nExact audit_at to captured_at matches in sample: {exact_ev_matches}/{len(sample_reqs)}")
