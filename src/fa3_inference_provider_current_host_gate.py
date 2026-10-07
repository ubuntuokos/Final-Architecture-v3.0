#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

CONFORMANCE_ID="FA3-INFERENCE-PROVIDER-CURRENT-HOST-CONFORMANCE-001"
PARENT_GATE_ID="FA3-INFERENCE-PORTABILITY-GATESET-001"
MATERIALIZATION_SUBGATE_ID="FA3-INFERENCE-PROVIDER-CURRENT-HOST-MATERIALIZATION-001"
CURRENT_HOST_GATE_ID="FA3-GATE-INFERENCE-PROVIDER-CURRENT-HOST-001"
DECISION_ID="FA3-DEC-INFERENCE-PROVIDER-CURRENT-HOST-2026-09-23"
AGGREGATE_RECEIPT="evidence/receipts/inference-provider-current-host.json"
REFERENCE_EVIDENCE="evidence/reference/inference-provider-current-host-materialization-ci-2026-09-23.json"
PROVIDERS=['FA3-PROVIDER-OPENVINO-001','FA3-PROVIDER-ONNXRUNTIME-001','FA3-PROVIDER-TENSORRT-001','FA3-PROVIDER-TENSORRT-RTX-001']
RULES=['PROVIDER_ABSENCE_IS_PROBE_ENVIRONMENT_SCOPED_AND_NEVER_HOST_WIDE_BY_DEFAULT','PROVIDER_ADMISSION_CLAIM_REQUIRES_REAL_CURRENT_HOST_EXECUTION','PROVIDER_RUNTIME_VERSION_AND_EXECUTION_IDENTITY_ARE_EXACTLY_RECORDED_AND_IMMUTABLE_ADMISSION_PIN_MATCHED','CPU_SCOPE_MUST_NOT_REQUIRE_OR_CARRY_ACCELERATOR_LEASE','ACCELERATOR_SCOPE_REQUIRES_EXACT_DEVICE_BOUND_HRB_LEASE','NVIDIA_ACCELERATOR_SCOPE_REQUIRES_EXPLICIT_SUPPORT_MATRIX_RECEIPT','DECISION_FABRIC_ADVISORY_MAY_NOT_EXPAND_OR_AUTHORIZE_PROVIDER_CANDIDATES','DIRECT_PROVIDER_PROBE_IS_ADMISSION_HARNESS_ONLY_NOT_APPLICATION_ROUTING','NO_AUTO_INSTALL_AND_NO_NETWORK_MODEL_FETCH_DURING_ADMISSION','MODEL_ROUTER_MAY_CONSUME_ONLY_SCOPE_BOUND_ADMITTED_PROVIDER_RECEIPTS','TENSORRT_RTX_PRODUCTION_ADMISSION_REQUIRES_RUNTIME_CACHE_OBSERVABILITY','CURRENT_HOST_PROVIDER_ADMISSION_NEVER_IMPLIES_GLOBAL_FA3_PROMOTION']
CAPABILITY_COUNT=module_active_capability_count(__file__)
EVIDENCE_LEVEL="CURRENT_HOST_PROVIDER_SCOPE_PRODUCTION_E2E_PASS"


