#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from typing import Any
from fa3_release_baseline import load_active_release_baseline

GATESET_ID="FA3-KHRONOS-OPEN-STANDARDS-GATESET-001"
P={
 "profile":"canonical/profiles/FA3-KHRONOS-OPEN-STANDARDS-001.json",
 "contract":"canonical/contracts/FA3-KHRONOS-OPEN-STANDARDS-CONTRACTS-001.json",
 "intent":"canonical/intents/FA3-KHRONOS-OPEN-STANDARDS-APPLICATION-INTENT-001.json",
 "assessment":"canonical/assessments/FA3-KHRONOS-OPEN-STANDARDS-REUSE-ASSESSMENT-001.json",
 "decision":"canonical/decisions/FA3-DEC-KHRONOS-OPEN-STANDARDS-2026-09-27.json",
 "reference":"canonical/references/FA3-KHRONOS-SDK-SET-UPSTREAM-REFERENCE-2026-09-27.json",
 "materialization":"canonical/materialization/FA3-KHRONOS-SDK-MATERIALIZATION-001.json",
 "integration":"canonical/integrations/FA3-KHRONOS-OPEN-STANDARDS-INTEGRATION-001.json",
 "adapter_registry":"canonical/FA3-KHRONOS-ADAPTER-REGISTRY-001.json",
 "gate":"canonical/FA3-GATE-KHRONOS-OPEN-STANDARDS-001.json",
 "gate_registry":"canonical/FA3-GATE-REGISTRY-001.json",
 "policy":"canonical/enforcement-policy.json",
 "distribution_registry":"canonical/distribution-registry.json",
 "distribution_manifest":"canonical/distribution-manifest.json",
 "release_projection":"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
 "evidence":"evidence/evidence-registry.json",
 "build_dependencies":"canonical/third-party/FA3-KHRONOS-BUILD-DEPENDENCIES-001.json",
 "proof_recipes":"canonical/current-host-capability-proof-recipes.json",
 "producer_registry":"canonical/current-host-capability-qualification-constituent-producers.json",
 "matrix":"canonical/conformance-matrix.csv",
}
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

EXPECTED_BUILD_DEPS={
"KhronosGroup/SPIRV-Headers":"29981f65241605e08b0ede4cfeb999fe3b723c6a",
"KhronosGroup/Vulkan-Utility-Libraries":"c279fa4350059faac3d2365df0538977e7e5b097",
"open-source-parsers/jsoncpp":"89e2973c754a9c02a49974d839779b151e95afd6",
"tristanpenman/valijson":"0b4771e273a065d437814baf426bcfcafec0f434",
}
CAP083_PRODUCER_PATH="src/fa3_cap083_khronos_current_host.py"
CAP083_PRODUCER_SHA256="e98a9a44372df017213e618762dcbcbd871d2989ac5643b1cbf30d3f4d5e1be9"
KHRONOS_CURRENT_HOST_WORKFLOW=".github/workflows/fa3-khronos-current-host.yml"
GLOBAL_CURRENT_HOST_WORKFLOW=".github/workflows/fa3-global-current-host-closure.yml"

