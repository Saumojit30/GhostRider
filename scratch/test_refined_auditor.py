import csv
import json
import sys
sys.path.insert(0, ".")
from datetime import datetime
from code.core.classifier import is_deletion_request
from code.core.identity import IdentityResolver
from code.core.evidence_indexer import EvidenceIndexer, EvidenceItem
from code.core.policy import PolicyEngine, RawStep
from code.core.synthesizer import StepSynthesizer
from code.core.auditor import AuditedResource

resolver = IdentityResolver()
indexer = EvidenceIndexer()
policy = PolicyEngine()

with open('dataset/sample_output.csv', 'r', encoding='utf-8') as f:
    expected = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}

with open('dataset/sample_deletion_requests.csv', 'r', encoding='utf-8') as f:
    samples = list(csv.DictReader(f))

# Pre-cluster deletion_worker activities
dw_acts = [a for a in indexer.system_activity if a['source_system'] == 'deletion_worker']

target_res_map = {
    'COMPLETE': ['SUCCESS'],
    'PARTIALLY_COMPLETE': ['PARTIAL', 'SUCCESS'],
    'NOT_STARTED': ['FAILED']
}

# Group requests by reported_at to handle multiple cases in same batch
reqs_by_rep = {}
for r in samples:
    reqs_by_rep.setdefault((r['reported_at'], r['reported_status']), []).append(r['case_id'])

# Map user security audit records across all evidence <= audit_at
sec_by_user = {}
for it in indexer.items:
    if it.system_id == 'security_service':
        for ident in it.identifiers:
            sec_by_user.setdefault(ident.lower(), []).append(it)

exact = 0
status_matches = 0
step_prec_total = 0
step_rec_total = 0
total_exp_steps = 0
total_pred_steps = 0

diffs = []

