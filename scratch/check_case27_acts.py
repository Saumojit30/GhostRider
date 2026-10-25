import csv

with open("dataset/system_activity.csv", encoding="utf-8") as f:
    acts = list(csv.DictReader(f))

res_set = {'account_3866', 'analytics_4574', 'support_4707', 'data_flow_2295', 'backup_5970', 'audit_record_3830'}
for a in acts:
    if a['resource_id'] in res_set or any(r in a['details'] for r in res_set):
        print(f"{a['activity_id']} {a['event_time']} {a['event_type']} {a['source_system']} -> {a['target_system']} {a['resource_id']} {a['reported_result']}")
