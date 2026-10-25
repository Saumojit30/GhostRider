# Proposal

## Why
Northstar Shop suffered a $2.4M incident due to "ghost data" lingering across secondary replicas, search indices, logs, and active synchronization pipelines after deletion was reported complete. The platform requires an AI-powered, deterministic deletion-audit engine to independently investigate deletion requests, resolve historical identity aliases, audit resource states strictly at the `audit_at` cutoff, apply retention/deletion policies, and output ordered remediation and verification steps conforming to the challenge evaluation contract.

## What Changes
- Implement a multilingual request intent classifier that filters non-deletion actions (access, export, marketing opt-outs, profile corrections) into `NOT_APPLICABLE` with empty step arrays.
- Implement an identity graph resolver connecting current snapshots (`user_identities.csv`) and historical change logs (`user_audit_log.csv`) across names, emails, phone numbers, and SHA-256 hashes.
- Implement a multi-modal temporal evidence indexer querying SQLite database replicas, JSON snapshot bundles, key-value observability logs, documents, and screenshots up to `audit_at`.
- Implement a policy rules engine enforcing `deletion_rules.csv`, handling account tombstones, data flows, and restore risks.
- Implement a step synthesizer ensuring strict ordering (`FINDING` -> `REMEDIATION` -> `VERIFICATION`), operation priority, alphanumeric sorting, consecutive step numbering, and valid evidence citations.
- Implement an automated evaluation harness verifying status, field, and sequence accuracy against ground truth (`dataset/sample_output.csv`), and generating required Markdown evaluation and usage reports.

## Capabilities

### New Capabilities
- `deletion-audit/intent-classification`: Classifies multilingual request texts to distinguish authorized deletion requests from non-deletion inquiries (export, access, marketing opt-out).
- `deletion-audit/identity-resolution`: Resolves complete current and historical identity profiles and alias graphs from identity snapshots and audit logs.
- `deletion-audit/temporal-state-auditing`: Evaluates point-in-time resource states across heterogeneous evidence sources bounded by `audit_at`.
- `deletion-audit/policy-synthesis`: Maps audited resource states to policy rules and synthesizes canonically sorted finding, remediation, and verification steps.

### Modified Capabilities
*(None - greenfield specification)*

## Impact
- **Code**: Introduces modular components under `code/core/` and entry point `code/main.py`.
- **Evaluation**: Establishes `code/evaluation/` with automated benchmark suite and report generators (`evaluation_report.md`, `usage_report.md`).
- **Submission**: Directly produces `output.csv` at the repository root matching all 518 cases in `dataset/deletion_requests.csv`.
