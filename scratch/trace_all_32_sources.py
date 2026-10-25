import csv
import json

with open('dataset/sample_deletion_requests.csv', encoding='utf-8') as f:
    sample_reqs = list(csv.DictReader(f))

with open('dataset/sample_output.csv', encoding='utf-8') as f:
    expected = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

with open('dataset/user_identities.csv', encoding='utf-8') as f:
    user_identities = {r['email']: r for r in csv.DictReader(f)}

with open('dataset/user_audit_log.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['field_name'] == 'email' and r['old_value']:
            user_identities[r['old_value']] = {'user_id': r['user_id'], 'email': r['old_value']}

# For each case, look at:
# 1. Reported status and time
# 2. Expected resources and their cited evidence_id
for req in sample_reqs:
    cid = req['case_id']
    st, steps = expected[cid]
    email = req['email']
    user_id = user_identities.get(email, {}).get('user_id', 'unknown')
    
    print(f"==================================================")
    print(f"{cid} | user: {user_id} | status: {st} | reported: {req['reported_status']} @ {req['reported_at']}")
    print(f"audit_at: {req['audit_at']}")
    
    ev_cites = set()
    for s in steps:
        if s['evidence_id']:
            ev_cites.add(s['evidence_id'])
        print(f"  [{s['phase']}] {s['operation']:<24} {s['system_id']:<18} {s['resource_id']:<16} {s['state']:<10} {s['evidence_id']}")
    print(f"Evidence files cited: {list(ev_cites)}")
