import csv
import json

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    reqs = list(csv.DictReader(f))

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    expected = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

with open('dataset/user_identities.csv', encoding='utf-8') as f:
    identities = {r['email']: r for r in csv.DictReader(f)}

with open('dataset/user_audit_log.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['field_name'] == 'email' and r['old_value']:
            if r['old_value'] not in identities and r['user_id']:
                identities[r['old_value']] = {'user_id': r['user_id'], 'email': r['old_value']}

# Map activities by resource_id
with open('dataset/system_activity.csv', encoding='utf-8') as f:
    activities = list(csv.DictReader(f))

res_to_act = {}
for act in activities:
    res = act['resource_id']
    if res not in res_to_act:
        res_to_act[res] = []
    res_to_act[res].append(act)

print(f"{'Case':<8} {'Status':<12} {'User':<10} {'Expected Resources':<60}")
print("-" * 85)

for req in reqs:
    cid = req['case_id']
    email = req['email']
    st, steps = expected[cid]
    uid = identities.get(email, {}).get('user_id', 'UNKNOWN')
    
    # Unique resources in expected steps
    res_list = []
    for s in steps:
        r = f"{s['system_id']}:{s['resource_id']}"
        if r not in res_list:
            res_list.append(r)
    
    print(f"{cid:<8} {st:<12} {uid:<10} {', '.join(res_list)}")
