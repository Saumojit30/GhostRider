import sys
sys.path.insert(0, ".")
from code.core.identity import IdentityResolver
from scratch.enhanced_indexer import EnhancedIndexer
from scratch.clean_auditor import CleanAuditor

resolver = IdentityResolver()
indexer = EnhancedIndexer()
auditor = CleanAuditor(indexer)

ident = resolver.resolve("smartinez6461@gmail.com")
res = auditor.audit_case("smartinez6461@gmail.com", "2026-09-15T12:00:00Z", "2026-08-30T12:00:00Z", ident)
print(f"Resources found for case_28 ({len(res)}):")
for r in res:
    print(" ", r["system_id"], r["resource_id"], r["state"], r["evidence_id"])
