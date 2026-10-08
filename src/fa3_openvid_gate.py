#!/usr/bin/env python3
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path

CAP = 175
PIN = "293916f25ef48d1799bceea13b78999596a11f0b"
RUNTIME = "DENIED_BASELINE_AND_COMMERCIAL_RUNTIME_BY_LICENSE_POLICY"
RULES = json.loads(r'''["OPENVID_NATIVE_FAST_COMPOSE_STANDALONE_AND_OPENCUT_EMBEDDED","NATIVE_FA3OPENVID_PROJECT_STATE_NOT_EXTERNAL_PROVIDER","BIDIRECTIONAL_EDITABLE_REFERENCE_NO_AUTO_FLATTEN","SHARED_MOTION_DESIGNER_EXCLUSIVE_ADVANCED_MOTION","CFA3_VIDEO_EDITOR_EXCLUSIVE_FULL_NLE","SHARED_PROGRAMMABLE_VIDEO_EDITING_FABRIC_REQUIRED","SHARED_ENGINE_SELECTOR_MLT_OR_CFA3_NATIVE","SHARED_FFMPEG_WITHOUT_DUPLICATE_CORE","WEBDESIGN_EMBEDDED_COMPOSITION_HANDOFF","OPENTIMELINEIO_INTERCHANGE_ONLY","CPU_ONLY_BASELINE_AND_HRB_ADMITTED_OPTIONAL_GPU","UPSTREAM_NONCOMMERCIAL_REFERENCE_ONLY","UPSTREAM_RUNTIME_REQUIRES_LICENSE_AND_EVIDENCE","TYPED_MUTATION_DRY_RUN_AND_PROVENANCE","EXPLICIT_CLOUD_ESCALATION_ONLY","BOUNDED_EXPORT_AND_ARTIFACT_QA","CAPABILITY_175_NO_NEW_AUTHORITY","HISTORICAL_REFERENCE_EVIDENCE_IMMUTABLE","NO_CURRENT_HOST_RUNTIME_PROMOTION","WORKLOAD_MODE_GLOBAL_INDICATOR"]''')
SPEC = json.loads(r'''{"fast_compose_role":"FAST_COMPOSE","project_format":".fa3openvid","handoff":"BIDIRECTIONAL_EDITABLE_REFERENCE_NO_AUTO_FLATTEN","motion_owner":"CFA3_SHARED_MOTION_DESIGNER","nle_owner":"CFA3_VIDEO_EDITOR","shared_fabric":"FA3-PROGRAMMABLE-VIDEO-EDITING-001","engines":"MLT|CFA3 Native Media Composition","ffmpeg":true,"webdesign":true,"timeline_ir":"CFA3_NATIVE_PROJECT_STATE","cpu_only":true,"license":"PolyForm Noncommercial License 1.0.0","runtime_status":"DENIED_BASELINE_AND_COMMERCIAL_RUNTIME_BY_LICENSE_POLICY","dry_run":true,"explicit_cloud":true,"bounded_export":true,"capability_count":175,"historical_evidence":"FA3-EVID-OPENVID-CI-2026-09-04","runtime_promotion":false,"global_indicator":true}''')
PATHS = json.loads(r'''{"c":"canonical/contracts/FA3-BROWSER-LOCAL-VIDEO-COMPOSITING-CONTRACTS-001.json","d":"canonical/decisions/FA3-DEC-OPENVID-BROWSER-LOCAL-COMPOSITING-2026-09-04.json","p":"canonical/providers/FA3-PROVIDER-OPENVID-001.json","g":"canonical/FA3-GATE-OPENVID-001.json","e":"canonical/openvid-enforcement.json","a":"canonical/openvid-runtime-admission.json","r":"canonical/releases/FA3-RELEASE-PROJECTION-OPENVID-2026-09-04.json","apps":"canonical/FA3-APPLICATION-DONOR-LINKS-001.json","profile":"canonical/profiles/FA3-PROGRAMMABLE-VIDEO-EDITING-001.json","shared":"canonical/contracts/FA3-VIDEO-TIMELINE-PROVIDER-CONTRACTS-001.json","reuse":"canonical/assessments/CFA3-OPENVID-SHARED-REUSE-ASSESSMENT-2026-10-08.json","intent":"canonical/intents/CFA3-OPENVID-SHARED-APPLICATION-INTENT-2026-10-08.json","impact":"canonical/current-host-impact/CFA3-CH-IMPACT-OPENVID-SHARED-20261008.json","history":"evidence/reference/openvid-ci-2026-09-04.json"}''')

def runtime_admission_allowed(value):
    return all(value.get(k) is True for k in (
        "license_compatible_with_intended_deployment",
        "separate_license_or_independent_implementation",
        "immutable_source_pin",
        "contract_conformance_pass", "current_host_e2e_pass"))

