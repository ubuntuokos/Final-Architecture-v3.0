#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
from fa3_terax_gate import gate as terax_gate, reference_check as terax_reference_check
from fa3_kaneo_gate import gate as kaneo_gate
from fa3_kanboard_gate import gate as kanboard_gate
from fa3_buzz_gate import gate as buzz_gate
from fa3_xcmd_gate import gate as xcmd_gate
from fa3_ai_engineering_gate import gate as ai_engineering_gate
from fa3_external_api_discovery_gate import gate as external_api_discovery_gate
from fa3_autogpt_gate import gate as autogpt_gate
from fa3_ai_infra_guard_gate import gate as ai_infra_guard_gate, current_host_gate as ai_infra_guard_current_host_gate
from fa3_munder_difflin_gate import gate as munder_difflin_gate
from fa3_munder_difflin_executable_gate import gate as munder_difflin_executable_gate
from fa3_muse_code_gate import gate as muse_code_gate
from fa3_openhands_gate import gate as openhands_gate
from fa3_openbmb_gate import gate as openbmb_gate
from fa3_tencentdb_agent_memory_gate import gate as tencentdb_agent_memory_gate
from fa3_stability_sgm_gate import gate as stability_sgm_gate
from fa3_stability_portfolio_gate import gate as stability_portfolio_gate
from fa3_developer_agent_coordination_gate import gate as developer_agent_coordination_gate
from fa3_codex_gate import gate as codex_gate, current_host_gate as codex_current_host_gate
from fa3_modular_gate import gate as modular_gate
from fa3_inference_portability_gate import gate as inference_portability_gate
from fa3_model_manager_gate import gate as model_manager_gate
from fa3_model_manager_current_host_gate import gate as model_manager_current_host_gate
from fa3_modular_runtime import run_executable_conformance as modular_provider_conformance
from fa3_modular_current_host_gate import gate as modular_current_host_gate
from fa3_demucs_gate import gate as demucs_gate
from fa3_demucs_provider import run_executable_conformance as demucs_provider_conformance
from fa3_demucs_current_host_gate import gate as demucs_current_host_gate
from fa3_acestep_gate import gate as ace_step_gate
from fa3_blackhole_kdenlive_gate import gate as blackhole_kdenlive_gate
from fa3_kdenlive_editorial_gate import gate as kdenlive_editorial_gate
from fa3_opencut_gate import gate as opencut_gate
from fa3_ffmpeg_ai_gate import gate as ffmpeg_ai_gate
from fa3_ffmpeg_ai_current_host_gate import gate as ffmpeg_ai_current_host_gate
from fa3_hybrid_editorial_gate import gate as hybrid_editorial_gate
from fa3_marketing_gate import gate as marketing_gate
from fa3_whisper_stt_gate import gate as whisper_stt_gate
from fa3_whisper_stt_provider import run_executable_conformance as whisper_stt_provider_conformance
from fa3_cosyvoice_gate import gate as cosyvoice_gate, current_host_gate as cosyvoice_current_host_gate
from fa3_voice_synthesis_gate import gate as voice_synthesis_gate
from fa3_release_projection_gate import gate as release_projection_gate
from fa3_mentor_gate import gate as mentor_gate
from fa3_presenton_gate import gate as presenton_gate, current_host_gate as presenton_current_host_gate
from fa3_hrb_deterministic_locality_gate import gate as hrb_deterministic_locality_gate
from fa3_cpu_numa_threading_gate import gate as cpu_numa_threading_gate
from fa3_cpu_numa_threading_current_host_gate import gate as cpu_numa_threading_current_host_gate

OK=0
BLOCKED=2
INPUT=3
RELEASE="2026-08-23/v3.0.11"
CAPS=143
FORBIDDEN={"OPEN","ORPHANED","UNCLASSIFIED"}

