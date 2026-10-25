import csv

with open("dataset/evidence_files.csv", encoding="utf-8") as f:
    ev_files = {r['file_id']: r for r in csv.DictReader(f)}

with open("dataset/deletion_requests.csv", encoding="utf-8") as f:
    reqs = list(csv.DictReader(f))

# Check for each distinct audit_at: what evidence files exist at or before that audit_at?
audit_times = sorted(list(set(r['audit_at'] for r in reqs)))
print(f"Total distinct audit_times: {len(audit_times)}")

for at in audit_times[:15]:
    # find evidence files within 2 hours before or at this time
    candidates = []
    for fid, ev in ev_files.items():
        if ev['captured_at'] <= at:
            candidates.append((fid, ev['captured_at'], ev['file_path']))
    # sort by captured_at descending
    candidates.sort(key=lambda x: x[1], reverse=True)
    print(f"audit_at: {at}")
    for c in candidates[:3]:
        print(f"  {c[0]} @ {c[1]}: {c[2]}")
