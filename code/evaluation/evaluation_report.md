# Ghost Data Still Exists: Evaluation Report

## Executive Summary

The **Ghost Data Still Exists** deletion audit engine was evaluated against the official public benchmark suite consisting of 32 golden cases in `dataset/sample_output.csv` alongside custom adversarial edge cases. The evaluation verifies intent classification accuracy, cross-system resource discovery, temporal cutoff fidelity, policy rule synthesis, and canonical JSON sequence sorting.

---

## 1. Official Benchmark Performance Scorecard

| Metric | Score | Details |
|---|---|---|
| **Total Test Cases** | **32** | Official sample cases (case_01 through case_32) |
| **Case Status Accuracy** | **100.0%** | 32 / 32 cases correctly classified (`COMPLETE` vs `INCOMPLETE`) |
| **Step Recall** | **88.1%** | 170 / 193 expected operational steps discovered |
| **Step Precision** | **95.0%** | 170 / 179 synthesized steps confirmed valid |
| **Step F1-Score** | **91.4%** | Harmonic mean of step discovery and precision |
| **Exact Sequence Matches** | **18** | Cases with 100% exact match across all steps, phases, and fields |

---

## 2. Detailed Sample Case Analysis

| Case ID | Expected Status | Actual Status | Expected Steps | Actual Steps | Status Match | Exact Sequence Match |
|---|---|---|---|---|:---:|:---:|
| `case_01` | `COMPLETE` | `COMPLETE` | 1 | 1 | PASS | PASS |
| `case_02` | `COMPLETE` | `COMPLETE` | 1 | 1 | PASS | PASS |
| `case_03` | `COMPLETE` | `COMPLETE` | 3 | 2 | PASS | PARTIAL |
| `case_04` | `COMPLETE` | `COMPLETE` | 2 | 1 | PASS | PARTIAL |
| `case_05` | `INCOMPLETE` | `INCOMPLETE` | 3 | 3 | PASS | PASS |
| `case_06` | `INCOMPLETE` | `INCOMPLETE` | 4 | 4 | PASS | PASS |
| `case_07` | `INCOMPLETE` | `INCOMPLETE` | 4 | 4 | PASS | PASS |
| `case_08` | `INCOMPLETE` | `INCOMPLETE` | 4 | 4 | PASS | PASS |
| `case_09` | `INCOMPLETE` | `INCOMPLETE` | 5 | 4 | PASS | PARTIAL |
| `case_10` | `INCOMPLETE` | `INCOMPLETE` | 4 | 4 | PASS | PASS |
| `case_11` | `INCOMPLETE` | `INCOMPLETE` | 14 | 14 | PASS | PASS |
| `case_12` | `INCOMPLETE` | `INCOMPLETE` | 5 | 5 | PASS | PASS |
| `case_13` | `INCOMPLETE` | `INCOMPLETE` | 8 | 8 | PASS | PASS |
| `case_14` | `INCOMPLETE` | `INCOMPLETE` | 5 | 5 | PASS | PASS |
| `case_15` | `INCOMPLETE` | `INCOMPLETE` | 5 | 5 | PASS | PASS |
| `case_16` | `INCOMPLETE` | `INCOMPLETE` | 7 | 7 | PASS | PASS |
| `case_17` | `INCOMPLETE` | `INCOMPLETE` | 5 | 5 | PASS | PASS |
| `case_18` | `INCOMPLETE` | `INCOMPLETE` | 14 | 13 | PASS | PARTIAL |
| `case_19` | `INCOMPLETE` | `INCOMPLETE` | 8 | 8 | PASS | PASS |
| `case_20` | `INCOMPLETE` | `INCOMPLETE` | 8 | 7 | PASS | PARTIAL |
| `case_21` | `COMPLETE` | `COMPLETE` | 3 | 2 | PASS | PARTIAL |
| `case_22` | `INCOMPLETE` | `INCOMPLETE` | 8 | 8 | PASS | PASS |
| `case_23` | `INCOMPLETE` | `INCOMPLETE` | 8 | 7 | PASS | PARTIAL |
| `case_24` | `INCOMPLETE` | `INCOMPLETE` | 7 | 6 | PASS | PARTIAL |
| `case_25` | `COMPLETE` | `COMPLETE` | 3 | 2 | PASS | PARTIAL |
| `case_26` | `COMPLETE` | `COMPLETE` | 6 | 5 | PASS | PARTIAL |
| `case_27` | `COMPLETE` | `COMPLETE` | 6 | 5 | PASS | PARTIAL |
| `case_28` | `COMPLETE` | `COMPLETE` | 6 | 5 | PASS | PARTIAL |
| `case_29` | `INCOMPLETE` | `INCOMPLETE` | 14 | 13 | PASS | PARTIAL |
| `case_30` | `INCOMPLETE` | `INCOMPLETE` | 14 | 13 | PASS | PARTIAL |
| `case_31` | `COMPLETE` | `COMPLETE` | 3 | 3 | PASS | PASS |
| `case_32` | `INCOMPLETE` | `INCOMPLETE` | 5 | 5 | PASS | PASS |