RECEIPTS={
  4:["host-fingerprint.json","source-exclusion-receipt.json"],
  5:["provider-runtime-plans.json"],
  6:["host-budget-acceptance.json"],
  7:["survival-plane-acceptance.json"],
  8:["w3-local-inference.json"],
  9:["creative-golden-paths.json"],
  10:["rnnoise-current-host.json"],
  11:["openviking-current-host.json"],
  12:["ace-step-current-host.json"],
  13:["memory-hugepages-current-host.json"],
  14:["conversational-nle-current-host.json"],
  15:["conditional-provider-disposition.json"],
  16:["privileged-action-coverage.json"],
  17:["rollback-expiry-drill.json"],
  18:["release-integrity.json"],
  19:["independent-review.json","human-promotion-receipt.json"],
}
NAMES={
  1:"modular source graph and schema lint PASS",
  2:"authority lint has no duplicate owner",
  3:"143 capability catalog validation PASS",
  4:"current-host fingerprint and source exclusion receipt signed",
  5:"every active provider has current ResolvedRuntimePlan",
  6:"process and CPU/RAM/VRAM/I/O/network envelope fits host budget",
  7:"survival plane boot/security/observability runtime acceptance PASS",
  8:"W3 local inference positive/negative/degraded/rollback PASS",
  9:"creative film/office/audio golden paths human-approved PASS",
  10:"RNNoise current-host conformance PASS",
  11:"OpenViking current-host conformance PASS",
  12:"ACE-Step current-host conformance PASS",
  13:"Host memory-compaction/HugePages acceptance PASS",
  14:"Conversational NLE/editorial conformance PASS",
  15:"conditional providers explicitly dormant or evidence-promoted",
  16:"no orphan MUST and no orphan privileged action",
  17:"evidence expiry/invalidation and rollback drill works",
  18:"generated master digest matches release manifest",
  19:"independent review and human promotion receipt complete",
}

