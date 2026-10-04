#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def loadj(rel):
    return json.loads((ROOT/rel).read_text(encoding='utf-8'))

def gate(root=ROOT):
    findings=[]
    required=[
        'canonical/FA3-LOCAL-AI-MODEL-DEVELOPMENT-POLICY-001.json',
        'canonical/local-ai-model-development-enforcement.json',
        'canonical/assessments/FA3-LOCAL-AI-MODEL-DEVELOPMENT-POLICY-REUSE-ASSESSMENT-2026-10-04.json',
        'canonical/current-host-impact/FA3-LOCAL-AI-MODEL-DEVELOPMENT-POLICY-2026-10-04.json',
        'canonical/FA3-AI-STUDIO-APP-CATALOG-001.json',
        'AGENTS.md']
    for rel in required:
        if not (root/rel).is_file(): findings.append('missing:'+rel)
    if findings:
        return {'schema':'fa3.local-ai-model-development-gate-report.v1','gate_id':'FA3-LOCAL-AI-MODEL-DEVELOPMENT-GATESET-001','result':'FAIL','findings':findings}
    p=json.loads((root/required[0]).read_text(encoding='utf-8'))
    e=json.loads((root/required[1]).read_text(encoding='utf-8'))
    a=json.loads((root/required[2]).read_text(encoding='utf-8'))
    i=json.loads((root/required[3]).read_text(encoding='utf-8'))
    c=json.loads((root/required[4]).read_text(encoding='utf-8'))
    agents=(root/required[5]).read_text(encoding='utf-8')

    if p.get('id')!='FA3-LOCAL-AI-MODEL-DEVELOPMENT-POLICY-001' or p.get('mandatory') is not True or p.get('retroactive') is not True: findings.append('policy identity/mandatory/retroactive')
    if p.get('capability_count')!=175 or p.get('capability_delta')!=0 or p.get('architectural_authority_delta')!=0: findings.append('baseline/authority delta')
    d=p.get('development_requirements',{})
    if not (d.get('current_model_research_required') is True and d.get('reuse_discovery_required') is True and d.get('model_matrix_required') is True): findings.append('research/reuse/model matrix')
    if len(d.get('model_matrix_minimum_fields',[]))<15: findings.append('model matrix fields')
    h=p.get('hardware_aware_selection',{})
    if not (h.get('required') is True and h.get('cpu_only_path_mandatory') is True and h.get('vendor_neutral') is True and h.get('accelerator_cardinality')=='0..N'): findings.append('hardware aware cpu-only')
    if h.get('recommendation_is_execution_authority') is not False or h.get('recommendation_is_install_authority') is not False: findings.append('recommendation authority')
    if h.get('no_silent_fallback') is not True or h.get('no_silent_local_to_cloud_fallback') is not True: findings.append('silent fallback')
    dg=h.get('display_gpu_policy',{})
    if dg.get('default_ai_compute') is not False or dg.get('hardware_detection_may_override_rule') is not False: findings.append('display gpu default')
    if 'NO_OTHER_GPU_AND_NO_NPU' not in str(dg.get('automatic_use_allowed_when','')): findings.append('display gpu sole-device exception')
    if 'EXPLICIT_IN_APPLICATION_TASK_AND_MODEL_SPECIFIC_USER_SELECTION' not in str(dg.get('when_other_gpu_or_npu_exists','')): findings.append('display gpu manual exception')
    auth=p.get('existing_authorities',{})
    if auth.get('model_provider_routing')!='FA3-AUTH-MODEL-ROUTER-001' or auth.get('resource_admission_placement_reservation_lease')!='FA3-AUTH-HOST-RESOURCE-BROKER-001': findings.append('router/hrb binding')
    if auth.get('model_artifact_lifecycle')!='FA3-MODEL-MANAGER-001' or auth.get('engine_provider_user_intent')!='FA3-ENGINE-SELECTION-FABRIC-001': findings.append('manager/selector binding')
    ui=p.get('application_ui_contract',{})
    if not (ui.get('required_inside_each_consuming_application') is True and ui.get('all_admitted_compatible_candidates_visible') is True and ui.get('compatible_not_installed_candidates_visible') is True and ui.get('manual_compatible_alternative_selection') is True): findings.append('application model UI')
    if ui.get('application_may_hide_non_primary_eligible_candidates') is not False: findings.append('hidden alternatives')
    dl=p.get('optional_download_install',{})
    if not (dl.get('user_initiated_only') is True and dl.get('automatic_download') is False and dl.get('automatic_install') is False and dl.get('model_manager_mediated') is True): findings.append('download boundary')
    if not (dl.get('license_rights_pass_required') is True and dl.get('model_artifact_security_pass_required') is True and dl.get('provenance_required') is True): findings.append('download admission')
    if e.get('gate_id')!='FA3-LOCAL-AI-MODEL-DEVELOPMENT-GATESET-001' or e.get('mandatory') is not True or e.get('fail_closed') is not True or e.get('capability_count')!=175 or len(e.get('rules',[]))<17: findings.append('enforcement')
    snap=a.get('donor_planning_snapshot',{})
    if not (a.get('result')=='PASS' and a.get('pending_or_unmerged_donors_consumed') is False and snap.get('published_main_commit')=='6be38def0d6a56b4e8fded74fb3c5ed2e3c1506f' and snap.get('donor_registry_blob_sha')=='1362d75186c6da74e5cf947fdf0b8867d462636a' and snap.get('donor_registry_sha256')=='b8d0eb42ee02885863af375071ffae89033664089ddba3c69682a8d0f7c7cff1' and snap.get('donor_registry_entry_count')==1427): findings.append('donor snapshot')
    sp=a.get('shared_capability_placement',{})
    if not (sp.get('disposition')=='SHARED' and sp.get('local_duplicate_created') is False and sp.get('retrospective_consumer_impact_reviewed') is True): findings.append('shared placement')
    if not (i.get('schema')=='fa3.current-host-structural-impact.v1' and i.get('status')=='NO_RUNTIME_IMPACT' and i.get('runtime_change') is False and i.get('provider_or_model_activation') is False and i.get('hardware_mutation') is False and i.get('physical_current_host_pass_claimed') is False and i.get('physical_requalification_required') is False): findings.append('current host impact')
    if c.get('local_ai_model_development_policy')!='FA3-LOCAL-AI-MODEL-DEVELOPMENT-POLICY-001' or c.get('all_entries_inherit_fa3_development_rules') is not True: findings.append('application catalog inheritance')
    if '## FA3 local AI model development rule' not in agents: findings.append('agent policy section')
    for token in ('Model Router','Model Manager','Host Resource Broker','display GPU','optional download'):
        if token not in agents: findings.append('agent token:'+token)
    return {'schema':'fa3.local-ai-model-development-gate-report.v1','gate_id':'FA3-LOCAL-AI-MODEL-DEVELOPMENT-GATESET-001','policy_id':'FA3-LOCAL-AI-MODEL-DEVELOPMENT-POLICY-001','capability_count':175,'result':'PASS' if not findings else 'FAIL','findings':findings,'runtime_promotion_claim':False,'physical_current_host_pass_claimed':False}

if __name__=='__main__':
    report=gate()
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['result']=='PASS' else 2)
