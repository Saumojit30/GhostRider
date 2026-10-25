"""Identity Graph Resolver for Ghost Data Still Exists.

Resolves current and historical user identities by linking user_identities.csv
and user_audit_log.csv.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from code.config import DATASET_DIR


@dataclass
class ResolvedIdentity:
    user_id: str
    primary_name: str
    primary_email: str
    primary_phone: str
    primary_hash: str
    all_names: Set[str] = field(default_factory=set)
    all_emails: Set[str] = field(default_factory=set)
    all_phones: Set[str] = field(default_factory=set)
    all_hashes: Set[str] = field(default_factory=set)
    audit_ids: List[str] = field(default_factory=list)


class IdentityResolver:
    """Loads and traverses user identities and audit logs."""

    def __init__(self, dataset_dir: Path = DATASET_DIR):
        self.dataset_dir = dataset_dir
        self.identities_by_id: Dict[str, dict] = {}
        self.email_to_userid: Dict[str, str] = {}
        self.hash_to_userid: Dict[str, str] = {}
        self.phone_to_userid: Dict[str, str] = {}
        self.audit_by_userid: Dict[str, List[dict]] = {}
        self._load_data()

    def _load_data(self):
        # 1. Load user_identities.csv
        identities_file = self.dataset_dir / "user_identities.csv"
        with open(identities_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row["user_id"]
                self.identities_by_id[uid] = row
                email = row["email"].strip().lower()
                ehash = row["email_hash"].strip().lower()
                phone = row["phone"].strip()

                if email:
                    self.email_to_userid[email] = uid
                if ehash:
                    self.hash_to_userid[ehash] = uid
                if phone:
                    self.phone_to_userid[phone] = uid

        # 2. Load user_audit_log.csv
        audit_file = self.dataset_dir / "user_audit_log.csv"
        with open(audit_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row["user_id"]
                self.audit_by_userid.setdefault(uid, []).append(row)

                # Map historical emails, hashes, and phones back to user_id
                field_name = row.get("field_name")
                old_val = row.get("old_value", "").strip()
                new_val = row.get("new_value", "").strip()

                if field_name == "email":
                    if old_val:
                        self.email_to_userid[old_val.lower()] = uid
                    if new_val:
                        self.email_to_userid[new_val.lower()] = uid
                elif field_name == "email_hash":
                    if old_val:
                        self.hash_to_userid[old_val.lower()] = uid
                    if new_val:
                        self.hash_to_userid[new_val.lower()] = uid
                elif field_name == "phone":
                    if old_val:
                        self.phone_to_userid[old_val] = uid
                    if new_val:
                        self.phone_to_userid[new_val] = uid

    def resolve(self, seed_email: str) -> Optional[ResolvedIdentity]:
        """Resolves the complete identity graph from a seed email (current or historical)."""
        clean_email = seed_email.strip().lower()
        user_id = self.email_to_userid.get(clean_email)
        if not user_id:
            return None

        current = self.identities_by_id.get(user_id, {})
        history = self.audit_by_userid.get(user_id, [])

        all_names = set()
        all_emails = {clean_email}
        all_phones = set()
        all_hashes = set()
        audit_ids = []

        if current.get("name"):
            all_names.add(current["name"])
        if current.get("email"):
            all_emails.add(current["email"].lower())
        if current.get("phone"):
            all_phones.add(current["phone"])
        if current.get("email_hash"):
            all_hashes.add(current["email_hash"].lower())

        for audit in history:
            audit_ids.append(audit["audit_id"])
            fname = audit.get("field_name")
            old_v = audit.get("old_value", "").strip()
            new_v = audit.get("new_value", "").strip()

            if fname == "email":
                if old_v:
                    all_emails.add(old_v.lower())
                if new_v:
                    all_emails.add(new_v.lower())
            elif fname == "email_hash":
                if old_v:
                    all_hashes.add(old_v.lower())
                if new_v:
                    all_hashes.add(new_v.lower())
            elif fname == "phone":
                if old_v:
                    all_phones.add(old_v)
                if new_v:
                    all_phones.add(new_v)
            elif fname == "name":
                if old_v:
                    all_names.add(old_v)
                if new_v:
                    all_names.add(new_v)

        return ResolvedIdentity(
            user_id=user_id,
            primary_name=current.get("name", ""),
            primary_email=current.get("email", ""),
            primary_phone=current.get("phone", ""),
            primary_hash=current.get("email_hash", ""),
            all_names=all_names,
            all_emails=all_emails,
            all_phones=all_phones,
            all_hashes=all_hashes,
            audit_ids=audit_ids,
        )
