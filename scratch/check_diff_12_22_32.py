import sys
sys.path.insert(0, ".")
import json

from code.core.identity import IdentityResolver
from scratch.enhanced_indexer import EnhancedIndexer
from code.core.policy import PolicyEngine
from code.core.synthesizer import StepSynthesizer
from code.core.auditor import Auditor

resolver = IdentityResolver()
indexer = EnhancedIndexer()
auditor = Auditor(indexer)
policy = PolicyEngine()
synthesizer = StepSynthesizer()

with open("dataset/sample_output.csv", encoding="utf-8") as f:
    import csv
    expected = {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"])) for r in csv.DictReader(f)}

with open("dataset/sample_deletion_requests.csv", encoding="utf-8") as f:
    sample_reqs = {r["case_id"]: r for r in csv.DictReader(f)}

for cid in ["case_12", "case_22", "case_32"]:
    req = sample_reqs[cid]
    ident = resolver.resolve(req["email"])
    audited = auditor.audit_case(req["email"], req["audit_at"], req["reported_at"], ident)
    st, raw = policy.evaluate(audited)
    steps_json = synthesizer.synthesize(raw)
    act_steps = json.loads(steps_json)
    exp_st, exp_steps = expected[cid]
    print(f"=== {cid} ===")
    print("Actual:")
    for s in act_steps:
        print(f"  {s['phase']} {s['operation']} {s['system_id']} {s['resource_id']} {s['evidence_id']}")
    print("Expected:")
    for s in exp_steps:
        print(f"  {s['phase']} {s['operation']} {s['system_id']} {s['resource_id']} {s['evidence_id']}")
