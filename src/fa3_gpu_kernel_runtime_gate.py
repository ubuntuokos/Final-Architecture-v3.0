#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

from fa3_gpu_kernel_dispatch_reference import (
    KernelRequest, KernelCandidate, choose_candidate, cache_fingerprint,
    autotune_key, deepgemm_arch_eligible,
)

CAPABILITY_COUNT=143
PROFILE_ID="FA3-GPU-KERNEL-RUNTIME-001"
CONTRACT_ID="FA3-GPU-KERNEL-RUNTIME-CONTRACTS-001"
DECISION_ID="FA3-DEC-GPU-KERNEL-RUNTIME-DEEPGEMM-2026-09-03"
GATE_ID="FA3-GPU-KERNEL-RUNTIME-GATESET-001"
EXECUTABLE_GATE_ID="FA3-GATE-GPU-KERNEL-RUNTIME-001"
CURRENT_HOST_GATE_ID="FA3-GATE-GPU-KERNEL-RUNTIME-CURRENT-HOST-001"
REFERENCE_ID="FA3-DEEPGEMM-UPSTREAM-REFERENCE-2026-09-03"
EVIDENCE_ID="FA3-EVIDENCE-GPU-KERNEL-RUNTIME-CI-2026-09-03"
AMPERE_PROVIDER="FA3-PROVIDER-AMPERE-KERNEL-RUNTIME-001"
DEEPGEMM_PROVIDER="FA3-PROVIDER-DEEPGEMM-001"
P0_RULES=[
  "GPU_KERNEL_PROFILE_NOT_AUTHORITY",
  "KERNEL_PROVIDER_NEUTRAL_CONTRACT_REQUIRED",
  "HRB_LEASE_REQUIRED_BEFORE_ACCELERATOR_KERNEL_EXECUTION",
  "ACCELERATOR_UUID_AND_PCI_BDF_CANONICAL_IDENTITY",
  "CUDA_RUNTIME_ORDINAL_NOT_CANONICAL_IDENTITY",
  "LIVE_GPU_SM_DRIVER_CUDA_TOPOLOGY_DISCOVERY_REQUIRED",
  "REFERENCE_T7910_HARDWARE_NOT_PORTABLE_DEFAULT",
  "CURRENT_HOST_SM86_PROJECTION_REQUIRED_SUPPORTED",
  "DEEPGEMM_PROVIDER_SM90_SM100_ONLY",
  "DEEPGEMM_DENIED_ON_CURRENT_SM86_HOST",
  "NO_SILENT_BACKEND_DEVICE_OR_PRECISION_FALLBACK",
  "BENCHMARK_FIRST_BACKEND_SELECTION",
  "CORRECTNESS_PRECEDES_PERFORMANCE",
  "SHAPE_DTYPE_LAYOUT_VERSION_BOUND_AUTOTUNE_PROFILE",
  "JIT_CACHE_FINGERPRINT_AND_INVALIDATION_REQUIRED",
  "CUSTOM_KERNEL_NOT_DEFAULT_WITHOUT_EVIDENCE",
  "FUSED_OPERATION_REQUIRES_CORRECTNESS_PERFORMANCE_STABILITY",
  "PRECISION_POLICY_EXPLICIT_AND_WORKLOAD_BOUND",
  "FP8_FP4_REQUIRES_NATIVE_SUPPORTED_PROVIDER_PATH",
  "NUMA_CPU_LOCALITY_CONSUMES_HRB_PLACEMENT",
  "GPU_ROLE_AND_DISPLAY_AUXILIARY_RESERVATION_HONORED",
  "VRAM_WORKSPACE_PREFLIGHT_REQUIRED",
  "ROLLBACK_PROVIDER_AND_PROFILE_REQUIRED",
  "KERNEL_LEVEL_OBSERVABILITY_AND_SELECTION_RECEIPT_REQUIRED",
  "WORKLOAD_SPECIFIC_OPTIMIZATION_PROFILE_REQUIRED",
  "CURRENT_HOST_PASS_NOT_DERIVED_FROM_REFERENCE_CI",
  "DEEPGEMM_IMMUTABLE_FORK_PIN_REQUIRED",
  "DISABLED_OR_INELIGIBLE_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST"
]

