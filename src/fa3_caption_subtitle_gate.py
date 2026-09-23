#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from fa3_caption_subtitle import CaptionError, build_narration_plan, export_subtitle, parse_subtitle, timing_repair, validate_document

GATE_ID="FA3-CAPTION-SUBTITLE-GATESET-001"
PROFILE="canonical/profiles/FA3-CAPTION-SUBTITLE-001.json"
CONTRACT="canonical/contracts/FA3-CAPTION-SUBTITLE-CONTRACTS-001.json"
DECISION="canonical/decisions/FA3-DEC-CAPTION-NARRATION-STUDIOS-2026-09-23.json"
REFERENCE="canonical/references/FA3-CAPTION-SUBTITLE-UPSTREAM-REFERENCE-2026-09-23.json"
ENFORCEMENT="canonical/caption-subtitle-enforcement.json"

def load(root:Path,rel:str):
    return json.loads((root/rel).read_text(encoding="utf-8"))

def gate(root:Path)->dict:
    findings=[]
    def chk(ok:bool,code:str,message:str):
        if not ok: findings.append({"code":code,"severity":"P0","message":message})
    for rel in (PROFILE,CONTRACT,DECISION,REFERENCE,ENFORCEMENT,"src/fa3_caption_subtitle.py","src/fa3_caption_studio_server.py","bin/fa3-caption-studio","bin/fa3-narration-studio","apps/fa3-control-center/qml/SubtitleStudioPage.qml","apps/fa3-control-center/qml/NarrationStudioPage.qml",
                "src/fa3_caption_workflows.py", "src/fa3_caption_uaf.py",
                "src/fa3_caption_subtitle_current_host_gate.py",
                "canonical/providers/FA3-PROVIDER-CAPTION-NATIVE-001.json",
                ".github/workflows/fa3-caption-subtitle-current-host.yml"):
        chk((root/rel).exists(),"CAPSUB-001",f"missing materialization path: {rel}")
    if findings: return {"schema":"fa3.caption-subtitle-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}

    p,c,d,r,e=(load(root,x) for x in (PROFILE,CONTRACT,DECISION,REFERENCE,ENFORCEMENT))
    chk(p.get("id")=="FA3-CAPTION-SUBTITLE-001" and p.get("status")=="CANONICAL","CAPSUB-002","profile identity/state drift")
    chk(p.get("capability_count")==143 and not p.get("new_capability") and not p.get("new_architectural_authority"),"CAPSUB-003","capability/authority drift")
    chk(c.get("profile")==p.get("id") and c.get("provider_neutral") is True,"CAPSUB-004","contract boundary drift")
    chk(d.get("capability_count_before")==143 and d.get("capability_count_after")==143,"CAPSUB-005","decision capability count drift")
    apps=p.get("applications",{})
    chk({"subtitle_studio","narration_studio"}<=set(apps),"CAPSUB-006","standalone application projection missing")
    auth=p.get("authority_boundaries",{})
    chk(auth.get("speech_recognition")=="FA3-STT-MEDIA-001" and auth.get("voice_synthesis_and_cloning")=="FA3-VOICE-001","CAPSUB-007","STT/Voice delegation drift")
    chk(auth.get("provider_routing")=="FA3-AUTH-MODEL-ROUTER-001" and auth.get("host_resource_admission")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","CAPSUB-008","routing/resource authority drift")
    agent=p.get("agent_native",{})
    chk(agent.get("uaf_required_for_actions") is True and agent.get("direct_provider_invocation") is False and agent.get("participant_set_expansion_allowed") is False,"CAPSUB-009","Agent Native/UAF boundary drift")
    hw=p.get("hardware_audit_compliance",{})
    chk(hw.get("cpu_only_host_valid") is True and hw.get("accelerator_cardinality")=="0..N","CAPSUB-010","hardware portability drift")
    chk(hw.get("accelerator_vendor_pin")=="FORBIDDEN" and hw.get("gpu_sku_pin")=="FORBIDDEN" and hw.get("cuda_requirement") is False,"CAPSUB-011","vendor-specific hardware pin returned")
    chk(hw.get("accelerator_execution_requires_hrb_lease") is True,"CAPSUB-012","HRB accelerator boundary missing")
    desktop=p.get("desktop_portability",{})
    chk(desktop.get("wayland")=="PREFERRED_WHEN_AVAILABLE" and desktop.get("x11")=="SUPPORTED","CAPSUB-013","desktop portability drift")
    chk(p.get("distribution",{}).get("implementation_class")=="FA3_NATIVE" and p.get("distribution",{}).get("upstream_projects_embedded") is False,"CAPSUB-014","distribution classification drift")
    chk(r.get("code_embedded") is False and all(x.get("reuse","").startswith("REFERENCE_ONLY") for x in r.get("projects",[])),"CAPSUB-015","upstream reference-only boundary drift")
    chk(e.get("fail_closed") is True and e.get("current_host_status")=="PENDING_CURRENT_HOST","CAPSUB-016","promotion boundary drift")
    chk(c.get("narration",{}).get("provider_selection_by_application_forbidden") is True and c.get("narration",{}).get("subtitle_source_text_mutation_by_timing_engine_forbidden") is True,"CAPSUB-017","narration authority/text-mutation rule drift")

    sample="1\n00:00:01,000 --> 00:00:02,500\nElső sor.\n\n2\n00:00:03,000 --> 00:00:04,000\nMásodik sor.\n"
    try:
        doc=parse_subtitle(sample,"srt",language="hu-HU")
        chk(validate_document(doc)["cues"]==2,"CAPSUB-018","SRT parser/validation failed")
        chk("WEBVTT" in export_subtitle(doc,"vtt"),"CAPSUB-019","VTT export failed")
        chk("[Events]" in export_subtitle(doc,"ass"),"CAPSUB-020","ASS export failed")
        chk("<tt " in export_subtitle(doc,"ttml"),"CAPSUB-021","TTML export failed")
        plan=build_narration_plan(doc,voice_identity_ref="VOICE-TEST",narration_mode="VOICE_OVER")
        chk(plan.get("voice_authority")=="FA3-VOICE-001" and plan.get("provider_selection_owned_by_application") is False,"CAPSUB-022","narration delegation failed")
        chk(all(x["voice_request"]["schema"]=="fa3.voice-synthesis-request.v2" for x in plan["segments"]),"CAPSUB-023","voice contract projection failed")
        chk(timing_repair(1000,900)["decision"]=="ACCEPT_AND_PAD_IF_NEEDED","CAPSUB-024","timing fit policy failed")
        chk(timing_repair(1000,1100)["decision"]=="BOUNDED_RATE_ADJUSTMENT","CAPSUB-025","bounded rate policy failed")
        over=timing_repair(1000,1500)
        chk(over["decision"]=="HUMAN_REVIEW_TEXT_ADAPTATION_REQUIRED" and over["text_rewrite"] is False,"CAPSUB-026","material overrun must require human review")
        try:
            parse_subtitle("1\n00:00:02,000 --> 00:00:03,000\nA\n\n2\n00:00:02,500 --> 00:00:04,000\nB\n","srt")
            chk(False,"CAPSUB-027","overlap unexpectedly accepted")
        except CaptionError: pass
    except Exception as ex:
        chk(False,"CAPSUB-028",f"reference runtime failed: {ex}")

    main=(root/"apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
    cmake=(root/"apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
    for token in ('label: "Subtitle Studio"; pageIndex: 35','label: "Narration Studio"; pageIndex: 36',"SubtitleStudioPage {","NarrationStudioPage {"):
        chk(token in main,"CAPSUB-029",f"Control Center wiring missing: {token}")
    chk("qml/SubtitleStudioPage.qml" in cmake and "qml/NarrationStudioPage.qml" in cmake,"CAPSUB-030","QML resource registration missing")
    expected_actions={"caption.import","caption.edit","caption.sync","caption.qc","caption.export","caption.translate","caption.hardsub.recover","caption.overlay.project","caption.editorial.project","narration.plan","narration.synthesize","narration.mix","audio-description.plan"}
    chk(set(p.get("uaf_actions",[]))==expected_actions,"CAPSUB-031","UAF caption/narration action inventory drift")
    chk(p.get("native_provider")=="FA3-PROVIDER-CAPTION-NATIVE-001","CAPSUB-032","native provider binding missing")
    provider=load(root,"canonical/providers/FA3-PROVIDER-CAPTION-NATIVE-001.json")
    chk(provider.get("architectural_authority") is False and provider.get("provider_selection_authority") is False and provider.get("distribution_class")=="FA3_NATIVE","CAPSUB-033","native provider authority/distribution drift")
    action_files={x.stem for x in (root/"canonical/actions").glob("*.json")}
    chk(expected_actions.issubset(action_files),"CAPSUB-034","caption/narration UAF action contract missing")
    ch=p.get("current_host",{})
    chk(ch.get("gate_id")=="FA3-CAPTION-SUBTITLE-CURRENT-HOST-GATESET-001" and ch.get("global_promotion_claim") is False,"CAPSUB-035","current-host boundary drift")
    return {"schema":"fa3.caption-subtitle-gate-report.v1","gate_id":GATE_ID,"profile_id":p.get("id"),"result":"PASS" if not findings else "FAIL","current_host_status":"PENDING_CURRENT_HOST","findings":findings}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--report"); args=ap.parse_args()
    result=gate(Path(args.root).resolve()); text=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.report:
        Path(args.report).parent.mkdir(parents=True,exist_ok=True); Path(args.report).write_text(text,encoding="utf-8")
    print(text,end=""); return 0 if result["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())