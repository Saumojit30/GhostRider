import csv
import json

with open("dataset/sample_output.csv", encoding="utf-8") as f:
    samples = list(csv.DictReader(f))

for row in samples:
    cid = row['case_id']
    st = row['deletion_status']
    steps = json.loads(row['steps_json'])
    verifs = [s['operation'] for s in steps if s['phase'] == 'VERIFICATION']
    print(f"{cid} [{st}]: {verifs}")
