#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from fa3_agent_workload import (
    WorkloadContractError, project_to_ax, resume_requirements, select_runner,
    suspension_semantics, transition_allowed, validate_checkpoint, validate_network_envelope,
    validate_task, validate_workspace,
)
from fa3_release_baseline import load_active_release_baseline
from fa3_uaf import ActionRegistry

PROFILE_ID="FA3-AGENT-WORKLOAD-RUNTIME-001"
CONTRACT_ID="FA3-AGENT-WORKLOAD-RUNTIME-CONTRACTS-001"
DECISION_ID="FA3-DEC-AGENT-WORKLOAD-RUNTIME-AX-DERIVED-2026-09-24"
ASSESSMENT_ID="FA3-AGENT-WORKLOAD-RUNTIME-2026-09-24"
REFERENCE_ID="FA3-GOOGLE-AX-UPSTREAM-REFERENCE-2026-09-24"
REGISTRY_ID="FA3-AGENT-RUNTIME-PROVIDER-REGISTRY-001"
GATE_ID="FA3-GATE-AGENT-WORKLOAD-RUNTIME-001"
GATESET_ID="FA3-AGENT-WORKLOAD-RUNTIME-GATESET-001"
AX_COMMIT="e6211f84a9e30dd309304167b8f1d51cbdaf8dab"
ACTIONS={
 "agent.workload.declare","agent.workload.start","agent.workload.pause","agent.workload.suspend",
 "agent.workload.resume","agent.workload.terminate","agent.workload.inspect","agent.workload.debug.exec",
 "agent.workspace.materialize",
}