def project_handoff_allowed(value):
    return (value.get("project_format") == ".fa3openvid"
        and value.get("editable_reference") is True
        and value.get("round_trip") is True
        and value.get("auto_flatten") is False)

def export_plan_allowed(value):
    return value.get("backend_order") == [
        "CPU_ONLY_BASELINE","HRB_ADMITTED_ACCELERATOR_OPTIONAL",
        "SOFTWARE_ENCODER","WASM_FALLBACK_BOUNDED"
    ] and all(value.get(k) is True for k in (
        "bounded_memory","fallbacks_observable","direct_to_disk_preferred"))

def regression_cases():
    results=[]
    for index,(key,expected) in enumerate(SPEC.items()):
        correct=copy.deepcopy(SPEC)
        rejected=copy.deepcopy(SPEC)
        rejected[key]=None
        positive=correct.get(key)==expected
        negative=rejected.get(key)!=expected
        results.append({"rule":RULES[index],"positive":positive,
                        "negative_refusal":negative,
                        "result":"PASS" if positive and negative else "FAIL"})
    return results

def _report(findings,cases):
    return {"schema":"fa3.openvid-shared-gate-report.v1",
            "gate_id":"FA3-OPENVID-GATESET-001",
            "status":"PASS" if not findings else "FAIL","fail_closed":True,
            "finding_count":len(findings),"findings":findings,
            "regression_count":len(cases),"regressions":cases,
            "capability_count_after":CAP,
            "current_host_runtime_promotion_claimed":False}

