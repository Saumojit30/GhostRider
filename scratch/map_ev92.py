import json
import csv

with open("dataset/evidence/records/service_resource_export_20260915_114455.json", encoding="utf-8") as f:
    ev92 = json.load(f)

with open("dataset/sample_output.csv", encoding="utf-8") as f:
    expected = {r["case_id"]: json.loads(r["steps_json"]) for r in csv.DictReader(f)}

# All resources in ev92
print("=== All resources in evidence_92 ===")
for sname, obj in ev92["service_exports"].items():
    for subk, items in obj.items():
        res_list = [it.get("resource_id") for it in items]
        print(f"  {sname}: {res_list}")

print("\n=== Expected resources for cases 21 to 30 ===")
for cid in [f"case_{i}" for i in range(21, 31)]:
    steps = expected[cid]
    res_list = [f"{s['system_id']}:{s['resource_id']}" for s in steps if s['phase'] == 'VERIFICATION']
    print(f"  {cid}: {res_list}")
