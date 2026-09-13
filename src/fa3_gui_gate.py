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
    "operations_gate": ROOT / "canonical/FA3-GATE-GUI-OPERATIONS-001.json",
    "runtime": ROOT / "canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json",
    "evidence": ROOT / "evidence/reference/fa3-gui-settings-mentor-coach-reference-pass.json",
    "cmake": ROOT / "apps/fa3-control-center/CMakeLists.txt",
    "main_cpp": ROOT / "apps/fa3-control-center/src/main.cpp",
    "repo_model_cpp": ROOT / "apps/fa3-control-center/src/Fa3RepositoryModel.cpp",
    "repo_model_h": ROOT / "apps/fa3-control-center/src/Fa3RepositoryModel.h",
    "settings_cpp": ROOT / "apps/fa3-control-center/src/SettingsStore.cpp",
    "settings_h": ROOT / "apps/fa3-control-center/src/SettingsStore.h",
    "shell": ROOT / "apps/fa3-control-center/qml/AppShell.qml",
    "embedded_apps_qml": ROOT / "apps/fa3-control-center/qml/EmbeddedAppsPage.qml",
    "settings_qml": ROOT / "apps/fa3-control-center/qml/SettingsPage.qml",
    "mentor_qml": ROOT / "apps/fa3-control-center/qml/MentorPage.qml",
    "coach_qml": ROOT / "apps/fa3-control-center/qml/CoachPage.qml",
    "manager_qml": ROOT / "apps/fa3-control-center/qml/ManagerPage.qml",
    "model_manager_qml": ROOT / "apps/fa3-control-center/qml/ModelManagerPage.qml",
    "system_qml": ROOT / "apps/fa3-control-center/qml/SystemPage.qml",
    "desktop": ROOT / "apps/fa3-control-center/packaging/org.fa3.ControlCenter.desktop",
    "installer": ROOT / "deployment/fa3-gui/install.sh",
    "workflow": ROOT / ".github/workflows/fa3-gui-gate.yml",
}

NAVIGATION = [
    "Command Center", "Projects", "AI Studio", "AI Applications", "Agents & Workflows",
    "Model Manager", "Architecture", "Resources", "Security & Approvals", "Observability",
    "Evidence", "Integrations", "System", "Settings",
]

STUDIO_MODULES = ["Image", "Video", "Animation", "3D / VFX", "Audio", "Music", "Story / Screenplay"]
SYSTEM_SECTIONS = [
    "Overview", "CPU / NUMA", "GPU / Accelerators", "Memory", "Storage",
    "Services", "Thermal & Power", "Software", "Maintenance", "Peripherals",
]

SETTINGS_SURFACES = [
    "Megjelenés", "Language & Region", "Paths & Libraries", "Gyorsbillentyűk",
    "Integrációk", "GIMP", "Krita", "Kdenlive", "OpenShot", "Ardour", "Audacity",
    "Blender", "Bforartist", "LibreOffice", "Obsidian", "Publikálás", "YouTube",
    "Facebook", "TikTok", "HDR", "AI Mentor", "AI Coach", "Manager", "Ellenőr",
    "Ötletelő", "Tanácsadó", "Kérdezd a Mentort gomb", "Kérdezd a Coachot gomb",
    "Kérdezd a Managert gomb", "Kérdezd az Ellenőrt gomb", "Kérdezd az Ötletelőt gomb",
    "Kérdezd a Tanácsadót gomb", "FA3-INSPECTOR-001", "FA3-IDEATOR-001",
    "FA3-ADVISOR-001", "FA3-IDEATION-ADVISORY-001", "FA3-GUI-LANGUAGE-CONTROL-001",
    "Frissítés", "Névjegy", "chooseDirectory", "pathStatus",
]

FORBIDDEN_BACKEND_TOKENS = ["QProcess", "std::system(", "popen(", "/bin/sh", "/bin/bash", "pkexec", "setuid("]
FORBIDDEN_SETTINGS_TOKENS = ["/etc/fstab", "systemctl", "mount ", "umount ", "sudo ", "pkexec", "QProcess"]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_all(text: str, tokens: list[str], prefix: str) -> list[str]:
    return [f"{prefix}:{token}" for token in tokens if token not in text]


