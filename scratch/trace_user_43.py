import csv
import json
import glob

uid = "user_43"

print(f"=== Searching for {uid} in system_activity.csv ===")
with open('dataset/system_activity.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if uid in json.dumps(r) or '7566' in json.dumps(r) or '2016' in json.dumps(r) or '9406' in json.dumps(r):
            print(f"  {r['activity_id']} {r['event_time']} {r['event_type']} {r['source_system']} -> {r['target_system']} {r['resource_id']} {r['reported_result']}")

print(f"\n=== Searching for {uid} or resources in evidence files ===")
for path in glob.glob('dataset/evidence/**/*.*', recursive=True):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            found = []
            for term in [uid, '7566', '2016', '9406']:
                if term in content:
                    found.append(term)
            if found:
                print(f"  {path}: found {found}")
    except Exception as e:
        pass