def loadj(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def writej(p:Path,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def finding(code,msg,**kw):
    return {"code":code,"severity":"P0","message":msg,**kw}

def static_check(root:Path):
    fs=[]
    pol=loadj(root/"canonical/enforcement-policy.json")
    att=loadj(root/"canonical/source-graph-attestation.json")
    geom=loadj(root/"canonical/geometry-closure.json")
    mapping=loadj(root/"canonical/fa3_legacy_gap_to_registry_mapping_2026-08-26.json")
    rows=list(csv.DictReader((root/"canonical/conformance-matrix.csv").open(encoding="utf-8-sig",newline="")))

    projection_ref=release_projection_gate(root)
    if projection_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-039","Unified post-v3.0.11 canonical release projection gate failed",release_projection_gate=projection_ref))

    if pol.get("architecture_release")!=RELEASE or pol.get("canonical_capability_count")!=CAPS:
        fs.append(finding("FA3-STATIC-001","Enforcement policy release/capability invariant mismatch"))
    if not pol.get("fail_closed") or not pol.get("document_only_promotion_forbidden"):
        fs.append(finding("FA3-STATIC-002","Fail-closed/document-only promotion invariant disabled"))
    if "Linux Recovery/Rebuild Projection" not in pol.get("out_of_scope",[]):
        fs.append(finding("FA3-STATIC-003","Removed Linux Recovery/Rebuild Projection returned to scope"))
    if "FA3-TERAX-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-015","Terax mandatory reference gate is not bound into global enforcement policy"))
    if "FA3-KANEO-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-016","Kaneo mandatory canonical gate is not bound into global enforcement policy"))
    if "FA3-BUZZ-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-028","Buzz authority-separation gate is not bound into global enforcement policy"))
    if "FA3-XCMD-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-030","X-CMD security/boundary gate is not bound into global enforcement policy"))
    if "FA3-MODULAR-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-032","Modular MAX/Mojo boundary/lineage/cache gate is not bound into global enforcement policy"))
    if "FA3-INFERENCE-PORTABILITY-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-050","Inference portability compatibility/provider gate is not bound into global enforcement policy"))
    if "FA3-MODEL-MANAGER-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-052","Model Manager/StabilityMatrix canonical gate is not bound into global enforcement policy"))
    if "FA3-MUNDER-DIFFLIN-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-034","Munder Difflin multi-agent coordination gate is not bound into global enforcement policy"))
    if "FA3-MUSE-CODE-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-060","Muse Code durable/replayable execution gate is not bound into global enforcement policy"))
    if "FA3-OPENHANDS-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-066","OpenHands developer-agent execution gate is not bound into global enforcement policy"))
    if "FA3-OPENBMB-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-070","OpenBMB provider-family boundary/hardware gate is not bound into global enforcement policy"))
    if "FA3-STABILITY-SGM-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-062","Stability SGM generative-pipeline/multi-view gate is not bound into global enforcement policy"))
    if "FA3-STABILITY-PORTFOLIO-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-070","Stability provider portfolio gate is not bound into global enforcement policy"))
    if "FA3-DEVELOPER-AGENT-COORDINATION-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-046","Developer-agent coordination gate is not bound into global enforcement policy"))
    if "FA3-CODEX-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-048","Codex adapter gate is not bound into global enforcement policy"))
    if "FA3-AUTOGPT-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-037","AutoGPT agentic-workflow boundary gate is not bound into global enforcement policy"))
    if "FA3-EXTERNAL-API-DISCOVERY-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-042","External API/MCP discovery gate is not bound into global enforcement policy"))
    if "FA3-DEMUCS-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-018","Demucs mandatory canonical gate is not bound into global enforcement policy"))
    if "FA3-ACE-STEP-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-020","ACE-Step mandatory provider gate is not bound into global enforcement policy"))
    if "FA3-BLACKHOLE-KDENLIVE-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-022","Blackhole/Kdenlive integration gate is not bound into global enforcement policy"))
    if "FA3-KDENLIVE-EDITORIAL-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-024","Kdenlive editorial canonical gate is not bound into global enforcement policy"))
    if "FA3-OPENCUT-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-064","OpenCut programmable editor gate is not bound into global enforcement policy"))
    if "FA3-HYBRID-EDITORIAL-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-054","Hybrid editorial executable gate is not bound into global enforcement policy"))
    if "FA3-MARKETING-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-056","Marketing/Hungarian-first executable gate is not bound into global enforcement policy"))
    if "FA3-WHISPER-STT-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-026","Whisper STT provider gate is not bound into global enforcement policy"))
    if "FA3-MENTOR-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-040","FA3 Mentor mandatory gate is not bound into global enforcement policy"))
    if "FA3-PRESENTON-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-044","Presenton mandatory provider boundary gate is not bound into global enforcement policy"))
    if "FA3-AI-INFRA-GUARD-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-048","AI-Infra-Guard security-validation gate is not bound into global enforcement policy"))
    if "FA3-VOICE-SYNTHESIS-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-066","Voice synthesis portfolio/Hungarian routing gate is not bound into global enforcement policy"))
    if "FA3-CPU-NUMA-THREADING-GATESET-001" not in pol.get("mandatory_reference_gates",[]):
        fs.append(finding("FA3-STATIC-068","CPU/NUMA thread-pool governance gate is not bound into global enforcement policy"))

    if att.get("release")!=RELEASE or att.get("ci_status")!="PASS" or att.get("design_coverage_status")!="STRUCTURALLY_COMPLETE":
        fs.append(finding("FA3-STATIC-004","Source-graph attestation not current structural PASS"))
    if att.get("sha256")!="0418528b52fd9a29d993fc69c1ea508f57cd527d96e234d738c6b8fc553c4f16":
        fs.append(finding("FA3-STATIC-005","Canonical source-graph attestation digest drift"))
    if att.get("graph_nodes")!=1615 or att.get("graph_edges")!=6144:
        fs.append(finding("FA3-STATIC-006","Canonical source-graph structural-count drift"))
    if any(att.get(k)!=0 for k in ("orphan_must","unmapped_capabilities","missing_evidence_mappings")):
        fs.append(finding("FA3-STATIC-007","Source graph contains unresolved design gaps"))

    expected=[f"CAP-{i:03d}" for i in range(1,144)]
    ids=[r.get("capability_id") for r in rows]
    if len(rows)!=CAPS or ids!=expected:
        fs.append(finding("FA3-STATIC-008","Capability catalog is not exact CAP-001..CAP-143",rows=len(rows)))
    bad=[r.get("capability_id") for r in rows if r.get("design_conformance")!="DESIGN-CONFORMANT"]
    if bad:
        fs.append(finding("FA3-STATIC-009","Non design-conformant capability found",sample=bad[:20]))

    maps=mapping.get("mappings",[])
    if mapping.get("record_id")!="FA3-CGR-2026-08-26" or mapping.get("status")!="CANONICAL_CLOSED":
        fs.append(finding("FA3-STATIC-010","Legacy reconciliation not CANONICAL_CLOSED"))
    if len(maps)!=36:
        fs.append(finding("FA3-STATIC-011","Legacy reconciliation count is not 36",count=len(maps)))
    if mapping.get("capability_count_after")!=CAPS or mapping.get("new_capabilities")!=0 or mapping.get("new_architectural_authorities")!=0:
        fs.append(finding("FA3-STATIC-012","Legacy reconciliation changed capability/authority invariant"))
    openm=[m for m in maps if str(m.get("status","")).upper() in FORBIDDEN or str(m.get("disposition","")).upper() in FORBIDDEN]
    if openm:
        fs.append(finding("FA3-STATIC-013","Unclosed legacy reconciliation records",count=len(openm)))

    if not (
      geom.get("status")=="CANONICAL_CLOSED" and
      geom.get("canonical_root")=="FA3-3D-GEOM-001" and
      geom.get("specialized_child")=="FA3-MESH-GEN-001" and
      geom.get("relationship")=="SUBPROFILE-OF" and
      geom.get("canonical_geometry_root_count")==1 and
      geom.get("open_overlaps")==0 and
      geom.get("canonical_capability_count")==CAPS
    ):
        fs.append(finding("FA3-STATIC-014","Geometry canonical closure invariant failed"))

    terax_ref=terax_reference_check(root)
    if terax_ref["result"]!="PASS":
        fs.extend(terax_ref.get("findings",[]))
    kaneo_ref=kaneo_gate(root)
    if kaneo_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-017","Kaneo mandatory canonical invariant gate failed",kaneo_gate=kaneo_ref))
    buzz_ref=buzz_gate(root)
    if buzz_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-029","Buzz mandatory authority-separation regression gate failed",buzz_gate=buzz_ref))
    xcmd_ref=xcmd_gate(root)
    if xcmd_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-031","X-CMD mandatory security/boundary regression gate failed",xcmd_gate=xcmd_ref))
    ai_ref=ai_engineering_gate(root)
    if ai_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-035","AI engineering source mandatory cross-cutting regression gate failed",ai_engineering_gate=ai_ref))
    autogpt_ref=autogpt_gate(root)
    if autogpt_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-038","AutoGPT mandatory agentic workflow/boundary regression gate failed",autogpt_gate=autogpt_ref))
    external_discovery_ref=external_api_discovery_gate(root)
    if external_discovery_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-043","External API/MCP discovery mandatory admission-boundary gate failed",external_api_discovery_gate=external_discovery_ref))
    modular_ref=modular_gate(root)
    if modular_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-033","Modular MAX/Mojo mandatory boundary/lineage/cache regression gate failed",modular_gate=modular_ref))
    inference_portability_ref=inference_portability_gate(root)
    if inference_portability_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-051","Inference portability compatibility/provider regression gate failed",inference_portability_gate=inference_portability_ref))
    model_manager_ref=model_manager_gate(root)
    if model_manager_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-053","Model Manager/StabilityMatrix canonical regression gate failed",model_manager_gate=model_manager_ref))
    munder_ref=munder_difflin_gate(root)
    if munder_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-035","Munder Difflin mandatory multi-agent coordination regression gate failed",munder_difflin_gate=munder_ref))
    muse_code_ref=muse_code_gate(root)
    if muse_code_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-061","Muse Code durable/replayable multi-agent execution regression gate failed",muse_code_gate=muse_code_ref))
    openhands_ref=openhands_gate(root)
    if openhands_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-067","OpenHands developer-agent execution boundary regression gate failed",openhands_gate=openhands_ref))
    openbmb_ref=openbmb_gate(root)
    if openbmb_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-072","OpenBMB provider-family boundary/hardware regression gate failed",openbmb_gate=openbmb_ref))
    tdai_ref=tencentdb_agent_memory_gate(root)
    if tdai_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-075","TencentDB Agent Memory governance/security boundary regression gate failed",tencentdb_agent_memory_gate=tdai_ref))
    stability_sgm_ref=stability_sgm_gate(root)
    if stability_sgm_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-063","Stability SGM generative-pipeline/multi-view regression gate failed",stability_sgm_gate=stability_sgm_ref))
    stability_portfolio_ref=stability_portfolio_gate(root)
    if stability_portfolio_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-071","Stability provider portfolio canonical/admission gate failed",stability_portfolio_gate=stability_portfolio_ref))
    dac_ref=developer_agent_coordination_gate(root)
    if dac_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-047","Developer-agent coordination contract/runtime E2E gate failed",developer_agent_coordination_gate=dac_ref))
    codex_ref=codex_gate(root)
    if codex_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-049","Codex adapter/admission regression gate failed",codex_gate=codex_ref))
    demucs_ref=demucs_gate(root)
    if demucs_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-019","Demucs mandatory canonical invariant gate failed",demucs_gate=demucs_ref))
    ace_ref=ace_step_gate(root)
    if ace_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-021","ACE-Step mandatory provider invariant gate failed",ace_step_gate=ace_ref))
    kdenlive_ref=kdenlive_editorial_gate(root)
    if kdenlive_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-025","Kdenlive mandatory editorial gate failed",kdenlive_editorial_gate=kdenlive_ref))
    opencut_ref=opencut_gate(root)
    if opencut_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-065","OpenCut programmable editor canonical/executable gate failed",opencut_gate=opencut_ref))
    ffmpeg_ai_ref=ffmpeg_ai_gate(root)
    if ffmpeg_ai_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-073","FFmpeg neural-media execution canonical/admission gate failed",ffmpeg_ai_gate=ffmpeg_ai_ref))
    hybrid_editorial_ref=hybrid_editorial_gate(root)
    if hybrid_editorial_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-055","Hybrid animation/live-action editorial executable gate failed",hybrid_editorial_gate=hybrid_editorial_ref))
    marketing_ref=marketing_gate(root)
    if marketing_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-057","Marketing/Hungarian-first executable gate failed",marketing_gate=marketing_ref))
    blackhole_ref=blackhole_kdenlive_gate(root)
    if blackhole_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-023","Blackhole/Kdenlive mandatory integration gate failed",blackhole_kdenlive_gate=blackhole_ref))
    whisper_ref=whisper_stt_gate(root)
    if whisper_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-027","Whisper STT mandatory provider gate failed",whisper_stt_gate=whisper_ref))
    cosyvoice_ref=cosyvoice_gate(root)
    if cosyvoice_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-059","CosyVoice voice-provider canonical/executable gate failed",cosyvoice_gate=cosyvoice_ref))
    voice_synthesis_ref=voice_synthesis_gate(root)
    if voice_synthesis_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-067","Voice synthesis provider portfolio/Hungarian routing gate failed",voice_synthesis_gate=voice_synthesis_ref))
    hrb_deterministic_ref=hrb_deterministic_locality_gate(root)
    if hrb_deterministic_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-074","HRB deterministic locality/systemd manager-default gate failed",hrb_deterministic_locality_gate=hrb_deterministic_ref))
    cpu_numa_threading_ref=cpu_numa_threading_gate(root)
    if cpu_numa_threading_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-069","CPU/NUMA physical-core-first thread governance gate failed",cpu_numa_threading_gate=cpu_numa_threading_ref))
    mentor_ref=mentor_gate(root)
    if mentor_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-041","FA3 Mentor mandatory canonical/regression gate failed",mentor_gate=mentor_ref))
    presenton_ref=presenton_gate(root)
    if presenton_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-045","Presenton mandatory provider/deployment gate failed",presenton_gate=presenton_ref))
    ai_infra_guard_ref=ai_infra_guard_gate(root)
    if ai_infra_guard_ref["result"]!="PASS":
        fs.append(finding("FA3-STATIC-049","AI-Infra-Guard mandatory security-validation gate failed",ai_infra_guard_gate=ai_infra_guard_ref))

    result="PASS" if not fs else "FAIL"
    rep={"schema":"fa3.static-gate-report.v1","architecture_release":RELEASE,"result":result,"blocking_findings":len(fs),"findings":fs,
         "details":{"capabilities":len(rows),"reconciliation_records":len(maps),"geometry_status":geom.get("status"),"source_graph_sha256":att.get("sha256"),"terax_reference_status":terax_ref["result"],"kaneo_gate_status":kaneo_ref["result"],"buzz_gate_status":buzz_ref["result"],"xcmd_gate_status":xcmd_ref["result"],"ai_engineering_gate_status":ai_ref["result"],"autogpt_gate_status":autogpt_ref["result"],"external_api_discovery_gate_status":external_discovery_ref["result"],"modular_gate_status":modular_ref["result"],"inference_portability_gate_status":inference_portability_ref["result"],"model_manager_gate_status":model_manager_ref["result"],"munder_difflin_gate_status":munder_ref["result"],"muse_code_gate_status":muse_code_ref["result"],"openhands_gate_status":openhands_ref["result"],"openbmb_gate_status":openbmb_ref["result"],"stability_sgm_gate_status":stability_sgm_ref["result"],"developer_agent_coordination_gate_status":dac_ref["result"],"codex_gate_status":codex_ref["result"],"demucs_gate_status":demucs_ref["result"],"ace_step_gate_status":ace_ref["result"],"kdenlive_editorial_gate_status":kdenlive_ref["result"],"opencut_gate_status":opencut_ref["result"],"ffmpeg_ai_gate_status":ffmpeg_ai_ref["result"],"hybrid_editorial_gate_status":hybrid_editorial_ref["result"],"marketing_gate_status":marketing_ref["result"],"blackhole_kdenlive_gate_status":blackhole_ref["result"],"whisper_stt_gate_status":whisper_ref["result"],"cosyvoice_gate_status":cosyvoice_ref["result"],"voice_synthesis_gate_status":voice_synthesis_ref["result"],"hrb_deterministic_locality_gate_status":hrb_deterministic_ref["result"],"cpu_numa_threading_gate_status":cpu_numa_threading_ref["result"],"release_projection_gate_status":projection_ref["result"],"mentor_gate_status":mentor_ref["result"],"presenton_gate_status":presenton_ref["result"],"ai_infra_guard_gate_status":ai_infra_guard_ref["result"]}}
    writej(root/"reports/static-gate-report.json",rep)
    return rep

