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
clusters = []
curr = []
for a in dw_acts:
    if not curr:
        curr.append(a)
    else:
        t0 = datetime.fromisoformat(curr[-1]['event_time'].replace('Z', '+00:00'))
        t1 = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
        if (t1 - t0).total_seconds() > 900:
            clusters.append(curr)
            curr = [a]
        else:
            curr.append(a)
if curr:
    clusters.append(curr)

items_by_res = {}
for it in indexer.items:
    items_by_res.setdefault(it.resource_id, []).append(it)

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

        user_anchors = {it.resource_id for it in latest_items.values() if it.resource_id and it.system_id != 'account_service'}

        # Find best matching cluster around rep_at
        matched_cluster = None
        for c in clusters:
            if any(a['resource_id'] in user_anchors for a in c):
                t_mid = datetime.fromisoformat(c[0]['event_time'].replace('Z', '+00:00'))
                if abs((t_mid - dt_rep).total_seconds()) <= 10800:
                    matched_cluster = c
                    break
        
        if not matched_cluster:
            cands = []
            for c in clusters:
                t_mid = datetime.fromisoformat(c[0]['event_time'].replace('Z', '+00:00'))
                diff = abs((t_mid - dt_rep).total_seconds())
                if diff <= 7200:
                    cands.append((diff, c))
            if cands:
                cands.sort(key=lambda x: x[0])
                matched_cluster = cands[0][1]

        cluster = matched_cluster if matched_cluster else []

        # Account resolution
        account_id = None
        for (sys_id, rid), it in latest_items.items():
            if sys_id == 'account_service':
                account_id = rid
                break

        if not account_id and cluster:
            acc_cands = [a for a in cluster if a['target_system'] == 'account_service' and a['event_type'] == 'DELETE_RECORD']
            if len(acc_cands) == 1:
                account_id = acc_cands[0]['resource_id']
            elif len(acc_cands) > 1:
                target_res = {'COMPLETE': ['SUCCESS'], 'PARTIALLY_COMPLETE': ['PARTIAL', 'SUCCESS'], 'NOT_STARTED': ['FAILED']}[rep_st]
                matching_res = [a for a in acc_cands if a['reported_result'] in target_res]
                
                tomb = next((it.resource_id for it in latest_items.values() if it.system_id == 'identity_service'), None)
                matched_acc = None
                if tomb:
                    tomb_acts = [a for a in cluster if a['target_system'] == 'identity_service']
                    if tomb_acts:
                        idx = next((i for i, a in enumerate(tomb_acts) if a['resource_id'] == tomb), 0)
                        if idx < len(matching_res):
                            matched_acc = matching_res[idx]['resource_id']
                            
                if not matched_acc and user_anchors:
                    anchor_acts = [a for a in cluster if a['resource_id'] in user_anchors]
                    if anchor_acts:
                        anc_t = datetime.fromisoformat(anchor_acts[0]['event_time'].replace('Z', '+00:00'))
                        matching_res.sort(key=lambda a: abs((datetime.fromisoformat(a['event_time'].replace('Z', '+00:00')) - anc_t).total_seconds()))
                        matched_acc = matching_res[0]['resource_id']
                        
                if matched_acc: account_id = matched_acc
                elif matching_res: account_id = matching_res[0]['resource_id']
                else: account_id = acc_cands[0]['resource_id']

        if not account_id:
            account_id = f'account_{int(ident.user_id.split("_")[1]):03d}'

        # Anonymized analytics stitching
        if cluster:
            ana_acts = [a for a in cluster if a['target_system'] == 'analytics_platform' and a['event_type'] == 'ANONYMIZE_RECORD' and a['reported_result'] == 'SUCCESS']
            if ana_acts:
                matched_ana = None
                if len(ana_acts) == 1:
                    matched_ana = ana_acts[0]['resource_id']
                else:
                    acc_acts = [a for a in cluster if a['target_system'] == 'account_service']
                    acc_idx = next((i for i, a in enumerate(acc_acts) if a['resource_id'] == account_id), 0)
                    if acc_idx < len(ana_acts):
                        matched_ana = ana_acts[acc_idx]['resource_id']
                if matched_ana and matched_ana in items_by_res:
                    v_its = [it for it in items_by_res[matched_ana] if it.captured_at <= aud_at]
                    if v_its:
                        latest_items[('analytics_platform', matched_ana)] = max(v_its, key=lambda x: x.captured_at)

        # Baseline account_service
        primary_file = max((it.file_id for it in latest_items.values()), default='evidence_54')
        acc_state = 'ABSENT'
        acc_evid = primary_file
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
