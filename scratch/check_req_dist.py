import csv
from collections import Counter

with open("dataset/deletion_requests.csv", encoding="utf-8") as f:
    reqs = list(csv.DictReader(f))

print(f"Total requests in deletion_requests.csv: {len(reqs)}")
audit_dates = Counter(r['audit_at'] for r in reqs)
print(f"Unique audit_at timestamps: {len(audit_dates)}")
for d, count in audit_dates.most_common(20):
    print(f"  {d}: {count} cases")
