# Tasks

## 1. Foundation & Configuration

- [x] 1.1 Create core package structure under `code/core/` and `code/evaluation/` with `__init__.py` files and verify directory presence.
- [x] 1.2 Implement `code/config.py` defining operation priority maps, phase order constants, and dataset paths.

## 2. Intent Classification & Identity Resolution

- [x] 2.1 Implement `code/core/classifier.py` with multilingual intent parsing and NOT_APPLICABLE detection; verify against non-deletion cases 533–542.
- [x] 2.2 Implement `code/core/identity.py` traversing `user_identities.csv` and `user_audit_log.csv` into unified identity graphs; verify alias resolution on test cases.

## 3. Evidence Indexing & Temporal State Auditing

- [x] 3.1 Implement `code/core/evidence_indexer.py` executing SQLite database snapshots, JSON exports, and log parsers filtered by `audit_at`.
- [x] 3.2 Implement `code/core/auditor.py` evaluating cross-system resource presence, tombstone PII leaks, active data flows, and restore risks.

## 4. Policy Mapping & Step Synthesis

- [x] 4.1 Implement `code/core/policy.py` applying `deletion_rules.csv` and generating corresponding finding, remediation, and verification operations.
- [x] 4.2 Implement `code/core/synthesizer.py` applying phase ordering, operation priority sorting, alphanumeric tie-breaking, and consecutive renumbering.

## 5. Verification & Submission Reports

- [x] 5.1 Implement `code/evaluation/main.py` and verify 100% exact match against all 32 cases in `dataset/sample_output.csv`.
- [x] 5.2 Implement `code/main.py` to audit all 518 cases in `dataset/deletion_requests.csv` and produce root `output.csv`.
- [x] 5.3 Generate `code/evaluation/evaluation_report.md` with metric breakdowns and 3 custom test cases, and `code/evaluation/usage_report.md` with token and cost metrics.

## Workflow follow-up

- Archive the change after implementation and evaluation verification.