def runtime_check(root:Path):
    fs=[]
    reg=loadj(root/"evidence/evidence-registry.json")
    recs=reg.get("records",[])
    if reg.get("architecture_release")!=RELEASE:
        fs.append(finding("FA3-RUNTIME-001","Evidence Registry release mismatch"))
    expected=[f"CAP-{i:03d}" for i in range(1,144)]
    ids=[r.get("subject_id") for r in recs]
    if len(recs)!=CAPS or ids!=expected:
        fs.append(finding("FA3-RUNTIME-002","Evidence Registry is not exact 143 capability set",records=len(recs)))
    pending=[]
    invalid=[]
    for r in recs:
        s=str(r.get("status","")).upper()
        if s!="PASS":
            pending.append(r.get("subject_id"))
        if not r.get("required_positive_test") or not r.get("required_negative_test") or not r.get("rollback_requirement"):
            invalid.append(r.get("subject_id"))
        if s=="PASS" and not r.get("expires_at"):
            invalid.append(r.get("subject_id"))
    if pending:
        fs.append(finding("FA3-RUNTIME-003","Current-host evidence is not complete",pending_count=len(pending),sample=pending[:20]))
    if invalid:
        fs.append(finding("FA3-RUNTIME-004","Evidence record missing test/rollback/expiry requirement",sample=invalid[:20]))
    result="PASS" if not fs else "FAIL"
    rep={"schema":"fa3.runtime-gate-report.v1","architecture_release":RELEASE,"result":result,"blocking_findings":len(fs),
         "evidence_records":len(recs),"pass_count":sum(str(r.get("status","")).upper()=="PASS" for r in recs),
         "pending_count":sum(str(r.get("status","")).upper()!="PASS" for r in recs),"findings":fs}
    writej(root/"reports/runtime-gate-report.json",rep)
    return rep

