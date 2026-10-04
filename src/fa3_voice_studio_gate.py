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
    "voice.generate.submit", "voice.fit-to-clip.plan", "voice.quick-dub.plan",
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

    workspace = required["workspace"].read_text(encoding="utf-8")
    for token in (
        "BLOCKED_NOT_ADMITTED", "discover_admitted_voice_providers", "resolve_route",
        "fit_to_clip_plan", "quick_dub_plan", "timeline_handoff",
        "accept_generation_result", "silent_text_rewrite", "host_mutation_authorized",
        "RESOLVED_BY_MODEL_ROUTER_RUNTIME", "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    ):
        check(f"VSTUDIO-PY-{token}", token in workspace, f"workspace core missing invariant token: {token}")

    service_h = required["service_h"].read_text(encoding="utf-8")
    service_cpp = required["service_cpp"].read_text(encoding="utf-8")
    for token in (
        "upsertVoiceProfile", "createCapture", "stageGeneration", "fitToClip",
        "stageQuickDub", "acceptProviderResult", "stageTimelineHandoff", "cancelJob",
        "startMicrophoneCapture", "stopMicrophoneCapture",
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

    voice_qml = required["voice_qml"].read_text(encoding="utf-8")
    quick_qml = required["quick_qml"].read_text(encoding="utf-8")
    overlay_qml = required["overlay_qml"].read_text(encoding="utf-8")
    for token in (
        "fa3VoiceWorkspace.stageGeneration", "fa3VoiceWorkspace.upsertVoiceProfile",
        "fa3VoiceWorkspace.startMicrophoneCapture", "fa3VoiceWorkspace.stopMicrophoneCapture",
        "fa3VoiceWorkspace.stageQuickDub", "fa3VoiceWorkspace.stageTimelineHandoff",
        "fa3VoiceWorkspace.cancelJob", "VoiceTransformationPanel", "AI TTS enabled",
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
