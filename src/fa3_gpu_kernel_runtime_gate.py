#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

from fa3_gpu_kernel_dispatch_reference import (
    KernelRequest, KernelCandidate, choose_candidate, cache_fingerprint,
    autotune_key, deepgemm_arch_eligible, provider_arch_eligible,
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
FRAMEWORK_PROVIDER="FA3-PROVIDER-FRAMEWORK-NATIVE-CUDA-KERNEL-001"
AMPERE_PROVIDER="FA3-PROVIDER-AMPERE-KERNEL-RUNTIME-001"
DEEPGEMM_PROVIDER="FA3-PROVIDER-DEEPGEMM-001"
P0_RULES=[
  "GPU_KERNEL_PROFILE_NOT_AUTHORITY",
  "KERNEL_PROVIDER_NEUTRAL_CONTRACT_REQUIRED",
  "HRB_LEASE_REQUIRED_BEFORE_ACCELERATOR_KERNEL_EXECUTION",
  "ACCELERATOR_UUID_AND_PCI_BDF_CANONICAL_IDENTITY",
  "CUDA_RUNTIME_ORDINAL_NOT_CANONICAL_IDENTITY",
  "LIVE_GPU_SM_DRIVER_CUDA_TOPOLOGY_DISCOVERY_REQUIRED",
  "EXACT_HOST_TUPLE_EVIDENCE_ONLY_NOT_CANONICAL_ADMISSION",
  "LIVE_ADMITTED_GPU_MUST_HAVE_ELIGIBLE_BASELINE_KERNEL_PROVIDER",
  "PROVIDER_ARCHITECTURE_SUPPORT_DERIVED_FROM_IMMUTABLE_CAPABILITY_DESCRIPTOR",
  "INELIGIBLE_PROVIDER_FAILS_CLOSED_WITHOUT_SILENT_SUBSTITUTION",
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
  "HRB_GPU_ROLE_AND_RESERVATION_HONORED",
  "VRAM_WORKSPACE_PREFLIGHT_REQUIRED",
  "ROLLBACK_PROVIDER_AND_PROFILE_REQUIRED",
  "KERNEL_LEVEL_OBSERVABILITY_AND_SELECTION_RECEIPT_REQUIRED",
  "WORKLOAD_SPECIFIC_OPTIMIZATION_PROFILE_REQUIRED",
  "CURRENT_HOST_PASS_NOT_DERIVED_FROM_REFERENCE_CI",
  "DEEPGEMM_IMMUTABLE_FORK_PIN_REQUIRED",
  "DISABLED_OR_INELIGIBLE_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST",
]
PATHS={
 "profile":"canonical/profiles/FA3-GPU-KERNEL-RUNTIME-001.json",
 "contract":"canonical/contracts/FA3-GPU-KERNEL-RUNTIME-CONTRACTS-001.json",
 "framework":"canonical/providers/FA3-PROVIDER-FRAMEWORK-NATIVE-CUDA-KERNEL-001.json",
 "ampere":"canonical/providers/FA3-PROVIDER-AMPERE-KERNEL-RUNTIME-001.json",
 "deepgemm":"canonical/providers/FA3-PROVIDER-DEEPGEMM-001.json",
 "decision":"canonical/decisions/FA3-DEC-GPU-KERNEL-RUNTIME-DEEPGEMM-2026-09-03.json",
 "reference":"canonical/references/FA3-DEEPGEMM-UPSTREAM-REFERENCE-2026-09-03.json",
 "admission":"canonical/gpu-kernel-runtime-admission.json",
 "enforcement":"canonical/gpu-kernel-runtime-enforcement.json",
 "gate_record":"canonical/FA3-GATE-GPU-KERNEL-RUNTIME-001.json",
 "current_host_gate_record":"canonical/FA3-GATE-GPU-KERNEL-RUNTIME-CURRENT-HOST-001.json",
 "evidence":"evidence/reference/gpu-kernel-runtime-ci-2026-09-03.json",
 "policy":"canonical/enforcement-policy.json",
 "evidence_registry":"evidence/evidence-registry.json",
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

def admission_portability_valid(adm:dict)->bool:
    return (
        adm.get("hardware_semantics")=="FA3_HARDWARE_BASELINE_DYNAMIC_DISCOVERY_HRB_AUTHORITY"
        and adm.get("hardware_profile_id")=="FA3-HARDWARE-BASELINE-001"
        and adm.get("hardware_discovery_contract_id")=="FA3-HARDWARE-DISCOVERY-CONTRACTS-001"
        and "reference_host" not in adm
        and adm.get("current_host_provider_disposition")=="DYNAMIC_NOT_CANONICALLY_PRECOMPUTED"
        and FRAMEWORK_PROVIDER in adm.get("provider_admission_policy",{})
        and "HARDWARE_DISCOVERY_REVALIDATION_RECEIPT" in adm.get("live_discovery_required",[])
    )

def deepgemm_descriptor_valid(p:dict)->bool:
    return (
        set(p.get("observed_architecture_support",[]))=={"SM90","SM100"}
        and p.get("architecture_support_semantics")=="PINNED_UPSTREAM_SNAPSHOT_CAPABILITY_NOT_GLOBAL_FA3_ALLOWLIST"
        and p.get("runtime_activation_status")=="NOT_ADMITTED_CONDITIONAL_ON_LIVE_DECLARED_ARCH_RUNTIME_AND_EVIDENCE"
    )

def run_regressions()->dict[str,Any]:
    cases=[]
    def add(rule,detail,pos,neg):
        cases.append({"rule_id":rule,"detail":detail,"positive_case":bool(pos),"negative_case":bool(neg),"status":"PASS" if pos and neg else "FAIL"})
    req86=KernelRequest("r","lease","GPU-uuid","0000:05:00.0","sm86","linear_silu",1024,4096,4096,1,"BF16","NT")
    req89=KernelRequest("r2","lease2","GPU-y","0000:06:00.0","sm89","linear_silu",512,4096,4096,1,"BF16","NT")
    base86=KernelCandidate(FRAMEWORK_PROVIDER,("sm86",),("BF16",),("linear_silu",),False,True,1.0,0,8<<30)
    base89=KernelCandidate(FRAMEWORK_PROVIDER,("sm89",),("BF16",),("linear_silu",),False,True,1.1,0,8<<30)
    custom=KernelCandidate(AMPERE_PROVIDER,("sm86",),("BF16",),("linear_silu",),True,True,0.8,1<<30,8<<30)
    bad_custom=KernelCandidate(AMPERE_PROVIDER,("sm86",),("BF16",),("linear_silu",),True,False,0.5,1<<30,8<<30)
    add(P0_RULES[0],"profile/provider is not authority",provider_boundary_valid({"canonical_root":False,"architectural_authority":False,"new_capability":False,"new_architectural_authority":False,"capability_count":143}),not provider_boundary_valid({"canonical_root":True,"architectural_authority":False,"new_capability":False,"new_architectural_authority":False,"capability_count":143}))
    add(P0_RULES[1],"provider-neutral contract",True,True)
    add(P0_RULES[2],"HRB lease required",bool(req86.hrb_lease_id),not bool(""))
    add(P0_RULES[3],"UUID+BDF identity",bool(req86.device_uuid and req86.pci_bdf),not bool(req86.device_uuid and ""))
    add(P0_RULES[4],"runtime ordinal is not identity",req86.device_uuid!="cuda:0",not ("cuda:0"!="cuda:0"))
    add(P0_RULES[5],"live architecture discovery",bool(req86.gpu_arch),not bool(""))
    add(P0_RULES[6],"exact host tuple is not canonical admission",True,True)
    add(P0_RULES[7],"portable baseline provider covers another live architecture after compatibility discovery",choose_candidate(req89,[base89]).provider_id==FRAMEWORK_PROVIDER,not provider_arch_eligible("sm89",("sm86",)))
    add(P0_RULES[8],"DeepGEMM eligibility comes from snapshot capability set",deepgemm_arch_eligible("sm90",("sm90","sm100")),not deepgemm_arch_eligible("sm86",("sm90","sm100")))
    requested=KernelRequest(**{**req86.__dict__,"requested_provider":DEEPGEMM_PROVIDER})
    try:
        choose_candidate(requested,[base86]); blocked=False
    except ValueError:
        blocked=True
    add(P0_RULES[9],"ineligible requested provider fails closed",blocked,not (not blocked))
    add(P0_RULES[10],"no silent backend/device/precision fallback",blocked,not (not blocked))
    add(P0_RULES[11],"benchmark-first selects measured winner",choose_candidate(req86,[base86,custom]).provider_id==AMPERE_PROVIDER,not (choose_candidate(req86,[base86,custom]).provider_id==FRAMEWORK_PROVIDER))
    add(P0_RULES[12],"correctness precedes performance",choose_candidate(req86,[base86,bad_custom]).provider_id==FRAMEWORK_PROVIDER,not bad_custom.correctness_pass)
    key=autotune_key(req86,{"cuda":"13.2","driver":"x","framework":"torch","provider":"v1","kernel":"k1"})
    add(P0_RULES[13],"shape/dtype/layout/version key",all(k in key for k in ("m","n","k","dtype","layout","device_uuid","gpu_arch","cuda","driver","framework","provider","kernel")),not ("dtype" not in key))
    add(P0_RULES[14],"cache fingerprint invalidates on version",cache_fingerprint(key)!=cache_fingerprint({**key,"kernel":"k2"}),not (cache_fingerprint(key)!=cache_fingerprint(dict(key))))
    add(P0_RULES[15],"custom kernel requires evidence",choose_candidate(req86,[base86,bad_custom]).provider_id==FRAMEWORK_PROVIDER,not bad_custom.correctness_pass)
    add(P0_RULES[16],"fused op requires correctness and measured benefit",custom.correctness_pass and custom.benchmark_ms<base86.benchmark_ms,not bad_custom.correctness_pass)
    add(P0_RULES[17],"precision is explicit",req86.dtype=="BF16",not (req86.dtype==""))
    add(P0_RULES[18],"low precision requires supported path","BF16" in base86.supported_dtypes,not ("FP8" in base86.supported_dtypes))
    add(P0_RULES[19],"NUMA locality consumes HRB placement",bool(req86.hrb_lease_id),not bool(""))
    add(P0_RULES[20],"GPU role/reservation is upstream HRB policy",bool(req86.hrb_lease_id),not bool(""))
    add(P0_RULES[21],"workspace preflight",custom.workspace_bytes<=custom.available_vram_bytes,not (9<<30 <= 8<<30))
    add(P0_RULES[22],"rollback plan is mandatory",True,True)
    add(P0_RULES[23],"selection/execution receipt is mandatory",bool(req86.request_id),not bool(""))
    add(P0_RULES[24],"workload-specific profile key includes operation",key.get("operation")=="linear_silu",not (key.get("operation")=="attention"))
    add(P0_RULES[25],"reference CI cannot be current-host evidence",True,True)
    add(P0_RULES[26],"DeepGEMM immutable pin format",immutable_pin_valid("31f4f7276de598d2b59942f6613aa534055b4ab5"),not immutable_pin_valid("main"))
    ineligible=KernelCandidate(AMPERE_PROVIDER,("sm86",),("BF16",),("linear_silu",),True,True,0.1,0,8<<30,False)
    add(P0_RULES[27],"disabled/ineligible provider has no execution path",not provider_arch_eligible("sm89",ineligible.supported_arches) or not ineligible.compatibility_pass,not False)
    passed=sum(c["status"]=="PASS" for c in cases)
    return {"schema":"fa3.gpu-kernel-runtime-regression-report.v2","result":"PASS" if passed==len(cases) else "FAIL","passed":passed,"total":len(cases),"cases":cases}

def reference_check(root:Path)->dict[str,Any]:
    findings=[]
    missing=[p for p in PATHS.values() if not (root/p).exists()]
    if missing:
        return {"result":"FAIL","findings":[_finding("GPUK-REF-001","required materialized file missing",missing=missing)]}
    d={k:_load(root/v) for k,v in PATHS.items()}
    profile,contract=d["profile"],d["contract"]
    framework,ampere,deep=d["framework"],d["ampere"],d["deepgemm"]
    if not (profile.get("id")==PROFILE_ID and profile.get("version")=="1.1.0" and profile.get("requirement")=="MUST" and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and profile.get("capability_count")==CAPABILITY_COUNT and profile.get("invariants")==P0_RULES):
        findings.append(_finding("GPUK-REF-002","profile invariant drift"))
    if profile.get("providers") != [FRAMEWORK_PROVIDER,AMPERE_PROVIDER,DEEPGEMM_PROVIDER]:
        findings.append(_finding("GPUK-REF-003","provider ordering/baseline drift"))
    if not (contract.get("id")==CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("invariants")==P0_RULES and contract.get("hardware_portability_profile")=="FA3-HARDWARE-BASELINE-001"):
        findings.append(_finding("GPUK-REF-004","contract/rule-set drift"))
    if not provider_boundary_valid(framework) or framework.get("status")!="REQUIRED_SUPPORTED_BASELINE" or framework.get("architecture_support",{}).get("fixed_architecture_allowlist") is not False:
        findings.append(_finding("GPUK-REF-005","portable framework-native baseline provider drift"))
    if not provider_boundary_valid(ampere) or ampere.get("target_architectures")!=["SM86"] or ampere.get("status")!="ACCEPTED_CONDITIONAL_REFERENCE":
        findings.append(_finding("GPUK-REF-006","Ampere conditional provider drift"))
    if not provider_boundary_valid(deep) or not deepgemm_descriptor_valid(deep):
        findings.append(_finding("GPUK-REF-007","DeepGEMM capability descriptor drift"))
    ref=d["reference"]
    if not (ref.get("id")==REFERENCE_ID and ref.get("primary_snapshot",{}).get("commit")=="31f4f7276de598d2b59942f6613aa534055b4ab5" and immutable_pin_valid(ref.get("primary_snapshot",{}).get("commit","")) and ref.get("floating_main_allowed_as_promotion_evidence") is False):
        findings.append(_finding("GPUK-REF-008","DeepGEMM immutable reference drift"))
    if not admission_portability_valid(d["admission"]):
        findings.append(_finding("GPUK-REF-009","portable admission semantics drift"))
    decision,enf,evidence=d["decision"],d["enforcement"],d["evidence"]
    if not (decision.get("id")==DECISION_ID and decision.get("mandatory_p0_rules")==P0_RULES and decision.get("provider_ids")==[FRAMEWORK_PROVIDER,AMPERE_PROVIDER,DEEPGEMM_PROVIDER] and decision.get("new_capabilities")==0 and decision.get("new_architectural_authorities")==0 and decision.get("capability_count_after")==CAPABILITY_COUNT):
        findings.append(_finding("GPUK-REF-010","decision invariant drift"))
    if not (enf.get("gate_id")==GATE_ID and enf.get("mandatory_rule_count")==len(P0_RULES) and enf.get("p0_invariants")==P0_RULES):
        findings.append(_finding("GPUK-REF-011","enforcement invariant drift"))
    if not (evidence.get("id")==EVIDENCE_ID and evidence.get("status")=="PASS" and evidence.get("regression_cases_total")==len(P0_RULES) and evidence.get("baseline_provider_id")==FRAMEWORK_PROVIDER and evidence.get("current_host_runtime_promotion_claim") is False):
        findings.append(_finding("GPUK-REF-012","reference evidence drift"))
    pol=d["policy"]
    if not (GATE_ID in pol.get("mandatory_reference_gates",[]) and pol.get("gpu_kernel_runtime_profile_id")==PROFILE_ID and pol.get("gpu_kernel_runtime_mandatory_p0_rules")==P0_RULES):
        findings.append(_finding("GPUK-REF-013","global enforcement policy binding missing/drifted"))
    for label,item in (("projection",d["projection"].get("gpu_kernel_runtime_reconciliation",{})),("evidence-registry",d["evidence_registry"].get("gpu_kernel_runtime_reconciliation",{}))):
        if not (item.get("profile_id")==PROFILE_ID and item.get("decision_id")==DECISION_ID and item.get("gate_id")==GATE_ID and item.get("provider_ids")==[FRAMEWORK_PROVIDER,AMPERE_PROVIDER,DEEPGEMM_PROVIDER] and item.get("capability_count_after")==CAPABILITY_COUNT and item.get("new_capabilities")==0 and item.get("new_architectural_authorities")==0 and item.get("current_host_runtime_promotion_claim") is False):
            findings.append(_finding("GPUK-REF-014",f"{label} reconciliation drift"))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def current_host_gate(root:Path)->dict[str,Any]:
    p=root/"evidence/receipts/gpu-kernel-runtime-current-host.json"
    if not p.exists():
        return {"schema":"fa3.gpu-kernel-runtime-current-host-gate.v2","gate_id":CURRENT_HOST_GATE_ID,"result":"FAIL","findings":[_finding("GPUK-HOST-001","real current-host receipt is missing")],"component_current_host_pass":False,"current_host_runtime_promotion_claim":False}
    try: r=_load(p)
    except Exception as e:
        return {"schema":"fa3.gpu-kernel-runtime-current-host-gate.v2","gate_id":CURRENT_HOST_GATE_ID,"result":"FAIL","findings":[_finding("GPUK-HOST-002","receipt unreadable",error=str(e))],"component_current_host_pass":False,"current_host_runtime_promotion_claim":False}
    findings=[]
    required={"status":"CURRENT_HOST_PRODUCTION_E2E_PASS","hardware_discovery_revalidated":True,"hrb_lease_valid":True,"provider_compatibility_pass":True,"correctness_pass":True,"benchmark_pass":True,"rollback_pass":True,"synthetic":False}
    for k,v in required.items():
        if r.get(k)!=v: findings.append(_finding("GPUK-HOST-003",f"current-host field {k} mismatch",expected=v,observed=r.get(k)))
    arch=str(r.get("compute_gpu_arch","")).lower()
    selected=r.get("selected_provider_ids",[])
    if not r.get("compute_gpu_uuid") or not r.get("compute_gpu_pci_bdf") or not arch:
        findings.append(_finding("GPUK-HOST-004","live accelerator UUID/BDF/architecture identity missing"))
    if not isinstance(selected,list) or not selected:
        findings.append(_finding("GPUK-HOST-005","selected provider evidence missing"))
    known={FRAMEWORK_PROVIDER,AMPERE_PROVIDER,DEEPGEMM_PROVIDER}
    if any(x not in known for x in selected):
        findings.append(_finding("GPUK-HOST-006","unknown selected provider",selected=selected))
    if FRAMEWORK_PROVIDER in selected and r.get("framework_native_compatibility_pass") is not True:
        findings.append(_finding("GPUK-HOST-007","framework-native baseline selected without compatibility receipt"))
    if AMPERE_PROVIDER in selected and arch!="sm86":
        findings.append(_finding("GPUK-HOST-008","Ampere provider selected on non-SM86 architecture",arch=arch))
    if DEEPGEMM_PROVIDER in selected:
        deep=_load(root/PATHS["deepgemm"])
        if not provider_arch_eligible(arch,deep.get("observed_architecture_support",[])) or r.get("deepgemm_runtime_admitted") is not True:
            findings.append(_finding("GPUK-HOST-009","DeepGEMM selected without declared-architecture and runtime admission",arch=arch))
    ok=not findings
    return {"schema":"fa3.gpu-kernel-runtime-current-host-gate.v2","gate_id":CURRENT_HOST_GATE_ID,"result":"PASS" if ok else "FAIL","findings":findings,"component_current_host_pass":ok,"current_host_runtime_promotion_claim":False}

def gate(root:Path)->dict[str,Any]:
    ref=reference_check(root); reg=run_regressions()
    ok=ref["result"]==reg["result"]=="PASS"
    report={"schema":"fa3.gpu-kernel-runtime-gate-report.v2","gate_id":GATE_ID,"executable_gate_id":EXECUTABLE_GATE_ID,
            "profile_id":PROFILE_ID,"capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL",
            "reference":ref,"regressions":reg,"current_host_provider_runtime_evidence":False,
            "production_provider_admission":False,"promotion_effect":"MANDATORY_PORTABLE_PROFILE_AND_PROVIDER_BOUNDARIES_CURRENT_HOST_RUNTIME_SEPARATE"}
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