def receipt_ok(p:Path,signed=False,human=False,independent=False):
    if not p.exists(): return False,"missing"
    try: d=loadj(p)
    except Exception: return False,"unreadable"
    if d.get("status")!="PASS": return False,str(d.get("status","not PASS"))
    if signed and not d.get("signed"): return False,"not signed"
    if human and not d.get("approved"): return False,"not approved"
    if independent and not d.get("independent"): return False,"not independent"
    return True,"PASS"

def acceptance_check(root:Path):
    s=static_check(root)
    r=runtime_check(root)
    t=terax_gate(root,require_current_host=True)
    results=[]
    for i in range(1,20):
        reasons=[]
        if i in (1,2):
            ok=s["result"]=="PASS"
            if not ok: reasons=["static/authority structural gate not PASS"]
        elif i==3:
            ok=s["result"]=="PASS" and s["details"]["capabilities"]==CAPS
            if not ok: reasons=["143 capability validation not PASS"]
        else:
            ok=True
            for fn in RECEIPTS[i]:
                rok,why=receipt_ok(root/"evidence/receipts"/fn,
                                   signed=(i in (4,19)),
                                   human=(fn=="human-promotion-receipt.json"),
                                   independent=(fn=="independent-review.json"))
                if not rok:
                    ok=False
                    reasons.append(f"{fn}: {why}")
        results.append({"id":i,"name":NAMES[i],"status":"PASS" if ok else "PENDING_OR_FAIL","reasons":reasons})
    all_ok=all(x["status"]=="PASS" for x in results) and r["result"]=="PASS" and t["result"]=="PASS"
    rep={"schema":"fa3.acceptance-report.v1","architecture_release":RELEASE,
         "status":"PASS" if all_ok else "DENIED","decision":"ACCEPT" if all_ok else "DENY","fail_closed":True,
         "static_gate":s["result"],"runtime_gate":r["result"],"terax_gate":t["result"],
         "criteria_passed":sum(x["status"]=="PASS" for x in results),"criteria_total":19,"criteria":results}
    writej(root/"acceptance/acceptance-report.json",rep)
    return rep

