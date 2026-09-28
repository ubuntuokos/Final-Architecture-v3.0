#!/usr/bin/env python3
"""PR Watch -> *existing admitted* UAF agent.workload.start bridge.

No standalone agent executor, provider choice, resource grant, model route,
Temporal engine, GitHub token or success declaration lives in this adapter.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from fa3_agent_workload import validate_task
from fa3_goal_execution import digest as goal_digest, validate_goal
from fa3_pr_watch import PRWatchDenied
from fa3_uaf import ActionDispatcher, ActionRequest, ExecutionContext

HEX40=re.compile(r"^[a-f0-9]{40}$")
ACTION="agent.workload.start"


def sha256_ref(payload:Any)->str:
    return "sha256:"+hashlib.sha256(json.dumps(
        payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def build_admitted_start_request(
    item:dict[str,Any], preview:dict[str,Any], goal:dict[str,Any],
    *, task_id:str, principal:dict[str,Any],
    runtime_admission_receipt_ref:str, task_spec_ref:str, execution_plan_ref:str,
    approval:dict[str,Any],
)->ActionRequest:
    """Build exact-SHA request; actual Security/HRB admission is never delegated here."""
    goal=validate_goal(goal)
    plan=preview.get("proposal") if isinstance(preview,dict) else None
    if not isinstance(item,dict) or not isinstance(plan,dict):
        raise PRWatchDenied("PLAN_OR_SOURCE_MISSING")
    repo=item.get("repository")
    head=item.get("head_sha")
    if (item.get("kind")!="PR" or not isinstance(repo,str) or not repo
            or not isinstance(head,str) or not HEX40.fullmatch(head)
            or preview.get("source_sha")!=head
            or preview.get("external_key")!=item.get("external_key")
            or preview.get("authority") is not False
            or preview.get("execution_performed") is not False
            or plan.get("schema")!="fa3.goal-plan.v1"
            or plan.get("status")!="PLAN_ONLY_REQUIRES_EXISTING_AUTHORITY_ADMISSION"
            or plan.get("goal_digest")!=goal_digest(goal)
            or plan.get("goal_revision")!=goal["revision"]
            or plan.get("authority") is not False
            or plan.get("execution_performed") is not False
            or plan.get("temporal_lifecycle_authority")!="EXISTING_TEMPORAL_ONLY"):
        raise PRWatchDenied("PLAN_SOURCE_OR_AUTHORITY_DRIFT")
    preflight=plan.get("preflight_references",{})
    if preflight.get("source_sha")!=head or preflight.get("repository_scope")!=repo:
        raise PRWatchDenied("PLAN_PREFLIGHT_SCOPE_DRIFT")
    choices=[s for s in plan.get("steps",[]) if isinstance(s,dict) and s.get("task_id")==task_id]
    if len(choices)!=1:
        raise PRWatchDenied("TASK_NOT_UNIQUE_IN_PLAN")
    step=choices[0]
    task=validate_task(step.get("workload_candidate"))
    if step.get("runtime_admission")!="PENDING_EXISTING_AUTHORITIES" or step.get("execution_performed") is not False:
        raise PRWatchDenied("TASK_RUNTIME_STATE_DRIFT")
    if (task.get("task_id")!=task_id or task.get("root_task_id")!=goal["goal_id"]
            or task.get("action_ref")!=step.get("uaf_action_ref")
            or task.get("authorized_ai_participants")!=goal["execution_policy"]["authorized_ai_participants"]):
        raise PRWatchDenied("WORKLOAD_TASK_IDENTITY_DRIFT")
    if task_spec_ref!=sha256_ref(task) or execution_plan_ref!=sha256_ref(plan):
        raise PRWatchDenied("IMMUTABLE_TASK_OR_PLAN_REF_INVALID")
    if not isinstance(runtime_admission_receipt_ref,str) or not runtime_admission_receipt_ref.startswith("receipt:"):
        raise PRWatchDenied("RUNTIME_RECEIPT_REQUIRED")
    if (not isinstance(principal,dict) or not isinstance(principal.get("id"),str)
            or not principal["id"].strip()
            or not isinstance(approval,dict) or not approval):
        raise PRWatchDenied("PRINCIPAL_AND_EXTERNAL_APPROVAL_REQUIRED")
    operation=hashlib.sha256(
        (item["external_key"]+"\0"+head+"\0"+goal_digest(goal)+"\0"+task_id).encode()
    ).hexdigest()
    return ActionRequest(
        action_id=ACTION,
        arguments={
            "operation_id":"fa3-pr-watch-"+operation,
            "workload_id":task_id,
            "task_spec_ref":task_spec_ref,
            "runtime_admission_receipt_ref":runtime_admission_receipt_ref,
            "execution_plan_ref":execution_plan_ref,
            "reason":"Scoped PR Watch request from immutable approved source SHA "+head,
        },
        principal=principal,
        context=ExecutionContext(context_id="pr-watch:"+operation,
            workspace=repo,application="FA3 Work Management",
            selection={"external_key":item["external_key"],"source_sha":head,"task_id":task_id}),
        approval=approval,
    )


def dispatch_with_existing_uaf(
    request:ActionRequest,dispatcher:ActionDispatcher,
)->dict[str,Any]:
    """No UAF substitute: enforce *external* Security approval, HRB, provider and evidence."""
    if not isinstance(dispatcher,ActionDispatcher) or request.action_id!=ACTION:
        raise PRWatchDenied("EXISTING_UAF_REQUIRED")
    if (dispatcher.authorize is None or dispatcher.verify_approval is None
            or dispatcher.acquire_resources is None or dispatcher.release_resources is None
            or dispatcher.evidence_sink is None):
        raise PRWatchDenied("UAF_SECURITY_HRB_EVIDENCE_BRIDGES_REQUIRED")
    contract=dispatcher.registry.get(ACTION)
    if contract.resources.get("hrb_required") is not True or contract.evidence.get("required") is not True:
        raise PRWatchDenied("RUNTIME_ACTION_CONTRACT_DRIFT")
    if dispatcher.verify_approval(request,contract) is not True:
        raise PRWatchDenied("EXTERNAL_APPROVAL_DENIED")
    result=dispatcher.execute(request)
    if result.status!="success" or not isinstance(result.evidence,dict):
        raise PRWatchDenied("UAF_EFFECT_OR_RECEIPT_MISSING")
    return {"schema":"fa3.pr-watch-uaf-dispatch.v1",
        "status":"SUBMITTED_TO_EXISTING_UAF_NOT_VERIFIED",
        "uaf_action_id":result.action_id,"uaf_request_id":result.request_id,
        "provider_id":result.provider_id,
        "existing_uaf_receipt":result.evidence,
        "canonical_evidence_verified":False,
        "global_promotion_claim":False}
