import csv

with open("dataset/system_activity.csv", encoding="utf-8") as f:
    acts = list(csv.DictReader(f))

# Let's search for any activity mentioning 5482, 6077, 2351, 2337, 838, or 9265
res_set = {'account_5482', 'analytics_6077', 'support_2351', 'data_flow_2337', 'backup_838', 'audit_record_9265'}
for a in acts:
    if a['resource_id'] in res_set or any(r in a['details'] for r in res_set):
        print(f"{a['activity_id']} {a['event_time']} {a['event_type']} {a['source_system']} -> {a['target_system']} {a['resource_id']} {a['reported_result']}")
