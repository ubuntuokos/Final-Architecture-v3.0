#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_creative_project_workflow import CreativeProjectError, build_timeline_projection_plan, plan_scoped_revision, validate_project_state
from fa3_release_baseline import load_active_release_baseline

CONTRACT="canonical/contracts/FA3-CREATIVE-PROJECT-WORKFLOW-CONTRACTS-001.json"
INTENT="canonical/intents/FA3-CREATIVE-PROJECT-WORKFLOW-APPLICATION-INTENT-001.json"
ASSESSMENT="canonical/assessments/FA3-CREATIVE-PROJECT-WORKFLOW-REUSE-ASSESSMENT-001.json"
DECISION="canonical/decisions/FA3-DEC-CREATIVE-PROJECT-WORKFLOW-FLOVA-PATTERNS-2026-09-26.json"
VIDEO_PROFILE="canonical/profiles/FA3-VIDEO-001.json"
SKILL_REGISTRY="canonical/skill-registry.json"
SKILL="skills/fa3-creative-project-workflow/SKILL.md"
GATE_RECORD="canonical/FA3-GATE-CREATIVE-PROJECT-WORKFLOW-001.json"
ENFORCEMENT="canonical/creative-project-workflow-enforcement.json"
EVIDENCE="evidence/reference/creative-project-workflow-ci-2026-09-26.json"
GATE_ID="FA3-CREATIVE-PROJECT-WORKFLOW-GATESET-001"
CONTRACT_ID="FA3-CREATIVE-PROJECT-WORKFLOW-CONTRACTS-001"
SKILL_ID="fa3-creative-project-workflow"
CAPABILITIES=["CAP-014","CAP-041","CAP-111","CAP-159","CAP-166","CAP-168","CAP-170","CAP-171","CAP-172"]

def loadj(path: Path) -> dict[str, Any]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict): raise ValueError(f"{path}: top-level object required")
    return obj

def sample_project() -> dict[str, Any]:
    return {
      "schema":"fa3.creative-project-state.v1","project_id":"gate-sample",
      "nodes":[
        {"id":"shot-a","type":"SHOT","order":1},{"id":"asset-a","type":"ASSET"},{"id":"timeline-a","type":"TIMELINE_SEGMENT"},
        {"id":"shot-b","type":"SHOT","order":2},{"id":"asset-b","type":"ASSET"}],
      "edges":[
        {"from":"shot-a","to":"asset-a","type":"DERIVED_FROM","invalidate_on_revision":True},
        {"from":"asset-a","to":"timeline-a","type":"EDIT_SOURCE","invalidate_on_revision":True},
        {"from":"shot-b","to":"asset-b","type":"DERIVED_FROM","invalidate_on_revision":True}],
      "documents":[
        {"id":"spec","origin":"USER","editable":True,"scope":["*"]},
        {"id":"notes","origin":"AI","editable":True,"scope":["shot-a"],"provenance_ref":"prov:1"},
        {"id":"reference","origin":"IMPORTED_REFERENCE","editable":False,"scope":["shot-b"]}]}

