import sys
sys.path.insert(0, ".")
import csv
import json

from code.core.classifier import is_deletion_request
from code.core.identity import IdentityResolver
from code.core.evidence_indexer import EvidenceIndexer
from code.core.auditor import Auditor
from code.core.policy import PolicyEngine
from code.core.synthesizer import StepSynthesizer

print("Initializing benchmark...")
resolver = IdentityResolver()
indexer = EvidenceIndexer()
auditor = Auditor(indexer)
policy = PolicyEngine()
synthesizer = StepSynthesizer()

with open("dataset/sample_deletion_requests.csv", encoding="utf-8") as f:
    sample_reqs = list(csv.DictReader(f))

with open("dataset/sample_output.csv", encoding="utf-8") as f:
    expected = {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(f)}

status_matches = 0
step_count_matches = 0
exact_matches = 0
total = len(sample_reqs)

for req in sample_reqs:
    cid = req["case_id"]
    email = req["email"]
    audit_at = req["audit_at"]
    reported_at = req["reported_at"]
    req_text = req["request_text"]

    if not is_deletion_request(req_text):
        status = "NOT_APPLICABLE"
        steps_json = "[]"
    else:
        ident = resolver.resolve(email)
        if not ident:
            status = "NOT_APPLICABLE"
            steps_json = "[]"
        else:
            audited = auditor.audit_case(email, audit_at, reported_at, ident)
            status, raw_steps = policy.evaluate(audited)
            steps_json = synthesizer.synthesize(raw_steps)

    exp_status, exp_steps = expected[cid]
    actual_steps = json.loads(steps_json)
    
    st_match = (status == exp_status)
    sc_match = (len(actual_steps) == len(exp_steps))
    if st_match:
        status_matches += 1
    if sc_match:
        step_count_matches += 1

    # Check field match
    fields_match = True
    if sc_match and st_match:
        for s1, s2 in zip(actual_steps, exp_steps):
            for k in ["phase", "operation", "state", "system_id", "resource_id"]:
                if s1.get(k) != s2.get(k):
                    fields_match = False
                    break
    else:
        fields_match = False

    if fields_match:
        exact_matches += 1
        print(f"[{cid}] EXACT MATCH: {status} ({len(actual_steps)} steps)")
    else:
        print(f"[{cid}] DIFF: st={status} (exp {exp_status}) steps={len(actual_steps)} (exp {len(exp_steps)})")

print(f"\nResults on {total} sample cases:")
print(f"  Status Accuracy:     {status_matches} / {total} ({status_matches/total*100:.1f}%)")
print(f"  Step Count Accuracy: {step_count_matches} / {total} ({step_count_matches/total*100:.1f}%)")
print(f"  Exact Step Match:    {exact_matches} / {total} ({exact_matches/total*100:.1f}%)")