def promote(root:Path):
    a=acceptance_check(root)
    allowed=a["status"]=="PASS"
    state={"schema":"fa3.runtime-status.v1","architecture_release":RELEASE,"target_state":"PROMOTED",
           "actual_state":"PROMOTED" if allowed else "PROMOTION_BLOCKED","promotion_allowed":allowed,"acceptance":a["status"],
           "reason":None if allowed else "Fail-closed: PROMOTED is forbidden until all current-host evidence, all 19 acceptance criteria, and the mandatory Terax gate are PASS."}
    writej(root/"promotion/runtime-status.json",state)
    return state,OK if allowed else BLOCKED

def main():
    ap=argparse.ArgumentParser(description="FINAL ARCHITECTURE v3.0 permanent enforcement")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--ci-only",action="store_true",help="For Terax gate: validate immutable reference + executable regressions without claiming current-host evidence")
    ap.add_argument("command",choices=("static","release-projection","runtime","terax","kaneo","kanboard","buzz","xcmd","ai-engineering","external-api-discovery","autogpt","ai-infra-guard","ai-infra-guard-current-host","munder-difflin","munder-difflin-executable","muse-code","openhands","openbmb","tencentdb-agent-memory","stability-sgm","stability-portfolio","developer-agent-coordination","codex","codex-current-host","modular","inference-portability","model-manager","model-manager-current-host","modular-provider","modular-current-host","demucs","demucs-provider","demucs-current-host","acestep","kdenlive-editorial","opencut","ffmpeg-ai","ffmpeg-ai-current-host","hybrid-editorial","marketing","blackhole-kdenlive","whisper-stt","whisper-stt-provider","cosyvoice","cosyvoice-current-host","voice-synthesis","hrb-deterministic-locality","cpu-numa-threading","cpu-numa-threading-current-host","mentor","presenton","presenton-current-host","acceptance","promote","all","status"))
    a=ap.parse_args()
    root=Path(a.root).resolve()
    try:
        if a.command=="static":
            x=static_check(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="release-projection":
            x=release_projection_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="runtime":
            x=runtime_check(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="terax":
            x=terax_gate(root,require_current_host=not a.ci_only); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="kaneo":
            x=kaneo_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="kanboard":
            x=kanboard_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="buzz":
            x=buzz_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="xcmd":
            x=xcmd_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="ai-engineering":
            x=ai_engineering_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="external-api-discovery":
            x=external_api_discovery_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="autogpt":
            x=autogpt_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="ai-infra-guard":
            x=ai_infra_guard_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="ai-infra-guard-current-host":
            x=ai_infra_guard_current_host_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="munder-difflin":
            x=munder_difflin_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="munder-difflin-executable":
            x=munder_difflin_executable_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="muse-code":
            x=muse_code_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="openhands":
            x=openhands_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="openbmb":
            x=openbmb_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="tencentdb-agent-memory":
            x=tencentdb_agent_memory_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="stability-sgm":
            x=stability_sgm_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="stability-portfolio":
            x=stability_portfolio_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="developer-agent-coordination":
            x=developer_agent_coordination_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="codex":
            x=codex_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="codex-current-host":
            x=codex_current_host_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="modular":
            x=modular_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="inference-portability":
            x=inference_portability_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="model-manager":
            x=model_manager_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="model-manager-current-host":
            x=model_manager_current_host_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="modular-provider":
            x=modular_provider_conformance(root); writej(root/"reports/modular-runtime-conformance-report.json",x); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="modular-current-host":
            x=modular_current_host_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="demucs":
            x=demucs_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="demucs-provider":
            x=demucs_provider_conformance(root); writej(root/"reports/demucs-provider-conformance-report.json",x); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="demucs-current-host":
            x=demucs_current_host_gate(root,require_production=True); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="acestep":
            x=ace_step_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="kdenlive-editorial":
            x=kdenlive_editorial_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="opencut":
            x=opencut_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="ffmpeg-ai":
            x=ffmpeg_ai_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="ffmpeg-ai-current-host":
            x=ffmpeg_ai_current_host_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="hybrid-editorial":
            x=hybrid_editorial_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="marketing":
            x=marketing_gate(root); print(json.dumps(x,indent=2,ensure_ascii=False)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="blackhole-kdenlive":
            x=blackhole_kdenlive_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="whisper-stt":
            x=whisper_stt_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="whisper-stt-provider":
            x=whisper_stt_provider_conformance(root); writej(root/"reports/whisper-stt-conformance-report.json",x); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="cosyvoice":
            x=cosyvoice_gate(root); print(json.dumps(x,indent=2,ensure_ascii=False)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="cosyvoice-current-host":
            x=cosyvoice_current_host_gate(root); print(json.dumps(x,indent=2,ensure_ascii=False)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="voice-synthesis":
            x=voice_synthesis_gate(root); print(json.dumps(x,indent=2,ensure_ascii=False)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="hrb-deterministic-locality":
            x=hrb_deterministic_locality_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="cpu-numa-threading":
            x=cpu_numa_threading_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="cpu-numa-threading-current-host":
            x=cpu_numa_threading_current_host_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="mentor":
            x=mentor_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="presenton":
            x=presenton_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="presenton-current-host":
            x=presenton_current_host_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED
        if a.command=="acceptance":
            x=acceptance_check(root); print(json.dumps(x,indent=2)); return OK if x["status"]=="PASS" else BLOCKED
        if a.command in ("promote","all"):
            x,rc=promote(root); print(json.dumps(x,indent=2)); return rc
        p=root/"promotion/runtime-status.json"
        print(p.read_text() if p.exists() else '{"actual_state":"UNKNOWN"}')
        return OK
    except Exception as e:
        print(f"INPUT ERROR: {e}",file=sys.stderr)
        return INPUT

if __name__=="__main__":
    raise SystemExit(main())
