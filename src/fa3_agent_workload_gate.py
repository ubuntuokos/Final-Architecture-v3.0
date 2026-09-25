#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from fa3_agent_workload import (
    WorkloadContractError, compile_orchestration_workload, project_to_ax, resume_requirements, select_runner,
    suspension_semantics, transition_allowed, validate_checkpoint, validate_network_envelope,
    validate_task, validate_workspace,
)
from fa3_google_ax_provider import AxProviderBridgeError, compile_ax_provider_bridge
from fa3_google_ax_custom_runner import AxCustomRunnerError, compile_custom_runner_plan
from fa3_google_ax_cluster_apply import AxClusterApplyError, compile_cluster_apply_plan
from fa3_release_baseline import load_active_release_baseline
from fa3_adk2_runtime_gate import gate as adk2_runtime_semantics_gate
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

def expect_ax_error(fn) -> bool:
    try: fn()
    except AxProviderBridgeError: return True
    return False

def expect_ax_runner_error(fn) -> bool:
    try: fn()
    except AxCustomRunnerError: return True
    return False

def expect_ax_cluster_error(fn) -> bool:
    try: fn()
    except AxClusterApplyError: return True
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
    ax_ws={"schema":"fa3.agent-workspace.v1","workspace_id":"workspace-1","sources":[],"bootstrap_mode":"NONE"}
    ax_task=copy.deepcopy(task); ax_task["task_id"]="agent-task-1"; ax_task["root_task_id"]="agent-task-1"; ax_task["workspace_refs"]=["workspace-1"]
    ax_net=copy.deepcopy(net); ax_net["egress"]=[{"host":"router.fa3.internal","port":443}]
    ax_binding={
      "schema":"fa3.google-ax-provider-binding.v1","provider_id":"FA3-PROVIDER-GOOGLE-AX-001","atespace":"fa3",
      "runner_image":"registry.example/fa3-ax-runner@sha256:"+"a"*64,"command":["fa3-agent-runner","--execute"],
      "workspace_order":["workspace-1"],"workspace_paths":{"workspace-1":"/workspace/workspace-1"},
      "gateway_name":"agent-task-1-gateway","resources":{"requests":{"cpu":"1","memory":"1Gi"}},
      "hrb_admission_ref":"hrb-auth:1","resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
      "model_router_binding_ref":"model-route:1","model_router_authority":"FA3-AUTH-MODEL-ROUTER-001",
      "mcp_gateway_binding_ref":"mcp-session:1","mcp_gateway_authority":"FA3-AUTH-MCP-GATEWAY-001",
      "network_envelope_ref":"net:1","debug":False,
    }
    ax_projection=compile_ax_provider_bridge(ax_task,[ax_ws],ax_net,ax_binding)
    ax_runner_ws=copy.deepcopy(ax_ws); ax_runner_ws["sources"]=[{"kind":"GIT","repo":"https://github.com/example/repo.git","commit":"a"*40}]
    ax_runner_net=copy.deepcopy(ax_net); ax_runner_net["egress"]=[{"host":"github.com","port":443}]
    ax_runner_plan=compile_custom_runner_plan(ax_task,[ax_runner_ws],ax_runner_net,ax_binding)
    ax_runner_bad_net=copy.deepcopy(ax_runner_net); ax_runner_bad_net["egress"]=[]
    ax_runner_evidence={"schema":"fa3.google-ax-runner-image-evidence.v1","runner_image":ax_binding["runner_image"],"evidence_ref":"evidence:ax-runner-image:1","build_verified":True,"digest_verified":True,"current_host_runtime_promotion_claim":False}
    ax_cluster_binding={"schema":"fa3.google-ax-cluster-binding.v1","cluster_scope_ref":"cluster-scope:ax-test","kubernetes_context_ref":"k8s-context:ax-test","agent_substrate_ref":"agent-substrate:ax-test","security_approval_ref":"security-approval:ax-test","namespace":"fa3","scope_bound":True,"debug_guest_services_authorized":False}
    ax_cluster_apply_plan=compile_cluster_apply_plan(ax_projection,ax_runner_plan,ax_runner_evidence,ax_cluster_binding)
    ax_runner_bad_evidence=copy.deepcopy(ax_runner_evidence); ax_runner_bad_evidence["build_verified"]=False
    ax_cluster_bad_credentials=copy.deepcopy(ax_cluster_binding); ax_cluster_bad_credentials["token"]="secret"
    ax_git_ws=copy.deepcopy(ax_ws); ax_git_ws["sources"]=[{"kind":"GIT","repo":"https://example.invalid/repo.git","commit":"a"*40}]
    ax_debug=copy.deepcopy(ax_binding); ax_debug["debug"]=True
    ax_wild=copy.deepcopy(ax_net); ax_wild["egress"]=[{"host":"*","port":443}]
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
      ("AX_PROJECTION_HAS_NO_MODEL_AUTHORITY", projection["authority"] is False and projection["canonical_ir"] is False and projection["upstream_valid_manifest"] is False and projection["task"]["model_resource_emitted"] is False and projection["model_intent_forwarding"]["authority"]=="FA3-AUTH-MODEL-ROUTER-001"),
      ("AX_SAFE_SUBSET_MANIFEST_SHAPE", [x["kind"] for x in ax_projection["manifests"]]==["Workspace","Gateway","Task"] and all(x["apiVersion"]=="ax.io/v1alpha1" for x in ax_projection["manifests"]) and ax_projection["cluster_apply_ready"] is False),
      ("AX_MODEL_RESOURCE_NOT_EMITTED", "Model" not in {x["kind"] for x in ax_projection["manifests"]}),
      ("AX_PINNED_SCHEMA_IMMUTABLE_GIT_GAP_FAILS_CLOSED", expect_ax_error(lambda: compile_ax_provider_bridge(ax_task,[ax_git_ws],ax_net,ax_binding))),
      ("AX_DEBUG_WITHOUT_APPROVAL_FAILS_CLOSED", expect_ax_error(lambda: compile_ax_provider_bridge(ax_task,[ax_ws],ax_net,ax_debug))),
      ("AX_WILDCARD_EGRESS_FAILS_CLOSED", expect_ax_error(lambda: compile_ax_provider_bridge(ax_task,[ax_ws],ax_wild,ax_binding))),
      ("AX_CUSTOM_RUNNER_IMMUTABLE_GIT_PLAN", ax_runner_plan["workspace_materializations"][0]["mode"]=="IMMUTABLE_GIT_COMMIT" and ax_runner_plan["workspace_materializations"][0]["detached_checkout"] is True and ax_runner_plan["google_ax_runtime_promotion_claim"] is False),
      ("AX_CUSTOM_RUNNER_GIT_EGRESS_FAILS_CLOSED", expect_ax_runner_error(lambda: compile_custom_runner_plan(ax_task,[ax_runner_ws],ax_runner_bad_net,ax_binding))),
      ("AX_CLUSTER_APPLY_REQUIRES_VERIFIED_IMAGE_EVIDENCE", ax_cluster_apply_plan["cluster_apply_adapter_materialized"] is True and ax_cluster_apply_plan["runtime_promotion_eligible"] is False and expect_ax_cluster_error(lambda: compile_cluster_apply_plan(ax_projection,ax_runner_plan,ax_runner_bad_evidence,ax_cluster_binding))),
      ("AX_CLUSTER_APPLY_REJECTS_RAW_CLUSTER_CREDENTIALS", expect_ax_cluster_error(lambda: compile_cluster_apply_plan(ax_projection,ax_runner_plan,ax_runner_evidence,ax_cluster_bad_credentials))),
      ("FANOUT_LIMITS_REQUIRED", expect_error(lambda: validate_task(bad_fan))),
      ("ORCHESTRATION_ROUTE_COMPILES_TO_UAF_WORKLOAD",
       compile_orchestration_workload(
          {"schema":"fa3.orchestration-route-decision.v1","task_id":"orch-1","status":"ROUTED","uaf_execution_required":True,
           "resource_boundary":{"resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","requirements":{"cpu_physical_cores":1}},
           "authorized_ai_participants":["agent:def:1"]},
          agent_definition_ref="agent:def:1",workspace_refs=["ws:1"],network_envelope_ref="net:1",
          model_intent={"capability":"coding"},
          fanout_limits={"max_children":2,"max_depth":1,"max_concurrent_children":1,"max_runtime_seconds":300,"max_retries":1,"max_tool_calls":10,"max_model_requests":10},
       )["action_ref"]=="orchestration.execute"),
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
      "orchestration":root/"canonical/profiles/FA3-ORCHESTRATION-WORKFORCE-001.json",
      "work_management":root/"canonical/FA3-WORK-MANAGEMENT-PROJECTION-001.json",
      "surface_registry":root/"canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
      "work_qml":root/"apps/fa3-control-center/qml/WorkManagementPage.qml",
      "current_host":root/"canonical/FA3-AGENT-WORKLOAD-RUNTIME-CURRENT-HOST-CONFORMANCE-001.json",
      "current_host_gate":root/"canonical/FA3-GATE-AGENT-WORKLOAD-RUNTIME-CURRENT-HOST-001.json",
      "ax_bridge_schema":root/"canonical/contracts/FA3-GOOGLE-AX-PROVIDER-BRIDGE-001.schema.json",
      "ax_bridge_intent":root/"canonical/intents/FA3-GOOGLE-AX-PROVIDER-BRIDGE-APPLICATION-INTENT-001.json",
      "ax_bridge_reuse":root/"canonical/assessments/FA3-GOOGLE-AX-PROVIDER-BRIDGE-REUSE-ASSESSMENT-001.json",
      "ax_runner_schema":root/"canonical/contracts/FA3-GOOGLE-AX-CUSTOM-RUNNER-PLAN-001.schema.json",
      "ax_cluster_apply_schema":root/"canonical/contracts/FA3-GOOGLE-AX-CLUSTER-APPLY-PLAN-001.schema.json",
    }
    for name,path in paths.items():
        if not path.is_file(): findings.append(finding("AWR-001","required file missing",name=name,path=path.as_posix()))
    if findings: return {"schema":"fa3.agent-workload-runtime-gate.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}
    p,c,d,a,r,reg,native,podman,ax,enf,g,pol,dr,dm,ev,orch,wm,surfaces,ch,chgate=[load(paths[k]) for k in ("profile","contract","decision","assessment","reference","registry","native","podman","ax","enforcement","gate","policy","dist_registry","dist_manifest","evidence","orchestration","work_management","surface_registry","current_host","current_host_gate")]
    ax_bridge_schema,ax_bridge_intent,ax_bridge_reuse,ax_runner_schema,ax_cluster_apply_schema=[load(paths[k]) for k in ("ax_bridge_schema","ax_bridge_intent","ax_bridge_reuse","ax_runner_schema","ax_cluster_apply_schema")]
    work_qml=paths["work_qml"].read_text(encoding="utf-8")
    checks=[
      (p.get("id")==PROFILE_ID and p.get("priority")=="P0" and p.get("requirement")=="MUST","AWR-010","profile identity/priority drift"),
      (p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==cap and p.get("capability_bindings")==["CAP-028"],"AWR-011","capability/authority baseline drift"),
      (p.get("authority_boundaries",{}).get("durable_workflow")=="TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY" and p.get("authority_boundaries",{}).get("host_resources")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and p.get("authority_boundaries",{}).get("model_routing")=="FA3-AUTH-MODEL-ROUTER-001" and p.get("authority_boundaries",{}).get("tool_mediation")=="FA3-AUTH-MCP-GATEWAY-001","AWR-012","authority boundary drift"),
      (c.get("id")==CONTRACT_ID and c.get("capability_count")==cap and c.get("provider_neutral") is True and c.get("fail_closed") is True,"AWR-013","contract baseline drift"),
      (d.get("id")==DECISION_ID and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("current_host_runtime_promotion_claim") is False,"AWR-014","decision promotion/baseline drift"),
      (a.get("project_id")==ASSESSMENT_ID and a.get("assessment")=="RECOMMENDED" and a.get("project_radar_checked") is True and a.get("capability_delta")==0 and a.get("authority_delta")==0,"AWR-015","Decision Fabric assessment invalid"),
      (r.get("id")==REFERENCE_ID and r.get("commit")==AX_COMMIT and r.get("license")=="Apache-2.0" and r.get("observed_repository_facts",{}).get("api_version")=="ax.io/v1alpha1" and r.get("observed_repository_facts",{}).get("upstream_breaking_changes_warning") is True and r.get("observed_repository_facts",{}).get("workspace_git_immutable_commit_supported") is False and r.get("fa3_interpretation",{}).get("architectural_authority") is False,"AWR-016","Google AX immutable provenance or interpretation drift"),
      (reg.get("id")==REGISTRY_ID and reg.get("provider_self_admission") is False and len(reg.get("providers",[]))==3,"AWR-017","runner registry drift"),
      (native.get("runtime_activation_status")=="PENDING_CURRENT_HOST" and podman.get("runtime_activation_status")=="PENDING_CURRENT_HOST" and ax.get("runtime_activation_status")=="PENDING_RUNNER_IMAGE_BUILD_EVIDENCE_AND_SCOPE_BOUND_CLUSTER_E2E","AWR-018","provider runtime status improperly promoted"),
      (ax.get("activation_mode")=="OPTIONAL_DISABLED_BY_DEFAULT" and ax.get("translation",{}).get("canonical_ax_schema") is False and ax.get("translation",{}).get("ax_model_to_fa3_model_resource") is False and ax.get("translation",{}).get("fa3_agent_workspace_to_ax_workspace")=="PARTIAL_FAIL_CLOSED" and ax.get("runner_bridge",{}).get("manifest_compiler_materialized") is True and ax.get("runner_bridge",{}).get("custom_runner_source_materialized") is True and ax.get("runner_bridge",{}).get("custom_runner_materialized") is False and ax.get("runner_bridge",{}).get("runner_image_build_evidence") is False and ax.get("runner_bridge",{}).get("cluster_apply_adapter_materialized") is True and ax.get("runner_bridge",{}).get("cluster_apply_requires_verified_runner_image_evidence") is True,"AWR-019","Google AX boundary drift"),
      (enf.get("gateset_id")==GATESET_ID and enf.get("fail_closed") is True and "STATIC_REFERENCE_PASS_NOT_CURRENT_HOST_PROMOTION" in enf.get("mandatory_rules",[]),"AWR-020","enforcement rules incomplete"),
      (g.get("id")==GATE_ID and g.get("gateset_id")==GATESET_ID and g.get("regression_case_count")==21 and g.get("current_host_runtime_evidence") is False,"AWR-021","executable gate record drift"),
      (GATESET_ID in set(pol.get("mandatory_reference_gates",[])) and pol.get("agent_workload_runtime_profile_id")==PROFILE_ID and pol.get("agent_workload_runtime_reference_id")==REFERENCE_ID,"AWR-022","global enforcement policy binding missing"),
      (ev.get("status")=="PASS" and ev.get("evidence_class")=="REFERENCE_STATIC_CONFORMANCE" and ev.get("current_host_runtime_promotion_claim") is False,"AWR-023","reference evidence semantics drift"),
      ("FA3-AGENT-WORKLOAD-RUNTIME-CONTRACTS-001" in orch.get("contracts",[]) and orch.get("authority_boundaries",{}).get("workload_execution")=="FA3-AGENT-WORKLOAD-RUNTIME-001_NON_AUTHORITY_TASK_LOCAL_EXECUTION_PROJECTION" and "AGENT_WORKLOAD_RUNTIME_IS_TASK_LOCAL_EXECUTION_PROJECTION_NOT_DURABLE_WORKFLOW_AUTHORITY" in orch.get("invariants",[]),"AWR-032","Orchestration Workforce workload-runtime binding drift"),
      (wm.get("agent_workload_projection",{}).get("profile_id")==PROFILE_ID and wm.get("agent_workload_projection",{}).get("work_item_identity_distinct") is True and wm.get("agent_workload_projection",{}).get("mutation_semantics")=="DRAFT_UAF_INTENT_ONLY" and wm.get("agent_workload_projection",{}).get("direct_runner_execution_from_gui") is False,"AWR-033","Work Management workload projection boundary drift"),
      (any(s.get("route_id")=="home.work-management" and "agent-workloads" in s.get("child_views",[]) and s.get("direct_runtime_execution") is False for s in surfaces.get("surfaces",[])) and "Agent Workloads" in work_qml and "typed UAF draft intent" in work_qml and "nem gyárt RUNNING / PASS / CONNECTED" in work_qml,"AWR-034","GUI workload projection drift or fabricated-state guard missing"),
      (ch.get("id")=="FA3-AGENT-WORKLOAD-RUNTIME-CURRENT-HOST-CONFORMANCE-001" and ch.get("status")=="PENDING_CURRENT_HOST" and ch.get("production_admitted") is False and ch.get("required_runner_labels")==["self-hosted","linux","x64","fa3-current-host"] and chgate.get("current_host_evidence_required") is True,"AWR-035","current-host fail-closed conformance materialization drift"),
      (p.get("runtime_semantics_profile",{}).get("profile_id")=="FA3-AGENT-RUNTIME-SEMANTICS-001" and c.get("runtime_semantics_contract")=="FA3-AGENT-RUNTIME-SEMANTICS-CONTRACTS-001" and "FA3-ADK2-DERIVED-AGENT-RUNTIME-GATESET-001" in set(g.get("child_gates",[])),"AWR-036","ADK2-derived runtime semantics child binding drift"),
      (ax_bridge_schema.get("x-fa3-contract-id")=="FA3-GOOGLE-AX-PROVIDER-BRIDGE-001" and "FA3-GOOGLE-AX-PROVIDER-BRIDGE-001.schema.json" in c.get("contract_schemas",[]),"AWR-037","Google AX provider bridge contract binding drift"),
      (ax_bridge_intent.get("project_id")=="FA3-GOOGLE-AX-PROVIDER-BRIDGE-001" and ax_bridge_intent.get("hardware_audit",{}).get("cpu_only_viable") is True and ax_bridge_intent.get("hardware_audit",{}).get("accelerator_cardinality")=="0..N","AWR-038","Google AX provider bridge ApplicationIntent/Hardware Audit drift"),
      (ax_bridge_reuse.get("result")=="PASS" and ax_bridge_reuse.get("implementation_readiness")=="READY_FOR_STATIC_PROVIDER_BRIDGE_ONLY" and ax_bridge_reuse.get("google_ax_runtime_promotion_claim") is False,"AWR-039","Google AX provider bridge ReuseAssessment drift"),
      (ax_runner_schema.get("x-fa3-contract-id")=="FA3-GOOGLE-AX-CUSTOM-RUNNER-PLAN-001" and "FA3-GOOGLE-AX-CUSTOM-RUNNER-PLAN-001.schema.json" in c.get("contract_schemas",[]),"AWR-042","Google AX custom runner plan contract binding drift"),
      (ax_cluster_apply_schema.get("x-fa3-contract-id")=="FA3-GOOGLE-AX-CLUSTER-APPLY-PLAN-001" and "FA3-GOOGLE-AX-CLUSTER-APPLY-PLAN-001.schema.json" in c.get("contract_schemas",[]),"AWR-043","Google AX cluster apply plan contract binding drift"),
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
    child=adk2_runtime_semantics_gate(root)
    if child["result"]!="PASS": findings.append(finding("AWR-041","ADK2-derived runtime semantics child gate failed",child_gate=child))
    rr=regression_cases()
    if rr["result"]!="PASS": findings.append(finding("AWR-040","runtime contract regression failed",regressions=rr))
    report={"schema":"fa3.agent-workload-runtime-gate.v1","gate_id":GATE_ID,"result":"PASS" if not findings else "FAIL","findings":findings,"regressions":rr,"capability_delta":0,"authority_delta":0,"current_host_runtime_claim":False,"child_gates":{"FA3-ADK2-DERIVED-AGENT-RUNTIME-GATESET-001":child["result"]}}
    out=root/"reports/agent-workload-runtime-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args()
    r=gate(Path(a.root)); print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
