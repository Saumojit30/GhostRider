import csv
import json

with open("output.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Header: {reader.fieldnames}")
assert reader.fieldnames == ["case_id", "deletion_status", "steps_json"], f"Invalid header: {reader.fieldnames}"

print(f"Total rows: {len(rows)}")
assert len(rows) == 518, f"Expected 518 rows, got {len(rows)}"

# Check sorting
case_ids = [r["case_id"] for r in rows]
with open("dataset/deletion_requests.csv", "r", encoding="utf-8") as f:
    expected_ids = [r["case_id"] for r in csv.DictReader(f)]

assert case_ids == expected_ids, "Case IDs do not match deletion_requests.csv order!"

# Check each row
not_app_count = 0
for idx, r in enumerate(rows):
    cid = r["case_id"]
    st = r["deletion_status"]
    assert st in ["COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"], f"Invalid status: {st} in {cid}"
    
    steps = json.loads(r["steps_json"])
    assert isinstance(steps, list), f"steps_json must be list in {cid}"
    
    if st == "NOT_APPLICABLE":
        not_app_count += 1
        assert steps == [], f"NOT_APPLICABLE must have empty steps_json in {cid}"
    elif st == "COMPLETE":
        for s in steps:
            assert s["phase"] == "VERIFICATION", f"COMPLETE case cannot have finding/remediation: {s} in {cid}"
            assert s["evidence_id"] != "", f"COMPLETE case verification must have evidence_id: {s} in {cid}"
    elif st == "INCOMPLETE":
        has_finding = any(s["phase"] == "FINDING" for s in steps)
        assert has_finding, f"INCOMPLETE case must have findings in {cid}"

print(f"All 518 rows validated successfully! NOT_APPLICABLE cases: {not_app_count}")
