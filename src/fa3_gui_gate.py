#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "desktop_profile": ROOT / "canonical/profiles/FA3-DESKTOP-001.json",
    "desktop_contract": ROOT / "canonical/contracts/FA3-DESKTOP-CONTRACTS-001.json",
    "gui_settings_profile": ROOT / "canonical/profiles/FA3-GUI-SETTINGS-001.json",
    "gui_settings_contract": ROOT / "canonical/contracts/FA3-GUI-SETTINGS-CONTRACTS-001.json",
    "mentor_profile": ROOT / "canonical/profiles/FA3-MENTOR-001.json",
    "mentor_settings_profile": ROOT / "canonical/profiles/FA3-MENTOR-SETTINGS-001.json",
    "mentor_prefs_contract": ROOT / "canonical/contracts/FA3-MENTOR-USER-PREFS-CONTRACT-001.json",
    "coach_profile": ROOT / "canonical/profiles/FA3-COACH-001.json",
    "coach_settings_profile": ROOT / "canonical/profiles/FA3-COACH-SETTINGS-001.json",
    "coach_prefs_contract": ROOT / "canonical/contracts/FA3-COACH-USER-PREFS-CONTRACT-001.json",
    "mentor_coach_contract": ROOT / "canonical/contracts/FA3-MENTOR-COACH-INTERACTION-CONTRACT-001.json",
    "settings_decision": ROOT / "canonical/decisions/FA3-DEC-GUI-SETTINGS-MENTOR-COACH-2026-09-12.json",
    "operations_decision": ROOT / "canonical/decisions/FA3-DEC-GUI-OPERATIONS-2026-09-12.json",
    "settings_gate": ROOT / "canonical/FA3-GATE-GUI-SETTINGS-001.json",
    "runtime": ROOT / "canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json",
    "evidence": ROOT / "evidence/reference/fa3-gui-settings-mentor-coach-reference-pass.json",
    "cmake": ROOT / "apps/fa3-control-center/CMakeLists.txt",
    "main_cpp": ROOT / "apps/fa3-control-center/src/main.cpp",
    "repo_model_cpp": ROOT / "apps/fa3-control-center/src/Fa3RepositoryModel.cpp",
    "repo_model_h": ROOT / "apps/fa3-control-center/src/Fa3RepositoryModel.h",
    "settings_cpp": ROOT / "apps/fa3-control-center/src/SettingsStore.cpp",
    "settings_h": ROOT / "apps/fa3-control-center/src/SettingsStore.h",
    "shell": ROOT / "apps/fa3-control-center/qml/AppShell.qml",
    "settings_qml": ROOT / "apps/fa3-control-center/qml/SettingsPage.qml",
    "mentor_qml": ROOT / "apps/fa3-control-center/qml/MentorPage.qml",
    "coach_qml": ROOT / "apps/fa3-control-center/qml/CoachPage.qml",
    "manager_qml": ROOT / "apps/fa3-control-center/qml/ManagerPage.qml",
    "model_manager_qml": ROOT / "apps/fa3-control-center/qml/ModelManagerPage.qml",
    "system_qml": ROOT / "apps/fa3-control-center/qml/SystemPage.qml",
    "desktop": ROOT / "apps/fa3-control-center/packaging/org.fa3.ControlCenter.desktop",
    "installer": ROOT / "deployment/fa3-gui/install.sh",
}

NAVIGATION = [
    "Command Center",
    "Projects",
    "AI Studio",
    "AI Mentor",
    "AI Coach",
    "Manager",
    "Agents & Workflows",
    "Model Manager",
    "Architecture",
    "Resources",
    "Security & Approvals",
    "Observability",
    "Evidence",
    "Integrations",
    "System",
    "Settings",
]

STUDIO_MODULES = ["Image", "Video", "Animation", "3D / VFX", "Audio", "Music", "Story / Screenplay"]
SYSTEM_SECTIONS = [
    "Overview",
    "CPU / NUMA",
    "GPU / Accelerators",
    "Memory",
    "Storage",
    "Services",
    "Thermal & Power",
    "Software",
    "Maintenance",
    "Peripherals",
]

