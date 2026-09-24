#!/usr/bin/env python3
from __future__ import annotations

import copy
import re
from typing import Any

TASK_SCHEMA = "fa3.agent-workload-task.v1"
WORKSPACE_SCHEMA = "fa3.agent-workspace.v1"
NETWORK_SCHEMA = "fa3.execution-network-envelope.v1"
CHECKPOINT_SCHEMA = "fa3.agent-checkpoint-manifest.v1"

PHASES = {
    "DECLARED","VALIDATING","ADMISSION_PENDING","ADMITTED","PREPARING","STARTING","RUNNING",
    "PAUSING","PAUSED","RESUMING","SUSPENDING","SUSPENDED","TERMINATING","TERMINATED",
    "COMPLETED","FAILED","REJECTED","LEASE_EXPIRED","LEASE_REVOKED","CHECKPOINT_INCOMPATIBLE","POLICY_REVOKED",
}
TRANSITIONS = {
    "DECLARED":{"VALIDATING","REJECTED"},
    "VALIDATING":{"ADMISSION_PENDING","REJECTED"},
    "ADMISSION_PENDING":{"ADMITTED","REJECTED"},
    "ADMITTED":{"PREPARING","TERMINATING"},
    "PREPARING":{"STARTING","FAILED","TERMINATING"},
    "STARTING":{"RUNNING","FAILED","TERMINATING"},
    "RUNNING":{"COMPLETED","FAILED","PAUSING","SUSPENDING","TERMINATING","LEASE_EXPIRED","LEASE_REVOKED","POLICY_REVOKED"},
    "PAUSING":{"PAUSED","FAILED","TERMINATING"},
    "PAUSED":{"RESUMING","SUSPENDING","TERMINATING"},
    "RESUMING":{"RUNNING","FAILED","CHECKPOINT_INCOMPATIBLE","REJECTED"},
    "SUSPENDING":{"SUSPENDED","FAILED","TERMINATING"},
    "SUSPENDED":{"RESUMING","TERMINATING","CHECKPOINT_INCOMPATIBLE"},
    "TERMINATING":{"TERMINATED"},
}
TERMINAL={"TERMINATED","COMPLETED","FAILED","REJECTED","LEASE_EXPIRED","LEASE_REVOKED","CHECKPOINT_INCOMPATIBLE","POLICY_REVOKED"}
FORBIDDEN_KEYS={
    "api_key","apikey","password","secret","secret_value","token","bearer_token",
    "direct_model_provider","direct_provider_endpoint","model_provider","physical_model_id",
    "gpu_index","gpu_ordinal","cuda_visible_devices","rocr_visible_devices",
}
HEX40=re.compile(r"^[0-9a-f]{40}$")

class WorkloadContractError(ValueError):
    pass

def _walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            k=str(key).lower()
            if k in FORBIDDEN_KEYS:
                raise WorkloadContractError(f"forbidden field {path}.{key}")
            _walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{i}]")