def validate():
    failures: list[str] = []
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
    settings_gate = load_json(REQUIRED["settings_gate"])
    operations_gate = load_json(REQUIRED["operations_gate"])
    runtime = load_json(REQUIRED["runtime"])
    ev = load_json(REQUIRED["evidence"])

    role_list = dp.get("role_navigation_policy", {}).get("roles", [])
    role_invariants = dc.get("role_ui_invariants", [])
    checks = [
        (dp.get("version") == "1.5.0", "desktop-version"),
        (dp.get("new_capability") is False, "desktop-no-capability"),
        (dp.get("new_architectural_authority") is False, "desktop-no-authority"),
        (dp.get("capability_count") == 143, "desktop-count"),
        (dp.get("runtime", {}).get("browser_shell") is False, "desktop-not-browser-shell"),
        (dp.get("runtime", {}).get("embedded_web_runtime") == "Qt WebEngine", "desktop-embedded-web-runtime"),
        (dp.get("embedded_web_policy", {}).get("external_browser_for_ai_ui") == "FORBIDDEN_BY_DEFAULT", "desktop-no-external-ai-browser"),
        (dp.get("embedded_web_policy", {}).get("new_window_requests") == "RETAIN_INSIDE_FA3_WEB_SURFACE", "desktop-retain-new-window"),
        (dp.get("maintenance_policy", {}).get("routine_gpu_cleanup_uses_reset") is False, "desktop-no-routine-gpu-reset"),
        (dp.get("maintenance_policy", {}).get("evidence_excluded_from_generic_cleanup") is True, "desktop-evidence-not-cleanup"),
        (dp.get("role_navigation_policy", {}).get("configuration_location") == "SETTINGS", "role-config-settings-only"),
        (dp.get("role_navigation_policy", {}).get("ask_button_visibility") == "LOCAL_QSETTINGS_PREFERENCE", "role-button-qsettings"),
        (dp.get("role_navigation_policy", {}).get("ask_button_visibility_changes_role_authority") is False, "role-button-not-authority"),
        ("FA3-INSPECTOR-001" in role_list, "inspector-role-projected"),
        ("FA3-IDEATOR-001" in role_list, "ideator-role-projected"),
        ("FA3-ADVISOR-001" in role_list, "advisor-role-projected"),
        (dc.get("version") == "1.5.0", "contract-version"),
        (dc.get("mutation_model", {}).get("direct_canonical_write") == "FORBIDDEN", "no-direct-canonical"),
        (dc.get("mutation_model", {}).get("direct_gpu_hard_reset") == "FORBIDDEN", "no-direct-gpu-reset"),
        (dc.get("mutation_model", {}).get("direct_peripheral_kernel_or_device_mutation") == "FORBIDDEN", "no-direct-peripheral-mutation"),
        (dc.get("mutation_model", {}).get("direct_ideation_advisory_decision") == "FORBIDDEN", "no-direct-ideation-advisory-decision"),
        (dc.get("mutation_model", {}).get("direct_ideation_advisory_execution") == "FORBIDDEN", "no-direct-ideation-advisory-execution"),
        ("ROLE_CONFIGURATION_LIVES_UNDER_SETTINGS_NOT_PRIMARY_NAVIGATION" in role_invariants, "role-settings-invariant"),
        ("ASK_ROLE_ACTIONS_OPEN_CONVERSATION_SURFACES_NOT_CONFIGURATION_PAGES" in role_invariants, "role-chat-not-config"),
        ("INSPECTOR_PREFERENCES_MUST_NOT_WEAKEN_INDEPENDENT_VERIFICATION" in role_invariants, "inspector-independence"),
        ("IDEATOR_OUTPUT_MUST_PRESERVE_IDEA_NOT_FACT_AND_HYPOTHESIS_NOT_EVIDENCE" in role_invariants, "ideator-semantic-boundary"),
        ("ADVISOR_OUTPUT_MUST_PRESERVE_RECOMMENDATION_NOT_DECISION" in role_invariants, "advisor-recommendation-boundary"),
        ("ADVISOR_MISSING_EVIDENCE_MUST_REMAIN_UNVERIFIED" in role_invariants, "advisor-missing-evidence-boundary"),
        ("ADVISOR_UNCERTAINTY_AND_CONFIDENCE_MUST_REMAIN_EXPLICIT" in role_invariants, "advisor-uncertainty-boundary"),
        ("ADVISOR_CONFLICTING_EVIDENCE_MUST_REMAIN_VISIBLE" in role_invariants, "advisor-conflict-boundary"),
        ("ADVISOR_HIGH_IMPACT_OR_PROMOTION_MUST_HANDOFF_TO_INSPECTOR" in role_invariants, "advisor-inspector-handoff"),
        ("AI_WEB_UI_EMBEDDED_IN_FA3_NATIVE_WINDOW_BY_DEFAULT" in dc.get("embedded_web_invariants", []), "embedded-ai-ui-required"),
        ("EXTERNAL_BROWSER_FOR_AI_UI_FORBIDDEN_BY_DEFAULT" in dc.get("embedded_web_invariants", []), "external-ai-browser-forbidden"),
        ("NEW_WINDOW_REQUESTS_RETAINED_INSIDE_FA3_WEB_SURFACE" in dc.get("embedded_web_invariants", []), "new-window-contained"),
        ("ROUTINE_GPU_MEMORY_CLEANUP_NEVER_REQUIRES_GPU_RESET" in dc.get("maintenance_invariants", []), "gpu-cleanup-no-reset"),
        ("EVIDENCE_EXCLUDED_FROM_GENERIC_CLEANUP" in dc.get("maintenance_invariants", []), "evidence-cleanup-boundary"),
        (gs.get("version") == "1.2.0", "settings-profile-version"),
        (gs.get("new_architectural_authority") is False, "settings-no-authority"),
        (gs.get("role_settings", {}).get("location") == "SETTINGS_ONLY", "settings-role-location"),
        (gs.get("role_settings", {}).get("visibility_changes_canonical_role") is False, "settings-role-visibility-not-authority"),
        (gc.get("version") == "1.2.0", "settings-contract-version"),
        (gc.get("storage", {}).get("backend") == "QSettings/XDG", "settings-xdg"),
        (gc.get("storage", {}).get("secret_values") == "FORBIDDEN", "settings-no-secrets"),
        (gc.get("role_ui", {}).get("configuration_location") == "SETTINGS", "settings-contract-role-location"),
        (gc.get("role_ui", {}).get("primary_navigation_role_pages") == "FORBIDDEN", "settings-contract-no-role-nav"),
        (gc.get("role_ui", {}).get("inspector_independence_can_be_disabled_by_preference") is False, "settings-inspector-independent"),
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
        (settings_gate.get("fail_closed") is True, "settings-gate-fail-closed"),
        (operations_gate.get("fail_closed") is True, "operations-gate-fail-closed"),
        (runtime.get("status") == "PENDING_CURRENT_HOST", "runtime-pending"),
        (runtime.get("production_admitted") is False, "runtime-not-production"),
        (ev.get("status") == "PASS", "evidence-pass"),
        (ev.get("production_admitted") is False, "evidence-not-production"),
    ]
    failures.extend(name for ok, name in checks if not ok)

    shell = REQUIRED["shell"].read_text(encoding="utf-8")
    shell_lines = {line.strip() for line in shell.splitlines()}
    failures += _contains_all(shell, NAVIGATION + STUDIO_MODULES, "qml-missing")
    for forbidden_role_nav in [
        '{ key: "mentor"', '{ key: "coach"', '{ key: "manager"', '{ key: "inspector"',
        '{ key: "ideator"', '{ key: "advisor"',
    ]:
        if forbidden_role_nav in shell:
            failures.append(f"qml-role-nav-forbidden:{forbidden_role_nav}")
    for forbidden_role_page in ["MentorPage {", "CoachPage {", "ManagerPage {"]:
        if forbidden_role_page in shell_lines:
            failures.append(f"qml-role-page-forbidden:{forbidden_role_page}")
    failures += _contains_all(shell, [
        "fa3Settings", "EmbeddedAppsPage", "ModelManagerPage", "SystemPage", "SettingsPage",
        "assistantDrawer", "ASSISTANT_TASK_PROPOSAL", "createDraftChangeSet", "Shortcut", "shortcuts/assistant",
        "LibreOffice", "Obsidian", "Kérdezd a Mentort", "Kérdezd a Coachot", "Kérdezd a Managert",
        "Kérdezd az Ellenőrt", "Kérdezd az Ötletelőt", "Kérdezd a Tanácsadót",
        "roleButtons/mentorVisible", "roleButtons/coachVisible", "roleButtons/managerVisible",
        "roleButtons/inspectorVisible", "roleButtons/ideatorVisible", "roleButtons/advisorVisible",
        "ideatorDialog", "advisorDialog", "settingsSectionKey", "navigationHistory", "sidebarCollapsed",
    ], "qml-shell-missing")

    embedded = REQUIRED["embedded_apps_qml"].read_text(encoding="utf-8")
    failures += _contains_all(embedded, [
        "import QtWebEngine", "WebEngineView", "Open WebUI", "ComfyUI", "InvokeAI", "n8n",
        "onNewWindowRequested", "request.openIn(webView)", "onNavigationRequested", "request.reject()",
        "webapps/", "Külső böngésző nincs használva",
    ], "embedded-web-missing")
    if "Qt.openUrlExternally" in embedded:
        failures.append("embedded-web-external-opener-forbidden")

    sq = REQUIRED["settings_qml"].read_text(encoding="utf-8")
    failures += _contains_all(sq, SETTINGS_SURFACES, "settings-qml-missing")
    failures += _contains_all(sq, [
        "roleButtons/mentorVisible", "roleButtons/coachVisible", "roleButtons/managerVisible",
        "roleButtons/inspectorVisible", "roleButtons/ideatorVisible", "roleButtons/advisorVisible",
        "manager/defaultView", "inspector/defaultLevel", "ideator/defaultMode", "advisor/defaultMode",
        "FA3-INSPECTOR-001 · REQUIRED", "openSection",
    ], "settings-role-qml-missing")

    mq = REQUIRED["mentor_qml"].read_text(encoding="utf-8")
    failures += _contains_all(mq, ["Memory & Personalization", "Practice Lab", "mentor/memoryPolicy", "mentor/masteryTracking"], "mentor-qml-missing")
    cq = REQUIRED["coach_qml"].read_text(encoding="utf-8")
    failures += _contains_all(cq, ["AI Coach", "Mentor ↔ Coach", "coach/projectAwareness", "coach/mentorReferrals"], "coach-qml-missing")
    manager_qml = REQUIRED["manager_qml"].read_text(encoding="utf-8")
    failures += _contains_all(manager_qml, ["EVIDENCE_PENDING", "VERIFIED", "Agent Execution / MCP", "FA3-MANAGER-001"], "manager-qml-missing")
    model_qml = REQUIRED["model_manager_qml"].read_text(encoding="utf-8")
    failures += _contains_all(model_qml, ["Model Inventory", "Installed Models", "Compatibility", "Duplicates", "FA3-MODEL-MANAGER", "SECURITY ADMITTED"], "model-manager-qml-missing")
    system_qml = REQUIRED["system_qml"].read_text(encoding="utf-8")
    failures += _contains_all(system_qml, SYSTEM_SECTIONS + [
        "Temporary files", "Cache Manager", "Model Runtime Cleanup", "GPU hard reset", "ROOT ONLY · LOCKED",
        "Keyboard & Hotkeys", "MIDI", "Drawing Tablet", "Scanner", "Webcam / Camera", "createDraftChangeSet",
    ], "system-qml-missing")

    repo = REQUIRED["repo_model_cpp"].read_text(encoding="utf-8")
    repo_h = REQUIRED["repo_model_h"].read_text(encoding="utf-8")
    for token in FORBIDDEN_BACKEND_TOKENS:
        if token in repo or token in repo_h:
            failures.append(f"backend-forbidden-token:{token}")

    scpp = REQUIRED["settings_cpp"].read_text(encoding="utf-8")
    sh = REQUIRED["settings_h"].read_text(encoding="utf-8")
    failures += _contains_all(scpp + sh, ["QSettings", "QStorageInfo", "QKeySequence", "chooseDirectory", "pathStatus", "validShortcut", "shortcutConflict", "resetGroup"], "settings-backend-missing")
    for token in FORBIDDEN_SETTINGS_TOKENS:
        if token in scpp:
            failures.append(f"settings-backend-forbidden-token:{token}")
    for token in ["password", "secret", "token", "cookie"]:
        if token not in scpp.lower():
            failures.append(f"settings-secret-filter-missing:{token}")

    main = REQUIRED["main_cpp"].read_text(encoding="utf-8")
    failures += _contains_all(main, ["SettingsStore", "fa3Settings", "AppShell.qml", "QtWebEngineQuick::initialize", "AA_ShareOpenGLContexts", "0.4.0"], "main-missing")
    cmake = REQUIRED["cmake"].read_text(encoding="utf-8")
    failures += _contains_all(cmake, [
        "VERSION 0.4.0", "WebEngineQuick", "Qt6::WebEngineQuick", "EmbeddedAppsPage.qml",
        "SettingsStore.cpp", "AppShell.qml", "SettingsPage.qml", "MentorPage.qml", "CoachPage.qml",
        "ManagerPage.qml", "ModelManagerPage.qml", "SystemPage.qml",
    ], "cmake-missing")

    installer = REQUIRED["installer"].read_text(encoding="utf-8")
    workflow = REQUIRED["workflow"].read_text(encoding="utf-8")
    for token in ["qt6-webengine-dev", "qml6-module-qtwebengine"]:
        if token not in installer:
            failures.append(f"installer-webengine-missing:{token}")
        if token not in workflow:
            failures.append(f"workflow-webengine-missing:{token}")

    return failures


def main():
    failures = validate()
    if failures:
        print("FA3 GUI gate: FAIL")
        for failure in failures:
            print(" -", failure)
        return 1
    print("FA3 GUI gate: PASS")
    print("desktop=1.5.0 app=0.4.0 role_settings=Mentor/Coach/Manager/Inspector/Ideator/Advisor semantic_interop=LanguageControl embedded_web=QtWebEngine capabilities=143 new_authorities=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
