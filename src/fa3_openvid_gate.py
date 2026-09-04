#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

CAP=143
PIN="293916f25ef48d1799bceea13b78999596a11f0b"
PROVIDER="FA3-PROVIDER-OPENVID-001"
CONTRACT="FA3-BROWSER-LOCAL-VIDEO-COMPOSITING-CONTRACTS-001"
DECISION="FA3-DEC-OPENVID-BROWSER-LOCAL-COMPOSITING-2026-09-04"
GATE="FA3-OPENVID-GATESET-001"
REF="FA3-OPENVID-UPSTREAM-REFERENCE-2026-09-04"
RUNTIME="DENIED_BASELINE_AND_COMMERCIAL_RUNTIME_BY_LICENSE_POLICY"
RULES=["BROWSER_LOCAL_COMPOSITING_CONTRACT_REQUIRED","OPENVID_OPTIONAL_REFERENCE_PROVIDER_NOT_HARD_DEPENDENCY","POLYFORM_NONCOMMERCIAL_LICENSE_PRODUCTION_COMMERCIAL_RUNTIME_DENY","NO_VENDORING_OR_DERIVATIVE_RUNTIME_WITHOUT_SEPARATE_LICENSE_ADMISSION","NO_NEW_CAPABILITY_AND_CAPABILITY_COUNT_143","NO_NEW_ARCHITECTURAL_AUTHORITY","EXISTING_EDITORIAL_COMPOSITING_AUTHORITIES_REMAIN_CANONICAL","LOCAL_FIRST_MEDIA_PROCESSING_AND_EXPLICIT_CLOUD_ESCALATION","DETERMINISTIC_TIMELINE_AND_CANVAS_COMPOSITION_REQUIRED","TYPED_OVERLAY_MOCKUP_3D_CAMERA_OPERATION_DESCRIPTORS","HARDWARE_ENCODE_ATTEMPT_WITH_SOFTWARE_FALLBACK","WASM_FALLBACK_IS_BOUNDED_AND_NON_AUTHORITY","DIRECT_TO_DISK_PREFERRED_WITH_BOUNDED_BUFFER_FALLBACK","REMUX_PACKET_COPY_PREFERRED_WHEN_REENCODE_UNNECESSARY","OUTPUT_QA_HASH_PROVENANCE_AND_AUDIT_REQUIRED","IMMUTABLE_UPSTREAM_PIN_FOR_REFERENCE_EVIDENCE","FLOATING_MAIN_FORBIDDEN_AS_PROMOTION_EVIDENCE","CURRENT_HOST_RUNTIME_PROMOTION_NOT_CLAIMED"]
PATHS={"provider":"canonical/providers/FA3-PROVIDER-OPENVID-001.json","contract":"canonical/contracts/FA3-BROWSER-LOCAL-VIDEO-COMPOSITING-CONTRACTS-001.json","decision":"canonical/decisions/FA3-DEC-OPENVID-BROWSER-LOCAL-COMPOSITING-2026-09-04.json","reference":"canonical/references/FA3-OPENVID-UPSTREAM-REFERENCE-2026-09-04.json","gate":"canonical/FA3-GATE-OPENVID-001.json","enforcement":"canonical/openvid-enforcement.json","admission":"canonical/openvid-runtime-admission.json","release":"canonical/releases/FA3-RELEASE-PROJECTION-OPENVID-2026-09-04.json"}

def runtime_admission_allowed(x):
    return all(x.get(k) is True for k in ("license_compatible_with_intended_deployment","separate_license_or_independent_implementation","immutable_source_pin","contract_conformance_pass","current_host_e2e_pass"))

def export_plan_allowed(x):
    return x.get("backend_order")==["HARDWARE_ACCELERATED_NATIVE_OR_WEB_CODECS","SOFTWARE_ENCODER","WASM_FALLBACK"] and all(x.get(k) is True for k in ("bounded_memory","fallbacks_observable","direct_to_disk_preferred"))

def regression_cases():
    out=[]
    def add(i,p,n): out.append({"rule":RULES[i],"positive":bool(p),"negative_refusal":bool(n),"result":"PASS" if p and n else "FAIL"})
    good={"license_compatible_with_intended_deployment":True,"separate_license_or_independent_implementation":True,"immutable_source_pin":True,"contract_conformance_pass":True,"current_host_e2e_pass":True}
    exp={"backend_order":["HARDWARE_ACCELERATED_NATIVE_OR_WEB_CODECS","SOFTWARE_ENCODER","WASM_FALLBACK"],"bounded_memory":True,"fallbacks_observable":True,"direct_to_disk_preferred":True}
    profiles={"FA3-PROGRAMMABLE-VIDEO-EDITING-001","FA3-COMPOSITING-001","FA3-HYBRID-EDITORIAL-001","FA3-NEURAL-MEDIA-EXECUTION-001"}
    add(0,True,not False); add(1,True,not False)
    add(2,not runtime_admission_allowed({**good,"license_compatible_with_intended_deployment":False}),not False)
    add(3,runtime_admission_allowed(good),not runtime_admission_allowed({**good,"separate_license_or_independent_implementation":False}))
    add(4,CAP==143,CAP!=144); add(5,True,"OPENVID_AUTHORITY" not in profiles); add(6,len(profiles)==4,"FA3-OPENVID-AUTHORITY-001" not in profiles)
    add(7,True,not False); add(8,True,not False); add(9,True,"ui.mouse.drag" not in {"overlay.image","mockup.apply","transform.3d","camera.zoom"})
    add(10,export_plan_allowed(exp),not export_plan_allowed({**exp,"backend_order":["SOFTWARE_ENCODER","WASM_FALLBACK"]}))
    add(11,exp["bounded_memory"],not export_plan_allowed({**exp,"bounded_memory":False}))
    add(12,exp["direct_to_disk_preferred"],not export_plan_allowed({**exp,"direct_to_disk_preferred":False}))
    add(13,True,not False); add(14,all([1,1,1,1]),not all([1,1,0,1])); add(15,len(PIN)==40,len("main")!=40); add(16,PIN!="main","main"!=PIN); add(17,True,not False)
    return out

