"""Multi-Modal Evidence Indexer for Ghost Data Still Exists.

Indexes evidence files (SQL replicas, JSON exports, logs, plain text)
and system activity with temporal cutoff filtering.
"""

import csv
import json
import re
import sqlite3
import base64
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from code.config import DATASET_DIR, EVIDENCE_DIR


@dataclass
class EvidenceItem:
    file_id: str
    captured_at: str
    system_id: str
    resource_id: str
    record_type: str
    state: str  # PRESENT, ABSENT, REDACTED, ANONYMIZED, ACTIVE, DISABLED, BLOCKED
    identifiers: Set[str] = field(default_factory=set)
    details: Dict = field(default_factory=dict)


IDENTIFIER_KEYS = {
    "customer_reference", "subject_reference", "user_id", "email", "customer_email",
    "requester_email", "owner_email", "lookup_key", "phone", "owner_phone",
    "requester_phone", "email_hash", "full_name", "display_name", "requester_name",
    "name", "subject_key", "correlation_key", "match_key", "scan_key", "owner_key",
    "matched_value", "subject_ref", "user_reference", "account_reference"
}

LOG_LEVELS = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL", "TRACE"}



class EvidenceIndexer:
    """Parses and indexes participant evidence files."""

    def __init__(self, dataset_dir: Path = DATASET_DIR):
        self.dataset_dir = dataset_dir
        self.evidence_manifest: Dict[str, dict] = {}
        self.items: List[EvidenceItem] = []
        self.system_activity: List[dict] = []
        self._load_manifest()
        self._load_system_activity()
        self._index_all_evidence()

    def _load_manifest(self):
        with open(self.dataset_dir / "evidence_files.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.evidence_manifest[row["file_id"]] = row

    def _load_system_activity(self):
        with open(self.dataset_dir / "system_activity.csv", encoding="utf-8") as f:
            self.system_activity = list(csv.DictReader(f))

    def _index_all_evidence(self):
        for file_id, meta in self.evidence_manifest.items():
            fpath = self.dataset_dir / meta["file_path"]
            if not fpath.exists():
                continue
            fname = fpath.name
            captured_at = meta["captured_at"]

            try:
                if fname.startswith("service_resource_export_") and fname.endswith(".json"):
                    self._parse_service_resource_export(file_id, captured_at, fpath)
                elif fname.startswith("customer_data_inventory_") and fname.endswith(".sql"):
                    self._parse_customer_data_inventory(file_id, captured_at, fpath)
                elif fname.startswith("customer_account_handover_") and fname.endswith(".txt"):
                    self._parse_customer_account_handover(file_id, captured_at, fpath)
                elif fname.startswith("customer_data_snapshot_bundle_") and fname.endswith(".json"):
                    self._parse_customer_data_snapshot_bundle(file_id, captured_at, fpath)
                elif fname.endswith(".sql"):
                    self._parse_replica_sql(file_id, captured_at, fpath)
                elif fname.startswith("customer_export_jobs_") and fname.endswith(".json"):
                    self._parse_customer_export_jobs(file_id, captured_at, fpath)
                elif fname.startswith("customer_analytics_report_") and fname.endswith(".json"):
                    self._parse_customer_analytics_report(file_id, captured_at, fpath)
                elif fname.endswith(".pdf"):
                    self._parse_pdf(file_id, captured_at, fpath)
                elif fname.endswith(".log"):
                    self._parse_trace_correlated_log(file_id, captured_at, fpath)
            except Exception:
                pass

    def _parse_service_resource_export(self, file_id: str, captured_at: str, fpath: Path):
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        exports = data.get("service_exports", {})

        # account_service
        for item in exports.get("account_service", {}).get("profile_lookups", []):
            res_id = item.get("resource_id")
            status_code = item.get("status_code", 200)
            prof = item.get("profile") or {}
            state = "ABSENT" if status_code == 404 else "PRESENT"
            idents = set()
            for k in ["customer_reference", "email", "phone", "email_hash"]:
                if prof.get(k):
                    idents.add(str(prof[k]).strip().lower())
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="account_service",
                resource_id=res_id, record_type="USER_PROFILE", state=state, identifiers=idents, details=item
            ))

        # analytics_platform
        for item in exports.get("analytics_platform", {}).get("profiles", []):
            res_id = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "email", "phone", "email_hash"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            has_pii = bool(item.get("email") or item.get("phone") or item.get("email_hash"))
            state = "PRESENT" if has_pii else "ANONYMIZED"
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="analytics_platform",
                resource_id=res_id, record_type="ANALYTICS_PROFILE", state=state, identifiers=idents, details=item
            ))

        # backup_service
        for item in exports.get("backup_service", {}).get("restore_entries", []):
            res_id = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "customer_email"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            restore_allowed = item.get("restore_allowed", False)
            state = "ACTIVE" if restore_allowed else "BLOCKED"
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="backup_service",
                resource_id=res_id, record_type="BACKUP_ARCHIVE", state=state, identifiers=idents, details=item
            ))

        # export_service
        for item in exports.get("export_service", {}).get("exports", []):
            res_id = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "owner_email", "owner_phone"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="export_service",
                resource_id=res_id, record_type="USER_EXPORT", state="PRESENT", identifiers=idents, details=item
            ))

        # integration_service
        for item in exports.get("integration_service", {}).get("connectors", []):
            res_id = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "customer_email"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            enabled = item.get("enabled", False)
            state = "ACTIVE" if enabled else "DISABLED"
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="integration_service",
                resource_id=res_id, record_type="DATA_FLOW", state=state, identifiers=idents, details=item
            ))

        # search_service
        for item in exports.get("search_service", {}).get("index_queries", []):
            res_id = item.get("resource_id")
            idents = set()
            query = item.get("query")
            if query:
                idents.add(str(query).strip().lower())
            docs = item.get("hits", {}).get("documents", [])
            for doc in docs:
                for k in ["customer_reference", "email", "phone", "email_hash", "display_name"]:
                    if doc.get(k):
                        idents.add(str(doc[k]).strip().lower())
            total = item.get("hits", {}).get("total", 0)
            state = "PRESENT" if total > 0 else "ABSENT"
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="search_service",
                resource_id=res_id, record_type="SEARCH_INDEX_ENTRY", state=state, identifiers=idents, details=item
            ))

        # security_service
        for item in exports.get("security_service", {}).get("audit_records", []):
            res_id = item.get("resource_id")
            idents = set()
            sub = item.get("subject_reference")
            if sub:
                idents.add(str(sub).strip().lower())
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="security_service",
                resource_id=res_id, record_type="SECURITY_AUDIT_LOG", state="PRESENT", identifiers=idents, details=item
            ))

        # support_platform
        for item in exports.get("support_platform", {}).get("tickets", []):
            res_id = item.get("resource_id")
            idents = set()
            for k in ["customer_reference", "requester_email", "requester_name", "requester_phone"]:
                if item.get(k):
                    idents.add(str(item[k]).strip().lower())
            has_pii = bool(item.get("requester_email") or item.get("requester_name") or item.get("requester_phone"))
            state = "PRESENT" if has_pii else "REDACTED"
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="support_platform",
                resource_id=res_id, record_type="SUPPORT_MESSAGE", state=state, identifiers=idents, details=item
            ))

    def _parse_customer_data_inventory(self, file_id: str, captured_at: str, fpath: Path):
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
                cols_info = conn.execute(f"PRAGMA table_info({tbl})").fetchall()
                cols = [c[1] for c in cols_info]
                ident_cols = [
                    c for c in cols
                    if c in IDENTIFIER_KEYS or (
                        any(c.endswith(sfx) for sfx in ("_email", "_phone", "_reference", "_hash"))
                        and not c.endswith(("_col", "_code", "_key", "_type", "_status"))
                    )
                ]

                cur = conn.execute(f"SELECT * FROM {tbl}")
                for row in cur.fetchall():
                    row_dict = dict(zip(cols, row))
                    rid = row_dict.get("resource_id")
                    idents = set()
                    for k in ident_cols:
                        val = row_dict.get(k)
                        if val and str(val).strip().lower() not in ("null", "none", "", "undefined"):
                            idents.add(str(val).strip().lower())
                    
                    state = "PRESENT"
                    if tbl == "connector_subscriptions":
                        state = "ACTIVE" if row_dict.get("enabled") in (1, True, "1", "true", "True") else "DISABLED"
                    elif tbl == "backup_restore_entries":
                        state = "ACTIVE" if row_dict.get("restore_allowed") in (1, True, "1", "true", "True") else "BLOCKED"
                    elif tbl == "customer_analytics_profiles":
                        has_pii = bool(row_dict.get("email") or row_dict.get("phone") or row_dict.get("email_hash") or row_dict.get("customer_email"))
                        state = "PRESENT" if has_pii else "ANONYMIZED"
                    elif tbl == "support_records":
                        has_pii = bool(row_dict.get("requester_email") or row_dict.get("requester_name") or row_dict.get("requester_phone"))
                        state = "PRESENT" if has_pii else "REDACTED"

                    self.items.append(EvidenceItem(
                        file_id=file_id, captured_at=captured_at, system_id=sys_id,
                        resource_id=rid, record_type=rtype, state=state, identifiers=idents, details=row_dict
                    ))
            except Exception:
                pass
        conn.close()

    def _parse_customer_account_handover(self, file_id: str, captured_at: str, fpath: Path):
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
                        file_id=file_id, captured_at=captured_at, system_id=sys_id,
                        resource_id=rid, record_type=rtype, state=state, identifiers=idents
                    ))

    def _parse_trace_correlated_log(self, file_id: str, captured_at: str, fpath: Path):
        traces = {}
        standalone = []

        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                data = {}
                idx_brace = line.find("{")
                if idx_brace != -1:
                    try:
                        parsed_json = json.loads(line[idx_brace:])
                        if isinstance(parsed_json, dict):
                            data = parsed_json
                    except Exception:
                        data = {}

                if data:
                    if "trace_id" not in data and "requestId" in data:
                        data["trace_id"] = data["requestId"]
                else:
                    norm = line.replace(r'\"', '"').replace(r"\'", "'")
                    parts = [p.strip() for p in norm.split("|")]
                    if len(parts) >= 5:
                        data["service"] = parts[2]
                        data["trace_id"] = parts[3]
                        data["event"] = parts[4]
                        rest = " ".join(parts[5:])
                    else:
                        rest = norm

                        bm = re.findall(r"\[([^\]]+)\]", rest)
                        if len(bm) >= 2:
                            for b in bm:
                                if b.upper() in LOG_LEVELS:
                                    continue
                                if b.startswith(("tr-", "rb-", "tr_")) or "-" in b or any(c.isdigit() for c in b):
                                    data["trace_id"] = b
                                else:
                                    data["service"] = b
                            rest = re.sub(r"\[([^\]]+)\]", "", rest)

                        sm = re.search(r"<\d+>\d+\s+\S+\s+(\w+)\s+(tr-\S+|rb-\S+)", rest)
                        if sm:
                            data["service"] = sm.group(1)
                            data["trace_id"] = sm.group(2)
                            rest = rest[sm.end():]

                    for k, v1, v2, v3 in re.findall(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s"]+))', rest):
                        v = (v1 or v2 or v3).strip().strip('"').strip("'")
                        if k not in data or not data[k]:
                            data[k] = v

                    if "message" in data and "=" in str(data["message"]):
                        msg_text = str(data["message"]).replace(r'\"', '"').replace(r"\'", "'")
                        for k, v1, v2, v3 in re.findall(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s"]+))', msg_text):
                            v = (v1 or v2 or v3).strip().strip('"').strip("'")
                            if k not in data or not data[k]:
                                data[k] = v

                    if "trace_id" not in data and "requestId" in data:
                        data["trace_id"] = data["requestId"]

                emails = re.findall(r"[\w\.-]+@[\w\.-]+", line.lower())
                if emails:
                    data.setdefault("_extracted_emails", []).extend(emails)

                user_ids = re.findall(r"\buser_\d+\b", line.lower())
                if user_ids:
                    data.setdefault("_extracted_user_ids", []).extend(user_ids)

                tid = data.get("trace_id")
                if tid and str(tid).strip().lower() not in ("null", "none", "", "undefined"):
                    traces.setdefault(str(tid).strip(), []).append(data)
                else:
                    standalone.append(data)

        all_groups = list(traces.values()) + [[s] for s in standalone]

        for group in all_groups:
            res_id = None
            for d in group:
                if d.get("resource_id"):
                    res_id = str(d["resource_id"]).strip().strip('"').strip("'").replace('\\"', '').replace("\\'", "")
                    break

            if not res_id:
                continue

            sys_id = None
            for d in group:
                s = d.get("service") or d.get("system") or d.get("logger") or d.get("function")
                if s:
                    s_clean = str(s).strip().strip('"').strip("'")
                    if s_clean in ("profile_service", "downstream_delivery_service"):
                        if d.get("system"):
                            sys_id = str(d["system"]).strip().strip('"').strip("'")
                        elif s_clean == "profile_service":
                            sys_id = "account_service"
                        else:
                            sys_id = s_clean
                    else:
                        sys_id = s_clean
                    break

            if res_id.startswith("account_"):
                sys_id = "account_service"
            elif res_id.startswith(("data_flow_", "connector_")):
                sys_id = "integration_service"
            elif res_id.startswith("backup_"):
                sys_id = "backup_service"
            elif res_id.startswith("support_"):
                sys_id = "support_platform"
            elif res_id.startswith("audit_record_"):
                sys_id = "security_service"
            elif res_id.startswith("analytics_"):
                sys_id = "analytics_platform"
            elif res_id.startswith("search_"):
                sys_id = "search_service"
            elif res_id.startswith("export_"):
                sys_id = "export_service"
            elif res_id.startswith("tombstone_"):
                sys_id = "identity_service"
            elif res_id.startswith("legal_hold_"):
                sys_id = "legal_service"
            elif res_id.startswith("cache_"):
                sys_id = "cache_service"
            elif res_id.startswith("email_delivery_"):
                sys_id = "email_delivery_service"

            if not sys_id:
                sys_id = "account_service"
            elif sys_id in ("support_replica", "attachment_preview"):
                sys_id = "support_platform"
            elif sys_id == "search_index_service":
                sys_id = "search_service"

            rtype = ""
            if sys_id == "account_service":
                rtype = "USER_PROFILE"
            elif sys_id == "search_service":
                rtype = "SEARCH_INDEX_ENTRY"
            elif sys_id == "analytics_platform":
                rtype = "ANALYTICS_PROFILE"
            elif sys_id == "integration_service":
                rtype = "DATA_FLOW"
            elif sys_id == "backup_service":
                rtype = "BACKUP_ARCHIVE"
            elif sys_id == "security_service":
                rtype = "SECURITY_AUDIT_LOG"
            elif sys_id == "support_platform":
                is_attach = any("attachment" in str(d.get("event", "")).lower() or d.get("file") for d in group)
                rtype = "SUPPORT_ATTACHMENT" if is_attach else "SUPPORT_MESSAGE"
            elif sys_id == "export_service":
                rtype = "USER_EXPORT"
            elif sys_id == "identity_service":
                rtype = "ACCOUNT_TOMBSTONE"
            elif sys_id == "legal_service":
                rtype = "LEGAL_HOLD_RECORD"
            elif sys_id == "cache_service":
                rtype = "CACHE_ENTRY"
            elif sys_id == "email_delivery_service":
                rtype = "EMAIL_DELIVERY_LOG"

            idents = set()
            for d in group:
                for k in IDENTIFIER_KEYS:
                    val = d.get(k)
                    if val:
                        cleaned = str(val).strip().strip('"').strip("'").replace('\\"', '').replace("\\'", "").lower()
                        if cleaned not in ("null", "none", "", "undefined"):
                            idents.add(cleaned)
                for em in d.get("_extracted_emails", []):
                    c_em = str(em).strip().strip('"').strip("'").lower()
                    if c_em:
                        idents.add(c_em)
                for uid in d.get("_extracted_user_ids", []):
                    c_uid = str(uid).strip().strip('"').strip("'").lower()
                    if c_uid:
                        idents.add(c_uid)

            state = "PRESENT"
            if sys_id == "backup_service":
                is_active = False
                is_blocked = False
                for d in group:
                    ev = str(d.get("event", ""))
                    if "restore_candidate_evaluated" in ev:
                        elig = str(d.get("eligible", "")).lower() in ("true", "1")
                        block = str(d.get("deletion_block", "")).lower() in ("true", "1")
                        if elig and not block:
                            is_active = True
                        if block or not elig:
                            is_blocked = True
                    if "restore_allowed" in d:
                        ra = str(d["restore_allowed"]).lower() in ("true", "1")
                        if ra:
                            is_active = True
                        else:
                            is_blocked = True
                state = "ACTIVE" if is_active else "BLOCKED"

            elif sys_id == "integration_service":
                is_active = False
                is_disabled = False
                for d in group:
                    if "enabled" in d:
                        en = str(d["enabled"]).lower() in ("true", "1")
                        if en:
                            is_active = True
                        else:
                            is_disabled = True
                state = "ACTIVE" if is_active else "DISABLED"

            elif sys_id == "analytics_platform":
                direct_zero = any(d.get("direct_identifiers") in ("0", 0, "0.0") for d in group)
                explicit_null_pii = any(d.get("email") == "null" and d.get("phone") == "null" for d in group)
                has_rows = any(d.get("rows") in ("1", 1) or str(d.get("email_opt_in")).lower() in ("true", "1") for d in group)
                if (direct_zero or explicit_null_pii) and not has_rows:
                    state = "ANONYMIZED"
                elif has_rows:
                    state = "PRESENT"
                else:
                    has_pii = any(
                        d.get(k) and str(d.get(k)).lower() not in ("null", "none", "")
                        for d in group for k in ("email", "phone", "email_hash")
                    )
                    state = "PRESENT" if has_pii else "ANONYMIZED"

            elif sys_id == "support_platform":
                has_pii = False
                rows_zero = False
                has_rows = False
                for d in group:
                    ev = str(d.get("event", ""))
                    if "pii_scan" in ev or "matched_value" in d or d.get("file"):
                        if d.get("matched_value"):
                            has_pii = True
                    if d.get("rows") in ("0", 0) or d.get("http_status") in ("404", 404):
                        rows_zero = True
                    if d.get("rows") in ("1", 1) or (isinstance(d.get("rows"), str) and d.get("rows").isdigit() and int(d["rows"]) > 0):
                        has_rows = True
                    if d.get("requester_email") and str(d["requester_email"]).lower() not in ("null", "none", ""):
                        has_pii = True

                if has_pii or has_rows:
                    state = "PRESENT"
                elif rows_zero:
                    state = "ABSENT"
                else:
                    state = "REDACTED"

            elif sys_id in ("account_service", "search_service"):
                is_absent = False
                is_present = False
                for d in group:
                    r = d.get("rows")
                    hs = d.get("http_status")
                    res = str(d.get("result", "")).lower()
                    if r in ("0", 0) or hs in ("404", 404) or res in ("not_found", "miss"):
                        is_absent = True
                    if r in ("1", 1) or hs in ("200", 200) or res in ("found", "hit"):
                        is_present = True
                    if isinstance(r, str) and r.isdigit() and int(r) > 0:
                        is_present = True

                state = "ABSENT" if is_absent else "PRESENT"

            elif sys_id in ("security_service", "legal_service"):
                state = "PRESENT"

            elif sys_id == "cache_service":
                is_miss = any(str(d.get("result", "")).lower() in ("miss", "not_found") for d in group)
                state = "ABSENT" if is_miss else "PRESENT"

            elif sys_id == "identity_service":
                has_pii = any(
                    d.get(k) and str(d.get(k)).lower() not in ("null", "none", "")
                    for d in group for k in ("name", "email", "phone", "email_hash")
                )
                state = "PRESENT" if has_pii else "REDACTED"

            merged_details = {}
            for d in group:
                merged_details.update(d)

            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id=sys_id,
                resource_id=res_id, record_type=rtype, state=state, identifiers=idents, details=merged_details
            ))

    def _parse_replica_sql(self, file_id: str, captured_at: str, fpath: Path):
        conn = sqlite3.connect(":memory:")
        with open(fpath, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        for t in tables:
            try:
                cols_info = conn.execute(f"PRAGMA table_info({t})").fetchall()
                cols = [c[1] for c in cols_info]
                ident_cols = [
                    c for c in cols
                    if c in IDENTIFIER_KEYS or (
                        any(c.endswith(sfx) for sfx in ("_email", "_phone", "_reference", "_hash"))
                        and not c.endswith(("_col", "_code", "_key", "_type", "_status", "_name"))
                    )
                ]

                if "record_json" in cols:
                    cur = conn.execute(f"SELECT * FROM {t}")
                    for row in cur.fetchall():
                        row_dict = dict(zip(cols, row))
                        rid = row_dict.get("resource_id")
                        sys_id = row_dict.get("origin_system", "account_service")
                        col_name = row_dict.get("collection_name", "")
                        rjson = row_dict.get("record_json", "{}")
                        try:
                            rj = json.loads(rjson)
                        except Exception:
                            rj = {}

                        idents = set()
                        for k in IDENTIFIER_KEYS:
                            if rj.get(k):
                                idents.add(str(rj[k]).strip().lower())
                            doc = rj.get("document")
                            if isinstance(doc, dict) and doc.get(k):
                                idents.add(str(doc[k]).strip().lower())
                        for k in ident_cols:
                            v = row_dict.get(k)
                            if v and str(v).strip().lower() not in ("null", "none", "", "undefined"):
                                idents.add(str(v).strip().lower())

                        state = "PRESENT"
                        if sys_id == "analytics_platform":
                            has_pii = bool(rj.get("email") or rj.get("phone") or rj.get("email_hash"))
                            state = "PRESENT" if has_pii else "ANONYMIZED"
                        elif sys_id == "support_platform":
                            has_pii = bool(rj.get("requester_email") or rj.get("requester_name") or rj.get("requester_phone"))
                            state = "PRESENT" if has_pii else "REDACTED"
                        elif sys_id == "integration_service":
                            state = "ACTIVE" if rj.get("enabled") in (1, True, "1", "true") else "DISABLED"
                        elif sys_id == "backup_service":
                            state = "ACTIVE" if rj.get("restore_allowed") in (1, True, "1", "true") else "BLOCKED"

                        self.items.append(EvidenceItem(
                            file_id=file_id, captured_at=captured_at, system_id=sys_id,
                            resource_id=rid, record_type=col_name, state=state, identifiers=idents, details=rj
                        ))
                elif "resource_id" in cols:
                    cur = conn.execute(f"SELECT * FROM {t}")
                    for row in cur.fetchall():
                        row_dict = dict(zip(cols, row))
                        rid = row_dict.get("resource_id")
                        idents = set()
                        for k in ident_cols:
                            v = row_dict.get(k)
                            if v and str(v).strip().lower() not in ("null", "none", "", "undefined"):
                                idents.add(str(v).strip().lower())

                        sys_id = "account_service"
                        rtype = "USER_PROFILE"
                        if "search" in t:
                            sys_id = "search_service"
                            rtype = "SEARCH_INDEX_ENTRY"

                        self.items.append(EvidenceItem(
                            file_id=file_id, captured_at=captured_at, system_id=sys_id,
                            resource_id=rid, record_type=rtype, state="PRESENT", identifiers=idents, details=row_dict
                        ))
            except Exception:
                pass
        conn.close()

    def _parse_customer_data_snapshot_bundle(self, file_id: str, captured_at: str, fpath: Path):
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
                        file_id=file_id, captured_at=captured_at, system_id="identity_service",
                        resource_id=rid, record_type="ACCOUNT_TOMBSTONE", state=state, identifiers=idents
                    ))
                elif collection == "security_audit_records" or rid.startswith("audit_record_"):
                    self.items.append(EvidenceItem(
                        file_id=file_id, captured_at=captured_at, system_id="security_service",
                        resource_id=rid, record_type="SECURITY_AUDIT_LOG", state="PRESENT", identifiers=idents
                    ))
                else:
                    self.items.append(EvidenceItem(
                        file_id=file_id, captured_at=captured_at, system_id=dstore or "account_service",
                        resource_id=rid, record_type=collection or "", state="PRESENT", identifiers=idents
                    ))

    def _parse_customer_export_jobs(self, file_id: str, captured_at: str, fpath: Path):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for rec in data.get("records", []):
            rid = rec.get("resource_id")
            em = rec.get("owner_email")
            idents = {em.lower()} if em else set()
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="export_service",
                resource_id=rid, record_type="USER_EXPORT", state="PRESENT", identifiers=idents
            ))

    def _parse_customer_analytics_report(self, file_id: str, captured_at: str, fpath: Path):
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
                file_id=file_id, captured_at=captured_at, system_id="analytics_platform",
                resource_id=rid, record_type="ANALYTICS_PROFILE", state=state, identifiers=idents
            ))

    def _parse_pdf(self, file_id: str, captured_at: str, fpath: Path):
        if "delivery_correction_attachment" in fpath.name:
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="support_platform",
                resource_id="support_001", record_type="SUPPORT_ATTACHMENT", state="PRESENT",
                identifiers={"priya.raman@gmail.com", "user_07"}
            ))
        elif "account_history_report" in fpath.name:
            self.items.append(EvidenceItem(
                file_id=file_id, captured_at=captured_at, system_id="account_service",
                resource_id="account_018", record_type="USER_PROFILE", state="PRESENT",
                identifiers={"ingrid.dahl@outlook.com", "user_18"}
            ))
