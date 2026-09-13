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
    "cmake": ROOT / "apps/fa3-control-center/CMakeLists.txt",
    "main_cpp": ROOT / "apps/fa3-control-center/src/main.cpp",
    "model_cpp": ROOT / "apps/fa3-control-center/src/Fa3RepositoryModel.cpp",
    "qml": ROOT / "apps/fa3-control-center/qml/Main.qml",
    "models_providers_qml": ROOT / "apps/fa3-control-center/qml/ModelsProvidersPage.qml",
    "studio_qml": ROOT / "apps/fa3-control-center/qml/AiStudioPage.qml",
    "settings_qml": ROOT / "apps/fa3-control-center/qml/SystemSettingsPage.qml",
    "rtd_qml": ROOT / "apps/fa3-control-center/qml/RtdProvidersPage.qml",
    "preference_store": ROOT / "apps/fa3-control-center/src/PreferenceStore.cpp",
    "device_model": ROOT / "apps/fa3-control-center/src/SystemDeviceModel.cpp",
    "desktop": ROOT / "apps/fa3-control-center/packaging/org.fa3.ControlCenter.desktop",
    "installer": ROOT / "deployment/fa3-gui/install.sh",
}

NAVIGATION = ["Command Center", "RTD Providers", "Projects", "AI Studio", "Agents & Workflows", "Models & Providers", "Architecture", "Resources", "Security & Approvals", "Observability", "Evidence", "Integrations", "System"]
FORBIDDEN_BACKEND_TOKENS = ["QProcess", "std::system(", "popen(", "/bin/sh", "/bin/bash", "pkexec", "setuid("]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    failures: list[str] = []
    for name, path in REQUIRED.items():
        if not path.exists(): failures.append(f"missing:{name}:{path.relative_to(ROOT)}")
    if failures: return failures

    profile = load_json(REQUIRED["profile"])
    contract = load_json(REQUIRED["contract"])
    decision = load_json(REQUIRED["decision"])
    gate = load_json(REQUIRED["gate"])
    runtime = load_json(REQUIRED["runtime"])

    checks = [
        (profile.get("id") == "FA3-DESKTOP-001", "profile-id"),
        (profile.get("new_capability") is False, "profile-no-new-capability"),
        (profile.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (profile.get("capability_count") == 143, "profile-capability-count"),
        (contract.get("provider_neutral") is True, "contract-provider-neutral"),
        (contract.get("mutation_model", {}).get("direct_canonical_write") == "FORBIDDEN", "no-direct-canonical-write"),
        (contract.get("mutation_model", {}).get("direct_systemd_or_cgroup_mutation") == "FORBIDDEN", "no-direct-host-enforcement"),
        (contract.get("mutation_model", {}).get("sudo_su_pkexec") == "FORBIDDEN", "no-privilege-bypass"),
        (decision.get("new_capabilities") == 0, "decision-no-new-capability"),
        (decision.get("new_architectural_authorities") == 0, "decision-no-new-authority"),
        (decision.get("capability_count_after") == 143, "decision-capability-count"),
        (gate.get("fail_closed") is True, "gate-fail-closed"),
        (runtime.get("status") == "PENDING_CURRENT_HOST", "runtime-not-falsely-promoted"),
        (runtime.get("production_admitted") is False, "runtime-production-not-admitted"),
    ]
    failures.extend(name for ok, name in checks if not ok)

    qml = REQUIRED["qml"].read_text(encoding="utf-8")
    for label in NAVIGATION:
        if label not in qml: failures.append(f"qml-navigation-missing:{label}")
    studio_qml = REQUIRED["studio_qml"].read_text(encoding="utf-8")
    for module in ["Image", "Video", "Animation", "3D / VFX", "Audio", "Music", "Story / Screenplay", "Office", "Marketing", "Weboldal", "Prezentáció"]:
        if module not in studio_qml: failures.append(f"qml-studio-module-missing:{module}")
    for office_surface in ["Writer", "Calc", "Impress", "Preview", "Apply/UNO", "Undo"]:
        if office_surface not in studio_qml: failures.append(f"qml-office-surface-missing:{office_surface}")
    if "createDraftChangeSet" not in qml: failures.append("qml-changeset-intent-missing")
    if "id: askButton" not in qml or "id: askMenu" not in qml or "y: parent.height" not in qml: failures.append("qml-ask-menu-anchor-missing")
    if "id: modulePage" not in qml or "model: modulePage.cards" not in qml or "width: modulePage.availableWidth" not in qml: failures.append("qml-module-page-render-contract-missing")
    if "id: modelRegistryList" not in qml or "modelManagerView.availableHeight - 250" not in qml or "ScrollBar.AlwaysOn" not in qml: failures.append("qml-model-registry-responsive-scrollbar-missing")
    if "id: llmFitButton" not in qml or "property bool llmFitExpanded" not in qml or "nincs terminálindítás" not in qml: failures.append("qml-model-manager-llmfit-surface-missing")
    if "id: searchScope" not in qml or "Telepített alkalmazások" not in qml or "FA3 funkciók" not in qml or "Beállítások" not in qml or "unifiedSearchResults" not in qml: failures.append("qml-unified-search-scopes-missing")
    if "id: architectureScope" not in qml or "Canonical Core" not in qml or "Execution Fabric" not in qml or "Evidence & Release" not in qml or "architectureResults" not in qml: failures.append("qml-architecture-semantic-view-missing")
    models_qml = REQUIRED["models_providers_qml"].read_text(encoding="utf-8")
    if "id: providerList" not in models_qml or "Layout.fillHeight: true" not in models_qml or "ScrollBar.AlwaysOn" not in models_qml: failures.append("qml-models-providers-responsive-scrollbar-missing")
    settings_qml = REQUIRED["settings_qml"].read_text(encoding="utf-8")
    if "compactNavigationRequested" not in settings_qml or "statusStripRequested" not in settings_qml or "ChangeSet-tervezet" not in settings_qml or "Security & Approvals megnyitása" not in settings_qml: failures.append("qml-system-settings-interaction-missing")
    for token in ["Appearance", "Chat Style", "Reasoning", "Gyorsbillentyűk", "CPU", "GPU", "NPU", "DGX", "Webkamera", "Nyomtató", "Scanner", "MIDI", "GIMP", "Ardour", "Auto-latch onto generating message"]:
        if token not in settings_qml: failures.append(f"qml-system-settings-surface-missing:{token}")
    preference_cpp = REQUIRED["preference_store"].read_text(encoding="utf-8")
    if "QSettings" not in preference_cpp or "normalizeShortcut" not in preference_cpp or "preferenceChanged" not in preference_cpp: failures.append("settings-preference-store-missing")
    device_cpp = REQUIRED["device_model"].read_text(encoding="utf-8")
    for token in ["QPrinterInfo", "/sys/class/accel", "/dev/video", "/dev/snd", "DGX", "ADAPTER-GATED"]:
        if token not in device_cpp: failures.append(f"settings-device-discovery-missing:{token}")
    for token in ["accentForTheme", "navigationBarPosition", "Shortcut {", "fa3Preferences.setValue"]:
        if token not in qml: failures.append(f"qml-persistent-settings-shell-missing:{token}")
    if "ModelsProvidersPage" not in qml or "AiStudioPage" not in qml or "SystemSettingsPage" not in qml: failures.append("qml-dedicated-page-wiring-missing")

    rtd_qml = REQUIRED["rtd_qml"].read_text(encoding="utf-8")
    for token in ["Real-Time Data", "ADAPTER-GATED", "Freshness SLA", "Provenance", "FAIL-CLOSED", "Adapter ChangeSet-tervezet"]:
        if token not in rtd_qml: failures.append(f"qml-rtd-provider-surface-missing:{token}")
    if "RtdProvidersPage" not in qml or "RTD Data Sources" not in qml or "RTD Adapters" not in qml or '{label: "Real-Time Data", value: "RTD"}' not in qml:
        failures.append("qml-rtd-cross-surface-projection-missing")

    model_cpp = REQUIRED["model_cpp"].read_text(encoding="utf-8")
    if "DRAFT_NOT_SUBMITTED" not in model_cpp: failures.append("backend-draft-status-missing")
    if '"direct_execution_allowed", false' not in model_cpp: failures.append("backend-direct-execution-denial-missing")
    if '"canonical_write_allowed", false' not in model_cpp: failures.append("backend-canonical-write-denial-missing")
    if "searchInstalledApplications" not in model_cpp or "scanApplications" not in model_cpp or "QSettings" not in model_cpp: failures.append("backend-installed-app-search-missing")
    for token in FORBIDDEN_BACKEND_TOKENS:
        if token in model_cpp or token in device_cpp or token in preference_cpp: failures.append(f"backend-forbidden-token:{token}")

    cmake = REQUIRED["cmake"].read_text(encoding="utf-8")
    if "Qt6" not in cmake or "qt_add_qml_module" not in cmake: failures.append("qt6-qml-build-contract-missing")
    if "PrintSupport" not in cmake or "PreferenceStore.cpp" not in cmake or "SystemDeviceModel.cpp" not in cmake: failures.append("settings-device-build-wiring-missing")
    desktop = REQUIRED["desktop"].read_text(encoding="utf-8")
    if "Exec=fa3-control-center" not in desktop: failures.append("desktop-entry-exec-missing")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("FA3 GUI gate: FAIL")
        for failure in failures: print(f" - {failure}")
        return 1
    print("FA3 GUI gate: PASS")
    print("profile=FA3-DESKTOP-001 capabilities=143 new_authorities=0 runtime=PENDING_CURRENT_HOST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
