"""Deletion Policy Engine for Ghost Data Still Exists.

Maps audited resources and violations to findings, remediations, and verifications
according to deletion_rules.csv.
"""

from dataclasses import dataclass
from typing import List, Optional

from code.core.auditor import AuditedResource


@dataclass
class RawStep:
    phase: str  # FINDING, REMEDIATION, VERIFICATION
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str = ""


class PolicyEngine:
    """Enforces deletion policies and generates operational steps."""

    def evaluate(self, audited_resources: List[AuditedResource]) -> tuple[str, List[RawStep]]:
        """Evaluates audited resources to produce deletion_status and raw steps.
        
        Returns:
            (status, steps) where status is 'COMPLETE' or 'INCOMPLETE'.
        """
        violations = [r for r in audited_resources if r.is_violation]
        is_complete = len(violations) == 0
        status = "COMPLETE" if is_complete else "INCOMPLETE"

        steps: List[RawStep] = []

        if is_complete:
            # For COMPLETE cases: only VERIFICATION steps proving current compliant state
            for res in audited_resources:
                if res.system_id == "account_service" and res.state == "ABSENT":
                    steps.append(RawStep(
                        phase="VERIFICATION", system_id=res.system_id, resource_id=res.resource_id,
                        operation="VERIFY_RECORD_ABSENT", state="ABSENT", evidence_id=res.evidence_id
                    ))
                elif res.system_id == "security_service" and res.state == "PRESENT":
                    steps.append(RawStep(
                        phase="VERIFICATION", system_id=res.system_id, resource_id=res.resource_id,
                        operation="VERIFY_RECORD_PRESENT", state="PRESENT", evidence_id=res.evidence_id
                    ))
                elif res.system_id == "analytics_platform" and res.state == "ANONYMIZED":
                    steps.append(RawStep(
                        phase="VERIFICATION", system_id=res.system_id, resource_id=res.resource_id,
                        operation="VERIFY_RECORD_ANONYMIZED", state="ANONYMIZED", evidence_id=res.evidence_id
                    ))
                elif res.system_id == "support_platform" and res.state == "REDACTED":
                    steps.append(RawStep(
                        phase="VERIFICATION", system_id=res.system_id, resource_id=res.resource_id,
                        operation="VERIFY_RECORD_REDACTED", state="REDACTED", evidence_id=res.evidence_id
                    ))
                elif res.system_id == "integration_service" and res.state == "DISABLED":
                    steps.append(RawStep(
                        phase="VERIFICATION", system_id=res.system_id, resource_id=res.resource_id,
                        operation="VERIFY_DATA_FLOW_DISABLED", state="DISABLED", evidence_id=res.evidence_id
                    ))
                elif res.system_id == "backup_service" and res.state == "BLOCKED":
                    steps.append(RawStep(
                        phase="VERIFICATION", system_id=res.system_id, resource_id=res.resource_id,
                        operation="VERIFY_RESTORE_BLOCKED", state="BLOCKED", evidence_id=res.evidence_id
                    ))
                elif res.system_id == "identity_service" and res.state == "REDACTED":
                    steps.append(RawStep(
                        phase="VERIFICATION", system_id=res.system_id, resource_id=res.resource_id,
                        operation="VERIFY_RECORD_REDACTED", state="REDACTED", evidence_id=res.evidence_id
                    ))
        else:
            # For INCOMPLETE cases: FINDINGS + REMEDIATIONS + VERIFICATIONS
            # 1. Findings (cite evidence_id)
            for res in violations:
                op = f"REPORT_{res.violation_type}"
                steps.append(RawStep(
                    phase="FINDING", system_id=res.system_id, resource_id=res.resource_id,
                    operation=op, state=res.state, evidence_id=res.evidence_id
                ))

            # 2. Remediations (evidence_id is empty string "")
            for res in violations:
                vt = res.violation_type
                sys_id = res.system_id
                rid = res.resource_id
                if vt == "ACTIVE_DATA_FLOW":
                    steps.append(RawStep("REMEDIATION", sys_id, rid, "DISABLE_DATA_FLOW", "DISABLED", ""))
                elif vt == "RESTORE_RISK":
                    steps.append(RawStep("REMEDIATION", sys_id, rid, "BLOCK_RESTORE", "BLOCKED", ""))
                elif vt == "REMAINING_RECORD":
                    steps.append(RawStep("REMEDIATION", sys_id, rid, "DELETE_RECORD", "ABSENT", ""))
                elif vt == "EXPOSED_PII":
                    if sys_id == "analytics_platform":
                        steps.append(RawStep("REMEDIATION", sys_id, rid, "ANONYMIZE_RECORD", "ANONYMIZED", ""))
                    else:
                        steps.append(RawStep("REMEDIATION", sys_id, rid, "REDACT_RECORD", "REDACTED", ""))

            # 3. Post-remediation Verifications (evidence_id is empty string "")
            # Baseline account_service absent (if not already remediated)
            account_remediated = any(r.system_id == "account_service" for r in violations)
            account_audited = next((r for r in audited_resources if r.system_id == "account_service"), None)
            if not account_remediated and account_audited:
                steps.append(RawStep(
                    phase="VERIFICATION", system_id="account_service", resource_id=account_audited.resource_id,
                    operation="VERIFY_RECORD_ABSENT", state="ABSENT", evidence_id=""
                ))

            # Remediated resources post-verification
            for res in violations:
                vt = res.violation_type
                sys_id = res.system_id
                rid = res.resource_id
                if vt == "ACTIVE_DATA_FLOW":
                    steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", ""))
                elif vt == "RESTORE_RISK":
                    steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RESTORE_BLOCKED", "BLOCKED", ""))
                elif vt == "REMAINING_RECORD":
                    steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_ABSENT", "ABSENT", ""))
                elif vt == "EXPOSED_PII":
                    if sys_id == "analytics_platform":
                        steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", ""))
                    else:
                        steps.append(RawStep("VERIFICATION", sys_id, rid, "VERIFY_RECORD_REDACTED", "REDACTED", ""))

            # Baseline security audit record present (ONLY IF audited in the case's evidence)
            sec_audited = next((r for r in audited_resources if r.system_id == "security_service"), None)
            if sec_audited and sec_audited.state == "PRESENT":
                steps.append(RawStep(
                    phase="VERIFICATION", system_id="security_service", resource_id=sec_audited.resource_id,
                    operation="VERIFY_RECORD_PRESENT", state="PRESENT", evidence_id=""
                ))

        return status, steps