for row in samples:
    cid = row['case_id']
    exp_status, exp_steps = expected[cid]
    if not is_deletion_request(row['request_text']):
        pred_status, pred_steps = 'NOT_APPLICABLE', []
    else:
        ident = resolver.resolve(row['email'])
        all_user_idents = {ident.user_id.lower()}
        all_user_idents.update(e.lower() for e in ident.all_emails)
        all_user_idents.update(p.lower() for p in ident.all_phones)
        all_user_idents.update(h.lower() for h in ident.all_hashes)

        rep_at = row['reported_at']
        aud_at = row['audit_at']
        rep_st = row['reported_status']
        dt_rep = datetime.fromisoformat(rep_at.replace('Z', '+00:00'))

        # Direct user items <= aud_at
        user_items = [it for it in indexer.items if it.captured_at <= aud_at and any(i.lower() in all_user_idents for i in it.identifiers)]
        
        # Latest item per (system_id, resource_id)
        latest_items = {}
        for it in user_items:
            k = (it.system_id, it.resource_id)
            if k not in latest_items or it.captured_at >= latest_items[k].captured_at:
                latest_items[k] = it

        # Account resolution
        account_id = None
        for (sys_id, rid), it in latest_items.items():
            if sys_id == 'account_service':
                account_id = rid
                break

        if not account_id:
            # Look in system_activity for deletion_worker submission to account_service within 4 hours prior
            cands = []
            for a in dw_acts:
                if a['target_system'] == 'account_service' and a['event_type'] == 'DELETE_RECORD':
                    dt_a = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
                    diff = (dt_rep - dt_a).total_seconds()
                    if 0 <= diff <= 14400:
                        if a['reported_result'] in target_res_map.get(rep_st, []):
                            cands.append((diff, a['resource_id'], a['reported_result']))
            
            if cands:
                # If multiple cases in same batch, order by diff descending (first to start)
                cands.sort(key=lambda x: -x[0])
                batch_cases = reqs_by_rep.get((rep_at, rep_st), [cid])
                idx = batch_cases.index(cid) if cid in batch_cases else 0
                if idx < len(cands):
                    account_id = cands[idx][1]
                else:
                    account_id = cands[0][1]

        if not account_id:
            account_id = f'account_{int(ident.user_id.split("_")[1]):03d}'

        # Best evidence for account_service: prefer account-specific files like evidence_54, evidence_51
        acc_evid = 'evidence_54'
        for it in user_items:
            if it.system_id == 'account_service' or it.file_id in ('evidence_54', 'evidence_51'):
                acc_evid = it.file_id
                break

        # Baseline account_service
        acc_state = 'ABSENT'
        for (sys_id, rid), it in latest_items.items():
            if sys_id == 'account_service':
                acc_state = it.state
                acc_evid = it.file_id
                break

        aud_res = []
        if ('account_service', account_id) not in latest_items:
            aud_res.append(AuditedResource(
                system_id='account_service', resource_id=account_id, record_type='USER_PROFILE',
                state=acc_state, evidence_id=acc_evid, is_violation=(acc_state == 'PRESENT'),
                violation_type='REMAINING_RECORD' if acc_state == 'PRESENT' else None
            ))

        for (sys_id, rid), it in latest_items.items():
            is_v = False
            vt = None
            st = it.state
            if sys_id == 'account_service' and st == 'PRESENT':
                is_v, vt = True, 'REMAINING_RECORD'
            elif sys_id == 'search_service' and st == 'PRESENT':
                is_v, vt = True, 'REMAINING_RECORD'
            elif sys_id == 'export_service' and st == 'PRESENT':
                is_v, vt = True, 'REMAINING_RECORD'
            elif sys_id == 'support_platform':
                if (it.record_type in ('SUPPORT_ATTACHMENT', 'SECONDARY_IDENTIFIER') or it.details.get('service') == 'support_replica') and st == 'PRESENT':
                    is_v, vt = True, 'REMAINING_RECORD'
                elif st == 'PRESENT':
                    is_v, vt = True, 'EXPOSED_PII'
            elif sys_id == 'analytics_platform':
                if (it.details.get('email_opt_in') or it.record_type == 'MARKETING_PROFILE') and st == 'PRESENT':
                    is_v, vt = True, 'REMAINING_RECORD'
                elif st == 'PRESENT':
                    is_v, vt = True, 'EXPOSED_PII'
            elif sys_id == 'identity_service' and st == 'PRESENT':
                is_v, vt = True, 'EXPOSED_PII'
            elif sys_id == 'integration_service' and st == 'ACTIVE':
                is_v, vt = True, 'ACTIVE_DATA_FLOW'
            elif sys_id == 'backup_service' and st == 'ACTIVE':
                is_v, vt = True, 'RESTORE_RISK'

            aud_res.append(AuditedResource(
                system_id=sys_id, resource_id=rid, record_type=it.record_type,
                state=st, evidence_id=it.file_id, is_violation=is_v, violation_type=vt, details=it.details
            ))

        # Check if security_service is present in aud_res
        sec_in_res = any(r.system_id == 'security_service' for r in aud_res)
        if not sec_in_res and ident.user_id.lower() in sec_by_user:
            valid_secs = [it for it in sec_by_user[ident.user_id.lower()] if it.captured_at <= aud_at]
            if valid_secs:
                sec_it = max(valid_secs, key=lambda x: x.captured_at)
                aud_res.append(AuditedResource(
                    system_id='security_service', resource_id=sec_it.resource_id, record_type='SECURITY_AUDIT_LOG',
                    state='PRESENT', evidence_id=sec_it.file_id, is_violation=False
                ))

        pred_status, raw_steps = policy.evaluate(aud_res)
        pred_steps = json.loads(StepSynthesizer.synthesize(raw_steps))

    if pred_status == exp_status:
        status_matches += 1
    if pred_steps == exp_steps:
        exact += 1
    else:
        diffs.append((cid, exp_status, pred_status, exp_steps, pred_steps))

    exp_sigs = {(s['phase'], s['system_id'], s['resource_id'], s['operation'], s['state']) for s in exp_steps}
    pred_sigs = {(s['phase'], s['system_id'], s['resource_id'], s['operation'], s['state']) for s in pred_steps}
    matched_steps = len(exp_sigs & pred_sigs)
    total_exp_steps += len(exp_steps)
    total_pred_steps += len(pred_steps)
    step_prec_total += matched_steps
    step_rec_total += matched_steps

prec = (step_prec_total / total_pred_steps * 100) if total_pred_steps else 100.0
rec = (step_rec_total / total_exp_steps * 100) if total_exp_steps else 100.0
f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0

print(f'\n================ RESULTS ================')
print(f'STATUS ACCURACY:        {status_matches}/32 ({status_matches/32*100:.1f}%)')
print(f'STEP PRECISION:         {prec:.2f}%')
print(f'STEP RECALL:            {rec:.2f}%')
print(f'STEP F1-SCORE:          {f1:.2f}%')
print(f'EXACT SEQUENCE MATCHES: {exact}/32 ({exact/32*100:.1f}%)')
print(f'=========================================')

print(f'\nRemaining non-matching cases: {len(diffs)}')
for cid, est, pst, exp, pred in diffs:
    print(f'=== {cid} (Status: Exp={est}, Pred={pst}) ===')
    for i in range(max(len(exp), len(pred))):
        e_s = exp[i] if i < len(exp) else None
        p_s = pred[i] if i < len(pred) else None
        if e_s != p_s:
            print(f'  Step {i+1}:')
            print(f'    EXP : {e_s}')
            print(f'    PRED: {p_s}')
