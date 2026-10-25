"""Main entry point for Ghost Data Still Exists Deletion-Audit Engine.

Processes all 518 customer requests from dataset/deletion_requests.csv,
executing multilingual intent classification, identity graph resolution,
temporal state auditing, policy rule synthesis, and canonical JSON sequence sorting,
writing the final output.csv to the repository root.
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from code.config import DATASET_DIR, OUTPUT_CSV_PATH
from code.core.classifier import is_deletion_request
from code.core.identity import IdentityResolver
from code.core.evidence_indexer import EvidenceIndexer
from code.core.auditor import Auditor
from code.core.policy import PolicyEngine
from code.core.synthesizer import StepSynthesizer


def run_pipeline():
    start_time = time.time()
    reqs_path = DATASET_DIR / "deletion_requests.csv"
    if not reqs_path.exists():
        raise FileNotFoundError(f"Missing {reqs_path}")

    print("==============================================================")
    print("Ghost Data Still Exists: Starting Deletion-Audit Engine")
    print(f"Reading target requests from: {reqs_path}")
    print("==============================================================")

    # Scaffolding components
    print("1/4 Loading multi-modal evidence indexer and parsing 94 evidence files...")
    indexer = EvidenceIndexer()
    print(f"    Indexed {len(indexer.items)} evidence records across all modalities.")

    print("2/4 Initializing identity resolver graph...")
    resolver = IdentityResolver()

    print("3/4 Initializing temporal state auditor and policy engine...")
    auditor = Auditor(indexer)
    policy = PolicyEngine()

    print("4/4 Processing all customer requests...")
    with open(reqs_path, "r", encoding="utf-8") as f:
        requests = list(csv.DictReader(f))

    total_requests = len(requests)
    print(f"    Total cases to audit: {total_requests}")

    output_rows = []
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}

    for idx, req in enumerate(requests, start=1):
        cid = req["case_id"]
        email = req["email"]
        audit_at = req["audit_at"]
        reported_at = req["reported_at"]
        req_text = req.get("request_text", "")

        # 1. Intent Classification
        is_del = is_deletion_request(req_text)
        if not is_del:
            status = "NOT_APPLICABLE"
            steps_json = "[]"
        else:
            # 2. Identity Resolution
            ident = resolver.resolve(email)

            # 3. Temporal State Auditing
            audited = auditor.audit_case(
                email, audit_at, reported_at, ident,
                reported_status=req.get("reported_status", "COMPLETE"),
                case_id=cid
            )

            # 4. Policy Mapping
            status, raw_steps = policy.evaluate(audited)

            # 5. Canonical Step Synthesis
            steps_json = StepSynthesizer.synthesize(raw_steps)

        status_counts[status] = status_counts.get(status, 0) + 1
        output_rows.append({
            "case_id": cid,
            "deletion_status": status,
            "steps_json": steps_json
        })

        if idx % 100 == 0 or idx == total_requests:
            print(f"    Processed {idx}/{total_requests} cases...")

    # Write root output.csv
    print(f"Writing final submission file to: {OUTPUT_CSV_PATH}")
    with open(OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "deletion_status", "steps_json"])
        writer.writeheader()
        writer.writerows(output_rows)

    elapsed = time.time() - start_time
    print("==============================================================")
    print("Audit Run Complete!")
    print(f"Total Cases:     {len(output_rows)}")
    print(f"COMPLETE:        {status_counts.get('COMPLETE', 0)}")
    print(f"INCOMPLETE:      {status_counts.get('INCOMPLETE', 0)}")
    print(f"NOT_APPLICABLE:  {status_counts.get('NOT_APPLICABLE', 0)}")
    print(f"Execution Time:  {elapsed:.2f} seconds")
    print(f"Output File:     {OUTPUT_CSV_PATH}")
    print("==============================================================")


if __name__ == "__main__":
    run_pipeline()
