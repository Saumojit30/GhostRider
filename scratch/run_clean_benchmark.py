import sys
sys.path.insert(0, ".")
import csv
import json

from code.core.classifier import is_deletion_request
from code.core.identity import IdentityResolver
from scratch.enhanced_indexer import EnhancedIndexer
from scratch.clean_auditor import CleanAuditor
from code.core.policy import RawStep
from code.core.synthesizer import StepSynthesizer

resolver = IdentityResolver()
indexer = EnhancedIndexer()
auditor = CleanAuditor(indexer)
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
            resources = auditor.audit_case(email, audit_at, reported_at, ident)
            
            # Policy evaluation
            violations = []
            for r in resources:
                sys_id = r["system_id"]
                st = r["state"]
                is_v = False
                v_type = None
                
                if sys_id == "account_service":
                    if st == "PRESENT":
                        is_v = True
                        v_type = "REMAINING_RECORD"
                elif sys_id == "search_service":
                    if st == "PRESENT":
                        is_v = True
                        v_type = "REMAINING_RECORD"
                elif sys_id == "export_service":
                    if st == "PRESENT":
                        is_v = True
                        v_type = "REMAINING_RECORD"
                elif sys_id == "support_platform":
                    if r.get("record_type") == "SUPPORT_ATTACHMENT" and st == "PRESENT":
                        is_v = True
                        v_type = "REMAINING_RECORD"
                    elif st == "PRESENT":
                        is_v = True
                        v_type = "EXPOSED_PII"
                elif sys_id == "analytics_platform":
                    # Check marketing profile vs analytics
                    if r.get("details", {}).get("email_opt_in") or r.get("record_type") == "MARKETING_PROFILE":
                        if st == "PRESENT":
                            is_v = True
                            v_type = "REMAINING_RECORD"
                    else:
                        if st == "PRESENT":
                            is_v = True
                            v_type = "EXPOSED_PII"
                elif sys_id == "identity_service":
                    if st == "PRESENT":
                        is_v = True
                        v_type = "EXPOSED_PII"
                elif sys_id == "integration_service":
                    if st == "ACTIVE":
                        is_v = True
                        v_type = "ACTIVE_DATA_FLOW"
                elif sys_id == "backup_service":
                    if st == "ACTIVE":
                        is_v = True
                        v_type = "RESTORE_RISK"

                if is_v:
                    violations.append({**r, "violation_type": v_type})

            is_complete = len(violations) == 0
            status = "COMPLETE" if is_complete else "INCOMPLETE"

            raw_steps = []
            if is_complete:
                for r in resources:
                    sys_id = r["system_id"]
                    rid = r["resource_id"]
                    st = r["state"]
                    fid = r["evidence_id"]
                    if sys_id == "account_service" and st == "ABSENT":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_ABSENT", "ABSENT", fid))
                    elif sys_id == "security_service" and st == "PRESENT":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_PRESENT", "PRESENT", fid))
                    elif sys_id == "analytics_platform" and st == "ANONYMIZED":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", fid))
                    elif sys_id == "support_platform" and st == "REDACTED":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_REDACTED", "REDACTED", fid))
                    elif sys_id == "integration_service" and st == "DISABLED":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", fid))
                    elif sys_id == "backup_service" and st == "BLOCKED":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RESTORE_BLOCKED", "BLOCKED", fid))
                    elif sys_id == "identity_service" and st == "REDACTED":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_REDACTED", "REDACTED", fid))
            else:
                # INCOMPLETE: Findings
                for v in violations:
                    raw_steps.append(RawStep(
                        "FINDING", v["system_id"], v["resource_id"],
                        f"REPORT_{v['violation_type']}", v["state"], v["evidence_id"]
                    ))

                # Remediations
                for v in violations:
                    vt = v["violation_type"]
                    sys_id = v["system_id"]
                    rid = v["resource_id"]
                    if vt == "ACTIVE_DATA_FLOW":
                        raw_steps.append(RawStep("REMEDIATION", sys_id, rid, "DISABLE_DATA_FLOW", "DISABLED", ""))
                    elif vt == "RESTORE_RISK":
                        raw_steps.append(RawStep("REMEDIATION", sys_id, rid, "BLOCK_RESTORE", "BLOCKED", ""))
                    elif vt == "REMAINING_RECORD":
                        raw_steps.append(RawStep("REMEDIATION", sys_id, rid, "DELETE_RECORD", "ABSENT", ""))
                    elif vt == "EXPOSED_PII":
                        if sys_id == "analytics_platform":
                            raw_steps.append(RawStep("REMEDIATION", sys_id, rid, "ANONYMIZE_RECORD", "ANONYMIZED", ""))
                        else:
                            raw_steps.append(RawStep("REMEDIATION", sys_id, rid, "REDACT_RECORD", "REDACTED", ""))

                # Verifications
                # 1. Baseline account absent
                acc_v = any(v["system_id"] == "account_service" for v in violations)
                acc_res = next((r for r in resources if r["system_id"] == "account_service"), None)
                if not acc_v and acc_res:
                    raw_steps.append(RawStep("VERIFICATION", "account_service", acc_res["resource_id"], "VERIFY_RECORD_ABSENT", "ABSENT", ""))

                # 2. Remediated verifications
                for v in violations:
                    vt = v["violation_type"]
                    sys_id = v["system_id"]
                    rid = v["resource_id"]
                    if vt == "ACTIVE_DATA_FLOW":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", ""))
                    elif vt == "RESTORE_RISK":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RESTORE_BLOCKED", "BLOCKED", ""))
                    elif vt == "REMAINING_RECORD":
                        raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_ABSENT", "ABSENT", ""))
                    elif vt == "EXPOSED_PII":
                        if sys_id == "analytics_platform":
                            raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", ""))
                        else:
                            raw_steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_REDACTED", "REDACTED", ""))

                # 3. Security audit log (only if in evidence for this case)
                sec_res = next((r for r in resources if r["system_id"] == "security_service"), None)
                if sec_res and sec_res["state"] == "PRESENT":
                    raw_steps.append(RawStep("VERIFICATION", "security_service", sec_res["resource_id"], "VERIFY_RECORD_PRESENT", "PRESENT", ""))

            steps_json = synthesizer.synthesize(raw_steps)

    exp_status, exp_steps = expected[cid]
    actual_steps = json.loads(steps_json)
    
    st_match = (status == exp_status)
    sc_match = (len(actual_steps) == len(exp_steps))
    if st_match:
        status_matches += 1
    if sc_match:
        step_count_matches += 1

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
