import csv, json
with open('dataset/sample_output.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['case_id'] in ['case_26', 'case_27', 'case_28', 'case_29', 'case_30']:
            print(f"=== {r['case_id']} [{r['deletion_status']}] ===")
            for s in json.loads(r['steps_json']):
                print(f"  {s['phase']} {s['operation']} {s['system_id']} {s['resource_id']}")
