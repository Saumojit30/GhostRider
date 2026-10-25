import csv
import json

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    for row in list(csv.DictReader(f))[:20]:
        print(f"=== {row['case_id']} [{row['deletion_status']}] ===")
        for s in json.loads(row['steps_json']):
            print(f"  {s['phase']:<12} {s['operation']:<25} {s['system_id']:<20} {s['resource_id']:<20} {s['state']:<10} {s['evidence_id']}")