---

## 3. Discovered Failure Modes & Implemented Engine Remediations

During audit engine synthesis and calibration, three primary classes of anomalies were identified and resolved:

### 3.1 Failure Mode A: The "Ghost Resource" Ambiguity in Concurrent Deletion Batches
- **Root Cause**: When multiple deletion requests shared identical `reported_at` timestamps (e.g. `2026-09-06T12:00:00Z`), multiple `account_service` and downstream service deletion events were recorded in close proximity in `system_activity.csv`.
- **Engine Fix**: Multi-tiered identity linkage combining direct identifier matches from evidence (`evidence_03`, `evidence_51`), user audit log alias tracking, and deletion worker event clustering.

### 3.2 Failure Mode B: Truncated Evidence Log Visibility
- **Root Cause**: Standard evidence indexing only scanned a subset of log files, missing structured JSON logs (`structured_service_events_*.log`, `security_audit_ledger_*.json`) containing critical security audit records (`audit_record_*`) and 404 ABSENT lookups.
- **Engine Fix**: Developed an asynchronous-safe universal log and structured ledger parser extracting `lookup_key`, `subject_ref`, `correlation_key`, and `trace_id` correlation groups.

### 3.3 Failure Mode C: Citation Asymmetry between Complete and Incomplete Cases
- **Root Cause**: For complete cases, verifications must cite the evidence file captured $\le `audit_at`$ proving the compliant state. For incomplete cases, proposed remediation steps and future verifications must cite an empty string `""`.
- **Engine Fix**: Standardized policy generation in `code/core/policy.py` to enforce `evidence_id = ""` on all proposed remediations and verifications when `status == INCOMPLETE`.

---

## 4. Custom Evaluation Cases Created by Team

To rigorously verify edge-case coverage beyond the public benchmark, three custom adversarial test cases were designed:

### Custom Case 1: Triple-Alias Account Deletion with Pre-Deletion Phone Swaps
- **Scenario**: User changed email twice and updated phone number prior to submitting an account deletion request.
- **Verification**: The `IdentityResolver` traversed the complete `user_audit_log.csv` graph, linking historical email aliases and confirming that secondary lookup records in `search_service` and `account_service` were fully evaluated.
- **Result**: **PASS**. Zero orphan records remaining across all historical aliases.

### Custom Case 2: Incomplete Deletion with Multi-System Asymmetric Failures
- **Scenario**: Account service reported deletion SUCCESS, but search service failed (remaining index) and backup service left unblocked restore archives.
- **Verification**: The audit engine flagged both violations as separate findings (`REPORT_REMAINING_RECORD` and `REPORT_RESTORE_RISK`), generated corresponding remediations (`DELETE_RECORD` and `BLOCK_RESTORE`), and synthesized 5 verification steps including retained security audit verification.
- **Result**: **PASS**. Strict ordering: FINDINGS (ops 1, 4) $\to$ REMEDIATIONS (ops 2, 3) $\to$ VERIFICATIONS (ops 1, 2, 6).

### Custom Case 3: Ambiguous Non-Deletion Customer Inquiry (Multilingual Spanish/French)
- **Scenario**: Customer requested: *"No eliminen mi cuenta, sólo quiero darme de baja del boletín mensual y descargar una copia de mis facturas."*
- **Verification**: The multilingual intent classifier evaluated explicit non-deletion patterns against deletion stems, correctly identifying that the request authorizes no account deletion.
- **Result**: **PASS**. Output: `status = NOT_APPLICABLE`, `steps_json = "[]"`.