def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def validate_fanout_limits(limits: dict[str, Any]) -> None:
    required=("max_children","max_depth","max_concurrent_children","max_runtime_seconds","max_retries","max_tool_calls","max_model_requests")
    if not isinstance(limits, dict) or any(k not in limits for k in required):
        raise WorkloadContractError("complete fanout limits required")
    for key in required:
        value=limits[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise WorkloadContractError(f"invalid fanout limit: {key}")
    if limits["max_concurrent_children"] > limits["max_children"]:
        raise WorkloadContractError("concurrent child limit exceeds max_children")

def validate_task(task: dict[str, Any]) -> dict[str, Any]:
    if task.get("schema") != TASK_SCHEMA:
        raise WorkloadContractError("task schema mismatch")
    required=("task_id","root_task_id","action_ref","agent_definition_ref","resource_requirements","network_envelope_ref","model_intent","authorized_ai_participants","fanout_limits")
    if any(k not in task for k in required):
        raise WorkloadContractError("task missing required field")
    for key in ("task_id","root_task_id","action_ref","agent_definition_ref","network_envelope_ref"):
        if not _nonempty(task.get(key)):
            raise WorkloadContractError(f"invalid {key}")
    if not isinstance(task.get("resource_requirements"), dict) or not isinstance(task.get("model_intent"), dict):
        raise WorkloadContractError("resource_requirements/model_intent must be objects")
    if any(k in task["model_intent"] for k in ("provider","provider_id","endpoint","model_id")):
        raise WorkloadContractError("physical model/provider pin forbidden; use logical model intent")
    participants=task.get("authorized_ai_participants")
    if not isinstance(participants,list) or not all(_nonempty(x) for x in participants):
        raise WorkloadContractError("authorized_ai_participants invalid")
    validate_fanout_limits(task["fanout_limits"])
    _walk_forbidden(task)
    return copy.deepcopy(task)

def validate_workspace(workspace: dict[str, Any]) -> dict[str, Any]:
    if workspace.get("schema") != WORKSPACE_SCHEMA or not _nonempty(workspace.get("workspace_id")):
        raise WorkloadContractError("workspace identity invalid")
    sources=workspace.get("sources")
    if not isinstance(sources,list):
        raise WorkloadContractError("workspace sources must be list")
    for source in sources:
        if not isinstance(source,dict):
            raise WorkloadContractError("workspace source must be object")
        kind=source.get("kind")
        if kind == "GIT":
            if not _nonempty(source.get("repo")) or not HEX40.fullmatch(str(source.get("commit",""))):
                raise WorkloadContractError("GIT workspace source requires immutable 40-hex commit")
            if source.get("branch") or source.get("tag") or source.get("ref") == "HEAD":
                raise WorkloadContractError("floating git reference forbidden in admitted workspace")
        elif kind == "SKILL":
            if source.get("admission_profile") != "FA3-SKILL-FABRIC-001" or not _nonempty(source.get("skill_ref")):
                raise WorkloadContractError("skill source requires Skill Fabric admission")
        elif kind == "MCP_CAPABILITY":
            if source.get("gateway_authority") != "FA3-AUTH-MCP-GATEWAY-001":
                raise WorkloadContractError("MCP capability must use central gateway")
        elif kind not in {"ARTIFACT","INPUT","SCRATCH","DURABLE_DATA"}:
            raise WorkloadContractError(f"unsupported workspace source kind: {kind}")
    if workspace.get("bootstrap_goal") and workspace.get("bootstrap_mode") != "TYPED_PLAN_REQUIRED":
        raise WorkloadContractError("plain-language workspace goal cannot directly execute")
    _walk_forbidden(workspace)
    return copy.deepcopy(workspace)

def validate_network_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    if envelope.get("schema") != NETWORK_SCHEMA or envelope.get("default") != "DENY":
        raise WorkloadContractError("network envelope must be default deny")
    if envelope.get("direct_model_provider_access") is not False or envelope.get("direct_external_tool_access") is not False:
        raise WorkloadContractError("direct model/tool provider bypass forbidden")
    if not isinstance(envelope.get("egress",[]), list):
        raise WorkloadContractError("egress allowlist must be list")
    _walk_forbidden(envelope)
    return copy.deepcopy(envelope)

def validate_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    if checkpoint.get("schema") != CHECKPOINT_SCHEMA:
        raise WorkloadContractError("checkpoint schema mismatch")
    if checkpoint.get("mode") not in {"APPLICATION","PROCESS","VM"}:
        raise WorkloadContractError("unsupported durable checkpoint mode")
    if checkpoint.get("secret_material_present") is not False or checkpoint.get("secret_handles_detached") is not True:
        raise WorkloadContractError("checkpoint secret hygiene failed")
    if not _nonempty(checkpoint.get("task_id")) or not _nonempty(checkpoint.get("task_spec_digest")):
        raise WorkloadContractError("checkpoint identity incomplete")
    if not isinstance(checkpoint.get("runner_identity"), dict) or not checkpoint["runner_identity"]:
        raise WorkloadContractError("runner identity required")
    _walk_forbidden(checkpoint)
    return copy.deepcopy(checkpoint)

def transition_allowed(current: str, requested: str) -> bool:
    return current in PHASES and requested in TRANSITIONS.get(current,set())

def suspension_semantics(mode: str) -> dict[str, Any]:
    if mode == "PAUSE":
        return {"mode":"PAUSE","durable":False,"resources_released":False,"memory_state_preserved":"RUNNER_DEPENDENT"}
    if mode in {"APPLICATION","PROCESS","VM"}:
        return {"mode":mode,"durable":True,"resources_released":True,"memory_state_preserved": mode in {"PROCESS","VM"}}
    raise WorkloadContractError("unsupported suspension mode")

def runner_eligible(provider: dict[str, Any], requested: set[str], *, admission_receipt_present: bool) -> bool:
    if provider.get("disabled") is True:
        return False
    if provider.get("runtime_promotion_status") != "CURRENT_HOST_PRODUCTION_E2E_PASS":
        return False
    caps={k for k,v in dict(provider.get("capabilities",{})).items() if v is True}
    if not requested.issubset(caps):
        return False
    return admission_receipt_present

def select_runner(providers: list[dict[str, Any]], requested: set[str], *, admission_receipt_present: bool, advisory_selected: str|None=None) -> str:
    eligible=[p for p in providers if runner_eligible(p,requested,admission_receipt_present=admission_receipt_present)]
    eligible.sort(key=lambda p:(int(p.get("priority",100)),str(p.get("provider_id",""))))
    if not eligible:
        raise WorkloadContractError("no admitted eligible runner")
    ids={p["provider_id"] for p in eligible}
    if advisory_selected is not None:
        if advisory_selected not in ids:
            raise WorkloadContractError("advisory selection outside eligible runner set")
        return advisory_selected
    return eligible[0]["provider_id"]

def resume_requirements(checkpoint: dict[str, Any], fresh_hrb_lease_ref: str, *, previous_hrb_lease_ref: str|None=None) -> dict[str, Any]:
    validate_checkpoint(checkpoint)
    if not _nonempty(fresh_hrb_lease_ref):
        raise WorkloadContractError("fresh HRB lease required for resume")
    if previous_hrb_lease_ref and fresh_hrb_lease_ref == previous_hrb_lease_ref:
        raise WorkloadContractError("old HRB lease cannot be reactivated on resume")
    return {"fresh_hrb_lease_ref":fresh_hrb_lease_ref,"old_lease_reused":False,"checkpoint_mode":checkpoint["mode"]}

def project_to_ax(task: dict[str, Any], workspace: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    validate_task(task); validate_workspace(workspace); validate_network_envelope(envelope)
    git=[{"repo":s["repo"],"commit":s["commit"]} for s in workspace["sources"] if s.get("kind")=="GIT"]
    return {
        "schema":"fa3.google-ax-projection.v1",
        "canonical_ir":False,
        "authority":False,
        "upstream_api_version":"ax.io/v1alpha1",
        "task":{"kind":"Task","metadata":{"name":task["task_id"]},"model_resource_emitted":False},
        "workspace":{"kind":"Workspace","metadata":{"name":workspace["workspace_id"]},"git":git},
        "gateway":{"kind":"Gateway","default":"DENY","egress":copy.deepcopy(envelope.get("egress",[]))},
        "model_intent_forwarding":{"authority":"FA3-AUTH-MODEL-ROUTER-001","physical_provider_pin":False},
    }