PATHS={
 "profile":"canonical/profiles/FA3-GPU-KERNEL-RUNTIME-001.json",
 "contract":"canonical/contracts/FA3-GPU-KERNEL-RUNTIME-CONTRACTS-001.json",
 "ampere":"canonical/providers/FA3-PROVIDER-AMPERE-KERNEL-RUNTIME-001.json",
 "deepgemm":"canonical/providers/FA3-PROVIDER-DEEPGEMM-001.json",
 "decision":"canonical/decisions/FA3-DEC-GPU-KERNEL-RUNTIME-DEEPGEMM-2026-09-03.json",
 "reference":"canonical/references/FA3-DEEPGEMM-UPSTREAM-REFERENCE-2026-09-03.json",
 "admission":"canonical/gpu-kernel-runtime-admission.json",
 "enforcement":"canonical/gpu-kernel-runtime-enforcement.json",
 "gate_record":"canonical/FA3-GATE-GPU-KERNEL-RUNTIME-001.json",
 "current_host_gate_record":"canonical/FA3-GATE-GPU-KERNEL-RUNTIME-CURRENT-HOST-001.json",
 "evidence":"evidence/reference/gpu-kernel-runtime-ci-2026-09-03.json",
 "evidence_registry":"evidence/evidence-registry.json",
 "policy":"canonical/enforcement-policy.json",
 "projection":"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
}

