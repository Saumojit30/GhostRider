# Spec Delta

## Purpose
Maps audited resource states to policy rules, generates ordered finding, remediation, and verification steps, and serializes the canonical output contract.

## ADDED Requirements

### Requirement: Policy rule enforcement
The system SHALL map every discovered resource and state to its required treatment per deletion_rules.csv, enforcing DELETE on profiles/exports/search, REDACT on support messages and account tombstones, ANONYMIZE on analytics, and RETAIN on security audit logs.

#### Scenario: Lingering account profile treatment
- **WHEN** account_service profile is PRESENT at audit_at
- **THEN** system emits REPORT_REMAINING_RECORD finding, DELETE_RECORD remediation, and VERIFY_RECORD_ABSENT verification.

#### Scenario: Unredacted account tombstone treatment
- **WHEN** identity_service tombstone contains exposed PII at audit_at
- **THEN** system emits REPORT_EXPOSED_PII finding, REDACT_RECORD remediation, and VERIFY_RECORD_REDACTED verification.

#### Scenario: Active data flow treatment
- **WHEN** integration_service connector is ACTIVE at audit_at
- **THEN** system emits REPORT_ACTIVE_DATA_FLOW finding, DISABLE_DATA_FLOW remediation, and VERIFY_DATA_FLOW_DISABLED verification.

#### Scenario: Active restore risk treatment
- **WHEN** backup_service archive has restore_allowed equal to 1 at audit_at
- **THEN** system emits REPORT_RESTORE_RISK finding, BLOCK_RESTORE remediation, and VERIFY_RESTORE_BLOCKED verification.

### Requirement: Canonical step ordering and numbering
The system SHALL order steps in steps_json by phase (FINDING, then REMEDIATION, then VERIFICATION), then by operation priority order, then by ascending system_id, then by ascending resource_id, numbered consecutively starting at 1.

#### Scenario: Complete case ordering and citations
- **WHEN** case has status COMPLETE
- **THEN** steps_json contains only VERIFICATION steps, all citing valid evidence IDs.

#### Scenario: Incomplete case ordering and citations
- **WHEN** case has status INCOMPLETE
- **THEN** steps_json contains FINDING steps (with evidence citations), followed by REMEDIATION steps (empty evidence_id), followed by VERIFICATION steps (empty evidence_id).