FORBIDDEN_BACKEND_TOKENS = ["QProcess", "std::system(", "popen(", "/bin/sh", "/bin/bash", "pkexec", "setuid("]
FORBIDDEN_SETTINGS_TOKENS = ["/etc/fstab", "systemctl", "mount ", "umount ", "sudo ", "pkexec", "QProcess"]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate():
    failures = []
    for name, path in REQUIRED.items():
        if not path.exists():
            failures.append(f"missing:{name}:{path.relative_to(ROOT)}")
    if failures:
        return failures

    dp = load_json(REQUIRED["desktop_profile"])
    dc = load_json(REQUIRED["desktop_contract"])
    gs = load_json(REQUIRED["gui_settings_profile"])
    gc = load_json(REQUIRED["gui_settings_contract"])
    mentor = load_json(REQUIRED["mentor_profile"])
    ms = load_json(REQUIRED["mentor_settings_profile"])
    mp = load_json(REQUIRED["mentor_prefs_contract"])
    coach = load_json(REQUIRED["coach_profile"])
    cs = load_json(REQUIRED["coach_settings_profile"])
    cp = load_json(REQUIRED["coach_prefs_contract"])
    inter = load_json(REQUIRED["mentor_coach_contract"])
    settings_decision = load_json(REQUIRED["settings_decision"])
    ops_decision = load_json(REQUIRED["operations_decision"])
    gate = load_json(REQUIRED["settings_gate"])
    runtime = load_json(REQUIRED["runtime"])
    ev = load_json(REQUIRED["evidence"])

    checks = [
        (dp.get("version") == "1.2.0", "desktop-version"),
        (dp.get("new_capability") is False, "desktop-no-capability"),
        (dp.get("new_architectural_authority") is False, "desktop-no-authority"),
        (dp.get("capability_count") == 143, "desktop-count"),
        (dp.get("maintenance_policy", {}).get("routine_gpu_cleanup_uses_reset") is False, "desktop-no-routine-gpu-reset"),
        (dp.get("maintenance_policy", {}).get("evidence_excluded_from_generic_cleanup") is True, "desktop-evidence-not-cleanup"),
        (dc.get("version") == "1.2.0", "contract-version"),
        (dc.get("mutation_model", {}).get("direct_canonical_write") == "FORBIDDEN", "no-direct-canonical"),
        (dc.get("mutation_model", {}).get("direct_gpu_hard_reset") == "FORBIDDEN", "no-direct-gpu-reset"),
        (dc.get("mutation_model", {}).get("direct_peripheral_kernel_or_device_mutation") == "FORBIDDEN", "no-direct-peripheral-mutation"),
        ("ROUTINE_GPU_MEMORY_CLEANUP_NEVER_REQUIRES_GPU_RESET" in dc.get("maintenance_invariants", []), "gpu-cleanup-no-reset"),
        ("EVIDENCE_EXCLUDED_FROM_GENERIC_CLEANUP" in dc.get("maintenance_invariants", []), "evidence-cleanup-boundary"),
        (gs.get("new_architectural_authority") is False, "settings-no-authority"),
        (gc.get("storage", {}).get("backend") == "QSettings/XDG", "settings-xdg"),
        (gc.get("mutation_model", {}).get("fstab_mutation") == "FORBIDDEN", "settings-no-fstab"),
        (mentor.get("id") == "FA3-MENTOR-001", "mentor-present"),
        (ms.get("relationship") == "SUBPROFILE-OF:FA3-MENTOR-001", "mentor-settings"),
        (mp.get("new_architectural_authority") is False, "mentor-prefs-no-authority"),
        (coach.get("id") == "FA3-COACH-001", "coach-id"),
        (coach.get("new_capability") is False, "coach-no-capability"),
        (coach.get("new_architectural_authority") is False, "coach-no-authority"),
        (coach.get("capability_count") == 143, "coach-count"),
        (cs.get("relationship") == "SUBPROFILE-OF:FA3-COACH-001", "coach-settings"),
        (cp.get("mutation_model", {}).get("direct_tool_execution") == "FORBIDDEN", "coach-no-direct-tool"),
        ("MENTOR_TEACHES_COACH_GUIDES_EXECUTION" in inter.get("invariants", []), "mentor-coach-boundary"),
        (settings_decision.get("new_capabilities") == 0, "settings-decision-no-capability"),
        (settings_decision.get("new_architectural_authorities") == 0, "settings-decision-no-authority"),
        (ops_decision.get("new_capabilities") == 0, "ops-decision-no-capability"),
        (ops_decision.get("new_architectural_authorities") == 0, "ops-decision-no-authority"),
        (ops_decision.get("capability_count_after") == 143, "ops-decision-count"),
        ("NO_DIRECT_GPU_HARD_RESET" in ops_decision.get("invariants", []), "ops-decision-gpu-reset-boundary"),
        (gate.get("fail_closed") is True, "gate-fail-closed"),
        (runtime.get("status") == "PENDING_CURRENT_HOST", "runtime-pending"),
        (runtime.get("production_admitted") is False, "runtime-not-production"),
        (ev.get("status") == "PASS", "evidence-pass"),
        (ev.get("production_admitted") is False, "evidence-not-production"),
    ]
    failures += [name for ok, name in checks if not ok]

    shell = REQUIRED["shell"].read_text(encoding="utf-8")
    for label in NAVIGATION:
        if label not in shell:
            failures.append(f"qml-navigation-missing:{label}")
    for module in STUDIO_MODULES:
        if module not in shell:
            failures.append(f"qml-studio-module-missing:{module}")
    for token in [
        "fa3Settings",
        "MentorPage",
        "CoachPage",
        "ManagerPage",
        "ModelManagerPage",
        "SystemPage",
        "SettingsPage",
        "assistantDrawer",
        "ASSISTANT_TASK_PROPOSAL",
        "createDraftChangeSet",
    ]:
        if token not in shell:
            failures.append(f"qml-shell-missing:{token}")

    sq = REQUIRED["settings_qml"].read_text(encoding="utf-8")
    for token in ["Megjelenés", "Language & Region", "Paths & Libraries", "AI Mentor", "AI Coach", "chooseDirectory", "pathStatus"]:
        if token not in sq:
            failures.append(f"settings-qml-missing:{token}")

    mq = REQUIRED["mentor_qml"].read_text(encoding="utf-8")
    for token in ["Memory & Personalization", "Practice Lab", "mentor/memoryPolicy", "mentor/masteryTracking"]:
        if token not in mq:
            failures.append(f"mentor-qml-missing:{token}")

    cq = REQUIRED["coach_qml"].read_text(encoding="utf-8")
    for token in ["AI Coach", "Mentor ↔ Coach", "coach/projectAwareness", "coach/mentorReferrals"]:
        if token not in cq:
            failures.append(f"coach-qml-missing:{token}")

    manager_qml = REQUIRED["manager_qml"].read_text(encoding="utf-8")
    for token in ["EVIDENCE_PENDING", "VERIFIED", "Agent Execution / MCP", "FA3-MANAGER-001"]:
        if token not in manager_qml:
            failures.append(f"manager-qml-missing:{token}")

    model_qml = REQUIRED["model_manager_qml"].read_text(encoding="utf-8")
    for token in ["Model Inventory", "Installed Models", "Compatibility", "Duplicates", "FA3-MODEL-MANAGER", "SECURITY ADMITTED"]:
        if token not in model_qml:
            failures.append(f"model-manager-qml-missing:{token}")

    system_qml = REQUIRED["system_qml"].read_text(encoding="utf-8")
    for token in SYSTEM_SECTIONS:
        if token not in system_qml:
            failures.append(f"system-qml-section-missing:{token}")
    for token in [
        "Temporary files",
        "Cache Manager",
        "Model Runtime Cleanup",
        "GPU hard reset",
        "ROOT ONLY · LOCKED",
        "Keyboard & Hotkeys",
        "MIDI",
        "Drawing Tablet",
        "Scanner",
        "Webcam / Camera",
        "createDraftChangeSet",
    ]:
        if token not in system_qml:
            failures.append(f"system-qml-missing:{token}")

    repo = REQUIRED["repo_model_cpp"].read_text(encoding="utf-8")
    repo_h = REQUIRED["repo_model_h"].read_text(encoding="utf-8")
    for token in FORBIDDEN_BACKEND_TOKENS:
        if token in repo or token in repo_h:
            failures.append(f"backend-forbidden-token:{token}")
    for token in ["gpuDevices", "storageDevices", "peripheralDevices", "/proc/driver/nvidia", "/sys/class/input", "/sys/class/video4linux"]:
        if token not in repo and token not in repo_h:
            failures.append(f"host-discovery-missing:{token}")

    scpp = REQUIRED["settings_cpp"].read_text(encoding="utf-8")
    sh = REQUIRED["settings_h"].read_text(encoding="utf-8")
    for token in ["QSettings", "QStorageInfo", "chooseDirectory", "pathStatus", "resetGroup"]:
        if token not in scpp and token not in sh:
            failures.append(f"settings-backend-missing:{token}")
    for token in FORBIDDEN_SETTINGS_TOKENS:
        if token in scpp:
            failures.append(f"settings-backend-forbidden-token:{token}")

    main = REQUIRED["main_cpp"].read_text(encoding="utf-8")
    if not all(token in main for token in ["SettingsStore", "fa3Settings", "AppShell.qml"]):
        failures.append("settings-context-not-wired")

    cmake = REQUIRED["cmake"].read_text(encoding="utf-8")
    for token in [
        "VERSION 0.3.0",
        "Qt6::Widgets",
        "SettingsStore.cpp",
        "AppShell.qml",
        "SettingsPage.qml",
        "MentorPage.qml",
        "CoachPage.qml",
        "ManagerPage.qml",
        "ModelManagerPage.qml",
        "SystemPage.qml",
    ]:
        if token not in cmake:
            failures.append(f"cmake-missing:{token}")

    return failures


def main():
    failures = validate()
    if failures:
        print("FA3 GUI gate: FAIL")
        for failure in failures:
            print(" -", failure)
        return 1
    print("FA3 GUI gate: PASS")
    print("desktop=1.2.0 operations=0.3.0 settings=QSettings/XDG capabilities=143 new_authorities=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
