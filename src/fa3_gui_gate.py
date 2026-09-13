#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "profile": ROOT / "canonical/profiles/FA3-DESKTOP-001.json",
    "contract": ROOT / "canonical/contracts/FA3-DESKTOP-CONTRACTS-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-GUI-2026-09-12.json",
    "gate": ROOT / "canonical/FA3-GATE-GUI-001.json",
    "runtime": ROOT / "canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json",
    "remote_ai_profile": ROOT / "canonical/profiles/FA3-REMOTE-AI-EXEC-001.json",
    "remote_ai_provider": ROOT / "canonical/providers/FA3-PROVIDER-HF-SPACES-001.json",
    "cmake": ROOT / "apps/fa3-control-center/CMakeLists.txt",
    "main_cpp": ROOT / "apps/fa3-control-center/src/main.cpp",
    "model_cpp": ROOT / "apps/fa3-control-center/src/Fa3RepositoryModel.cpp",
    "qml": ROOT / "apps/fa3-control-center/qml/Main.qml",
    "desktop": ROOT / "apps/fa3-control-center/packaging/org.fa3.ControlCenter.desktop",
    "installer": ROOT / "deployment/fa3-gui/install.sh",
}

NAVIGATION = ["Command Center", "Remote AI Hub", "Projects", "AI Studio", "Agents & Workflows", "Models & Providers", "Architecture", "Resources", "Security & Approvals", "Observability", "Evidence", "Integrations", "System"]
FORBIDDEN_BACKEND_TOKENS = ["QProcess", "std::system(", "popen(", "/bin/sh", "/bin/bash", "pkexec", "setuid("]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    failures: list[str] = []
    for name, path in REQUIRED.items():
        if not path.exists():
            failures.append(f"missing:{name}:{path.relative_to(ROOT)}")
    if failures:
        return failures

    profile = load_json(REQUIRED["profile"])
    contract = load_json(REQUIRED["contract"])
    decision = load_json(REQUIRED["decision"])
    gate = load_json(REQUIRED["gate"])
    runtime = load_json(REQUIRED["runtime"])
    remote_ai_profile = load_json(REQUIRED["remote_ai_profile"])
    remote_ai_provider = load_json(REQUIRED["remote_ai_provider"])

    checks = [
        (profile.get("id") == "FA3-DESKTOP-001", "profile-id"),
        (profile.get("new_capability") is False, "profile-no-new-capability"),
        (profile.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (profile.get("capability_count") == 143, "profile-capability-count"),
        ("REMOTE_AI_HUB_FEATURED_PROJECTION" in profile.get("scope", []), "profile-featured-remote-ai-scope"),
        (contract.get("provider_neutral") is True, "contract-provider-neutral"),
        (contract.get("navigation_baseline", [None, None])[0:2] == ["Command Center", "Remote AI Hub"], "remote-ai-navigation-order"),
        (contract.get("featured_navigation", {}).get("entry") == "Remote AI Hub", "remote-ai-featured-entry"),
        (contract.get("featured_navigation", {}).get("position") == 1, "remote-ai-featured-position"),
        (contract.get("mutation_model", {}).get("direct_canonical_write") == "FORBIDDEN", "no-direct-canonical-write"),
        (contract.get("mutation_model", {}).get("direct_systemd_or_cgroup_mutation") == "FORBIDDEN", "no-direct-host-enforcement"),
        (contract.get("mutation_model", {}).get("direct_remote_provider_execution") == "FORBIDDEN", "no-direct-remote-provider-execution"),
        (contract.get("mutation_model", {}).get("sudo_su_pkexec") == "FORBIDDEN", "no-privilege-bypass"),
        (decision.get("new_capabilities") == 0, "decision-no-new-capability"),
        (decision.get("new_architectural_authorities") == 0, "decision-no-new-authority"),
        (decision.get("capability_count_after") == 143, "decision-capability-count"),
        (gate.get("fail_closed") is True, "gate-fail-closed"),
        (runtime.get("status") == "PENDING_CURRENT_HOST", "runtime-not-falsely-promoted"),
        (runtime.get("production_admitted") is False, "runtime-production-not-admitted"),
        (remote_ai_profile.get("id") == "FA3-REMOTE-AI-EXEC-001", "remote-ai-profile-id"),
        (remote_ai_provider.get("id") == "FA3-PROVIDER-HF-SPACES-001", "remote-ai-provider-id"),
        (remote_ai_provider.get("architectural_authority") is False, "remote-ai-provider-no-authority"),
    ]
    failures.extend(name for ok, name in checks if not ok)

    qml = REQUIRED["qml"].read_text(encoding="utf-8")
    for label in NAVIGATION:
        if label not in qml:
            failures.append(f"qml-navigation-missing:{label}")
    command_pos = qml.find('label: "Command Center"')
    hub_pos = qml.find('label: "Remote AI Hub"')
    projects_pos = qml.find('label: "Projects"')
    if min(command_pos, hub_pos, projects_pos) < 0 or not command_pos < hub_pos < projects_pos:
        failures.append("qml-featured-remote-ai-order")
    for token in ["CORE", "FA3-REMOTE-AI-EXEC-001", "FA3-PROVIDER-HF-SPACES-001", "PRIMARY REFERENCE", "No silent fallback", "CredentialReference"]:
        if token not in qml:
            failures.append(f"qml-remote-ai-feature-missing:{token}")
    for module in ["Image", "Video", "Animation", "3D / VFX", "Audio", "Music", "Story / Screenplay"]:
        if module not in qml:
            failures.append(f"qml-studio-module-missing:{module}")
    if "createDraftChangeSet" not in qml:
        failures.append("qml-changeset-intent-missing")

    model_cpp = REQUIRED["model_cpp"].read_text(encoding="utf-8")
    if "DRAFT_NOT_SUBMITTED" not in model_cpp:
        failures.append("backend-draft-status-missing")
    if '"direct_execution_allowed", false' not in model_cpp:
        failures.append("backend-direct-execution-denial-missing")
    if '"canonical_write_allowed", false' not in model_cpp:
        failures.append("backend-canonical-write-denial-missing")
    for token in FORBIDDEN_BACKEND_TOKENS:
        if token in model_cpp:
            failures.append(f"backend-forbidden-token:{token}")

    cmake = REQUIRED["cmake"].read_text(encoding="utf-8")
    if "Qt6" not in cmake or "qt_add_qml_module" not in cmake:
        failures.append("qt6-qml-build-contract-missing")
    desktop = REQUIRED["desktop"].read_text(encoding="utf-8")
    if "Exec=fa3-control-center" not in desktop:
        failures.append("desktop-entry-exec-missing")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("FA3 GUI gate: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("FA3 GUI gate: PASS")
    print("profile=FA3-DESKTOP-001 capabilities=143 new_authorities=0 remote_ai_hub=FEATURED runtime=PENDING_CURRENT_HOST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
