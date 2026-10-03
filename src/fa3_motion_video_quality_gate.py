#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from fa3_release_baseline import module_active_capability_count
from fa3_motion_video_quality import MotionVideoQualityError,build_edit_proposal,deterministic_render_key,normalize_motion_plan,validate_review_binding
PROFILE_ID="FA3-SHARED-MOTION-VIDEO-QUALITY-001";GATE_ID="FA3-MOTION-VIDEO-QUALITY-GATESET-001";CAPABILITY_COUNT=module_active_capability_count(__file__)
CAPABILITY_BINDINGS=["CAP-121","CAP-126","CAP-159","CAP-161"];CONTRACT_IDS=["FA3-MOTION-PLAN-CONTRACTS-001","FA3-MOTION-RENDER-CONTRACTS-001","FA3-MEDIA-QUALITY-REVIEW-CONTRACTS-001","FA3-MOTION-COMPONENT-LAB-CONTRACTS-001"];RULES=["CAPABILITY_BASELINE_175","NO_NEW_CAPABILITY","NO_NEW_ARCHITECTURAL_AUTHORITY","SUBPROFILE_OF_FA3_VIDEO","PROVIDER_NEUTRAL","NATIVE_PROJECT_AUTHORITY_PRESERVED","DIRECT_NATIVE_PROJECT_MUTATION_FORBIDDEN","PROJECT_REVISION_BINDING_REQUIRED","TIMELINE_REVISION_BINDING_REQUIRED","STALE_PROPOSAL_FAILS_CLOSED","DETERMINISTIC_RENDER_CLAIM_EVIDENCE_BOUND","GENERATIVE_NONDETERMINISM_NOT_MISREPORTED","CPU_ONLY_ROUTE_VIABLE","ACCELERATOR_CARDINALITY_0_N","HRB_REMAINS_RESOURCE_AUTHORITY","MODEL_ROUTER_REMAINS_AI_ROUTING_AUTHORITY","ENGINE_SELECTOR_INTENT_ONLY","UAF_SECURITY_MEDIATION_REQUIRED","INDEPENDENT_REVIEW_REQUIRED","SELF_REVIEW_CANNOT_PASS","EVIDENCE_DIGEST_CHAIN_REQUIRED","ROLLBACK_REQUIRED_FOR_TIMELINE_MUTATION","EXISTING_MEDIA_AUTHORITIES_NOT_DUPLICATED","STATIC_TESTS_CANNOT_PROMOTE_CURRENT_HOST"];ACTION_IDS=["motion.plan","motion.preview","motion.apply","motion.render","motion.measure","motion.review","motion.verify"]
def load(root,rel):return json.loads((root/rel).read_text())
def gate(root):
 cases=[]
 def c(code,ok,detail):cases.append({"code":code,"status":"PASS" if ok else "FAIL","detail":detail})
 req=["canonical/profiles/FA3-SHARED-MOTION-VIDEO-QUALITY-001.json","canonical/decisions/FA3-DEC-SHARED-MOTION-VIDEO-QUALITY-2026-10-03.json","canonical/motion-video-quality-enforcement.json","canonical/FA3-APPLICATION-DONOR-LINKS-001.json","canonical/profiles/FA3-ENGINE-SELECTION-FABRIC-001.json","canonical/contracts/FA3-AGENT-APPLICATION-BLUEPRINT-CONTRACTS-001.json","fa3-current-host/manifest.json"]
 for cid in CONTRACT_IDS:req.append("canonical/contracts/"+cid+".json")
 missing=[x for x in req if not (root/x).is_file()]
 if missing:return {"schema":"fa3.motion-video-quality-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":[{"code":"MVQ-MISSING","paths":missing}]}
 p=load(root,req[0]);d=load(root,req[1]);e=load(root,req[2]);links=load(root,req[3]);selector=load(root,req[4]);blue=load(root,req[5]);host=load(root,req[6]);cs=[load(root,"canonical/contracts/"+x+".json") for x in CONTRACT_IDS]
 c("MVQ-001",CAPABILITY_COUNT==175 and p.get("capability_count")==175 and d.get("capability_count_after")==175,"baseline")
 c("MVQ-002",p.get("new_capability") is False and d.get("new_capabilities")==0,"no new capability")
 c("MVQ-003",p.get("new_architectural_authority") is False and p.get("authority") is False and d.get("new_architectural_authorities")==0,"no new authority")
 rel=p.get("relationship",{});c("MVQ-004",p.get("canonical_root") is False and rel.get("type")=="SUBPROFILE-OF" and rel.get("parent")=="FA3-VIDEO-001","parent")
 c("MVQ-005",p.get("provider_neutral") is True and all(x.get("provider_neutral") is True for x in cs),"provider neutral")
 n=p.get("native_project_policy",{});plan=cs[0].get("rules",{});rend=cs[1].get("rules",{});review=cs[2].get("rules",{});auth=p.get("authority_boundaries",{});hw=p.get("hardware_audit",{});eng=p.get("engine_selection",{});ch=p.get("current_host",{})
 c("MVQ-006",n.get("project_fa3video_authoritative") is True and n.get("otio_interchange_not_native_project_authority") is True,"native project")
 c("MVQ-007",n.get("direct_kdenlive_xml_mutation_forbidden") is True and plan.get("direct_native_project_file_mutation_forbidden") is True,"direct mutation")
 c("MVQ-008",plan.get("expected_project_revision_required") is True,"project revision")
 c("MVQ-009",plan.get("expected_timeline_revision_required") is True,"timeline revision")
 c("MVQ-010",plan.get("stale_project_or_timeline_revision_fails_closed") is True,"stale denial")
 c("MVQ-011",rend.get("deterministic_claim_requires_replay_or_seek_evidence") is True,"determinism evidence")
 c("MVQ-012",rend.get("nondeterministic_or_generative_output_must_not_claim_pixel_determinism") is True,"nondeterminism truth")
 c("MVQ-013",hw.get("cpu_only_viable") is True,"cpu only")
 c("MVQ-014",hw.get("accelerator_cardinality")=="0..N" and hw.get("global_accelerator_requirement") is False,"0..N")
 c("MVQ-015",auth.get("host_resource_admission")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","HRB")
 c("MVQ-016",auth.get("ai_provider_model_routing")=="FA3-AUTH-MODEL-ROUTER-001","Model Router")
 c("MVQ-017",eng.get("profile_id")=="FA3-ENGINE-SELECTION-FABRIC-001" and eng.get("authority") is False and eng.get("selection_intent_only") is True and selector.get("new_architectural_authority") is False,"engine selector")
 c("MVQ-018",auth.get("action_mediation")=="FA3-UNIFIED-ACTION-FABRIC-001" and auth.get("security")=="FA3-AUTH-SECURITY-GOV-001","UAF security")
 br=next((x for x in blue.get("contracts",[]) if x.get("id")=="FA3-BLUEPRINT-005"),{})
 c("MVQ-019",review.get("reviewer_identity_must_differ_from_producer_identity") is True and br.get("name")=="Independent Review","independent review")
 c("MVQ-020",review.get("self_review_cannot_produce_pass") is True,"self review")
 c("MVQ-021",review.get("measurement_and_review_receipts_require_artifact_digest") is True and rend.get("output_digest_and_lineage_required") is True,"digest chain")
 c("MVQ-022",n.get("rollback_reference_required_for_mutation") is True,"rollback")
 c("MVQ-023",set(p.get("reused_contracts",[])).issuperset({"FA3-MOTION-VIDEO-EXECUTION-CONTRACTS-001","FA3-VIDEO-REFINEMENT-CONTRACTS-001","FA3-CREATIVE-PROJECT-WORKFLOW-CONTRACTS-001"}),"reuse")
 c("MVQ-024",ch.get("physical_current_host_pass_claimed") is False and ch.get("global_promotion_claim") is False and e.get("current_host_runtime_promotion_claim") is False,"no static promotion")
 if p.get("capability_bindings")!=CAPABILITY_BINDINGS:cases.append({"code":"MVQ-BINDINGS","status":"FAIL","detail":"bindings"})
 if e.get("rules")!=RULES or e.get("rule_count")!=len(RULES) or e.get("fail_closed") is not True:cases.append({"code":"MVQ-ENFORCEMENT","status":"FAIL","detail":"enforcement"})
 acts={}
 for aid in ACTION_IDS:
  path="canonical/actions/"+aid+".json"
  if not (root/path).is_file():cases.append({"code":"MVQ-ACTION-MISSING","status":"FAIL","detail":aid})
  else:acts[aid]=load(root,path)
 if "motion.apply" in acts and not {"expected_project_revision","expected_timeline_revision","rollback_ref"}.issubset(set(acts["motion.apply"]["input_schema"]["required"])):cases.append({"code":"MVQ-ACTION-APPLY","status":"FAIL","detail":"guards"})
 if "motion.render" in acts and "engine_selection_intent" not in acts["motion.render"]["input_schema"]["required"]:cases.append({"code":"MVQ-ACTION-RENDER","status":"FAIL","detail":"engine intent"})
 shared=next((x for x in links.get("shared_capabilities",[]) if x.get("id")==PROFILE_ID),None)
 if not shared or shared.get("status")!="MATERIALIZED_STATIC" or shared.get("authority") is not False or (shared.get("current_host_impact") or {}).get("classification")!="RUNTIME_REQUALIFICATION_REQUIRED":cases.append({"code":"MVQ-SHARED","status":"FAIL","detail":"projection"})
 surf=next((x for x in host.get("registered_current_host_surfaces",[]) if x.get("name")=="motion-video-quality-shared"),None);align=host.get("motion_video_quality_alignment",{})
 if not surf or surf.get("physical_current_host_pass_claimed") is not False or surf.get("global_promotion_claim") is not False:cases.append({"code":"MVQ-CH-SURFACE","status":"FAIL","detail":"surface"})
 if not (align.get("structural_change") is True and align.get("physical_runtime_requalification_required") is True and align.get("current_host_promotion_claim") is False):cases.append({"code":"MVQ-CH-ALIGN","status":"FAIL","detail":"alignment"})
 sample={"schema":"fa3.motion-plan.v1","motion_plan_id":"sample","revision":"1","project_id":"p","project_revision":"pr1","timeline_revision":"tl1","timebase":{"fps":"24/1"},"beats":[],"actors":[],"transitions":[{"primitive":"OBJECT_HANDOFF"}],"camera_constraints":[],"motion_constraints":[],"continuity_constraints":[],"audio_cues":[],"quality_profile":{"profile_id":"draft"},"render_intent":{"kind":"PREVIEW"},"source_artifact_refs":[],"provenance":{"source":"gate"}}
 try:
  norm=normalize_motion_plan(sample);proposal=build_edit_proposal(norm,"pr1","tl1")
  if proposal.get("direct_native_project_mutation") is not False:raise MotionVideoQualityError("mutation")
  try:build_edit_proposal(norm,"stale","tl1");cases.append({"code":"MVQ-NEG-STALE","status":"FAIL","detail":"accepted"})
  except MotionVideoQualityError:pass
  deterministic_render_key({"input_artifact_digest":"a"*64,"motion_plan_digest":norm["digest"],"timeline_revision":"tl1","frame_or_range":{"frame":12},"engine_selection_intent":{"execution_requested":False,"engine_id":"FA3-ENGINE-MLT-001"},"render_profile":{"kind":"PREVIEW"}})
  try:validate_review_binding("producer","producer");cases.append({"code":"MVQ-NEG-SELF","status":"FAIL","detail":"accepted"})
  except MotionVideoQualityError:pass
 except Exception as ex:cases.append({"code":"MVQ-RUNTIME-REF","status":"FAIL","detail":str(ex)})
 findings=[x for x in cases if x["status"]!="PASS"]
 return {"schema":"fa3.motion-video-quality-gate-report.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,"capability_count":CAPABILITY_COUNT,"rules_checked":len(RULES),"result":"PASS" if not findings else "FAIL","cases":cases,"findings":findings,"current_host_runtime_promotion_claim":False}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));ap.add_argument("--check",action="store_true");a=ap.parse_args();r=gate(Path(a.root));print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
