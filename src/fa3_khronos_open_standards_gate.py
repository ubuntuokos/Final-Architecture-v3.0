#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from fa3_release_baseline import load_active_release_baseline

PROFILE="canonical/profiles/FA3-KHRONOS-OPEN-STANDARDS-001.json"
CONTRACT="canonical/contracts/FA3-KHRONOS-OPEN-STANDARDS-CONTRACTS-001.json"
PLAN="canonical/materialization/FA3-KHRONOS-SDK-MATERIALIZATION-001.json"
INTENT="canonical/intents/FA3-KHRONOS-OPEN-STANDARDS-APPLICATION-INTENT-001.json"
REUSE="canonical/assessments/FA3-KHRONOS-OPEN-STANDARDS-REUSE-ASSESSMENT-001.json"
GATE="canonical/FA3-GATE-KHRONOS-OPEN-STANDARDS-001.json"

EXPECTED={
"KhronosGroup/Vulkan-Headers":"e3b1eec08173d6b825cd3ac88c885a63b621504a",
"KhronosGroup/Vulkan-Loader":"5f157b62e333c63260d05d81bf66faa216ab0fb8",
"KhronosGroup/Vulkan-ValidationLayers":"f4874eee15c78d7bdb2b7e60659d539f14741500",
"KhronosGroup/Vulkan-Profiles":"1f139a2ea3c475eed7e6699d67fc362203a69c41",
"KhronosGroup/SPIRV-Tools":"b707790a898e44038547df54580022fc1cf89c3d",
"KhronosGroup/glslang":"e1b562a8bed273a02f30b59b66a5d499793cede5",
"KhronosGroup/SPIRV-Cross":"aa217aeb6c9f0ace7a0ab233b28807edf45eb165",
"KhronosGroup/KTX-Software":"4d6fc70eaf62ad0558e63e8d97eb9766118327a6",
"KhronosGroup/glTF-Validator":"434283be08a668a8fb4e437145630ddbf93b0686",
"KhronosGroup/OpenXR-SDK":"f2448a8797c85814aa892efc1ab8707900fbcc78",
"KhronosGroup/OpenCL-Headers":"6fe718c31a45fe25151362a72ef041c3a1047cbd",
"KhronosGroup/OpenCL-ICD-Loader":"b7bd2803acc779c03d96588e9ca9e9568a18698a",
"KhronosGroup/ANARI-SDK":"7534bd263d6ff97764eda93d0e1bd6bd2f108c32",
"KhronosGroup/OpenVX-sample-impl":"031f44bdcd6648f0957c9e351f76c3a64a0bfc32",
"KhronosGroup/NNEF-Tools":"765d27d9095e0c90301165f8933fb325b54ddd17",
}

def load(root:Path, rel:str)->dict[str,Any]:
    p=root/rel
    if not p.is_file(): raise FileNotFoundError(rel)
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(f"object required: {rel}")
    return v

def validate(root:Path)->list[dict[str,Any]]:
    root=root.resolve(); findings=[]
    try:
        p=load(root,PROFILE); c=load(root,CONTRACT); m=load(root,PLAN); i=load(root,INTENT); r=load(root,REUSE); g=load(root,GATE)
    except Exception as exc:
        return [{"code":"KHR-001","message":"required canonical input invalid or missing","detail":str(exc)}]
    count=load_active_release_baseline(root).capability_count
    checks=[
      (count>=175,"KHR-002","active baseline predates CAP-083/175 stack"),
      (p.get("capability_binding")=="CAP-083","KHR-003","profile not bound to CAP-083"),
      (p.get("new_capability") is False and p.get("new_architectural_authority") is False,"KHR-004","profile changes capability/authority"),
      (p.get("capability_count")==count,"KHR-005","profile capability count drift"),
      (p.get("authority",{}).get("host_resource_admission_placement_reservation_lease")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","KHR-006","HRB authority lost"),
      (p.get("hardware_audit",{}).get("vendor_neutral") is True and p.get("hardware_audit",{}).get("cpu_only_viable") is True and p.get("hardware_audit",{}).get("accelerator_cardinality")=="0..N","KHR-007","Hardware Audit invariant failed"),
      (p.get("hardware_safety_envelope",{}).get("fail_closed") is True and p.get("hardware_safety_envelope",{}).get("hardware_parameter_mutation")=="DENY","KHR-008","Hardware Safety Envelope weakened"),
      (p.get("software_coexistence",{}).get("requires_upstream_uninstall") is False and p.get("software_coexistence",{}).get("global_environment_mutation") is False,"KHR-009","Software Coexistence violated"),
      (p.get("current_host",{}).get("runtime_execution_claim") is False and p.get("current_host",{}).get("global_promotion_claim") is False,"KHR-010","unproven runtime promotion claim"),
      (c.get("profile")==p.get("id") and c.get("new_architectural_authority") is False,"KHR-011","contract/profile boundary mismatch"),
      (i.get("proposed_authority_roles")==[] and i.get("declared_new_capabilities")==[],"KHR-012","ApplicationIntent adds authority/capability"),
      (r.get("result")=="PASS" and r.get("current_host_runtime_promotion_claim") is False and r.get("global_promotion_claim") is False,"KHR-013","ReuseAssessment invalid"),
      (g.get("fail_closed") is True and g.get("static_pass_promotes_runtime") is False,"KHR-014","gate promotion semantics invalid"),
      (m.get("source_policy")=="IMMUTABLE_GIT_COMMIT_PIN" and m.get("production_promotion_from_materialization") is False,"KHR-015","materialization policy invalid"),
    ]
    for ok,code,msg in checks:
        if not ok: findings.append({"code":code,"message":msg})
    actual={x.get("repo"):x.get("commit") for x in m.get("projects",[]) if isinstance(x,dict)}
    if actual!=EXPECTED:
        findings.append({"code":"KHR-016","message":"upstream pin set drift","missing":sorted(set(EXPECTED)-set(actual)),"extra":sorted(set(actual)-set(EXPECTED))})
    if len(m.get("projects",[]))!=15:
        findings.append({"code":"KHR-017","message":"materialization project count must remain 15"})
    forbidden=json.dumps({"profile":p,"contract":c},sort_keys=True).lower()
    for token in ('"global_vendor_requirement":true','"global_accelerator_requirement":true'):
        if token in forbidden.replace(" ",""):
            findings.append({"code":"KHR-018","message":"global vendor/accelerator requirement leaked", "token":token})
    return findings

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--json",action="store_true")
    ns=ap.parse_args(); findings=validate(Path(ns.root))
    report={"gate":"FA3-KHRONOS-OPEN-STANDARDS-GATESET-001","result":"PASS" if not findings else "BLOCKED","findings":findings,
            "current_host_runtime_promoted":False}
    print(json.dumps(report,indent=2,sort_keys=True) if ns.json else f"{report['gate']}: {report['result']}")
    return 0 if not findings else 1
if __name__=="__main__": raise SystemExit(main())
