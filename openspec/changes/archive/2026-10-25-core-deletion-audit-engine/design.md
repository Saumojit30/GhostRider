# Design

## Context
See `proposal.md` for problem background and motivation. The challenge requires processing 518 cases across heterogeneous evidence formats (SQLite SQL files, JSON snapshot bundles, key-value syslog archives, structured JSON logs, image screenshots, and PDF documents) with strict temporal cutoff at `audit_at` and deterministic JSON step serialization.

## Goals / Non-Goals

**Goals:**
- Provide a clean, deterministic Python engine under `code/core/` runnable via `python code/main.py`.
- Guarantee exact 100% agreement on `dataset/sample_output.csv` (32 cases) across case status, step count, operation, state, system, and evidence citations.
- Complete execution of all 518 cases in under 30 seconds with zero runtime crashes and minimal token consumption.
- Automatically generate compliant `evaluation/evaluation_report.md` and `evaluation/usage_report.md`.

**Non-Goals:**
- Real-time continuous streaming daemon (batch audit execution is sufficient for challenge contract).
- Modification of source data under `dataset/`.
- Relying on external network calls during audit inference.

## Decisions

### Decision 1: In-Memory SQLite Evidence Query Engine
- **Decision**: Execute SQL snapshot evidence files into Python's built-in `sqlite3` in-memory instances at runtime.
- **Rationale**: SQL evidence files (`dataset/evidence/databases/*.sql`) are valid SQLite-compatible SQL. In-memory execution allows high-speed SQL queries to detect replication drift (e.g. comparing primary tables vs failover/regional replica tables) in microseconds.
- **Alternatives considered**: Raw string regex matching (fragile with multi-line SQL INSERT statements); external PostgreSQL container (unnecessary dependency overhead).

### Decision 2: Rule-Based Deterministic First Architecture with Fallbacks
- **Decision**: Implement intent classification and policy enforcement with high-speed deterministic regex/pattern heuristics, backed by structured metadata indexing.
- **Rationale**: Guarantees zero latency, zero API rate limits, identical reproducible output, and minimal token cost for submission reporting.
- **Alternatives considered**: Calling external LLMs for all 518 cases (high cost, high latency, nondeterministic JSON formatting errors, rate-limiting risk).

### Decision 3: Graph-Based Identifier Traversal
- **Decision**: Index `user_identities.csv` and `user_audit_log.csv` into an bidirectional identity graph mapping any email (current or past), phone, name, or SHA-256 hash to a canonical `user_id`.
- **Rationale**: Solves the "historical alias blindspot" where older systems store previous emails or email hashes.

### Decision 4: Strict Comparator & Sorter Pipeline
- **Decision**: Implement a canonical sort key for steps:
  1. Phase priority: `FINDING` (1), `REMEDIATION` (2), `VERIFICATION` (3)
  2. Operation priority index within phase
  3. `system_id` ascending
  4. `resource_id` ascending
- **Rationale**: Meets the exact sorting contract required by `problem_statement.md` §Allowed Operations.

## Risks / Trade-offs

- **[Risk] Multimodal screenshot/PDF evidence parsing complexity** → **Mitigation**: Extract known screenshot/PDF metadata into structured dictionaries matching evidence manifest IDs, with OCR/text fallbacks.
- **[Risk] Evidence timestamp filtering edge cases** → **Mitigation**: Strictly filter all evidence by `captured_at <= audit_at` and activity events by `event_time <= audit_at`.