def run_regressions() -> dict[str, Any]:
    cases=[]
    def record(name: str, ok: bool) -> None:
        cases.append({"case_id":f"CPW-{len(cases)+1:03d}","name":name,"status":"PASS" if ok else "FAIL"})
    p=sample_project()
    record("valid-project-state",validate_project_state(p)["result"]=="PASS")
    plan=plan_scoped_revision(p,["shot-a"])
    record("scoped-downstream-invalidation",plan["affected_node_ids"]==["asset-a","shot-a","timeline-a"])
    record("unrelated-nodes-preserved","shot-b" in plan["preserved_node_ids"] and "asset-b" in plan["preserved_node_ids"])
    record("planning-is-not-execution",plan["execution_authorized"] is False and plan["authority_expansion"] is False)
    record("router-hrb-uaf-boundaries",plan["model_provider_selection"]=="FA3-AUTH-MODEL-ROUTER-001" and plan["host_resource_admission"]=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and plan["action_execution"]=="FA3-UNIFIED-ACTION-FABRIC-001")
    locked=sample_project(); next(x for x in locked["nodes"] if x["id"]=="asset-a")["locked"]=True
    locked_plan=plan_scoped_revision(locked,["shot-a"])
    record("locked-node-approval-boundary",locked_plan["approval_required"] is True and locked_plan["approval_boundary_node_ids"]==["asset-a"])
    bad=sample_project(); next(x for x in bad["documents"] if x["id"]=="reference")["editable"]=True
    failed=False
    try: validate_project_state(bad)
    except CreativeProjectError: failed=True
    record("imported-reference-read-only",failed)
    timeline=build_timeline_projection_plan(p)
    record("timeline-no-direct-native-mutation",timeline["canonical_interchange"]=="OpenTimelineIO" and timeline["direct_native_project_mutation"] is False)
    return {"result":"PASS" if all(x["status"]=="PASS" for x in cases) else "FAIL","total":len(cases),"passed":sum(x["status"]=="PASS" for x in cases),"cases":cases}

