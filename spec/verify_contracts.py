#!/usr/bin/env python3
"""Transparent, bounded checks of the review artifact, not tests of a deployed keel.
No network, device access, third party libraries or configuration side effects.
"""
import copy, hashlib, json, sys
from collections import deque
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parent

def merge(base,patch):
    result=copy.deepcopy(base)
    for key,value in patch.items():
        if isinstance(value,dict) and isinstance(result.get(key),dict):result[key]=merge(result[key],value)
        else:result[key]=copy.deepcopy(value)
    return result

def admission(x,mutant=None):
    e,q,now=x['evidence'],x['request'],x['now']; reasons=[]
    if e['project']!=q['project']:reasons.append('project_mismatch')
    if not set(q['targets'])<=set(e['targets']):reasons.append('target_gap')
    if mutant!='ignore_paths' and not set(q['paths'])<=set(e['paths']):reasons.append('path_gap')
    if e['profile']!=q['profile']:reasons.append('profile_mismatch')
    if mutant!='ignore_versions' and any(e['versions'].get(k)!=v for k,v in q['versions'].items()):reasons.append('version_mismatch')
    if not e['collected_at']<=now<e['valid_until']:reasons.append('evidence_time_invalid')
    if not 0<=now-q['readiness_at']<=q['readiness_ttl']:reasons.append('readiness_stale')
    waived_requirements=set()
    if e['verdict']=='WAIVED':
        w=e.get('waiver',{})
        valid=q['allow_waived'] and now<w.get('valid_until',0) and all(w.get(k) for k in ['approver','reason','remediation'])
        if mutant!='ignore_waiver_scope':valid=valid and set(q['targets'])<=set(w.get('targets',[])) and set(q['paths'])<=set(w.get('paths',[]))
        if not valid:reasons.append('waiver_invalid')
        else:waived_requirements=set(w.get('requirements',[]))
    elif e['verdict']!='PASS':reasons.append('verdict_not_accepted')
    if mutant!='unknown_as_zero' and any(v['required'] and v['value']!='known' and v.get('requirement_id','required_quality') not in waived_requirements for v in e['quality']):reasons.append('required_quality_missing')
    for k in ['permission','resources','channel']:
        if not q[k]:reasons.append(k+'_missing')
    if q['blocking_alert']:reasons.append('blocking_alert')
    return dict(allowed=not reasons,reasons=reasons,preserved_verdict=e['verdict'])

def g2(x,mutant=None):
    if mutant!='ignore_missing_side' and not(x['host_collected'] and x['switch_collected']):return dict(verdict='BLOCKED',cause='missing_evidence')
    if x['host_neighbor']!=x['expected_host'] or x['switch_neighbor']!=x['expected_switch'] or not x['mac_match']:return dict(verdict='FAIL',cause='observed_mismatch')
    return dict(verdict='PASS',cause='three_way_match')

def ll03(x,mutant=None):
    if not x['capability'] or not x['samples_complete'] or x['counter_reset'] or (mutant!='ignore_rule_window' and x['window_seconds']<3600):return dict(evaluable=False,triggered=None)
    return dict(evaluable=True,triggered=x['ecn_all_zero'] and (x['queue_watermark']>0 or x['pfc_delta']>=1))

def run_case(case,defaults,mutant=None):
    k=case['kind']; x=copy.deepcopy(case['input']) if 'input'in case else merge(defaults[k],case.get('patch',{}))
    if k=='admission':actual=admission(x,mutant)
    elif k=='g2':actual=g2(x,mutant)
    elif k=='g2_finish':actual={'g2_complete':len(x['step_verdicts'])==3 and all(v=='PASS' for v in x['step_verdicts']) and x['dl_confirmed']}
    elif k=='ll03':actual=ll03(x,mutant)
    elif k=='group':actual={'allow_start':bool(x['members']) and set(x['members'])<=set(x['reserved']) and set(x['members'])<=set(x['ready']) and x['barrier']}
    elif k=='group_retry':actual={'restart':x['members'] if x['failed'] else [],'new_group_attempt':bool(x['failed'])}
    else:raise ValueError(k)
    mismatches=[]
    for key,want in case['expect'].items():
        if key=='reason':
            if want not in actual.get('reasons',[]):mismatches.append(key)
        elif actual.get(key)!=want:mismatches.append(key)
    return dict(id=case['id'],name=case['name'],invariants=case['inv'],status='pass' if not mismatches else 'fail',expected=case['expect'],actual=actual)

