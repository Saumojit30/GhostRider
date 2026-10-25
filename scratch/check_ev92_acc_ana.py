import json

with open('dataset/evidence/records/service_resource_export_20260915_114455.json', encoding='utf-8') as f:
    data = json.load(f)

print("account_service profile_lookups in evidence_92:")
for it in data['service_exports']['account_service']['profile_lookups']:
    print(it)

print("\nanalytics_platform profiles in evidence_92:")
for it in data['service_exports']['analytics_platform']['profiles']:
    print(it)