def canonical_check(root: Path) -> list[str]:
    required=[CONTRACT,INTENT,ASSESSMENT,DECISION,VIDEO_PROFILE,SKILL_REGISTRY,SKILL,GATE_RECORD,ENFORCEMENT,EVIDENCE]
    missing=[p for p in required if not (root/p).is_file()]
    if missing: return [f"missing files: {missing}"]
    f=[]; cap=load_active_release_baseline(root).capability_count
    c=loadj(root/CONTRACT); i=loadj(root/INTENT); a=loadj(root/ASSESSMENT); d=loadj(root/DECISION)
    v=loadj(root/VIDEO_PROFILE); r=loadj(root/SKILL_REGISTRY); g=loadj(root/GATE_RECORD); e=loadj(root/ENFORCEMENT); ev=loadj(root/EVIDENCE)
    skill=(root/SKILL).read_text(encoding="utf-8")
    if not (c.get("id")==CONTRACT_ID and c.get("provider_neutral") is True and c.get("new_capability") is False and c.get("new_architectural_authority") is False and c.get("capability_count")==cap==175 and c.get("capability_bindings")==CAPABILITIES): f.append("contract capability/authority baseline drift")
    ctx=c.get("project_context",{})
    if not (ctx.get("user_documents_and_ai_notes_separate") is True and ctx.get("ai_authored_documents_require_provenance") is True and ctx.get("imported_references_read_only_by_default") is True and ctx.get("global_project_corpus_auto_injection_forbidden") is True): f.append("project context provenance/scope invariant drift")
    rev=c.get("scoped_revision",{})
    if not (rev.get("plan_required_before_execution") is True and rev.get("unaffected_nodes_preserved_by_default") is True and rev.get("locked_or_human_approved_affected_nodes_require_approval") is True and rev.get("full_project_regeneration_is_default") is False): f.append("scoped revision invariant drift")
    route=c.get("execution_routing",{})
    if not (route.get("action_execution")=="FA3-UNIFIED-ACTION-FABRIC-001" and route.get("model_provider_selection")=="FA3-AUTH-MODEL-ROUTER-001" and route.get("host_resource_admission")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and route.get("direct_provider_bypass") is False and route.get("silent_provider_fallback") is False and route.get("billable_remote_execution_requires_explicit_ack") is True): f.append("execution authority boundary drift")
    ed=c.get("storyboard_media_timeline",{})
    if not (ed.get("canonical_interchange")=="OpenTimelineIO" and ed.get("direct_kdenlive_xml_mutation_forbidden") is True and "FA3_VIDEO_EDITOR_COMMAND_BUS" in ed.get("native_timeline_mutation","")): f.append("editorial projection boundary drift")
    pat=c.get("external_pattern_policy",{})
    if not (pat.get("classification")=="REFERENCE_ONLY_PATTERN_SOURCE" and pat.get("runtime_dependency") is False and pat.get("provider_dependency") is False and pat.get("external_code_imported") is False and pat.get("external_skill_content_imported") is False): f.append("external Flova pattern boundary drift")
    hw=i.get("hardware_audit",{})
    if not (hw.get("vendor_neutral") is True and hw.get("cpu_only_viable") is True and hw.get("accelerator_cardinality")=="0..N" and hw.get("global_accelerator_requirement") is False and hw.get("hardware_safety_envelope_required_for_parameter_mutation") is True): f.append("Hardware Audit invariant drift")
    if not (a.get("result")=="PASS" and "FA3-VIDEO-001" in a.get("covered_ids",[]) and a.get("new_capabilities")==0 and a.get("new_architectural_authorities")==0 and a.get("current_host_runtime_promotion_claim") is False and a.get("global_promotion_claim") is False): f.append("ReuseAssessment drift or runtime overclaim")
    effect=d.get("authority_effect",{})
    if not (effect.get("new_capability") is False and effect.get("new_architectural_authority") is False and effect.get("capability_count_after")==cap and d.get("current_host",{}).get("runtime_promotion_claim") is False): f.append("decision capability/authority/runtime boundary drift")
    wf=v.get("creative_project_workflow",{})
    if not (CONTRACT_ID in v.get("contracts",[]) and wf.get("contract_id")==CONTRACT_ID and wf.get("skill_id")==SKILL_ID and wf.get("runtime_promotion_claim") is False): f.append("FA3-VIDEO creative workflow binding missing")
    entries=[x for x in r.get("entries",[]) if x.get("skill_id")==SKILL_ID]
    if not (len(entries)==1 and entries[0].get("admission_status")=="ADMITTED" and entries[0].get("distribution_class")=="FA3_NATIVE" and entries[0].get("task_scoped") is True and entries[0].get("authority") is False and entries[0].get("remote_fetch") is False and entries[0].get("profile_id")=="FA3-VIDEO-001"): f.append("Skill Fabric registry binding drift")
    for heading in ("## use_when","## inputs","## procedure","## guardrails","## pitfalls","## acceptance_checks"):
        if heading not in skill: f.append(f"creative skill missing required heading: {heading}")
    if "Direct provider invocation is forbidden" not in skill or "paid service" not in skill: f.append("creative skill provider/billing guardrail missing")
    if not (g.get("gateset")==GATE_ID and g.get("fail_closed") is True and g.get("current_host_runtime_promotion") is False and e.get("gate_id")==GATE_ID and e.get("fail_closed") is True and len(e.get("mandatory_rules",[]))==20): f.append("gate/enforcement record drift")
    claims=ev.get("claims",{})
    if not (ev.get("status")=="PASS" and claims.get("static_contract_and_reference_regression_pass") is True and claims.get("flova_runtime_used") is False and claims.get("current_host_runtime_pass") is False and claims.get("production_provider_admitted") is False and claims.get("global_promotion_claim") is False): f.append("reference evidence overclaims runtime or provider admission")
    return f

def evaluate(root: Path) -> dict[str, Any]:
    root=Path(root).resolve(); findings=canonical_check(root); regressions=run_regressions(); cap=load_active_release_baseline(root).capability_count
    result="PASS" if not findings and regressions["result"]=="PASS" else "FAIL"
    report={"schema":"fa3.creative-project-workflow-gate-report.v1","gate_id":GATE_ID,"result":result,"findings":findings,"regressions":regressions,"capability_count":cap,"new_capabilities":0,"new_architectural_authorities":0,"current_host_runtime_claim":False,"hardware_audit":{"vendor_neutral":True,"cpu_only_planning_viable":True,"accelerator_cardinality":"0..N"}}
    out=root/"reports/creative-project-workflow-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); args=ap.parse_args()
    report=evaluate(Path(args.root)); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0 if report["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
