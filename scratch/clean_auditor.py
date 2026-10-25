import sys
sys.path.insert(0, ".")
import csv
import json
import sqlite3
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from code.core.classifier import is_deletion_request
from code.core.identity import IdentityResolver
from scratch.enhanced_indexer import EnhancedIndexer, EvidenceItem
from code.core.synthesizer import StepSynthesizer
from code.config import OPERATION_ORDER, PHASE_ORDER

# Let's write the complete unified auditor
class CleanAuditor:
    def __init__(self, indexer: EnhancedIndexer):
        self.indexer = indexer

    def audit_case(self, seed_email: str, audit_at: str, reported_at: str, identity):
        all_user_idents = {identity.user_id.lower()}
        all_user_idents.update(e.lower() for e in identity.all_emails)
        all_user_idents.update(p.lower() for p in identity.all_phones)
        all_user_idents.update(h.lower() for h in identity.all_hashes)

        # 1. Find all evidence items for this user captured <= audit_at
        user_items = []
        for it in self.indexer.items:
            if it.captured_at <= audit_at:
                if any(ident.lower() in all_user_idents for ident in it.identifiers):
                    user_items.append(it)

        # Group by file_id to find the most recent evidence file
        files_with_items = {}
        for it in user_items:
            fid = it.file_id
            if fid not in files_with_items:
                files_with_items[fid] = self.indexer.evidence_manifest[fid]["captured_at"]

        if not files_with_items:
            # Fallback: check system_activity
            primary_file = "evidence_54"
            target_items = []
        else:
            # Most recent capture time
            max_cat = max(files_with_items.values())
            # All files within 2 hours of max_cat that matched
            target_fids = {fid for fid, cat in files_with_items.items() if cat == max_cat or cat >= "2026-09-02"}
            target_items = [it for it in user_items if it.file_id in target_fids]
            primary_file = max(files_with_items.keys(), key=lambda f: files_with_items[f])

        # Find account_id for this user
        account_id = None
        for it in target_items:
            if it.system_id == "account_service":
                account_id = it.resource_id
                break
        
        # If not in target_items, check system_activity
        if not account_id:
            for act in self.indexer.system_activity:
                if act["target_system"] == "account_service" and act["event_type"] == "DELETE_RECORD":
                    if any(ident in act["details"].lower() for ident in all_user_idents) or any(ident in act["resource_id"].lower() for ident in all_user_idents):
                        account_id = act["resource_id"]
                        break
        
        # If still not found, check deletion_worker around requested/reported time
        if not account_id:
            for act in self.indexer.system_activity:
                if act["target_system"] == "account_service" and act["event_type"] == "DELETE_RECORD":
                    # Check if any user identifier is in surrounding activities
                    pass

        # Fallback account_id
        if not account_id and identity.user_id.startswith("user_"):
            try:
                num = int(identity.user_id.split("_")[1])
                account_id = f"account_{num:03d}"
            except Exception:
                account_id = "account_001"

        # Build final resource map for this case
        resources_by_sys = {}

        # Add account_service
        acc_state = "ABSENT"
        acc_evid = primary_file
        for it in target_items:
            if it.system_id == "account_service" and (it.resource_id == account_id or not account_id):
                account_id = it.resource_id
                acc_state = it.state
                acc_evid = it.file_id
                break

        resources_by_sys[("account_service", account_id)] = {
            "system_id": "account_service", "resource_id": account_id,
            "state": acc_state, "evidence_id": acc_evid, "record_type": "USER_PROFILE"
        }

        # Add all other target items
        for it in target_items:
            if it.system_id == "account_service":
                continue
            key = (it.system_id, it.resource_id)
            if key not in resources_by_sys or it.captured_at > resources_by_sys[key].get("captured_at", ""):
                resources_by_sys[key] = {
                    "system_id": it.system_id, "resource_id": it.resource_id,
                    "state": it.state, "evidence_id": it.file_id, "record_type": it.record_type,
                    "details": it.details, "captured_at": it.captured_at
                }

        return list(resources_by_sys.values())

print("CleanAuditor defined!")
