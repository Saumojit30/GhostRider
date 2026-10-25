# deletion-audit/temporal-state-auditing Specification

## Purpose
Inspects heterogeneous multi-modal evidence sources strictly up to the case audit_at cutoff to determine actual resource states and detect replication drift or active processes.

## Requirements

### Requirement: Temporal cutoff enforcement
The system SHALL evaluate only evidence files and activity log records whose capture time or event time is less than or equal to the case audit_at timestamp.

#### Scenario: Evidence captured prior to audit cutoff
- **WHEN** an evidence file has captured_at timestamp of 2026-09-02T23:00:00Z and case audit_at is 2026-09-08T13:40:00Z
- **THEN** the evidence is considered valid and included in the audit analysis.

#### Scenario: Evidence captured after audit cutoff
- **WHEN** an evidence file has captured_at timestamp of 2026-09-20T10:00:00Z and case audit_at is 2026-09-08T13:40:00Z
- **THEN** the evidence is strictly excluded from deciding the case state.

### Requirement: Cross-system replica and evidence state discovery
The system SHALL query SQLite databases, JSON exports, and service logs to identify records matching the subject's identifiers across account_service, search_service, support_platform, analytics_platform, export_service, integration_service, backup_service, and identity_service.

#### Scenario: Replication drift detection
- **WHEN** customer profile is deleted from customer_profiles_primary but still exists in customer_profiles_failover_replica
- **THEN** system determines that the account profile is PRESENT with finding evidence cited from the replica file.

#### Scenario: Active sync pipeline detection
- **WHEN** a connector subscription in integration_service matching the user's email has enabled equal to 1
- **THEN** system determines that an active data flow exists in state ACTIVE.

#### Scenario: Backup restore risk detection
- **WHEN** a backup catalog entry matching the user's email has restore_allowed equal to 1
- **THEN** system determines that a restore risk exists in state ACTIVE.