def load(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(f"object required: {path}")
    return value

def finding(code: str, message: str, **kw: Any) -> dict[str, Any]:
    return {"code":code,"severity":"P0","message":message,**kw}

def expect_error(fn) -> bool:
    try: fn()
    except WorkloadContractError: return True
    return False

def regression_cases() -> dict[str, Any]:
    task={"schema":"fa3.agent-workload-task.v1","task_id":"t1","root_task_id":"t1","action_ref":"orchestration.execute",
          "agent_definition_ref":"agent:def:1","workspace_refs":["ws:1"],"resource_requirements":{"cpu_physical_cores":1},
          "network_envelope_ref":"net:1","model_intent":{"capability":"coding","locality":"prefer_local"},
          "authorized_ai_participants":["agent:def:1"],
          "fanout_limits":{"max_children":4,"max_depth":2,"max_concurrent_children":2,"max_runtime_seconds":600,"max_retries":2,"max_tool_calls":50,"max_model_requests":50}}
    ws={"schema":"fa3.agent-workspace.v1","workspace_id":"ws1","sources":[{"kind":"GIT","repo":"https://example.invalid/repo.git","commit":"a"*40}],"bootstrap_mode":"NONE"}
    net={"schema":"fa3.execution-network-envelope.v1","default":"DENY","egress":[],"ingress":[],"direct_model_provider_access":False,"direct_external_tool_access":False,"authority":False}
    cp={"schema":"fa3.agent-checkpoint-manifest.v1","task_id":"t1","task_spec_digest":"sha256:abc","mode":"APPLICATION","secret_material_present":False,"secret_handles_detached":True,"runner_identity":{"provider_id":"runner"}}
    good_runner={"provider_id":"native","runtime_promotion_status":"CURRENT_HOST_PRODUCTION_E2E_PASS","priority":10,"capabilities":{"pause":True,"application_checkpoint":True}}
    pending_ax={"provider_id":"ax","runtime_promotion_status":"PENDING_CURRENT_HOST_OR_CLUSTER","priority":1,"capabilities":{"pause":True,"application_checkpoint":True}}
    bad_secret=copy.deepcopy(task); bad_secret["api_key"]="x"
    bad_model=copy.deepcopy(task); bad_model["model_intent"]["provider_id"]="direct"
    bad_net=copy.deepcopy(net); bad_net["default"]="ALLOW"
    bad_ws=copy.deepcopy(ws); bad_ws["sources"][0].pop("commit"); bad_ws["sources"][0]["branch"]="main"
    bad_cp=copy.deepcopy(cp); bad_cp["secret_material_present"]=True
    bad_fan=copy.deepcopy(task); bad_fan["fanout_limits"].pop("max_depth")
    projection=project_to_ax(task,ws,net)
    cases=[
      ("VALID_TASK", not bool(validate_task(task) is None)),
      ("RAW_SECRET_REJECTED", expect_error(lambda: validate_task(bad_secret))),
      ("DIRECT_MODEL_PROVIDER_REJECTED", expect_error(lambda: validate_task(bad_model))),
      ("NETWORK_DEFAULT_ALLOW_REJECTED", expect_error(lambda: validate_network_envelope(bad_net))),
      ("WORKSPACE_FLOATING_GIT_REJECTED", expect_error(lambda: validate_workspace(bad_ws))),
      ("CHECKPOINT_SECRET_REJECTED", expect_error(lambda: validate_checkpoint(bad_cp))),
      ("STATE_TRANSITION_GUARD", transition_allowed("RUNNING","PAUSING") and not transition_allowed("RUNNING","SUSPENDED")),
      ("PAUSE_NOT_DURABLE_SUSPEND", suspension_semantics("PAUSE")["durable"] is False and suspension_semantics("APPLICATION")["durable"] is True),
      ("PENDING_GOOGLE_AX_NOT_ELIGIBLE", expect_error(lambda: select_runner([pending_ax],{"pause"},admission_receipt_present=True))),
      ("ADVISORY_CANNOT_EXPAND_RUNNER_SET", expect_error(lambda: select_runner([good_runner],{"pause"},admission_receipt_present=True,advisory_selected="ax"))),
      ("RESUME_REQUIRES_FRESH_HRB_LEASE", expect_error(lambda: resume_requirements(cp,"LEASE-1",previous_hrb_lease_ref="LEASE-1")) and resume_requirements(cp,"LEASE-2",previous_hrb_lease_ref="LEASE-1")["old_lease_reused"] is False),
      ("AX_PROJECTION_HAS_NO_MODEL_AUTHORITY", projection["authority"] is False and projection["canonical_ir"] is False and projection["task"]["model_resource_emitted"] is False and projection["model_intent_forwarding"]["authority"]=="FA3-AUTH-MODEL-ROUTER-001"),
      ("FANOUT_LIMITS_REQUIRED", expect_error(lambda: validate_task(bad_fan))),
    ]
    return {"result":"PASS" if all(ok for _,ok in cases) else "FAIL","cases":[{"id":cid,"pass":bool(ok)} for cid,ok in cases]}

def gate(root: Path) -> dict[str, Any]:
    root=root.resolve(); findings=[]
    cap=load_active_release_baseline(root).capability_count
    paths={
      "profile":root/"canonical/profiles/FA3-AGENT-WORKLOAD-RUNTIME-001.json",
      "contract":root/"canonical/contracts/FA3-AGENT-WORKLOAD-RUNTIME-CONTRACTS-001.json",
      "decision":root/"canonical/decisions/FA3-DEC-AGENT-WORKLOAD-RUNTIME-AX-DERIVED-2026-09-24.json",
      "assessment":root/"canonical/assessments/FA3-AGENT-WORKLOAD-RUNTIME-DECISION-ASSESSMENT-2026-09-24.json",
      "reference":root/"canonical/references/FA3-GOOGLE-AX-UPSTREAM-REFERENCE-2026-09-24.json",
      "registry":root/"canonical/FA3-AGENT-RUNTIME-PROVIDER-REGISTRY-001.json",
      "native":root/"canonical/providers/FA3-PROVIDER-AGENT-RUNNER-NATIVE-001.json",
      "podman":root/"canonical/providers/FA3-PROVIDER-AGENT-RUNNER-PODMAN-001.json",
      "ax":root/"canonical/providers/FA3-PROVIDER-GOOGLE-AX-001.json",
      "enforcement":root/"canonical/agent-workload-runtime-enforcement.json",
      "gate":root/"canonical/FA3-GATE-AGENT-WORKLOAD-RUNTIME-001.json",
      "policy":root/"canonical/enforcement-policy.json",
      "dist_registry":root/"canonical/distribution-registry.json",
      "dist_manifest":root/"canonical/distribution-manifest.json",
      "evidence":root/"evidence/reference/agent-workload-runtime-ci-2026-09-24.json",
    }
    for name,path in paths.items():
        if not path.is_file(): findings.append(finding("AWR-001","required file missing",name=name,path=path.as_posix()))
    if findings: return {"schema":"fa3.agent-workload-runtime-gate.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}
    p,c,d,a,r,reg,native,podman,ax,enf,g,pol,dr,dm,ev=[load(paths[k]) for k in ("profile","contract","decision","assessment","reference","registry","native","podman","ax","enforcement","gate","policy","dist_registry","dist_manifest","evidence")]
    checks=[
      (p.get("id")==PROFILE_ID and p.get("priority")=="P0" and p.get("requirement")=="MUST","AWR-010","profile identity/priority drift"),
      (p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==cap and p.get("capability_bindings")==["CAP-028"],"AWR-011","capability/authority baseline drift"),
      (p.get("authority_boundaries",{}).get("durable_workflow")=="TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY" and p.get("authority_boundaries",{}).get("host_resources")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and p.get("authority_boundaries",{}).get("model_routing")=="FA3-AUTH-MODEL-ROUTER-001" and p.get("authority_boundaries",{}).get("tool_mediation")=="FA3-AUTH-MCP-GATEWAY-001","AWR-012","authority boundary drift"),
      (c.get("id")==CONTRACT_ID and c.get("capability_count")==cap and c.get("provider_neutral") is True and c.get("fail_closed") is True,"AWR-013","contract baseline drift"),
      (d.get("id")==DECISION_ID and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("current_host_runtime_promotion_claim") is False,"AWR-014","decision promotion/baseline drift"),
      (a.get("project_id")==ASSESSMENT_ID and a.get("assessment")=="RECOMMENDED" and a.get("project_radar_checked") is True and a.get("capability_delta")==0 and a.get("authority_delta")==0,"AWR-015","Decision Fabric assessment invalid"),
      (r.get("id")==REFERENCE_ID and r.get("commit")==AX_COMMIT and r.get("license")=="Apache-2.0" and r.get("observed_repository_facts",{}).get("api_version")=="ax.io/v1alpha1" and r.get("observed_repository_facts",{}).get("upstream_breaking_changes_warning") is True and r.get("fa3_interpretation",{}).get("architectural_authority") is False,"AWR-016","Google AX immutable provenance or interpretation drift"),
      (reg.get("id")==REGISTRY_ID and reg.get("provider_self_admission") is False and len(reg.get("providers",[]))==3,"AWR-017","runner registry drift"),
      (native.get("runtime_activation_status")=="PENDING_CURRENT_HOST" and podman.get("runtime_activation_status")=="PENDING_CURRENT_HOST" and ax.get("runtime_activation_status")=="PENDING_CURRENT_HOST_OR_CLUSTER","AWR-018","provider runtime status improperly promoted"),
      (ax.get("activation_mode")=="OPTIONAL_DISABLED_BY_DEFAULT" and ax.get("translation",{}).get("canonical_ax_schema") is False and ax.get("translation",{}).get("ax_model_to_fa3_model_resource") is False,"AWR-019","Google AX boundary drift"),
      (enf.get("gateset_id")==GATESET_ID and enf.get("fail_closed") is True and "STATIC_REFERENCE_PASS_NOT_CURRENT_HOST_PROMOTION" in enf.get("mandatory_rules",[]),"AWR-020","enforcement rules incomplete"),
      (g.get("id")==GATE_ID and g.get("gateset_id")==GATESET_ID and g.get("regression_case_count")==13 and g.get("current_host_runtime_evidence") is False,"AWR-021","executable gate record drift"),
      (GATESET_ID in set(pol.get("mandatory_reference_gates",[])) and pol.get("agent_workload_runtime_profile_id")==PROFILE_ID and pol.get("agent_workload_runtime_reference_id")==REFERENCE_ID,"AWR-022","global enforcement policy binding missing"),
      (ev.get("status")=="PASS" and ev.get("evidence_class")=="REFERENCE_STATIC_CONFORMANCE" and ev.get("current_host_runtime_promotion_claim") is False,"AWR-023","reference evidence semantics drift"),
    ]
    for ok,code,msg in checks:
        if not ok: findings.append(finding(code,msg))
    schema_root=root/"canonical/contracts"
    for name in c.get("contract_schemas",[]):
        sp=schema_root/name
        if not sp.is_file(): findings.append(finding("AWR-024","declared schema missing",schema=name))
        else:
            sd=load(sp)
            if sd.get("$schema")!="https://json-schema.org/draft/2020-12/schema" or not sd.get("x-fa3-contract-id"):
                findings.append(finding("AWR-024","declared schema identity invalid",schema=name))
    amap={x.action_id:x for x in ActionRegistry.from_directory(root/"canonical/actions").list()}
    if not ACTIONS.issubset(amap): findings.append(finding("AWR-025","UAF workload action set incomplete",missing=sorted(ACTIONS-set(amap))))
    for aid in ACTIONS & set(amap):
        action=amap[aid]
        if action.security.get("authentication")!="required" or action.security.get("authorization")!="required" or action.evidence.get("required") is not True:
            findings.append(finding("AWR-026","UAF action security/evidence boundary invalid",action_id=aid))
        if action.resources.get("accelerator",{}).get("cardinality")!="0..N":
            findings.append(finding("AWR-027","UAF accelerator cardinality drift",action_id=aid))
    if amap.get("agent.workload.debug.exec") and amap["agent.workload.debug.exec"].security.get("approval")!="explicit":
        findings.append(finding("AWR-028","debug exec does not require explicit approval"))
    for aid in ("agent.workload.start","agent.workload.resume"):
        if amap.get(aid) and amap[aid].resources.get("hrb_required") is not True:
            findings.append(finding("AWR-029","start/resume must enter HRB admission",action_id=aid))
    records={x.get("subject_id"):x for x in dr.get("records",[])}
    if records.get(REFERENCE_ID,{}).get("class")!="REFERENCE_ONLY" or records.get("FA3-PROVIDER-GOOGLE-AX-001",{}).get("class")!="EXTERNAL_REDISTRIBUTABLE":
        findings.append(finding("AWR-030","distribution registry binding missing"))
    mex={x.get("subject_id"):x for x in dm.get("excluded",[])}
    if mex.get(REFERENCE_ID,{}).get("release_bundle_status")!="EXCLUDED" or mex.get("FA3-PROVIDER-GOOGLE-AX-001",{}).get("release_bundle_status")!="EXCLUDED":
        findings.append(finding("AWR-031","distribution manifest does not exclude AX upstream/provider"))
    rr=regression_cases()
    if rr["result"]!="PASS": findings.append(finding("AWR-040","runtime contract regression failed",regressions=rr))
    report={"schema":"fa3.agent-workload-runtime-gate.v1","gate_id":GATE_ID,"result":"PASS" if not findings else "FAIL","findings":findings,"regressions":rr,"capability_delta":0,"authority_delta":0,"current_host_runtime_claim":False}
    out=root/"reports/agent-workload-runtime-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args()
    r=gate(Path(a.root)); print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
