#!/usr/bin/env python3
from __future__ import annotations

from fa3_release_baseline import module_active_capability_count
import argparse
import json
from pathlib import Path
from typing import Any

PROFILE_ID="FA3-INFERENCE-PORTABILITY-CURRENT-HOST-001"
GATE_ID="FA3-INFERENCE-PORTABILITY-CURRENT-HOST-GATESET-001"
DECISION_ID="FA3-DEC-INFERENCE-PORTABILITY-CURRENT-HOST-2026-09-23"
PENDING_EVIDENCE="evidence/reference/inference-portability-current-host-pending.json"
RECEIPT_SCHEMA="fa3.inference-portability-current-host-receipt.v1"
PROVIDER_IDS=['FA3-PROVIDER-OPENVINO-001','FA3-PROVIDER-ONNXRUNTIME-001','FA3-PROVIDER-TENSORRT-001','FA3-PROVIDER-TENSORRT-RTX-001']
CAPABILITY_IDS=['CAP-005','CAP-006','CAP-137','CAP-143']
RULES=(
  'INFERENCE_CURRENT_HOST_OPTIONAL_PROVIDER_ABSENCE_IS_NOT_GLOBAL_FAILURE',
  'INFERENCE_CURRENT_HOST_DISCOVERY_MUST_NOT_INSTALL_DOWNLOAD_OR_MUTATE_PROVIDER_RUNTIME',
  'INFERENCE_CURRENT_HOST_CPU_ONLY_HOST_REMAINS_GLOBALLY_CONFORMANT',
  'INFERENCE_CURRENT_HOST_PROVIDER_PRESENCE_IS_NOT_RUNTIME_ADMISSION',
  'INFERENCE_CURRENT_HOST_EXACT_RUNTIME_IDENTITY_MUST_BE_RECORDED',
  'INFERENCE_CURRENT_HOST_REFERENCE_VERSION_MATCH_IS_NOT_AUTOMATIC_PROMOTION',
  'INFERENCE_CURRENT_HOST_OPENVINO_ACCELERATOR_PATH_REQUIRES_DEVICE_BOUND_BACKEND_AND_HRB',
  'INFERENCE_CURRENT_HOST_ORT_ACCELERATOR_EP_REQUIRES_DEVICE_BOUND_BACKEND_AND_HRB',
  'INFERENCE_CURRENT_HOST_TENSORRT_REQUIRES_ACCELERATOR_HRB_E2E_FOR_RUNTIME_PASS',
  'INFERENCE_CURRENT_HOST_TENSORRT_RTX_REQUIRES_ACCELERATOR_HRB_E2E_FOR_RUNTIME_PASS',
  'INFERENCE_CURRENT_HOST_EXECUTION_PROVIDER_CANNOT_BECOME_MODEL_ROUTER',
  'INFERENCE_CURRENT_HOST_PROBE_IS_NOT_AGENT_NATIVE_ACTION_OR_AUTHORITY',
  'INFERENCE_CURRENT_HOST_BACKEND_DISCOVERY_CANNOT_EXPAND_AI_PARTICIPANT_SET',
  'INFERENCE_CURRENT_HOST_PRODUCTION_PROMOTION_REQUIRES_CANONICAL_MODEL_ROUTER_ROUTE_E2E',
  'INFERENCE_CURRENT_HOST_NO_SILENT_CPU_DEVICE_BACKEND_OR_CLOUD_FALLBACK',
  'INFERENCE_CURRENT_HOST_RECEIPT_MUST_BIND_RELEASE_AND_HOST_EVIDENCE',
  'INFERENCE_CURRENT_HOST_PROVIDER_EVIDENCE_DOES_NOT_REOPEN_429_CLOSURE',
  'INFERENCE_CURRENT_HOST_SELF_HOSTED_EXECUTION_REQUIRED_FOR_RUNTIME_EVIDENCE',
  'INFERENCE_CURRENT_HOST_SMOKE_MODEL_IS_EPHEMERAL_TEST_ARTIFACT_NOT_MODEL_REGISTRY_PROMOTION',
  'INFERENCE_CURRENT_HOST_ABSENT_OR_UNADMITTED_PROVIDER_HAS_ZERO_PRODUCTION_CLAIM'
)
CAPABILITY_COUNT=module_active_capability_count(__file__)