def structural(model):
    checks=[]
    def check(name,ok,detail):checks.append(dict(name=name,passed=bool(ok),detail=detail))
    fs={f['id']:f for f in model['flows']}; ars={a['id']:a for a in model['artifacts']}
    check('source_sha256',hashlib.sha256((ROOT/'source'/model['source']['name']).read_bytes()).hexdigest()==model['source']['sha256'],model['source']['sha256'])
    check('unique_ids',len(fs)==len(model['flows']) and len(ars)==len(model['artifacts']),'流程和逻辑产物ID唯一')
    check('complete_contracts',all(all(f.get(k) for k in ['name','source','purpose','inputs','resources','guards','actions','outputs','post','failure','retry','invalidation']) for f in fs.values()),'所有流程均具备契约字段')
    check('input_references',all(a in ars for f in fs.values() for a in f['inputs']),'输入有生产方或明确外部权威来源')
    check('output_ownership',all(ars[a['id']]['producer']==f['id'] for f in fs.values() for a in f['outputs']),'每个逻辑产物有对应生产边界')
    check('consumer_links',all(set(a['consumers']) == {f['id'] for f in fs.values() if a['id'] in f['inputs']} for a in ars.values()),'正向消费与反向索引一致')
    check('no_orphan_products',all(a['consumers'] or a.get('terminal_consumer') for a in ars.values()),'终端消费者和恢复回流显式登记')
    graph={f:set() for f in fs}
    for f in fs.values():
        for a in f['inputs']:
            p=ars[a]['producer']
            if p!='external':graph[p].add(f['id'])
    indeg={f:0 for f in fs}
    for targets in graph.values():
        for t in targets:indeg[t]+=1
    queue=deque(k for k,v in indeg.items() if not v); order=[]
    while queue:
        k=queue.popleft();order.append(k)
        for t in sorted(graph[k]):
            indeg[t]-=1
            if not indeg[t]:queue.append(t)
    check('normal_evidence_dag',len(order)==len(fs),'前向证据构建无环；恢复回流不是普通前置边')
    check('g2_not_waiting_for_g3','mapping' not in fs['H04']['inputs'],'G2不依赖Mapping发布')
    check('g4_not_omitted','g4' in fs['T00']['inputs'],'G5准入依赖有效G4')
    check('g5_not_forced_serial',not any(a in fs['T02']['inputs'] for a in ['l1']) and not any(a in fs['T03']['inputs'] for a in ['l2']),'没有将未定的L1→L2→L3串行策略写为既定硬依赖')
    check('decision_references',all(q in {d['id'] for d in model['decisions']} for f in fs.values() for q in f['decisions']),'Q引用存在')
    check('invariant_references',all(f in fs for v in model['invariants'] for f in v['flows']),'INV流程引用存在')
    root=ET.parse(ROOT/'keel-delivery.drawio').getroot(); diagrams=root.findall('diagram')
    xmlok=len(diagrams)==6; edge_count=0
    for diagram in diagrams:
        cells=diagram.findall('.//mxCell'); ids={c.attrib['id'] for c in cells}; xmlok=xmlok and len(ids)==len(cells)
        for c in cells:
            if c.attrib.get('edge')=='1':
                edge_count+=1;xmlok=xmlok and c.attrib.get('source') in ids and c.attrib.get('target') in ids
    check('drawio_xml_and_edges',xmlok,{'pages':len(diagrams),'edges':edge_count})
    doc=(ROOT/'keel-developer-contracts.md').read_text()
    check('document_contract_coverage',all('<!-- contract:'+f['id']+' -->' in doc for f in fs.values()),'文档覆盖全部流程ID')
    return checks,graph,order

def version_race(mutated=False):
    # Finite abstraction: one current revision (0/1), one active attempt,
    # finish/publication, and an optional single concurrent configuration change.
    # Historical artifact revision is retained even when not currently usable.
    initial=(0,-1,False,-1,False)
    queue=deque([initial]); paths={initial:[]}; transitions=0; violations=[]
    while queue:
        s=queue.popleft();rev,attempt,done,artifact,usable=s
        if usable and artifact!=rev:violations.append({'state':s,'trace':paths[s]})
        options=[]
        if attempt==-1 or done:options.append(('admit_current',(rev,rev,False,artifact,usable)))
        if attempt!=-1 and not done:options.append(('finish_attempt',(rev,attempt,True,artifact,usable)))
        if rev==0:options.append(('change_config',(1,attempt,done,artifact,False)))
        if done:
            options.append(('publish_result',(rev,attempt,done,attempt,True if mutated else attempt==rev)))
        for name,nxt in options:
            transitions+=1
            if nxt not in paths:paths[nxt]=paths[s]+[name];queue.append(nxt)
    return dict(states=len(paths),transitions=transitions,safety_ok=not violations,counterexample=violations[0] if violations else None,
      bounds='1 active attempt; 2 config revisions; at most one change; no real executor/message transport/time model')

