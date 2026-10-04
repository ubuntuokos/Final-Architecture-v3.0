#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

CAPS = module_active_capability_count(__file__)
PROFILE_ID = "FA3-VOICE-STUDIO-001"
CONTRACT_ID = "FA3-VOICE-STUDIO-CONTRACTS-001"
PLUGIN_ID = "FA3-VOICE-PLUGIN-MANIFEST-001"
GATE_ID = "FA3-VOICE-STUDIO-GATESET-001"
ACTIONS = {
    "voice.profile.list", "voice.profile.get", "voice.profile.upsert",
    "voice.capture", "voice.transcribe", "voice.speak", "voice.stop", "voice.status",
    "voice.generate.submit", "voice.generate.dispatch", "voice.fit-to-clip.plan", "voice.quick-dub.plan",
    "voice.timeline.insert",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(root: Path) -> dict[str, Any]:
    required = {
        "profile": root / "canonical/profiles/FA3-VOICE-STUDIO-001.json",
        "contract": root / "canonical/contracts/FA3-VOICE-STUDIO-CONTRACTS-001.json",
        "plugin": root / "canonical/FA3-VOICE-PLUGIN-MANIFEST-001.json",
        "workspace": root / "src/fa3_voice_workspace.py",
        "service_h": root / "apps/fa3-control-center/src/VoiceWorkspaceService.h",
        "service_cpp": root / "apps/fa3-control-center/src/VoiceWorkspaceService.cpp",
        "voice_qml": root / "apps/fa3-control-center/qml/VoiceStudioPage.qml",
        "quick_qml": root / "apps/fa3-control-center/qml/QuickVoicePluginPage.qml",
        "overlay_qml": root / "apps/fa3-control-center/qml/VoiceActivityOverlay.qml",
        "main_cpp": root / "apps/fa3-control-center/src/main.cpp",
        "main_qml": root / "apps/fa3-control-center/qml/Main.qml",
        "cmake": root / "apps/fa3-control-center/CMakeLists.txt",
        "cli": root / "bin/fa3-voice-studio",
        "test_policy": root / "tests/test_voice_workspace_policy.py",
        "test_flow": root / "tests/test_voice_workspace_flow.py",
        "uaf": root / "src/fa3_voice_uaf.py",
        "provider_spi": root / "src/fa3_voice_provider_spi.py",
        "gate_record": root / "canonical/FA3-GATE-VOICE-STUDIO-001.json",
        "enforcement": root / "canonical/voice-studio-enforcement.json",
        "gate_registry": root / "canonical/FA3-GATE-REGISTRY-001.json",
        "policy": root / "canonical/enforcement-policy.json",
        "surface_registry": root / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
        "reference_evidence": root / "evidence/reference/voice-studio-full-app-ci-2026-10-04.json",
    }
    for action in ACTIONS:
        required[f"action:{action}"] = root / f"canonical/actions/{action}.json"

    findings: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []

    def check(case_id: str, condition: bool, detail: str) -> None:
        cases.append({"id": case_id, "result": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            findings.append({"code": case_id, "severity": "P0", "message": detail})

    missing = [str(path.relative_to(root)) for path in required.values() if not path.is_file()]
    check("VSTUDIO-001", not missing, f"required full-app artifacts present; missing={missing}")
    if missing:
        return {
            "schema": "fa3.voice-studio-gate-report.v1", "gate_id": GATE_ID,
            "profile_id": PROFILE_ID, "result": "FAIL", "passed": 0,
            "total": len(cases), "cases": cases, "findings": findings,
        }

    profile = loadj(required["profile"])
    contract = loadj(required["contract"])
    plugin = loadj(required["plugin"])
    gate_record = loadj(required["gate_record"])
    enforcement = loadj(required["enforcement"])
    gate_registry = loadj(required["gate_registry"])
    policy = loadj(required["policy"])
    surface_registry = loadj(required["surface_registry"])
    reference_evidence = loadj(required["reference_evidence"])
    check("VSTUDIO-002",
          profile.get("id") == PROFILE_ID and profile.get("parent_architecture") == "FA3-VOICE-001"
          and profile.get("capability_count") == CAPS and profile.get("new_capability") is False
          and profile.get("architectural_authority") is False
          and profile.get("new_architectural_authority") is False,
          "Voice Studio profile preserves FA3-VOICE-001, 175 baseline and zero-authority boundary")
    check("VSTUDIO-003",
          contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True
          and contract.get("capability_count") == CAPS and contract.get("new_capabilities") == 0
          and contract.get("new_architectural_authorities") == 0,
          "provider-neutral workspace contracts preserve capability/authority baseline")
    check("VSTUDIO-004",
          plugin.get("id") == PLUGIN_ID and plugin.get("authority") is False
          and set(plugin.get("projections", {})) == {"QUICK", "STANDARD", "ADVANCED"}
          and plugin.get("direct_cuda_ordinal_allowed") is False
          and plugin.get("arbitrary_model_path_allowed") is False
          and plugin.get("arbitrary_provider_endpoint_allowed") is False,
          "Shared Voice Plugin projections and no-direct-routing invariants")

    action_ok = True
    for action in ACTIONS:
        obj = loadj(required[f"action:{action}"])
        action_ok = action_ok and (
            obj.get("schema") == "fa3.uaf.action-contract.v1"
            and obj.get("id") == action
            and obj.get("exposure", {}).get("mcp") is True
            and obj.get("exposure", {}).get("gui") is True
            and obj.get("security", {}).get("authorization") == "required"
            and obj.get("authority_bindings", {}).get("voice") == "FA3-VOICE-001"
            and obj.get("authority_bindings", {}).get("model_router") == "FA3-AUTH-MODEL-ROUTER-001"
            and obj.get("authority_bindings", {}).get("resource") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
            and obj.get("authority_bindings", {}).get("uaf") == "FA3-UNIFIED-ACTION-FABRIC-001"
        )
    check("VSTUDIO-005", action_ok and set(profile.get("uaf_actions", [])) == ACTIONS,
          "all Voice Studio typed actions are GUI/MCP exposed through existing UAF authorities")
    check("VSTUDIO-005A",
          gate_record.get("gateset_id") == GATE_ID and gate_record.get("profile_id") == PROFILE_ID
          and gate_record.get("contract_id") == CONTRACT_ID and gate_record.get("priority") == "P0"
          and gate_record.get("fail_closed") is True and gate_record.get("capability_count_after") == CAPS,
          "Voice Studio P0 gate record must remain fail-closed and baseline-bound")
    check("VSTUDIO-005B",
          enforcement.get("gate_id") == GATE_ID and enforcement.get("fail_closed") is True
          and enforcement.get("mandatory_rule_count") == len(enforcement.get("p0_invariants", [])) == 12
          and enforcement.get("capability_count") == CAPS and enforcement.get("authority_delta") == 0,
          "Voice Studio enforcement record invariant drift")
    check("VSTUDIO-005C",
          GATE_ID in gate_registry.get("mandatory_reference_gates", [])
          and gate_registry.get("mandatory_reference_gates") == policy.get("mandatory_reference_gates")
          and policy.get("voice_studio_profile_id") == PROFILE_ID
          and policy.get("voice_studio_contract_id") == CONTRACT_ID
          and policy.get("voice_studio_plugin_manifest_id") == PLUGIN_ID
          and policy.get("voice_studio_gate_id") == GATE_ID
          and policy.get("voice_studio_current_host_provider_runtime_claim") is False
          and policy.get("voice_studio_mandatory_p0_rules") == enforcement.get("p0_invariants"),
          "Voice Studio gate registry and permanent-policy mirror binding missing")
    surfaces = {row.get("route_id"): row for row in surface_registry.get("surfaces", [])}
    check("VSTUDIO-005D",
          surfaces.get("create.voice-studio", {}).get("profile_id") == PROFILE_ID
          and surfaces.get("create.voice-studio", {}).get("authority") is False
          and surfaces.get("create.voice-studio", {}).get("direct_provider_execution") is False
          and surfaces.get("create.quick-voice-plugin", {}).get("plugin_manifest_id") == PLUGIN_ID
          and surfaces.get("create.quick-voice-plugin", {}).get("authority") is False,
          "canonical GUI Surface Registry Voice Studio/Quick Voice boundary missing")
    check("VSTUDIO-005E",
          reference_evidence.get("subject_id") == PROFILE_ID
          and reference_evidence.get("gate_id") == GATE_ID
          and reference_evidence.get("provider_runtime_evidence") is False
          and reference_evidence.get("current_host_production_claim") is False
          and reference_evidence.get("global_promotion_claim") is False,
          "reference evidence scope must never manufacture provider/current-host promotion")

    workspace = required["workspace"].read_text(encoding="utf-8")
    for token in (
        "BLOCKED_NOT_ADMITTED", "discover_admitted_voice_providers", "resolve_route",
        "fit_to_clip_plan", "quick_dub_plan", "timeline_handoff",
        "accept_generation_result", "authorize_dispatch", "stage_transcription", "accept_transcription_result", "silent_text_rewrite", "host_mutation_authorized",
        "RESOLVED_BY_MODEL_ROUTER_RUNTIME", "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    ):
        check(f"VSTUDIO-PY-{token}", token in workspace, f"workspace core missing invariant token: {token}")

    service_h = required["service_h"].read_text(encoding="utf-8")
    service_cpp = required["service_cpp"].read_text(encoding="utf-8")
    for token in (
        "upsertVoiceProfile", "createCapture", "stageGeneration", "fitToClip",
        "stageQuickDub", "acceptProviderResult", "stageTimelineHandoff", "cancelJob",
        "startMicrophoneCapture", "stopMicrophoneCapture", "stageTranscription", "authorizeDispatch",
    ):
        check(f"VSTUDIO-SVC-{token}", token in service_h and token in service_cpp,
              f"Qt Voice Workspace service missing method: {token}")
    for token in (
        "QAudioSource", "QMediaDevices", "16000", "QAudioFormat::Int16",
        "no silent format fallback", "BLOCKED_NOT_ADMITTED",
        "FA3-AUTH-MODEL-ROUTER-001", "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    ):
        check(f"VSTUDIO-SVCINV-{token}", token in service_cpp,
              f"Qt service missing capture/routing invariant: {token}")

    uaf = required["uaf"].read_text(encoding="utf-8")
    provider_spi = required["provider_spi"].read_text(encoding="utf-8")
    for token in ("ActionDispatcher", "FA3-PROVIDER-VOICE-STUDIO-NATIVE-001", "FA3-PROVIDER-WHISPER-001",
                  "whisper_current_host_binding", "device") == "cpu", "voice.generate.dispatch"):
        check(f"VSTUDIO-UAF-{token}", token in uaf, f"Voice UAF adapter missing invariant token: {token}")
    for token in ("VoiceProviderAdapter", "resolve_exact", "current_host_admitted", "execute_dispatched_job",
                  "no runtime adapter for routed provider"):
        check(f"VSTUDIO-SPI-{token}", token in provider_spi, f"VoiceProvider SPI missing invariant token: {token}")

    voice_qml = required["voice_qml"].read_text(encoding="utf-8")
    quick_qml = required["quick_qml"].read_text(encoding="utf-8")
    overlay_qml = required["overlay_qml"].read_text(encoding="utf-8")
    for token in (
        "fa3VoiceWorkspace.stageGeneration", "fa3VoiceWorkspace.upsertVoiceProfile",
        "fa3VoiceWorkspace.startMicrophoneCapture", "fa3VoiceWorkspace.stopMicrophoneCapture",
        "fa3VoiceWorkspace.stageQuickDub", "fa3VoiceWorkspace.stageTimelineHandoff",
        "fa3VoiceWorkspace.cancelJob", "fa3VoiceWorkspace.stageTranscription", "VoiceTransformationPanel", "AI TTS enabled",
    ):
        check(f"VSTUDIO-GUI-{token}", token in voice_qml, f"Voice Studio GUI missing functional binding: {token}")
    for token in (
        "Generate & Insert", "fa3VoiceWorkspace.stageGeneration",
        "fa3VoiceWorkspace.fitToClip", "fa3VoiceWorkspace.stageQuickDub",
        "fa3VoiceWorkspace.startMicrophoneCapture", "BLOCKED_NOT_ADMITTED",
    ):
        check(f"VSTUDIO-QUICK-{token}", token in quick_qml, f"Quick Voice plugin missing functional binding: {token}")
    check("VSTUDIO-OVERLAY",
          'fa3VoiceWorkspace.cancelJob' in overlay_qml and 'property string jobId' in overlay_qml,
          "global Voice Activity Overlay must bind visible stop to workspace job")

    main_cpp = required["main_cpp"].read_text(encoding="utf-8")
    main_qml = required["main_qml"].read_text(encoding="utf-8")
    cmake = required["cmake"].read_text(encoding="utf-8")
    check("VSTUDIO-006",
          "VoiceWorkspaceService voiceWorkspace" in main_cpp
          and 'setContextProperty("fa3VoiceWorkspace"' in main_cpp
          and "src/VoiceWorkspaceService.cpp" in cmake
          and "Qt6::Multimedia" in cmake,
          "Control Center runtime must instantiate and link Voice Workspace service")
    check("VSTUDIO-007",
          'fa3VoiceWorkspace.activity.state' in main_qml
          and 'fa3VoiceWorkspace.activity.job_id' in main_qml,
          "Main.qml must bind global overlay to live Voice Workspace activity")

    check("VSTUDIO-008", "QProcess" not in service_cpp and "std::system(" not in service_cpp,
          "Voice GUI service cannot shell out or become an execution bypass")
    check("VSTUDIO-009", "runtime_execution_allowed" in workspace and "execution_requested" in workspace,
          "workspace distinguishes staged jobs from authorized runtime execution")
    check("VSTUDIO-009A", "Qt6::Multimedia" in cmake and "qt6-multimedia-dev" in (root / ".github/workflows/fa3-gui-gate.yml").read_text(encoding="utf-8")
          and "qt6-multimedia-dev" in (root / "deployment/fa3-gui/install.sh").read_text(encoding="utf-8"),
          "Qt Multimedia build/install dependency must be materialized")
    check("VSTUDIO-010", profile.get("runtime_promotion", {}).get("provider_audio_execution_claim") is False,
          "full application materialization must not fabricate provider audio production PASS")

    passed = sum(row["result"] == "PASS" for row in cases)
    return {
        "schema": "fa3.voice-studio-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "result": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "cases": cases,
        "findings": findings,
        "capability_count": CAPS,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "provider_runtime_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = run(root)
    out = root / "reports/voice-studio-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
