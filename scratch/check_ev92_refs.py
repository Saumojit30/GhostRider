import json

with open('dataset/evidence/records/service_resource_export_20260915_114455.json', encoding='utf-8') as f:
    data = json.load(f)

print("Checking customer references in evidence_92:")
cust_refs = set()
for sys_name, obj in data['service_exports'].items():
    for subkey, items in obj.items():
        for it in items:
            ref = it.get('customer_reference') or it.get('subject_reference')
            if ref:
                cust_refs.add(ref)

print(f"Unique references: {len(cust_refs)}")
print(sorted(list(cust_refs))[:20])

# Look for user_id of case_27 and case_28
# What are the user_ids of case_27 and case_28?
import csv
with open('dataset/user_identities.csv', encoding='utf-8') as f:
    users = {r['email']: r['user_id'] for r in csv.DictReader(f)}

print("case_27 email user_id:", users.get('lucas.d6290@outlook.com'))
print("case_28 email user_id:", users.get('smartinez6461@gmail.com'))

# Now let's print all records for case_28's user_id in evidence_92!
uid_28 = users.get('smartinez6461@gmail.com')
print(f"Records for {uid_28} in evidence_92:")
for sys_name, obj in data['service_exports'].items():
    for subkey, items in obj.items():
        for it in items:
            if it.get('customer_reference') == uid_28 or it.get('subject_reference') == uid_28:
                print(f"  {sys_name}: {it}")
