# Let's inspect how each evidence file links to user identifiers:
import csv
import json

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_reqs = {r['case_id']: r for r in csv.DictReader(f)}

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    sample_out = {r['case_id']: json.loads(r['steps_json']) for r in csv.DictReader(f)}

with open('dataset/user_identities.csv', encoding='utf-8') as f:
    users = {r['email']: r for r in csv.DictReader(f)}

with open('dataset/user_audit_log.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['field_name'] == 'email' and r['old_value']:
            users[r['old_value']] = {'user_id': r['user_id'], 'email': r['old_value']}

# Let's test cases 12, 15, 17, 19 in evidence_01:
print("--- Investigating evidence_01 (service_events_ap_south_20260915.log) ---")
for cid in ['case_12', 'case_15', 'case_17', 'case_19']:
    req = sample_reqs[cid]
    u = users[req['email']]
    exp_res = [s['resource_id'] for s in sample_out[cid]]
    print(f"{cid}: email={req['email']} user_id={u['user_id']} expected_resources={exp_res}")

print("\n--- Investigating evidence_05 (customer_data_read_replica_20260921.sql) ---")
for cid in ['case_16', 'case_22']:
    req = sample_reqs[cid]
    u = users[req['email']]
    exp_res = [s['resource_id'] for s in sample_out[cid]]
    print(f"{cid}: email={req['email']} user_id={u['user_id']} expected_resources={exp_res}")