def loadj(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, value: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


def finding(code: str, message: str, **extra: Any) -> dict[str,Any]:
    return {"code":code,"severity":"P0","message":message,**extra}


def advisory_valid(trace: Any, present: set[str]) -> bool:
    if not isinstance(trace,dict) or trace.get("authority") is not False or trace.get("candidate_set_expanded") is not False:
        return False
    if not present:
        return trace.get("status")=="NO_DECISION" and trace.get("candidate_ids")==[]
    result=trace.get("result") or {}
    ranked=result.get("ranked") if isinstance(result,dict) else None
    return trace.get("status")=="DECIDED" and isinstance(ranked,list) and set(ranked)==present and len(ranked)==len(present)


def _sha256_value(value: Any) -> bool:
    return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdef" for c in value)


def runtime_identity_valid(rec: dict[str,Any]) -> bool:
    probe=rec.get("probe_environment")
    identity=rec.get("runtime_identity")
    module=rec.get("module")
    cli=rec.get("cli")
    if not all(isinstance(x,dict) for x in (probe,identity,module,cli)):
        return False
    if identity.get("environment_id")!=probe.get("environment_id"):
        return False
    for path_key,sha_key in (("python_executable","python_executable_sha256"),("cli_path","cli_sha256")):
        if identity.get(path_key)!=probe.get(path_key) or identity.get(sha_key)!=probe.get(sha_key):
            return False
        path=probe.get(path_key)
        digest=probe.get(sha_key)
        if path is None:
            if digest not in (None,""):
                return False
        elif not str(path).strip() or not _sha256_value(digest):
            return False
    if module.get("present") is True:
        if identity.get("module_file")!=module.get("module_file") or identity.get("module_file_sha256")!=module.get("module_file_sha256"):
            return False
        if not str(identity.get("module_file") or "").strip() or not _sha256_value(identity.get("module_file_sha256")):
            return False
    else:
        if identity.get("module_file") not in (None,"") or identity.get("module_file_sha256") not in (None,""):
            return False
    if cli.get("path")!=identity.get("cli_path") or cli.get("sha256")!=identity.get("cli_sha256"):
        return False
    return True


def scope_valid(scope: dict[str,Any]) -> bool:
    required={"scope_id","execution_kind","status","evidence_level","e2e","runtime_pin","model_probe_sha256","hardware_binding","support_matrix"}
    if not required.issubset(scope):
        return False
    if scope.get("status")!="ADMITTED":
        return True
    if scope.get("evidence_level")!=EVIDENCE_LEVEL or (scope.get("e2e") or {}).get("result")!="PASS":
        return False
    hb=scope.get("hardware_binding") or {}
    if scope.get("execution_kind")=="CPU":
        return hb.get("accelerator") is False and hb.get("hrb_lease") in (None,{})
    if scope.get("execution_kind")=="ACCELERATOR":
        lease=hb.get("hrb_lease") or {}
        sm=scope.get("support_matrix") or {}
        return hb.get("accelerator") is True and lease.get("result")=="PASS" and sm.get("result")=="PASS"
    return False


def provider_receipt_valid(rec: dict[str,Any]) -> bool:
    required={"provider_id","provider_version","reference_version","reference_version_match","admission_pin","admission_pin_match","admission_identity_match","runtime_identity","present","status","admitted_scopes","scopes","probe_environment","module","cli","host_wide_absence_claim","direct_probe_scope","auto_install_performed","network_model_fetch_performed","global_promotion_claim"}
    if not required.issubset(rec) or rec.get("provider_id") not in PROVIDERS:
        return False
    if rec.get("direct_probe_scope")!="ADMISSION_HARNESS_ONLY_NOT_APPLICATION_PATH":
        return False
    probe=rec.get("probe_environment")
    if not isinstance(probe,dict) or not str(probe.get("environment_id","")).strip():
        return False
    if probe.get("discovery_scope") not in {"DEFAULT_RUNNER_ENVIRONMENT_ONLY","EXPLICIT_RUNTIME_ENVIRONMENT"}:
        return False
    if probe.get("host_wide_absence_claim") is not False or rec.get("host_wide_absence_claim") is not False:
        return False
    if not runtime_identity_valid(rec):
        return False
    if rec.get("auto_install_performed") is not False or rec.get("network_model_fetch_performed") is not False or rec.get("global_promotion_claim") is not False:
        return False
    scopes=rec.get("scopes")
    admitted=rec.get("admitted_scopes")
    if not isinstance(scopes,dict) or not isinstance(admitted,list):
        return False
    if any(name not in scopes for name in admitted):
        return False
    if any(not scope_valid(s) for s in scopes.values() if isinstance(s,dict)):
        return False
    if rec.get("present") is False and rec.get("status")!="NOT_PRESENT_IN_PROBE_ENVIRONMENT":
        return False
    if admitted:
        pin=rec.get("admission_pin") or {}
        if rec.get("present") is not True or rec.get("admission_pin_match") is not True or rec.get("admission_identity_match") is not True or rec.get("status")!="ADMITTED":
            return False
        if pin.get("result")!="PASS" or pin.get("identity_match") is not True or (pin.get("entry") or {}).get("runtime_identity")!=rec.get("runtime_identity"):
            return False
        if rec.get("provider_id") in {"FA3-PROVIDER-TENSORRT-001","FA3-PROVIDER-TENSORRT-RTX-001"}:
            if not rec.get("runtime_identity",{}).get("cli_path") or not _sha256_value(rec.get("runtime_identity",{}).get("cli_sha256")):
                return False
        for name in admitted:
            if scopes[name].get("status")!="ADMITTED":
                return False
    if rec.get("provider_id")=="FA3-PROVIDER-TENSORRT-RTX-001" and admitted:
        # Cache-hardening proof is mandatory for actual production admission.
        for name in admitted:
            cache=(scopes[name].get("runtime_cache_observability") or {})
            if cache.get("result")!="PASS":
                return False
    return True


def materialization_gate(root: Path) -> dict[str,Any]:
    root=root.resolve()
    findings=[]
    paths={
      "conformance":root/"canonical/FA3-INFERENCE-PROVIDER-CURRENT-HOST-CONFORMANCE-001.json",
      "enforcement":root/"canonical/inference-provider-current-host-enforcement.json",
      "decision":root/"canonical/decisions/FA3-DEC-INFERENCE-PROVIDER-CURRENT-HOST-2026-09-23.json",
      "profile":root/"canonical/profiles/FA3-INFERENCE-PORTABILITY-001.json",
      "contract":root/"canonical/contracts/FA3-INFERENCE-PORTABILITY-CONTRACTS-001.json",
      "evidence":root/REFERENCE_EVIDENCE,
      "collector":root/"src/fa3_inference_provider_current_host.py",
      "workflow":root/".github/workflows/fa3-inference-provider-current-host.yml",
      "runtime_descriptor_schema":root/"canonical/contracts/FA3-INFERENCE-PROVIDER-RUNTIME-DESCRIPTOR-001.schema.json",
    }
    for key,p in paths.items():
        if not p.is_file():
            findings.append(finding("INFER-HOST-MAT-001","required materialization artifact missing",artifact=key,path=str(p.relative_to(root))))
    if findings:
        return {"result":"FAIL","findings":findings}
    con=loadj(paths["conformance"]); enf=loadj(paths["enforcement"]); dec=loadj(paths["decision"])
    profile=loadj(paths["profile"]); contract=loadj(paths["contract"]); evid=loadj(paths["evidence"])
    if not (
      con.get("id")==CONFORMANCE_ID and con.get("current_host_gate")==CURRENT_HOST_GATE_ID
      and con.get("materialization_subgate")==MATERIALIZATION_SUBGATE_ID
      and con.get("provider_ids")==list(PROVIDERS) and con.get("capability_count")==CAPABILITY_COUNT
      and con.get("new_capability") is False and con.get("new_architectural_authority") is False
      and con.get("invariants")==list(RULES)
    ):
        findings.append(finding("INFER-HOST-MAT-010","conformance record drift"))
    if not (
      enf.get("materialization_subgate_id")==MATERIALIZATION_SUBGATE_ID and enf.get("current_host_gate_id")==CURRENT_HOST_GATE_ID
      and enf.get("fail_closed") is True and enf.get("p0_invariants")==list(RULES)
      and enf.get("provider_absence_global_failure") is False and enf.get("explicit_required_provider_failure") is True
      and enf.get("existing_429_closure_reopened") is False
    ):
        findings.append(finding("INFER-HOST-MAT-011","enforcement record drift"))
    if not (
      dec.get("id")==DECISION_ID and dec.get("source_decision_obligation") is False
      and dec.get("existing_429_closure_reopened") is False and dec.get("current_host_obligation_delta")==0
      and dec.get("new_capabilities")==0 and dec.get("new_architectural_authorities")==0
    ):
        findings.append(finding("INFER-HOST-MAT-012","decision/evidence-boundary drift"))
    pha=profile.get("current_host_provider_admission") or {}
    if not (
      pha.get("conformance_id")==CONFORMANCE_ID and pha.get("current_host_gate_id")==CURRENT_HOST_GATE_ID
      and pha.get("automatic_install")=="FORBIDDEN" and pha.get("network_model_fetch")=="FORBIDDEN"
      and pha.get("global_promotion_claim") is False
      and pha.get("host_wide_absence_claim") is False
      and pha.get("automatic_environment_scanning") is False
    ):
        findings.append(finding("INFER-HOST-MAT-013","profile current-host admission binding drift"))
    sem=contract.get("current_host_admission_semantics") or {}
    if not (
      "ProviderCurrentHostAdmissionReceipt" in contract.get("contracts",[])
      and "ProviderScopeAdmissionReceipt" in contract.get("contracts",[])
      and sem.get("direct_provider_probe")=="ALLOWED_ONLY_INSIDE_CURRENT_HOST_ADMISSION_HARNESS"
      and sem.get("model_router")=="CONSUMES_ONLY_ADMITTED_SCOPE_BOUND_RECEIPT_DIGESTS"
      and sem.get("decision_fabric")=="ADVISORY_ONLY_CANNOT_ADD_CANDIDATES_OR_AUTHORIZE_EXECUTION"
      and sem.get("provider_absence")=="NOT_PRESENT_IN_PROBE_ENVIRONMENT_ONLY"
      and sem.get("host_wide_absence_claim")=="FORBIDDEN_FROM_SINGLE_PROBE_ENVIRONMENT"
      and sem.get("runtime_probe_identity_binding")=="RESOLVED_EXECUTABLE_PATH_PLUS_SHA256_REQUIRED"
      and sem.get("runtime_admission_pin_identity")=="EXACT_ENVIRONMENT_INTERPRETER_PROVIDER_MODULE_AND_EXECUTION_BINARY_MATCH_REQUIRED"
      and "ProviderRuntimeProbeDescriptorReceipt" in contract.get("contracts",[])
    ):
        findings.append(finding("INFER-HOST-MAT-014","contract current-host semantics drift"))
    for pid in PROVIDERS:
        p=loadj(root/"canonical/providers"/f"{pid}.json")
        ch=p.get("current_host_admission") or {}
        if not (
          ch.get("framework_id")==CONFORMANCE_ID and ch.get("gate_id")==CURRENT_HOST_GATE_ID
          and ch.get("automatic_install") is False and ch.get("network_model_fetch") is False
          and ch.get("global_promotion_claim") is False
          and ch.get("host_wide_absence_claim") is False
          and ch.get("automatic_environment_scanning") is False
          and ch.get("absence_status")=="NOT_PRESENT_IN_PROBE_ENVIRONMENT"
        ):
            findings.append(finding("INFER-HOST-MAT-015","provider current-host binding drift",provider_id=pid))
    collector_text=paths["collector"].read_text(encoding="utf-8").lower()
    for token in ("pip install","apt install","apt-get install","dnf install","wget ","curl "):
        if token in collector_text:
            findings.append(finding("INFER-HOST-MAT-016","collector contains forbidden automatic installation/network fetch path",token=token))
    if not (
      evid.get("conformance_id")==CONFORMANCE_ID and evid.get("status")=="PASS"
      and evid.get("current_host_runtime_promotion_claim") is False
      and evid.get("existing_429_closure_reopened") is False
    ):
        findings.append(finding("INFER-HOST-MAT-017","reference materialization evidence drift"))
    return {
      "schema":"fa3.inference-provider-current-host-materialization-gate.v1",
      "parent_gate_id":PARENT_GATE_ID,"materialization_subgate_id":MATERIALIZATION_SUBGATE_ID,
      "result":"PASS" if not findings else "FAIL","findings":findings,
      "current_host_runtime_promotion_claim":False,"global_promotion_claim":False,
    }


def current_host_gate(root: Path, receipt_path: Path | None = None) -> dict[str,Any]:
    root=root.resolve()
    path=receipt_path or root/AGGREGATE_RECEIPT
    if not path.is_absolute(): path=root/path
    findings=[]
    try:
        rec=loadj(path)
    except Exception as exc:
        return {"schema":"fa3.inference-provider-current-host-gate.v1","gate_id":CURRENT_HOST_GATE_ID,"result":"BLOCKED","findings":[finding("INFER-HOST-001","aggregate receipt missing or unreadable",error=repr(exc))],"global_promotion_claim":False}
    if rec.get("schema")!="fa3.inference-provider-current-host-receipt.v1" or rec.get("conformance_id")!=CONFORMANCE_ID or rec.get("gate_id")!=CURRENT_HOST_GATE_ID:
        findings.append(finding("INFER-HOST-002","aggregate identity mismatch"))
    if rec.get("physical_current_host") is not True or rec.get("provider_neutral") is not True:
        findings.append(finding("INFER-HOST-003","receipt does not prove physical provider-neutral current-host execution"))
    if rec.get("inventory_scope")!="PROBE_ENVIRONMENT_SCOPED_NOT_HOST_WIDE" or rec.get("host_wide_absence_claim") is not False:
        findings.append(finding("INFER-HOST-014","receipt overstates provider absence beyond the probed runtime environment"))
    if rec.get("global_promotion_claim") is not False or rec.get("existing_429_closure_reopened") is not False or rec.get("current_host_obligation_delta")!=0:
        findings.append(finding("INFER-HOST-004","receipt overclaims global/current-host capability promotion"))
    if rec.get("auto_install_performed") is not False or rec.get("network_model_fetch_performed") is not False:
        findings.append(finding("INFER-HOST-005","admission performed forbidden installation/network model fetch"))
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if rec.get("repository_head")!=head:
            findings.append(finding("INFER-HOST-006","receipt not bound to checkout HEAD"))
    except Exception:
        findings.append(finding("INFER-HOST-006","unable to determine checkout HEAD"))
    ps=rec.get("providers")
    if not isinstance(ps,dict) or set(ps)!=set(PROVIDERS):
        findings.append(finding("INFER-HOST-007","provider inventory is incomplete or unexpected"))
        ps={} if not isinstance(ps,dict) else ps
    for pid,p in ps.items():
        if not isinstance(p,dict) or not provider_receipt_valid(p):
            findings.append(finding("INFER-HOST-008","provider receipt invalid",provider_id=pid))
    present={pid for pid,p in ps.items() if isinstance(p,dict) and p.get("present") is True}
    if not advisory_valid(rec.get("decision_fabric_advisory"),present):
        findings.append(finding("INFER-HOST-009","Decision Fabric advisory expanded/authorized candidates or mismatched deterministic present set"))
    required=set(rec.get("required_provider_ids") or [])
    if not required.issubset(set(PROVIDERS)):
        findings.append(finding("INFER-HOST-010","unknown required provider id"))
    missing={pid for pid in required if not (ps.get(pid) or {}).get("admitted_scopes")}
    if missing:
        findings.append(finding("INFER-HOST-011","explicitly required provider lacks admitted current-host scope",provider_ids=sorted(missing)))
    hashes=rec.get("provider_receipt_sha256")
    if not isinstance(hashes,dict):
        findings.append(finding("INFER-HOST-012","provider receipt digest map missing"))
    else:
        for pid in PROVIDERS:
            p=root/"evidence/receipts/inference-provider-current-host"/f"{pid}.json"
            if not p.is_file() or hashes.get(pid)!=hashlib.sha256(p.read_bytes()).hexdigest():
                findings.append(finding("INFER-HOST-012","provider receipt digest mismatch",provider_id=pid))
    expected_result="BLOCKED" if missing else "PASS"
    if rec.get("result")!=expected_result:
        findings.append(finding("INFER-HOST-013","aggregate result does not match required-provider admission state",expected=expected_result))
    return {
      "schema":"fa3.inference-provider-current-host-gate.v1",
      "gate_id":CURRENT_HOST_GATE_ID,
      "result":"PASS" if not findings else "BLOCKED",
      "findings":findings,
      "admitted_providers":sorted(pid for pid,p in ps.items() if isinstance(p,dict) and p.get("admitted_scopes")),
      "required_provider_ids":sorted(required),
      "evidence_ref":str(path),
      "global_promotion_claim":False,
      "promotion_effect":"PROVIDER_SCOPE_ADMISSION_ONLY_GLOBAL_PROMOTION_UNCHANGED",
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--current-host",action="store_true")
    ap.add_argument("--receipt")
    args=ap.parse_args()
    root=Path(args.root).resolve()
    report=current_host_gate(root,Path(args.receipt) if args.receipt else None) if args.current_host else materialization_gate(root)
    out=root/("reports/inference-provider-current-host-gate-report.json" if args.current_host else "reports/inference-provider-current-host-materialization-gate-report.json")
    writej(out,report)
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if report["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