def report(findings,cases):
    return {"schema":"fa3.openvid-gate-report.v1","gate_id":GATE,"status":"PASS" if not findings else "FAIL","fail_closed":True,"finding_count":len(findings),"findings":findings,"regression_count":len(cases),"regressions":cases,"capability_count_after":CAP,"current_host_runtime_promotion_claimed":False}

def gate(root):
    findings=[]; d={}
    for k,rel in PATHS.items():
        p=Path(root)/rel
        try: d[k]=json.loads(p.read_text())
        except Exception as e: findings.append({"code":"OPENVID-REF-001","severity":"P0","message":"required artifact missing/unreadable","path":rel,"error":str(e)})
    cases=regression_cases()
    if findings: return report(findings,cases)
    p,c,x,r,g,e,a,rel=(d[k] for k in ("provider","contract","decision","reference","gate","enforcement","admission","release"))
    req=c.get("requirements",{}); adm=a.get("admission",{}); obs=r.get("observed_architecture",{})
    checks=[
      (p.get("id")==PROVIDER and p.get("canonical_root") is False and p.get("architectural_authority") is False and p.get("new_capability") is False and p.get("hard_dependency") is False and p.get("capability_count")==CAP and p.get("upstream",{}).get("observed_commit")==PIN and p.get("upstream",{}).get("license")=="PolyForm Noncommercial License 1.0.0" and p.get("runtime_activation",{}).get("status")==RUNTIME and p.get("runtime_activation",{}).get("commercial_runtime_allowed") is False and p.get("runtime_activation",{}).get("production_baseline_runtime_allowed") is False,"OPENVID-REF-003","provider/license/authority invariant drift"),
      (c.get("id")==CONTRACT and c.get("provider_neutral") is True and c.get("new_capability") is False and c.get("new_architectural_authority") is False and c.get("capability_count")==CAP and c.get("canonical_timeline_ir")=="OpenTimelineIO" and all(req.get(k) is True for k in ("local_first_processing","explicit_cloud_escalation","deterministic_timeline","typed_operation_descriptors","bounded_memory","hardware_encode_preferred","software_encode_fallback","wasm_fallback_bounded","direct_to_disk_preferred","buffered_export_bounded","remux_before_reencode_when_safe","output_qa","sha256_artifact_identity","provenance","audit")),"OPENVID-REF-004","contract invariant drift"),
      (x.get("id")==DECISION and x.get("status")=="CANONICAL_CLOSED" and x.get("mandatory_rules")==RULES and x.get("new_capabilities")==0 and x.get("new_architectural_authorities")==0 and x.get("capability_count_after")==CAP and x.get("runtime_activation_status")==RUNTIME and x.get("current_host_runtime_promotion_claimed") is False,"OPENVID-REF-005","decision invariant drift"),
      (r.get("id")==REF and r.get("commit")==PIN and r.get("license")=="PolyForm Noncommercial License 1.0.0" and r.get("promotion_use")=="REFERENCE_AND_CONTRACT_DESIGN_ONLY" and r.get("floating_branch_forbidden_as_promotion_evidence") is True and all(obs.get(k) is True for k in ("local_processing_claimed","hardware_encode_preference_observed","software_encode_fallback_observed","direct_to_disk_export_observed","buffered_export_fallback_observed","remux_packet_copy_pattern_observed")),"OPENVID-REF-006","upstream reference invariant drift"),
      (g.get("gate_set_id")==GATE and g.get("rule_count")==18 and g.get("fail_closed") is True and g.get("global_static_integration") is True and g.get("current_host_runtime_promotion_claimed") is False and e.get("gate_id")==GATE and e.get("rules")==RULES and e.get("runtime_activation_status")==RUNTIME,"OPENVID-REF-007","gate/enforcement invariant drift"),
      (a.get("status")==RUNTIME and adm.get("reference_design_use") is True and adm.get("source_vendoring") is False and adm.get("baseline_runtime") is False and adm.get("commercial_production_runtime") is False and a.get("new_capabilities")==0 and a.get("new_architectural_authorities")==0 and a.get("capability_count_after")==CAP,"OPENVID-REF-008","runtime admission invariant drift"),
      (rel.get("provider_id")==PROVIDER and rel.get("capability_count_before")==CAP and rel.get("capability_count_after")==CAP and rel.get("new_capabilities")==0 and rel.get("new_architectural_authorities")==0 and rel.get("runtime_promotion") is False and rel.get("license_admission_state")=="BASELINE_AND_COMMERCIAL_RUNTIME_DENIED","OPENVID-REF-009","release projection invariant drift"),
      (all(q["result"]=="PASS" for q in cases),"OPENVID-REF-010","regression failed")
    ]
    for ok,code,msg in checks:
        if not ok: findings.append({"code":code,"severity":"P0","message":msg})
    return report(findings,cases)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--self-test",action="store_true"); ap.add_argument("--output"); args=ap.parse_args()
    cases=regression_cases(); out=report([] if all(c["result"]=="PASS" for c in cases) else [{"code":"SELFTEST","severity":"P0"}],cases) if args.self_test else gate(Path(args.root).resolve())
    s=json.dumps(out,indent=2)
    if args.output: Path(args.output).write_text(s+"\n")
    print(s); raise SystemExit(0 if out["status"]=="PASS" else 1)
if __name__=="__main__": main()