def load(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def write(path: Path,obj: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def finding(code: str,message: str,**extra: Any) -> dict[str,Any]:
    return {"code":code,"severity":"P0","message":message,**extra}

def reference_gate(root: Path) -> dict[str,Any]:
    paths={
      "profile":root/"canonical/FA3-INFERENCE-PORTABILITY-CURRENT-HOST-001.json",
      "decision":root/"canonical/decisions/FA3-DEC-INFERENCE-PORTABILITY-CURRENT-HOST-2026-09-23.json",
      "enforcement":root/"canonical/inference-portability-current-host-enforcement.json",
      "schema":root/"canonical/schemas/inference-portability-current-host-receipt.v1.json",
      "pending":root/PENDING_EVIDENCE,
      "manifest":root/"fa3-current-host/manifest.json",
      "policy":root/"canonical/enforcement-policy.json",
      "registry":root/"evidence/evidence-registry.json",
      "projection":root/"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    }
    findings=[]
    for key,path in paths.items():
        if not path.is_file(): findings.append(finding("INFER-CH-001","missing current-host artifact",artifact=key,path=str(path.relative_to(root))))
    if findings: return {"result":"FAIL","findings":findings}
    profile=load(paths["profile"]); decision=load(paths["decision"]); enf=load(paths["enforcement"])
    pending=load(paths["pending"]); manifest=load(paths["manifest"]); policy=load(paths["policy"])
    registry=load(paths["registry"]); projection=load(paths["projection"])
    if not (
      profile.get("id")==PROFILE_ID and profile.get("capability_count")==CAPABILITY_COUNT
      and profile.get("new_capabilities")==0 and profile.get("new_architectural_authorities")==0
      and profile.get("provider_ids")==list(PROVIDER_IDS)
      and profile.get("provider_absence_semantics")=="ABSENT_OPTIONAL_NOT_GLOBAL_FAILURE"
      and profile.get("cpu_only_host_conforms") is True
      and profile.get("promotion_boundary",{}).get("global_promotion") is False
      and profile.get("invariants")==list(RULES)
    ): findings.append(finding("INFER-CH-010","current-host profile drift"))
    if not (
      decision.get("id")==DECISION_ID
      and decision.get("capability_source_decision_projection")=="NON_OBLIGATION_BEARING_PROVIDER_SPECIFIC_CURRENT_HOST_PRE_ADMISSION"
      and decision.get("current_host_obligation_delta")==0
      and decision.get("existing_429_closure_reopened") is False
      and decision.get("global_promotion_claim") is False
    ): findings.append(finding("INFER-CH-011","decision/429 boundary drift"))
    if not (
      enf.get("gate_id")==GATE_ID and enf.get("fail_closed") is True
      and enf.get("p0_invariants")==list(RULES) and enf.get("mandatory_rule_count")==len(RULES)
      and enf.get("optional_provider_absence_is_failure") is False
      and enf.get("global_promotion_claim") is False
    ): findings.append(finding("INFER-CH-012","enforcement drift"))
    if not (
      pending.get("status")=="PENDING_REAL_SELF_HOSTED_PROVIDER_INVENTORY"
      and pending.get("current_host_provider_runtime_promotion_claim") is False
      and pending.get("existing_429_closure_reopened") is False
    ): findings.append(finding("INFER-CH-013","pending evidence drift"))
    if (
      GATE_ID not in policy.get("mandatory_reference_gates",[])
      or policy.get("inference_portability_current_host_p0_rules")!=list(RULES)
      or policy.get("inference_portability_current_host_provider_ids")!=list(PROVIDER_IDS)
    ): findings.append(finding("INFER-CH-014","global policy binding drift"))
    surface=next((x for x in manifest.get("registered_current_host_surfaces",[]) if x.get("name")=="inference-portability-provider-pre-admission"),{})
    required={
      ".github/workflows/fa3-inference-portability-current-host.yml",
      "canonical/FA3-INFERENCE-PORTABILITY-CURRENT-HOST-001.json",
      "canonical/inference-portability-current-host-enforcement.json",
      "evidence/collect-inference-portability-current-host.py",
      "src/fa3_inference_portability_current_host_gate.py",
      "tests/test_inference_portability_current_host_gate.py",
    }
    missing=sorted(required-set(manifest.get("required_repository_paths",[])))
    if not (
      surface.get("gate")=="inference-current-host"
      and surface.get("optional_provider_absence_is_failure") is False
      and surface.get("existing_429_closure_reopened") is False
      and surface.get("global_promotion_claim") is False
      and not missing
    ): findings.append(finding("INFER-CH-015","current-host manifest surface drift",missing_paths=missing))
    records={r.get("subject_id"):r for r in registry.get("records",[])}
    bad=[]
    for cap in CAPABILITY_IDS:
        rec=records.get(cap,{})
        binding=rec.get("inference_portability_current_host_projection_status",{})
        if (
          DECISION_ID in rec.get("source_decision_ids",[])
          or PENDING_EVIDENCE not in rec.get("evidence_artifacts",[])
          or binding.get("binding_class")!="NON_OBLIGATION_BEARING_PROVIDER_SPECIFIC_CURRENT_HOST_PRE_ADMISSION"
          or binding.get("existing_429_closure_reopened") is not False
          or binding.get("current_host_obligation_delta")!=0
        ): bad.append(cap)
    if bad: findings.append(finding("INFER-CH-016","Evidence Registry binding drift",capability_ids=bad))
    prj=projection.get("inference_portability_current_host_reconciliation",{})
    manifest_paths={x.get("path") for x in projection.get("manifest",[])}
    required_release={
      "canonical/FA3-INFERENCE-PORTABILITY-CURRENT-HOST-001.json",
      "canonical/decisions/FA3-DEC-INFERENCE-PORTABILITY-CURRENT-HOST-2026-09-23.json",
      "canonical/inference-portability-current-host-enforcement.json",
      "evidence/collect-inference-portability-current-host.py",
      "src/fa3_inference_portability_current_host_gate.py",
      "tests/test_inference_portability_current_host_gate.py",
      PENDING_EVIDENCE,
    }
    missing_release=sorted(required_release-manifest_paths)
    if not (
      prj.get("profile_id")==PROFILE_ID and prj.get("gate_id")==GATE_ID
      and prj.get("current_host_obligation_delta")==0
      and prj.get("existing_429_closure_reopened") is False
      and prj.get("provider_runtime_promotion_claim") is False
      and prj.get("capability_count_after")==CAPABILITY_COUNT
      and not missing_release
    ): findings.append(finding("INFER-CH-017","release projection reconciliation drift",missing_manifest=missing_release))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def validate_runtime_receipt(receipt: dict[str,Any]) -> dict[str,Any]:
    findings=[]
    if receipt.get("schema")!=RECEIPT_SCHEMA: findings.append(finding("INFER-CH-R001","receipt schema mismatch"))
    if receipt.get("current_host") is not True or receipt.get("synthetic") is not False or receipt.get("ci_reference_only") is not False:
        findings.append(finding("INFER-CH-R002","receipt is not real current-host evidence"))
    pol=receipt.get("collection_policy",{})
    if not (pol.get("read_only") is True and pol.get("network_fetch") is False and pol.get("package_install") is False and pol.get("provider_mutation") is False and pol.get("secret_collection")=="PROHIBITED"):
        findings.append(finding("INFER-CH-R003","collector safety boundary drift"))
    providers=receipt.get("providers",[])
    if [p.get("provider_id") for p in providers] != list(PROVIDER_IDS):
        findings.append(finding("INFER-CH-R004","provider inventory identity/order drift"))
    for p in providers:
        pid=p.get("provider_id"); state=p.get("admission_state")
        if p.get("production_runtime_promoted") is not False or p.get("global_promotion_claim") is not False:
            findings.append(finding("INFER-CH-R005","pre-admission receipt made promotion claim",provider_id=pid))
        if p.get("model_router_semantics")!="PROBE_ONLY_NOT_ROUTING_AUTHORITY":
            findings.append(finding("INFER-CH-R006","provider probe claimed routing semantics",provider_id=pid))
        if p.get("agent_native_action") is not False or p.get("ai_participant_set_expanded") is not False:
            findings.append(finding("INFER-CH-R007","probe expanded agent/comms semantics",provider_id=pid))
        if p.get("network_fetch") is not False or p.get("runtime_mutation") is not False:
            findings.append(finding("INFER-CH-R008","provider probe mutated/fetched runtime",provider_id=pid))
        if p.get("presence_status")=="ABSENT_OPTIONAL":
            if state!="ABSENT_OPTIONAL":
                findings.append(finding("INFER-CH-R009","absent provider state mismatch",provider_id=pid))
            continue
        if not p.get("runtime_version") and p.get("probe_status")=="PRESENT":
            findings.append(finding("INFER-CH-R010","present provider missing runtime version",provider_id=pid))
        for candidate in p.get("execution_candidates",[]):
            if candidate.get("execution_kind")=="ACCELERATOR":
                if candidate.get("binding_scope")!="HOST_UNBOUND":
                    # A future E2E reconciler may provide DEVICE only with a real HRB-bound execution receipt;
                    # this pre-admission collector is intentionally not authorized to mint one.
                    findings.append(finding("INFER-CH-R011","pre-admission collector claimed device-bound accelerator path",provider_id=pid))
                if candidate.get("runtime_promotion_eligible") is not False:
                    findings.append(finding("INFER-CH-R012","accelerator discovery claimed promotion eligibility",provider_id=pid))
        if state and "PRODUCTION" in state and state!="CPU_SMOKE_PASS_PRODUCTION_ROUTE_PENDING":
            findings.append(finding("INFER-CH-R013","unexpected production state",provider_id=pid,state=state))
    result=receipt.get("result",{})
    non_claims=set(result.get("non_claims",[]))
    required_non={"GLOBAL_FA3_PROMOTION","GLOBAL_429_REOPEN","PROVIDER_PRODUCTION_RUNTIME_PASS","ACCELERATOR_E2E_WITHOUT_HRB","MODEL_ROUTER_PRODUCTION_ROUTE_E2E"}
    if result.get("status")!="PASS" or not required_non.issubset(non_claims):
        findings.append(finding("INFER-CH-R014","receipt result/non-claims drift"))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root: Path,receipt_path: Path | None=None) -> dict[str,Any]:
    ref=reference_gate(root)
    runtime={"result":"NOT_RUN","findings":[]}
    if receipt_path is not None:
        if not receipt_path.is_file():
            runtime={"result":"FAIL","findings":[finding("INFER-CH-R000","runtime receipt missing",path=str(receipt_path))]}
        else:
            runtime=validate_runtime_receipt(load(receipt_path))
    ok=ref["result"]=="PASS" and runtime["result"] in {"PASS","NOT_RUN"}
    report={
      "schema":"fa3.inference-portability-current-host-gate-report.v1","gate_id":GATE_ID,
      "profile_id":PROFILE_ID,"result":"PASS" if ok else "FAIL","reference":ref,"runtime":runtime,
      "runtime_receipt_supplied":receipt_path is not None,
      "provider_runtime_promotion_claim":False,"global_promotion_claim":False,
      "current_host_obligation_delta":0,"existing_429_closure_reopened":False,
    }
    write(root/"reports/inference-portability-current-host-gate-report.json",report)
    return report

def main() -> int:
    ap=argparse.ArgumentParser(description="FA3 inference portability current-host pre-admission gate")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--receipt")
    args=ap.parse_args()
    root=Path(args.root).resolve()
    receipt=Path(args.receipt).resolve() if args.receipt else None
    report=gate(root,receipt)
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
