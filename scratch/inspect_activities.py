import csv
import sys

time_pattern = sys.argv[1] if len(sys.argv) > 1 else "2026-08-30"

with open('dataset/system_activity.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        t = r['event_time']
        if time_pattern in t:
            print(f"{r['activity_id']} {t} {r['event_type']:<22} {r['source_system']:<18} -> {r['target_system']:<20} {r['resource_id']:<18} {r['reported_result']:<10} {r['details']}")