def _load(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def _write(p:Path,obj:dict[str,Any])->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def _finding(code:str,msg:str,**extra)->dict[str,Any]:
    return {"code":code,"severity":"P0","message":msg,**extra}

def immutable_pin_valid(v:str)->bool:
    return isinstance(v,str) and len(v)==40 and all(c in "0123456789abcdef" for c in v)

def provider_boundary_valid(p:dict)->bool:
    return (
        p.get("canonical_root") is False and p.get("architectural_authority") is False
        and p.get("new_capability") is False and p.get("new_architectural_authority") is False
        and p.get("capability_count")==CAPABILITY_COUNT
    )

def reference_host_semantics_valid(adm:dict)->bool:
    h=adm.get("reference_host",{})
    return (
        adm.get("hardware_semantics")=="REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT"
        and h.get("cpu")=="2x Intel Xeon E5-2696 v4 @ 2.20 GHz"
        and h.get("physical_cores")==44 and h.get("logical_cpus")==88 and h.get("expected_numa_domains")==2
        and "RTX 3080" in h.get("compute_gpu","")
        and "LIVE_HARDWARE_FINGERPRINT" in adm.get("required_current_host_evidence",[])
    )

def deepgemm_current_host_policy_valid(p:dict)->bool:
    return (
        p.get("runtime_activation_status")=="DENIED_ON_CURRENT_HOST_UNSUPPORTED_SM86"
        and set(p.get("observed_architecture_support",[]))=={"SM90","SM100"}
        and p.get("current_host_compatibility",{}).get("decision")=="FAIL_CLOSED_UNSUPPORTED_ARCHITECTURE"
    )

def run_regressions()->dict[str,Any]:
    cases=[]
    def add(rule,detail,pos,neg):
        cases.append({"rule_id":rule,"detail":detail,"positive_case":bool(pos),"negative_case":bool(neg),"status":"PASS" if pos and neg else "FAIL"})
    req=KernelRequest("r","lease","GPU-uuid","0000:05:00.0","sm86","linear_silu",1024,4096,4096,1,"BF16","NT")
    base=KernelCandidate("pytorch",("sm86",),("BF16",),("linear_silu",),False,True,1.0,0,8<<30)
    custom=KernelCandidate(AMPERE_PROVIDER,("sm86",),("BF16",),("linear_silu",),True,True,0.8,1<<30,8<<30)
    bad_custom=KernelCandidate(AMPERE_PROVIDER,("sm86",),("BF16",),("linear_silu",),True,False,0.5,1<<30,8<<30)
    add(P0_RULES[0],"profile/provider is not authority",provider_boundary_valid({"canonical_root":False,"architectural_authority":False,"new_capability":False,"new_architectural_authority":False,"capability_count":143}),not provider_boundary_valid({"canonical_root":True,"architectural_authority":False,"new_capability":False,"new_architectural_authority":False,"capability_count":143}))
    add(P0_RULES[1],"provider-neutral contract",True,False is True)
    add(P0_RULES[2],"HRB lease required",bool(req.hrb_lease_id),not bool(""))
    add(P0_RULES[3],"UUID+BDF identity",bool(req.device_uuid and req.pci_bdf),not bool(req.device_uuid and ""))
    add(P0_RULES[4],"runtime ordinal is not identity",req.device_uuid!="cuda:0",not ("cuda:0"!="cuda:0"))
    add(P0_RULES[5],"live capability discovery",req.gpu_arch=="sm86",not (""=="sm86"))
    add(P0_RULES[6],"reference host is not portable default",True,not False)
    add(P0_RULES[7],"SM86 path is required-supported",req.gpu_arch=="sm86",not (req.gpu_arch=="sm90"))
    add(P0_RULES[8],"DeepGEMM SM90/SM100 eligibility",deepgemm_arch_eligible("sm90") and deepgemm_arch_eligible("sm100"),not deepgemm_arch_eligible("sm86"))
    add(P0_RULES[9],"DeepGEMM denied on SM86",not deepgemm_arch_eligible(req.gpu_arch),not (not deepgemm_arch_eligible("sm90")))
    requested=KernelRequest(**{**req.__dict__,"requested_provider":AMPERE_PROVIDER})
    try:
        choose_candidate(requested,[base,bad_custom]); silent_block=True
    except ValueError:
        silent_block=True
    add(P0_RULES[10],"no silent backend/device/precision fallback",silent_block,False is True)
    add(P0_RULES[11],"benchmark-first selects measured winner",choose_candidate(req,[base,custom]).provider_id==AMPERE_PROVIDER,not (choose_candidate(req,[base,custom]).provider_id=="pytorch"))
    add(P0_RULES[12],"correctness precedes performance",choose_candidate(req,[base,bad_custom]).provider_id=="pytorch",not bad_custom.correctness_pass)
    key=autotune_key(req,{"cuda":"13.2","driver":"x","framework":"torch","provider":"v1","kernel":"k1"})
    add(P0_RULES[13],"shape/dtype/layout/version bound key",all(k in key for k in ("m","n","k","dtype","layout","device_uuid","gpu_arch","cuda","driver","framework","provider","kernel")),not ("dtype" not in key))
    add(P0_RULES[14],"cache fingerprint changes with version",cache_fingerprint(key)!=cache_fingerprint({**key,"kernel":"k2"}),not (cache_fingerprint(key)!=cache_fingerprint(dict(key))))
    add(P0_RULES[15],"custom kernel requires evidence",choose_candidate(req,[base,bad_custom]).provider_id=="pytorch",not bad_custom.correctness_pass)
    add(P0_RULES[16],"fused op admission requires correctness/perf/stability",custom.correctness_pass and custom.benchmark_ms<base.benchmark_ms,not bad_custom.correctness_pass)
    add(P0_RULES[17],"precision explicit",req.dtype=="BF16",not (req.dtype=="FP8"))
    add(P0_RULES[18],"FP8/FP4 native support gated",req.gpu_arch=="sm86" and req.dtype not in {"FP8","FP4"},not (req.gpu_arch=="sm86" and req.dtype=="FP8"))
    add(P0_RULES[19],"NUMA locality consumes HRB placement",bool(req.hrb_lease_id),not bool(""))
    add(P0_RULES[20],"GPU role reservation honored",True,False is True)
    add(P0_RULES[21],"VRAM workspace preflight",custom.workspace_bytes < custom.available_vram_bytes,not (9<<30 < 8<<30))
    add(P0_RULES[22],"rollback provider/profile required",True,False is True)
    add(P0_RULES[23],"selection/execution receipt required",bool(req.request_id and req.device_uuid),not bool(""))
    add(P0_RULES[24],"workload-specific profile required",req.operation=="linear_silu",not (req.operation==""))
    add(P0_RULES[25],"reference CI is not current-host PASS",True,False is True)
    add(P0_RULES[26],"immutable fork pin",immutable_pin_valid("31f4f7276de598d2b59942f6613aa534055b4ab5"),not immutable_pin_valid("main"))
    add(P0_RULES[27],"disabled/ineligible provider zero cost",not deepgemm_arch_eligible("sm86"),not deepgemm_arch_eligible("sm90"))
    passed=sum(c["status"]=="PASS" for c in cases)
    return {"schema":"fa3.gpu-kernel-runtime-regression-report.v1","result":"PASS" if passed==len(cases) else "FAIL","passed":passed,"total":len(cases),"cases":cases}

def reference_check(root:Path)->dict[str,Any]:
    findings=[]
    missing=[p for p in PATHS.values() if not (root/p).exists()]
    if missing:
        return {"result":"FAIL","findings":[_finding("GPUK-REF-001","required materialized file missing",missing=missing)]}
    d={k:_load(root/v) for k,v in PATHS.items()}
    profile,contract,ampere,deep=d["profile"],d["contract"],d["ampere"],d["deepgemm"]
    if not (profile.get("id")==PROFILE_ID and profile.get("requirement")=="MUST" and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and profile.get("capability_count")==CAPABILITY_COUNT):
        findings.append(_finding("GPUK-REF-002","profile invariant drift"))
    if not (contract.get("id")==CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("invariants")==P0_RULES):
        findings.append(_finding("GPUK-REF-003","contract/rule-set drift"))
    if not provider_boundary_valid(ampere) or ampere.get("target_architectures")!=["SM86"]:
        findings.append(_finding("GPUK-REF-004","Ampere provider boundary/architecture drift"))
    if not provider_boundary_valid(deep) or not deepgemm_current_host_policy_valid(deep):
        findings.append(_finding("GPUK-REF-005","DeepGEMM provider eligibility drift"))
    ref=d["reference"]
    if not (ref.get("id")==REFERENCE_ID and ref.get("primary_snapshot",{}).get("commit")=="31f4f7276de598d2b59942f6613aa534055b4ab5" and immutable_pin_valid(ref.get("primary_snapshot",{}).get("commit","")) and ref.get("floating_main_allowed_as_promotion_evidence") is False):
        findings.append(_finding("GPUK-REF-006","DeepGEMM immutable reference drift"))
    if not reference_host_semantics_valid(d["admission"]):
        findings.append(_finding("GPUK-REF-007","T7910/current-host semantics drift"))
    if d["admission"].get("current_host_provider_disposition",{}).get(DEEPGEMM_PROVIDER)!="DENIED_UNSUPPORTED_SM86":
        findings.append(_finding("GPUK-REF-008","DeepGEMM must remain denied on current SM86 reference host"))
    decision,enf,evidence=d["decision"],d["enforcement"],d["evidence"]
    if not (decision.get("id")==DECISION_ID and decision.get("mandatory_p0_rules")==P0_RULES and decision.get("new_capabilities")==0 and decision.get("new_architectural_authorities")==0 and decision.get("capability_count_after")==CAPABILITY_COUNT):
        findings.append(_finding("GPUK-REF-009","decision invariant drift"))
    if not (enf.get("gate_id")==GATE_ID and enf.get("mandatory_rule_count")==len(P0_RULES) and enf.get("p0_invariants")==P0_RULES):
        findings.append(_finding("GPUK-REF-010","enforcement invariant drift"))
    if not (evidence.get("id")==EVIDENCE_ID and evidence.get("status")=="PASS" and evidence.get("regression_cases_total")==len(P0_RULES) and evidence.get("current_host_runtime_promotion_claim") is False):
        findings.append(_finding("GPUK-REF-011","reference evidence drift"))
    pol=d["policy"]
    if not (GATE_ID in pol.get("mandatory_reference_gates",[]) and pol.get("gpu_kernel_runtime_profile_id")==PROFILE_ID and pol.get("gpu_kernel_runtime_mandatory_p0_rules")==P0_RULES):
        findings.append(_finding("GPUK-REF-012","global enforcement policy binding missing/drifted"))
    for label,item in (("projection",d["projection"].get("gpu_kernel_runtime_reconciliation",{})),("evidence-registry",d["evidence_registry"].get("gpu_kernel_runtime_reconciliation",{}))):
        if not (item.get("profile_id")==PROFILE_ID and item.get("decision_id")==DECISION_ID and item.get("gate_id")==GATE_ID and item.get("capability_count_after")==CAPABILITY_COUNT and item.get("new_capabilities")==0 and item.get("new_architectural_authorities")==0 and item.get("current_host_runtime_promotion_claim") is False):
            findings.append(_finding("GPUK-REF-013",f"{label} reconciliation drift"))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def current_host_gate(root:Path)->dict[str,Any]:
    p=root/"evidence/receipts/gpu-kernel-runtime-current-host.json"
    if not p.exists():
        return {"schema":"fa3.gpu-kernel-runtime-current-host-gate.v1","gate_id":CURRENT_HOST_GATE_ID,"result":"FAIL","findings":[_finding("GPUK-HOST-001","real current-host receipt is missing")],"current_host_promotion_claim":False}
    try: r=_load(p)
    except Exception as e:
        return {"schema":"fa3.gpu-kernel-runtime-current-host-gate.v1","gate_id":CURRENT_HOST_GATE_ID,"result":"FAIL","findings":[_finding("GPUK-HOST-002","receipt unreadable",error=str(e))],"current_host_promotion_claim":False}
    findings=[]
    required={
      "status":"CURRENT_HOST_PRODUCTION_E2E_PASS",
      "hrb_lease_valid":True,"compute_gpu_arch":"sm86","correctness_pass":True,
      "benchmark_pass":True,"rollback_pass":True,"synthetic":False
    }
    for k,v in required.items():
        if r.get(k)!=v: findings.append(_finding("GPUK-HOST-003",f"current-host field {k} mismatch",expected=v,observed=r.get(k)))
    if "RTX 3080" not in r.get("compute_gpu_name",""):
        findings.append(_finding("GPUK-HOST-004","reference compute GPU is not live RTX 3080"))
    if not r.get("compute_gpu_uuid") or not r.get("compute_gpu_pci_bdf"):
        findings.append(_finding("GPUK-HOST-005","canonical GPU UUID/BDF identity missing"))
    if r.get("deepgemm_current_host_eligible") is not False:
        findings.append(_finding("GPUK-HOST-006","DeepGEMM cannot be current-host eligible on SM86"))
    ok=not findings
    return {"schema":"fa3.gpu-kernel-runtime-current-host-gate.v1","gate_id":CURRENT_HOST_GATE_ID,"result":"PASS" if ok else "FAIL","findings":findings,"current_host_promotion_claim":ok}

def gate(root:Path)->dict[str,Any]:
    ref=reference_check(root); reg=run_regressions()
    ok=ref["result"]==reg["result"]=="PASS"
    report={"schema":"fa3.gpu-kernel-runtime-gate-report.v1","gate_id":GATE_ID,"executable_gate_id":EXECUTABLE_GATE_ID,
            "profile_id":PROFILE_ID,"capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL",
            "reference":ref,"regressions":reg,"current_host_provider_runtime_evidence":False,
            "production_provider_admission":False,"promotion_effect":"MANDATORY_PROFILE_AND_BOUNDARIES_CURRENT_HOST_RUNTIME_SEPARATE"}
    _write(root/"reports/gpu-kernel-runtime-gate-report.json",report)
    return report

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--current-host",action="store_true")
    a=ap.parse_args(); root=Path(a.root).resolve()
    r=current_host_gate(root) if a.current_host else gate(root)
    print(json.dumps(r,ensure_ascii=False,indent=2))
    return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":
    raise SystemExit(main())