def gate(root):
    root=Path(root)
    d={}
    findings=[]
    cases=regression_cases()
    for key,path in PATHS.items():
        try:
            d[key]=json.loads((root/path).read_text(encoding="utf-8"))
        except (OSError,ValueError) as exc:
            findings.append({"code":"OPENVID-SHARED-REQUIRED-ARTIFACT","path":path,"error":str(exc)})
    if findings:
        return _report(findings,cases)
    c,p,n=d["c"],d["p"],d["d"]
    app=c.get("fast_compose_application",{})
    auth=c.get("authority_boundaries",{})
    exe=c.get("execution_architecture",{})
    web=c.get("webdesign_integration",{})
    present={
      "fast_compose_role":app.get("role"),
      "project_format":app.get("project_format"),
      "handoff":app.get("two_way_handoff"),
      "motion_owner":auth.get("advanced_motion"),
      "nle_owner":auth.get("full_nle"),
      "shared_fabric":exe.get("shared_fabric"),
      "engines":"|".join(exe.get("engines",[])),
      "ffmpeg":exe.get("shared_ffmpeg"),
      "webdesign":web.get("supported"),
      "timeline_ir":c.get("canonical_timeline_ir"),
      "cpu_only":exe.get("cpu_only_baseline"),
      "license":p.get("upstream",{}).get("license"),
      "runtime_status":p.get("runtime_activation",{}).get("status"),
      "dry_run":d["shared"].get("operation_requirements",{}).get("destructive_mutation_requires_dry_run"),
      "explicit_cloud":c.get("requirements",{}).get("explicit_cloud_escalation"),
      "bounded_export":c.get("requirements",{}).get("buffered_export_bounded"),
      "capability_count":c.get("capability_count"),
      "historical_evidence":d["history"].get("evidence_id"),
      "runtime_promotion":n.get("current_host_runtime_promotion_claimed"),
      "global_indicator":app.get("gui",{}).get("global_workload_mode_indicator")}
    for k,want in SPEC.items():
        if present.get(k)!=want:
            findings.append({"code":"OPENVID-SHARED-SPEC-MISMATCH",
                             "field":k,"actual":present.get(k),"expected":want})
    def require(label,condition):
        if not condition:
            findings.append({"code":label})
    require("OPENVID-SHARED-ROUNDTRIP",
        project_handoff_allowed(app)
        and app.get("open_cut_project")==".fa3clip"
        and c.get("native_project_format")==".fa3openvid")
    require("OPENVID-SHARED-AUTHORITIES",
        c.get("project_state_authority")=="CFA3_OPENVID_SHARED_NATIVE_PROJECT"
        and c.get("interchange_ir")=="OpenTimelineIO"
        and auth.get("fast_edit")=="CFA3_OPENCUT"
        and d["profile"].get("authority_boundaries",{}).get("advanced_motion")=="CFA3_SHARED_MOTION_DESIGNER"
        and d["profile"].get("authority_boundaries",{}).get("human_finishing_nle")=="CFA3_VIDEO_EDITOR_SOLE_FULL_EDIT"
        and d["shared"].get("editorial_scope",{}).get("OpenVid Shared")=="FAST_COMPOSE_ONLY")
    require("OPENVID-SHARED-UPSTREAM-DENY",
        p.get("upstream",{}).get("observed_commit")==PIN
        and p.get("upstream",{}).get("floating_main_allowed_for_promotion_evidence") is False
        and p.get("runtime_activation",{}).get("source_vendoring_allowed") is False
        and p.get("runtime_activation",{}).get("commercial_runtime_allowed") is False
        and p.get("canonical_root") is False and p.get("architectural_authority") is False
        and p.get("hard_dependency") is False
        and d["a"].get("admission",{}).get("baseline_runtime") is False
        and d["a"].get("admission",{}).get("commercial_production_runtime") is False
        and d["a"].get("status")==RUNTIME
        and d["a"].get("current_host_runtime_evidence")=="NOT_CLAIMED")
    require("OPENVID-SHARED-ENGINE-ROUTE",
        exe.get("engine_selector")=="CFA3_ENGINE_SELECTOR"
        and exe.get("accelerator_opt_in_requires_hrb") is True
        and exe.get("display_gpu_ai_default") is False
        and export_plan_allowed({
          **c.get("render_policy",{}),
          "bounded_memory":c.get("requirements",{}).get("bounded_memory"),
          "direct_to_disk_preferred":c.get("requirements",{}).get("direct_to_disk_preferred")}))
    require("OPENVID-SHARED-WEB-INTEGRATION",
        web.get("editable_link_preserved") is True
        and web.get("fast_edit_via")=="CFA3_OPENCUT_EMBEDDED"
        and app.get("auto_flatten") is False)
    apps={x.get("application_id") for x in d["apps"].get("applications",[])}
    edges={(x.get("from_application"),x.get("to_application")) for x in d["apps"].get("relationships",[])}
    require("OPENVID-SHARED-APP-REGISTRY",
        {"fa3.openvid-shared","fa3.opencut","fa3.webdesign"}.issubset(apps)
        and {("fa3.openvid-shared","fa3.opencut"),
             ("fa3.opencut","fa3.openvid-shared"),
             ("fa3.openvid-shared","fa3.webdesign"),
             ("fa3.webdesign","fa3.openvid-shared")}.issubset(edges))
    require("OPENVID-SHARED-DONOR-REUSE",
        d["reuse"].get("result")=="PASS"
        and d["reuse"].get("donor_planning_snapshot",{}).get("published_main_commit")=="d4685845ae355f482b1dd0c82709f53d62ac8769"
        and d["reuse"].get("shared_capability_placement",{}).get("disposition")=="SHARED"
        and d["reuse"].get("donor_adoption_authorized") is False)
    require("OPENVID-SHARED-CH-IMPACT",
        d["impact"].get("status")=="NO_RUNTIME_IMPACT"
        and d["impact"].get("physical_requalification_required") is False
        and d["impact"].get("historical_evidence_reused") is False
        and not d["impact"].get("current_host_changes"))
    require("OPENVID-SHARED-HISTORY",
        n.get("historical_decision",{}).get("original",{}).get("capability_count_after")==143
        and d["history"].get("status")=="PASS"
        and d["history"].get("capability_count_after")==143
        and d["history"].get("regression_count")==18)
    require("OPENVID-SHARED-GATE-SET",
        d["g"].get("rule_count")==len(RULES)
        and d["g"].get("capability_count")==CAP
        and d["e"].get("rules")==RULES
        and d["e"].get("capability_count")==CAP
        and n.get("mandatory_rules")==RULES)
    require("OPENVID-SHARED-175-NO-NEW-AUTHORITY",
        all(x.get("capability_count_after",x.get("capability_count"))==CAP
            for x in (c,n,p,d["g"],d["e"],d["a"],d["r"]))
        and n.get("new_capabilities")==0
        and n.get("new_architectural_authorities")==0
        and d["r"].get("runtime_promotion") is False
        and d["intent"].get("runtime_delivery_claim") is False)
    require("OPENVID-SHARED-NEGATIVE-REGRESSIONS",
        len(cases)==len(RULES) and all(z["result"]=="PASS" for z in cases))
    return _report(findings,cases)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default=".")
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--output")
    args=parser.parse_args()
    cases=regression_cases()
    report=_report([] if all(c["result"]=="PASS" for c in cases) else [{"code":"SELFTEST"}],cases) if args.self_test else gate(args.root)
    result=json.dumps(report,indent=2)
    if args.output:
        Path(args.output).write_text(result+"\n",encoding="utf-8")
    print(result)
    raise SystemExit(0 if report["status"]=="PASS" else 1)

if __name__=="__main__":
    main()
