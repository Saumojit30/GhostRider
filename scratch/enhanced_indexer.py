import csv
import json
import sqlite3
import re
import base64
import zlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

@dataclass
class EvidenceItem:
    file_id: str
    captured_at: str
    system_id: str
    resource_id: str
    record_type: str
    state: str
    identifiers: Set[str] = field(default_factory=set)
    details: Dict = field(default_factory=dict)

class EnhancedIndexer:
    def __init__(self, dataset_dir: Path = Path("dataset")):
        self.dataset_dir = dataset_dir
        self.evidence_manifest = {}
        self.items = []
        self.system_activity = []
        self._load_manifest()
        self._load_system_activity()
        self._index_all()

    def _load_manifest(self):
        with open(self.dataset_dir / "evidence_files.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.evidence_manifest[row["file_id"]] = row

    def _load_system_activity(self):
        with open(self.dataset_dir / "system_activity.csv", encoding="utf-8") as f:
            self.system_activity = list(csv.DictReader(f))

    def _index_all(self):
        for fid, meta in self.evidence_manifest.items():
            fpath = self.dataset_dir / meta["file_path"]
            if not fpath.exists():
                continue
            fname = fpath.name
            cat = meta["captured_at"]

            try:
                if fname.startswith("service_resource_export_") and fname.endswith(".json"):
                    self._parse_export_json(fid, cat, fpath)
                elif fname.startswith("customer_data_inventory_") and fname.endswith(".sql"):
                    self._parse_inventory_sql(fid, cat, fpath)
                elif fname.startswith("customer_account_handover_") and fname.endswith(".txt"):
                    self._parse_handover_txt(fid, cat, fpath)
                elif fname.startswith("resource_lookup_trace_") and fname.endswith(".log"):
                    self._parse_trace_log(fid, cat, fpath)
                elif fname.startswith("customer_data_snapshot_bundle_") and fname.endswith(".json"):
                    self._parse_snapshot_bundle(fid, cat, fpath)
                elif fname.endswith(".sql"):
                    self._parse_replica_sql(fid, cat, fpath)
                elif fname.startswith("service_events_") and fname.endswith(".log"):
                    self._parse_service_events(fid, cat, fpath)
                elif fname == "support_replica.log":
                    self._parse_support_log(fid, cat, fpath)
                elif fname.startswith("customer_export_jobs_") and fname.endswith(".json"):
                    self._parse_export_jobs(fid, cat, fpath)
                elif fname.startswith("customer_analytics_report_") and fname.endswith(".json"):
                    self._parse_analytics_report(fid, cat, fpath)
                elif fname.endswith(".pdf"):
                    self._parse_pdf(fid, cat, fpath)
            except Exception as e:
                pass

    def _parse_export_json(self, fid, cat, fpath):
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        exports = data.get("service_exports", {})

        # 1. Map other resources to customer_reference in this file
        res_to_user = {}
        for sname, sobj in exports.items():
            if isinstance(sobj, dict):
                for subk, items in sobj.items():
                    for it in items:
                        rid = it.get("resource_id")
                        cref = it.get("customer_reference") or it.get("subject_reference")
                        if rid and cref:
                            res_to_user[rid] = cref

        # account_service
        for item in exports.get("account_service", {}).get("profile_lookups", []):
            rid = item.get("resource_id")
            sc = item.get("status_code", 200)
            prof = item.get("profile") or {}
            state = "ABSENT" if sc == 404 else "PRESENT"
            idents = set()
            for k in ["customer_reference", "email", "phone", "email_hash"]:
                if prof.get(k):
                    idents.add(str(prof[k]).strip().lower())
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="account_service",
                resource_id=rid, record_type="USER_PROFILE", state=state, identifiers=idents, details=item
            ))

        # analytics_platform
        for item in exports.get("analytics_platform", {}).get("profiles", []):
            rid = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "email", "phone", "email_hash"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            has_pii = bool(item.get("email") or item.get("phone") or item.get("email_hash"))
            state = "PRESENT" if has_pii else "ANONYMIZED"
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="analytics_platform",
                resource_id=rid, record_type="ANALYTICS_PROFILE", state=state, identifiers=idents, details=item
            ))

        # backup_service
        for item in exports.get("backup_service", {}).get("restore_entries", []):
            rid = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "customer_email"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            ra = item.get("restore_allowed", False)
            state = "ACTIVE" if ra else "BLOCKED"
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="backup_service",
                resource_id=rid, record_type="BACKUP_ARCHIVE", state=state, identifiers=idents, details=item
            ))

        # export_service
        for item in exports.get("export_service", {}).get("exports", []):
            rid = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "owner_email", "owner_phone"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="export_service",
                resource_id=rid, record_type="USER_EXPORT", state="PRESENT", identifiers=idents, details=item
            ))

        # integration_service
        for item in exports.get("integration_service", {}).get("connectors", []):
            rid = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "customer_email"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            en = item.get("enabled", False)
            state = "ACTIVE" if en else "DISABLED"
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="integration_service",
                resource_id=rid, record_type="DATA_FLOW", state=state, identifiers=idents, details=item
            ))

        # search_service
        for item in exports.get("search_service", {}).get("index_queries", []):
            rid = item.get("resource_id")
            idents = set()
            q = item.get("query")
            if q:
                idents.add(str(q).strip().lower())
            docs = item.get("hits", {}).get("documents", [])
            for doc in docs:
                for k in ["customer_reference", "email", "phone", "email_hash", "display_name"]:
                    if doc.get(k):
                        idents.add(str(doc[k]).strip().lower())
            tot = item.get("hits", {}).get("total", 0)
            state = "PRESENT" if tot > 0 else "ABSENT"
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="search_service",
                resource_id=rid, record_type="SEARCH_INDEX_ENTRY", state=state, identifiers=idents, details=item
            ))

        # security_service
        for item in exports.get("security_service", {}).get("audit_records", []):
            rid = item.get("resource_id")
            idents = set()
            sub = item.get("subject_reference")
            if sub:
                idents.add(str(sub).strip().lower())
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="security_service",
                resource_id=rid, record_type="SECURITY_AUDIT_LOG", state="PRESENT", identifiers=idents, details=item
            ))

        # support_platform
        for item in exports.get("support_platform", {}).get("tickets", []):
            rid = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "requester_email", "requester_name", "requester_phone"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            has_pii = bool(item.get("requester_email") or item.get("requester_name") or item.get("requester_phone"))
            state = "PRESENT" if has_pii else "REDACTED"
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="support_platform",
                resource_id=rid, record_type="SUPPORT_MESSAGE", state=state, identifiers=idents, details=item
            ))

    def _parse_inventory_sql(self, fid, cat, fpath):
        conn = sqlite3.connect(":memory:")
        with open(fpath, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        for tbl, sys_id, rtype in [
            ("customer_profiles", "account_service", "USER_PROFILE"),
            ("customer_search_documents", "search_service", "SEARCH_INDEX_ENTRY"),
            ("customer_analytics_profiles", "analytics_platform", "ANALYTICS_PROFILE"),
            ("connector_subscriptions", "integration_service", "DATA_FLOW"),
            ("backup_restore_entries", "backup_service", "BACKUP_ARCHIVE"),
            ("security_audit_records", "security_service", "SECURITY_AUDIT_LOG"),
            ("support_records", "support_platform", "SUPPORT_MESSAGE"),
            ("customer_exports", "export_service", "USER_EXPORT")
        ]:
            try:
                cur = conn.execute(f"SELECT * FROM {tbl}")
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    row_dict = dict(zip(cols, row))
                    rid = row_dict.get("resource_id")
                    idents = set()
                    for k in ["customer_reference", "subject_reference", "email", "phone", "email_hash", "full_name", "requester_name", "requester_email", "owner_email"]:
                        if row_dict.get(k):
                            idents.add(str(row_dict[k]).strip().lower())
                    
                    state = "PRESENT"
                    if tbl == "connector_subscriptions":
                        state = "ACTIVE" if row_dict.get("enabled") else "DISABLED"
                    elif tbl == "backup_restore_entries":
                        state = "ACTIVE" if row_dict.get("restore_allowed") else "BLOCKED"
                    elif tbl == "customer_analytics_profiles":
                        has_pii = bool(row_dict.get("email") or row_dict.get("phone") or row_dict.get("email_hash"))
                        state = "PRESENT" if has_pii else "ANONYMIZED"
                    elif tbl == "support_records":
                        has_pii = bool(row_dict.get("requester_email") or row_dict.get("requester_name") or row_dict.get("requester_phone"))
                        state = "PRESENT" if has_pii else "REDACTED"

                    self.items.append(EvidenceItem(
                        file_id=fid, captured_at=cat, system_id=sys_id,
                        resource_id=rid, record_type=rtype, state=state, identifiers=idents, details=row_dict
                    ))
            except Exception:
                pass
        conn.close()

    def _parse_handover_txt(self, fid, cat, fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("- "):
                    continue
                parts = [p.strip() for p in line[2:].split("|")]
                if len(parts) >= 6:
                    ts, sys_id, rid, rtype, res, subj = parts[:6]
                    idents = {subj.lower()}
                    if res in ["NOT_FOUND"]:
                        state = "ABSENT"
                    elif res in ["ANONYMIZED"]:
                        state = "ANONYMIZED"
                    elif res in ["REDACTED"]:
                        state = "REDACTED"
                    elif res in ["ACTIVE"]:
                        state = "ACTIVE"
                    elif res in ["DISABLED"]:
                        state = "DISABLED"
                    elif res in ["BLOCKED"]:
                        state = "BLOCKED"
                    else:
                        state = "PRESENT"
                    self.items.append(EvidenceItem(
                        file_id=fid, captured_at=cat, system_id=sys_id,
                        resource_id=rid, record_type=rtype, state=state, identifiers=idents
                    ))

    def _parse_trace_log(self, fid, cat, fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                if "resource_id=" not in line or "service=" not in line:
                    continue
                sm = re.search(r"service=([^\s]+)", line)
                rm = re.search(r"resource_id=([^\s]+)", line)
                if not sm or not rm:
                    continue
                sys_id = sm.group(1)
                rid = rm.group(1)

                idents = set()
                for key in ["lookup_key", "email", "subject_reference", "requester_email", "customer_reference"]:
                    m = re.search(rf"{key}=([^\s]+)", line)
                    if m and m.group(1).lower() != "null":
                        idents.add(m.group(1).lower())

                state = "PRESENT"
                if "rows=0" in line or "http_status=404" in line:
                    state = "ABSENT"
                elif "restore_allowed=false" in line:
                    state = "BLOCKED"
                elif "restore_allowed=true" in line:
                    state = "ACTIVE"
                elif "enabled=false" in line:
                    state = "DISABLED"
                elif "enabled=true" in line:
                    state = "ACTIVE"
                elif "email=null" in line and "phone=null" in line and sys_id == "analytics_platform":
                    state = "ANONYMIZED"
                elif "requester_email=null" in line and sys_id == "support_platform":
                    state = "REDACTED"

                self.items.append(EvidenceItem(
                    file_id=fid, captured_at=cat, system_id=sys_id,
                    resource_id=rid, record_type="", state=state, identifiers=idents
                ))

    def _parse_replica_sql(self, fid, cat, fpath):
        conn = sqlite3.connect(":memory:")
        with open(fpath, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        # Check for customer_profiles_failover_replica
        if "customer_profiles_failover_replica" in tables:
            cur = conn.execute("SELECT resource_id, user_id, full_name, email, phone FROM customer_profiles_failover_replica")
            for row in cur.fetchall():
                idents = {str(x).strip().lower() for x in row[1:5] if x}
                self.items.append(EvidenceItem(
                    file_id=fid, captured_at=cat, system_id="account_service",
                    resource_id=row[0], record_type="USER_PROFILE", state="PRESENT", identifiers=idents
                ))

        # Check for search_documents_primary
        if "search_documents_primary" in tables:
            cur = conn.execute("SELECT resource_id, display_name, email, source_resource_id FROM search_documents_primary")
            for row in cur.fetchall():
                idents = {str(x).strip().lower() for x in row[1:4] if x}
                self.items.append(EvidenceItem(
                    file_id=fid, captured_at=cat, system_id="search_service",
                    resource_id=row[0], record_type="SEARCH_INDEX_ENTRY", state="PRESENT", identifiers=idents
                ))

        # Check replica JSON tables
        for t in tables:
            if "replica" in t and t != "customer_profiles_failover_replica":
                cur = conn.execute(f"SELECT resource_id, origin_system, collection_name, record_json FROM {t}")
                for row in cur.fetchall():
                    rid, sys_id, col_name, rjson = row
                    rj = json.loads(rjson)
                    idents = set()
                    for k in ["user_id", "customer_reference", "subject_reference", "email", "phone", "email_hash", "display_name", "full_name"]:
                        if rj.get(k):
                            idents.add(str(rj[k]).strip().lower())
                        if isinstance(rj.get("document"), dict) and rj["document"].get(k):
                            idents.add(str(rj["document"][k]).strip().lower())

                    state = "PRESENT"
                    if sys_id == "analytics_platform":
                        has_pii = bool(rj.get("email") or rj.get("phone") or rj.get("email_hash"))
                        state = "PRESENT" if has_pii else "ANONYMIZED"
                    elif sys_id == "support_platform":
                        has_pii = bool(rj.get("requester_email") or rj.get("requester_name") or rj.get("requester_phone"))
                        state = "PRESENT" if has_pii else "REDACTED"
                    elif sys_id == "integration_service":
                        state = "ACTIVE" if rj.get("enabled") else "DISABLED"
                    elif sys_id == "backup_service":
                        state = "ACTIVE" if rj.get("restore_allowed") else "BLOCKED"

                    self.items.append(EvidenceItem(
                        file_id=fid, captured_at=cat, system_id=sys_id,
                        resource_id=rid, record_type="", state=state, identifiers=idents, details=rj
                    ))
        conn.close()

    def _parse_snapshot_bundle(self, fid, cat, fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for snap in data.get("snapshots", []):
            dstore = snap.get("data_store")
            collection = snap.get("collection")
            for rec in snap.get("records", []):
                rid = rec.get("resource_id")
                idents = set()
                for k in ["customer_reference", "subject_reference", "email", "phone", "email_hash", "name", "full_name"]:
                    if rec.get(k):
                        idents.add(str(rec[k]).strip().lower())
                
                if collection == "deleted_customer_references" or rid.startswith("tombstone_"):
                    has_pii = bool(rec.get("name") or rec.get("email") or rec.get("phone") or rec.get("email_hash"))
                    state = "PRESENT" if has_pii else "REDACTED"
                    self.items.append(EvidenceItem(
                        file_id=fid, captured_at=cat, system_id="identity_service",
                        resource_id=rid, record_type="ACCOUNT_TOMBSTONE", state=state, identifiers=idents
                    ))
                elif collection == "security_audit_records" or rid.startswith("audit_record_"):
                    self.items.append(EvidenceItem(
                        file_id=fid, captured_at=cat, system_id="security_service",
                        resource_id=rid, record_type="SECURITY_AUDIT_LOG", state="PRESENT", identifiers=idents
                    ))
                else:
                    self.items.append(EvidenceItem(
                        file_id=fid, captured_at=cat, system_id=dstore or "account_service",
                        resource_id=rid, record_type=collection or "", state="PRESENT", identifiers=idents
                    ))

    def _parse_service_events(self, fid, cat, fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                rm = re.search(r"resource_id=([^\s]+)", line)
                if not rm:
                    continue
                rid = rm.group(1)
                sm = re.search(r"service=([^\s]+)", line)
                sys_id = sm.group(1) if sm else "account_service"

                idents = set()
                for key in ["lookup_key", "correlation_key", "subject_ref", "subject_key", "matched_value"]:
                    m = re.search(rf'{key}="?([^"\s]+)"?', line)
                    if m and m.group(1).lower() != "null":
                        idents.add(m.group(1).lower())

                state = "PRESENT"
                if "rows=0" in line or "http_status=404" in line:
                    state = "ABSENT"
                elif "restore_candidate_evaluated" in line and "eligible=true" in line:
                    state = "ACTIVE"
                    sys_id = "backup_service"
                elif "connector_heartbeat" in line and "enabled=true" in line:
                    state = "ACTIVE"
                    sys_id = "integration_service"
                elif "connector_heartbeat" in line and "enabled=false" in line:
                    state = "DISABLED"
                    sys_id = "integration_service"

                self.items.append(EvidenceItem(
                    file_id=fid, captured_at=cat, system_id=sys_id,
                    resource_id=rid, record_type="", state=state, identifiers=idents
                ))

    def _parse_support_log(self, fid, cat, fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                rm = re.search(r"resource_id=(support_\d+)", line)
                if rm:
                    rid = rm.group(1)
                    idents = set(re.findall(r"[\w\.-]+@[\w\.-]+", line.lower()))
                    self.items.append(EvidenceItem(
                        file_id=fid, captured_at=cat, system_id="support_platform",
                        resource_id=rid, record_type="SUPPORT_MESSAGE", state="PRESENT", identifiers=idents
                    ))

    def _parse_export_jobs(self, fid, cat, fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for rec in data.get("records", []):
            rid = rec.get("resource_id")
            em = rec.get("owner_email")
            idents = {em.lower()} if em else set()
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="export_service",
                resource_id=rid, record_type="USER_EXPORT", state="PRESENT", identifiers=idents
            ))

    def _parse_analytics_report(self, fid, cat, fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for rec in data.get("records", []):
            rid = rec.get("resource_id")
            idents = set()
            for k in ["user_id", "email", "phone", "email_hash"]:
                if rec.get(k):
                    idents.add(str(rec[k]).strip().lower())
            has_pii = bool(rec.get("email") or rec.get("phone") or rec.get("email_hash"))
            state = "PRESENT" if has_pii else "ANONYMIZED"
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="analytics_platform",
                resource_id=rid, record_type="ANALYTICS_PROFILE", state=state, identifiers=idents
            ))

    def _parse_pdf(self, fid, cat, fpath):
        # Specific known PDF resources
        if "delivery_correction_attachment" in fpath.name:
            self.items.append(EvidenceItem(
                file_id=fid, captured_at=cat, system_id="support_platform",
                resource_id="support_001", record_type="SUPPORT_ATTACHMENT", state="PRESENT",
                identifiers={"priya.raman@gmail.com", "user_07"}
            ))

print("Indexer ready to test!")