def load(root:Path,key:str)->dict[str,Any]:
    v=json.loads((root/P[key]).read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(key)
    return v

def gate(root:Path)->dict[str,Any]:
    root=root.resolve(); f=[]
    missing=[v for v in P.values() if not (root/v).is_file()]
    if missing:
        return {"gate_id":GATESET_ID,"result":"FAIL","findings":[{"code":"KHR-000","message":"required files missing","paths":missing}],"current_host_runtime_promotion_claim":False}
    try:
        d={k:load(root,k) for k in P if k!="matrix"}
    except Exception as exc:
        return {"gate_id":GATESET_ID,"result":"FAIL","findings":[{"code":"KHR-001","message":str(exc)}],"current_host_runtime_promotion_claim":False}
    count=load_active_release_baseline(root).capability_count
    with (root/P["matrix"]).open(encoding="utf-8",newline="") as fh:
        rows=list(csv.DictReader(fh))
    ids={r.get("Capability ID") or r.get("capability_id") or r.get("id") for r in rows}
    # conformance-matrix currently has no stable header contract across historical releases;
    # text fallback keeps this validation release-compatible.
    matrix_text=(root/P["matrix"]).read_text(encoding="utf-8")
    required_caps={"CAP-083","CAP-146","CAP-147","CAP-175"}
    if not all(x in matrix_text for x in required_caps): f.append({"code":"KHR-002","message":"required capability bindings missing from conformance matrix"})
    p=d["profile"]; c=d["contract"]; i=d["intent"]; a=d["assessment"]; dec=d["decision"]; ref=d["reference"]; mat=d["materialization"]; integ=d["integration"]; ar=d["adapter_registry"]
    greg=d["gate_registry"]; pol=d["policy"]; dist=d["distribution_registry"]; mani=d["distribution_manifest"]; proj=d["release_projection"]; ev=d["evidence"]
    deps=d["build_dependencies"]; recipes=d["proof_recipes"]; producers=d["producer_registry"]
    checks=[
      (count==p.get("capability_count")==c.get("capability_count")==dec.get("capability_count_after")==a.get("capability_count_after")==integ.get("capability_count"),"KHR-003","active capability baseline drift"),
      (p.get("new_capability") is False and p.get("new_architectural_authority") is False and dec.get("new_capability") is False and dec.get("new_architectural_authority") is False,"KHR-004","capability or authority delta"),
      (p.get("authority",{}).get("host_resources")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","KHR-005","HRB authority lost"),
      (p.get("hardware_audit",{}).get("vendor_neutral") is True and p.get("hardware_audit",{}).get("cpu_only_viable") is True and p.get("hardware_audit",{}).get("accelerator_cardinality")=="0..N","KHR-006","Hardware Audit invariant failed"),
      (p.get("hardware_safety_envelope",{}).get("decision_id")=="FA3-DEC-HARDWARE-SAFETY-2026-09-26" and p.get("hardware_safety_envelope",{}).get("hardware_parameter_mutation")=="DENY","KHR-007","Hardware Safety Envelope weakened"),
      (p.get("software_coexistence",{}).get("capability")=="CAP-175" and p.get("software_coexistence",{}).get("requires_upstream_uninstall") is False and p.get("software_coexistence",{}).get("global_environment_mutation") is False,"KHR-008","CAP-175 coexistence boundary invalid"),
      (i.get("proposed_authority_roles")==[] and i.get("declared_new_capabilities")==[] and a.get("result")=="PASS","KHR-009","Reuse Discovery admission invalid"),
      (mat.get("source_policy")=="IMMUTABLE_GIT_COMMIT_PIN" and mat.get("production_promotion_from_materialization") is False,"KHR-010","materialization semantics invalid"),
      (integ.get("authority_delta")==0 and integ.get("current_host_runtime_promotion") is False,"KHR-011","integration authority/promotion boundary invalid"),
      (len(ar.get("adapters",[]))==13 and all(x.get("authority") is False for x in ar.get("adapters",[])),"KHR-012","adapter registry invalid"),
      (GATESET_ID in greg.get("mandatory_reference_gates",[]) and greg.get("mandatory_reference_gates")==pol.get("mandatory_reference_gates"),"KHR-013","Gate Registry/policy mirror missing or divergent"),
      (proj.get("khronos_open_standards_reconciliation",{}).get("gate_id")==GATESET_ID and proj.get("khronos_open_standards_reconciliation",{}).get("capability_count_after")==count,"KHR-014","release projection reconciliation missing"),
      (p.get("current_host",{}).get("runtime_promotion_claim") is False and dec.get("current_host",{}).get("current_host_runtime_promotion_claim") is False,"KHR-015","unproven current-host promotion claim"),
      (ref.get("build_dependency_record_id")=="FA3-KHRONOS-BUILD-DEPENDENCIES-001" and mat.get("build_dependency_record_id")=="FA3-KHRONOS-BUILD-DEPENDENCIES-001","KHR-019","build-only dependency record binding missing"),
      (mat.get("build_dependency_count")==4 and mat.get("build_policy",{}).get("automatic_upstream_dependency_fetch") is False and mat.get("build_policy",{}).get("cmake_update_deps")=="OFF","KHR-020","deterministic offline build policy invalid"),
    ]
    actual={x.get("repo"):x.get("commit") for x in ref.get("projects",[]) if isinstance(x,dict)}
    checks.append((actual==EXPECTED,"KHR-016","upstream immutable pin set drift"))
    dep_actual={x.get("repo"):x.get("commit") for x in deps.get("projects",[]) if isinstance(x,dict)}
    checks.append((dep_actual==EXPECTED_BUILD_DEPS,"KHR-021","build-only immutable dependency pin set drift"))
    checks.append((deps.get("role")=="IMMUTABLE_BUILD_ONLY_DEPENDENCIES_NOT_RUNTIME_PROVIDERS_NOT_AUTHORITIES" and deps.get("architectural_authority") is False and deps.get("runtime_dependency") is False,"KHR-022","build dependency authority/runtime boundary invalid"))
    openvx=next((x for x in ar.get("adapters",[]) if x.get("project")=="OpenVX-sample-impl"),{})
    checks.append((openvx.get("runtime_admitted") is False and "SAMPLE_IMPLEMENTATION" in str(openvx.get("mode")),"KHR-023","OpenVX sample implementation was promoted or mislabeled"))
    dist_ids={x.get("subject_id") for x in dist.get("records",[]) if isinstance(x,dict)}
    excluded_ids={x.get("subject_id") for x in mani.get("excluded",[]) if isinstance(x,dict)}
    for sid in ("FA3-KHRONOS-SDK-SET-UPSTREAM-REFERENCE-2026-09-27","FA3-KHRONOS-SDK-MATERIALIZATION-001","FA3-KHRONOS-BUILD-DEPENDENCIES-001"):
        checks.append((sid in dist_ids and sid in excluded_ids,"KHR-017","distribution exclusion missing: "+sid))
    cap83=next((x for x in ev.get("records",[]) if x.get("subject_id")=="CAP-083"),{})
    checks.append(("FA3-DEC-KHRONOS-OPEN-STANDARDS-2026-09-27" in cap83.get("source_decision_ids",[]),"KHR-018","CAP-083 Evidence Registry decision binding missing"))
    cap83_recipe=next((x for x in recipes.get("recipes",[]) if x.get("capability_id")=="CAP-083"),{})
    checks.append((cap83_recipe.get("primitive")=="khronos_open_standards_sdk","KHR-024","CAP-083 proof recipe is not Khronos-specific"))
    cap83_producers=[x for x in producers.get("entries",[]) if x.get("subject_id")=="CAP-083"]
    checks.append((len(cap83_producers)==3 and {x.get("test_kind") for x in cap83_producers}=={"positive","negative","rollback"} and all(x.get("adapter_path")==CAP083_PRODUCER_PATH and x.get("adapter_sha256")==CAP083_PRODUCER_SHA256 for x in cap83_producers),"KHR-025","CAP-083 dedicated producer registration/digest invalid"))
    producer_file=root/CAP083_PRODUCER_PATH
    checks.append((producer_file.is_file(),"KHR-026","CAP-083 dedicated producer file missing"))
    ch_workflow=(root/KHRONOS_CURRENT_HOST_WORKFLOW).read_text(encoding="utf-8") if (root/KHRONOS_CURRENT_HOST_WORKFLOW).is_file() else ""
    global_workflow=(root/GLOBAL_CURRENT_HOST_WORKFLOW).read_text(encoding="utf-8") if (root/GLOBAL_CURRENT_HOST_WORKFLOW).is_file() else ""
    checks.append(("--build-core" in ch_workflow and "github.event.pull_request.head.sha || github.sha" in ch_workflow,"KHR-027","exact-head Khronos current-host core build workflow binding missing"))
    checks.append(("Materialize exact-head Khronos core SDK when CAP-083 is selected" in global_workflow and "--build-core" in global_workflow,"KHR-028","global current-host closure lacks exact-head CAP-083 build"))
    for ok,code,msg in checks:
        if not ok:f.append({"code":code,"message":msg})
    return {"schema":"fa3.khronos-open-standards-gate-report.v1","gate_id":GATESET_ID,"result":"PASS" if not f else "FAIL","findings":f,"capability_delta":0,"authority_delta":0,"current_host_runtime_promotion_claim":False}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--json",action="store_true");ns=ap.parse_args()
    r=gate(Path(ns.root));print(json.dumps(r,indent=2,sort_keys=True) if ns.json else f"{GATESET_ID}: {r['result']}");return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