def recovery_path(disable_exception=False):
    graph={'open':['repair_registered'],'repair_registered':[] if disable_exception else ['verify_running'],'verify_running':['verification_pass','reopened'],'verification_pass':['closed'],'reopened':['repair_registered'],'closed':[]}
    q=deque([('open',[])]);seen=set()
    while q:
        at,path=q.popleft()
        if at in seen:continue
        seen.add(at)
        if at=='closed':return dict(reachable=True,path=path+[at],condition='authorized repair, unrelated constraints satisfied, and successful targeted revalidation')
        for n in graph[at]:q.append((n,path+[at]))
    return dict(reachable=False,path=[],condition='ordinary blocking alarm cannot be bypassed without the scoped recovery exception')

def main():
    model=json.loads((ROOT/'contract-model.json').read_text()); suite=json.loads((ROOT/'acceptance-cases.json').read_text())
    structure,graph,order=structural(model)
    known_inv={v['id'] for v in model['invariants']}
    assert all(i in known_inv for c in suite['cases'] for i in c['inv'])
    assert len({c['id'] for c in suite['cases']})==len(suite['cases'])
    results=[run_case(c,suite['defaults']) for c in suite['cases']]
    mutants=[]
    for m in ['ignore_paths','ignore_versions','unknown_as_zero','ignore_waiver_scope','ignore_missing_side','ignore_rule_window']:
        caught=[r['id'] for c in suite['cases'] if (r:=run_case(c,suite['defaults'],m))['status']=='fail']
        mutants.append(dict(mutation=m,killed=bool(caught),detected_by=caught))
    race=version_race();bad_race=version_race(True);recovery=recovery_path();bad_recovery=recovery_path(True)
    from verify_walkthrough import run as verify_actions
    reader=json.loads((ROOT/'reading-model.json').read_text())
    actions=verify_actions(model, reader)
    from decision_forms import verify as verify_decisions
    decision_checks=verify_decisions(reader,model)
    success=all(c['passed'] for c in decision_checks['checks']) and actions['passed'] and all(x['passed'] for x in structure) and all(x['status']=='pass' for x in results) and all(m['killed'] for m in mutants) and race['safety_ok'] and not bad_race['safety_ok'] and recovery['reachable'] and not bad_recovery['reachable']
    covered={i for c in suite['cases'] for i in c['inv']};covered|={'INV-14','INV-10','INV-12'}
    report=dict(status='passed' if success else 'failed',model_version=model['version'],source=model['source'],
      summary=dict(flows=len(model['flows']),artifacts=len(model['artifacts']),drawio_pages=6,structural_checks=len(structure),cases=len(results),passed_cases=sum(r['status']=='pass' for r in results),mutations=len(mutants),killed_mutations=sum(m['killed'] for m in mutants)),
      decision_forms=decision_checks,walkthrough=actions,reading_version=reader["version"],definition_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ["build_artifacts.py","decision_forms.py","collection.py","walkthrough.py","collection_model.py","verify_walkthrough.py","verify_contracts.py","acceptance-cases.json","collection-event.schema.json","DEVELOPMENT-REQUIREMENTS.md"]},structural_checks=structure,cases=results,mutations=mutants,version_race=race,version_race_mutant=bad_race,recovery=recovery,recovery_mutant=bad_recovery,
      explicitly_case_or_model_checked_invariants=sorted(covered),other_invariants_require_review=sorted(known_inv-covered),
      limitations=['No keel production implementation was tested.','No real device, adapter, vendor threshold or network topology was verified.','No third-party expert sign-off or formal completeness proof.','G5 scheduling/coverage/time/waiver policies remain Q1-Q12.','Model examples use exact profile equality and directed path strings; production compatibility and path derivation are not specified here.','Model interval is [collected_at, valid_until), readiness age is inclusive of TTL; final API boundaries must be agreed.','LL-03 trigger result is not overall network health or G5 PASS.'])
    (ROOT/'verification-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    from reading import report_markdown
    reader=json.loads((ROOT/'reading-model.json').read_text())
    md=report_markdown(report,reader)
    (ROOT/'verification-report.md').write_text(md)
    print(json.dumps(dict(status=report['status'],**report['summary'],race_states=race['states'],race_transitions=race['transitions'],action_checks=len(actions['checks']),action_checks_passed=sum(c['passed'] for c in actions['checks']),counterexample=bad_race['counterexample']),ensure_ascii=False))
    return 0 if success else 1
if __name__=='__main__':sys.exit(main())
