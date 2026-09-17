#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HEAD = {
    144: "fb21ccf8ced686232ea56ab32420c15e848d80b4",
    150: "2776157927735d1d0867afe2e24ed7cf10a8e449",
    151: "e1fea7f45d741703d6bcd8ec7c41b200f6193b12",
    152: "f9668daa7965352f2c205e0c9730d8a71fa6aa1d",
    155: "0d981b1f1f3e8182995c03a06fc0ddde75ec6e49",
    186: "0776e41908aa5efc71a7858617fdd35180d329a4",
    187: "71c022d585e92214b6bafd7c8a24c83628c05eea",
    195: "77353056eddfc73ce7ba505d148924e3c3b67b59",
    202: "edaf9fee16300e8ec8665fdcc6089a555292d3d7",
}


def run(*args: str) -> bytes:
    return subprocess.check_output(args, cwd=ROOT)


def show(pr: int, source: str) -> bytes:
    return run("git", "show", f"{HEAD[pr]}:{source}")


def write_bytes(path: str, data: bytes) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def write_text(path: str, text: str) -> None:
    write_bytes(path, text.encode("utf-8"))


def copy_from(pr: int, source: str, dest: str | None = None) -> None:
    write_bytes(dest or source, show(pr, source))


def loadj(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def savej(path: str, obj: dict) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def append_unique(seq: list, values: list) -> None:
    for value in values:
        if value not in seq:
            seq.append(value)


def add_to_list_containing(obj, sentinel: str, value: str) -> bool:
    if isinstance(obj, dict):
        for child in obj.values():
            if add_to_list_containing(child, sentinel, value):
                return True
    elif isinstance(obj, list):
        if sentinel in obj:
            if value not in obj:
                obj.append(value)
            return True
        for child in obj:
            if add_to_list_containing(child, sentinel, value):
                return True
    return False


# ---------------------------------------------------------------------------
# 1. Materialize provider-neutral/canonical/runtime artifacts from old PRs.
#    Shared shell/projection/dispatcher files are deliberately excluded here.
# ---------------------------------------------------------------------------

for path in [
    ".github/workflows/fa3-remote-ai-exec-gate.yml",
    "canonical/FA3-GATE-REMOTE-AI-EXEC-001.json",
    "canonical/contracts/FA3-REMOTE-AI-EXEC-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-REMOTE-AI-HF-SPACES-2026-09-13.json",
    "canonical/profiles/FA3-REMOTE-AI-EXEC-001.json",
    "canonical/providers/FA3-PROVIDER-HF-SPACES-001.json",
    "evidence/reference/remote-ai-hf-spaces-ci-2026-09-13.json",
    "src/fa3_remote_ai_exec_gate.py",
    "tests/test_remote_ai_exec_gate.py",
]:
    copy_from(150, path)

for path in [
    "apps/fa3-control-center/qml/ResourceStatusStrip.qml",
    "apps/fa3-control-center/src/ResourceTelemetry.cpp",
    "apps/fa3-control-center/src/ResourceTelemetry.h",
    "canonical/decisions/FA3-DEC-GUI-RESOURCE-STATUS-2026-09-13.json",
]:
    copy_from(152, path)

for path in [
    ".github/workflows/fa3-openmodeldb-provider-gate.yml",
    "apps/fa3-control-center/src/OpenModelDbService.cpp",
    "apps/fa3-control-center/src/OpenModelDbService.h",
    "canonical/decisions/FA3-DEC-OPENMODELDB-BROWSER-DOWNLOAD-2026-09-13.json",
    "canonical/openmodeldb-browser-download-enforcement.json",
]:
    copy_from(155, path)
copy_from(155, "apps/fa3-control-center/qml/ModelsProvidersPage.qml", "apps/fa3-control-center/qml/OpenModelDbPage.qml")

for path in [
    ".github/workflows/fa3-language-gateway-current-host.yml",
    ".github/workflows/fa3-language-gateway-gate.yml",
    "bin/fa3-language-gateway-current-host.sh",
    "canonical/FA3-LANGUAGE-BRIDGE-001.json",
    "canonical/language-gateway-enforcement.json",
    "canonical/profiles/FA3-LANGUAGE-ADMISSION-001.json",
    "canonical/profiles/FA3-LANGUAGE-FABRIC-001.json",
    "canonical/profiles/FA3-LANGUAGE-POLICY-001.json",
    "canonical/profiles/FA3-LLM-GATEWAY-001.json",
    "deployment/litellm/config.yaml",
    "docs/language-fabric-and-llm-gateway.md",
    "docs/language-gateway-current-host.md",
    "evidence/collect-language-gateway-current-host.py",
    "src/fa3_canonical_language_gate.py",
    "src/fa3_language_bridge.py",
    "src/fa3_language_gateway_current_host_gate.py",
    "src/fa3_language_gateway_gate.py",
    "tests/test_canonical_language_gate.py",
    "tests/test_language_bridge.py",
    "tests/test_language_gateway_current_host_gate.py",
    "tests/test_language_gateway_gate.py",
]:
    copy_from(186, path)
copy_from(186, "apps/fa3-control-center/qml/LanguageControlPage.qml", "apps/fa3-control-center/qml/LanguagePolicyPage.qml")

for path in [
    "apps/fa3-control-center/src/LanguageInterpreterService.cpp",
    "apps/fa3-control-center/src/LanguageInterpreterService.h",
    "canonical/FA3-LANGUAGE-INTERPRETER-RUNTIME-001.json",
]:
    copy_from(187, path)
copy_from(187, "apps/fa3-control-center/qml/LanguageControlPage.qml", "apps/fa3-control-center/qml/LiveInterpreterPage.qml")

for path in [
    ".github/workflows/fa3-tools-convertx-conformance.yml",
    "apps/fa3-control-center/qml/ToolsOverlay.qml",
    "apps/fa3-control-center/qml/ToolsPage.qml",
    "bin/fa3-convertx-gate",
    "canonical/FA3-CONVERTX-CONVERSION-ALLOWLIST-001.json",
    "canonical/FA3-CONVERTX-RUNTIME-CONFORMANCE-001.json",
    "canonical/FA3-FILE-CONVERSION-001.json",
    "canonical/FA3-PROVIDER-CONVERTX-001.json",
    "canonical/FA3-TOOLS-FABRIC-001.json",
    "canonical/contracts/FA3-CONVERTX-ADAPTER-CONTRACTS-001.json",
    "docs/FA3-TOOLS-CONVERTX-INTEGRATION.md",
    "evidence/collect-convertx-current-host.py",
    "evidence/reference/fa3-convertx-reference-pending.json",
    "src/fa3_convertx_adapter.py",
    "src/fa3_convertx_gate.py",
    "src/fa3_convertx_v018_http.py",
    "tests/test_convertx_gate.py",
    "tests/test_convertx_v018_http.py",
    "tests/test_tools_fabric.py",
]:
    copy_from(195, path)

for path in [
    ".githooks/pre-commit",
    ".github/workflows/fa3-dev-update-current-host.yml",
    ".github/workflows/fa3-dev-update-gate.yml",
    "apps/fa3-control-center/qml/UpdateCenterPage.qml",
    "bin/fa3-ci-lock-check.py",
    "bin/fa3-dev",
    "bin/fa3-init-hooks.sh",
    "bin/fa3-update",
    "canonical/FA3-DEV-MODE-001.json",
    "canonical/FA3-DEV-UPDATE-RUNTIME-CONFORMANCE-001.json",
    "canonical/FA3-SECURITY-UPDATE-001.json",
    "canonical/FA3-UPDATE-FABRIC-001.json",
    "canonical/FA3-UPDATE-RESTART-001.json",
    "config/fa3-dev-policy.json",
    "config/fa3-update-policy.json",
    "docs/FA3-DEV-UPDATE-FABRIC-001.md",
    "src/fa3_dev_mode.py",
    "src/fa3_dev_update_current_host_probe.py",
    "src/fa3_dev_update_gate.py",
    "src/fa3_update_fabric.py",
    "state/.gitignore",
    "tests/test_fa3_dev_update.py",
]:
    copy_from(202, path)

for path in [
    ".github/workflows/fa3-model-manager-llmfit-gui.yml",
    "apps/fa3-control-center/src/LlmfitClient.cpp",
    "apps/fa3-control-center/src/LlmfitClient.h",
    "canonical/decisions/FA3-DEC-MODEL-MANAGER-LLMFIT-GUI-2026-09-13.json",
    "canonical/model-manager-llmfit-gui-enforcement.json",
    "canonical/providers/FA3-PROVIDER-LLMFIT-001.json",
    "deployment/model-manager/llmfit/fa3-llmfit.service",
    "deployment/model-manager/llmfit/install.sh",
    "evidence/reference/model-manager-llmfit-gui-2026-09-13.json",
    "src/fa3_model_manager_llmfit_gui_gate.py",
    "tests/test_model_manager_llmfit_gui_gate.py",
]:
    copy_from(151, path)

copy_from(144, "apps/fa3-control-center/qml/ManagerPage.qml")
copy_from(144, "apps/fa3-control-center/qml/LlmfitPanel.qml", "apps/fa3-control-center/qml/LlmfitPage.qml")

# Keep the Tools launcher above the persistent telemetry strip.
tools_overlay = (ROOT / "apps/fa3-control-center/qml/ToolsOverlay.qml").read_text(encoding="utf-8")
tools_overlay = tools_overlay.replace("anchors.bottomMargin: 18", "anchors.bottomMargin: 54")
write_text("apps/fa3-control-center/qml/ToolsOverlay.qml", tools_overlay)

# llmfit page: retain the stronger #151 client but restore the proposal-only intents.
llmfit_page = (ROOT / "apps/fa3-control-center/qml/LlmfitPage.qml").read_text(encoding="utf-8")
llmfit_page = llmfit_page.replace('Label { text: "llmfit"; font.pixelSize: 24; font.bold: true; Layout.fillWidth: true }',
                                  'Label { text: "Model Manager · llmfit"; font.pixelSize: 24; font.bold: true; Layout.fillWidth: true }')
needle = '        Label { Layout.fillWidth: true; color: root.textMuted; wrapMode: Text.WordWrap; text: "A llmfit becslése nem production evidence, nem Model Router és nem Host Resource Broker döntés." }'
proposal = '''        RowLayout {\n            Layout.fillWidth: true\n            Button {\n                text: "Benchmark ChangeSet"\n                onClicked: fa3Repository.createDraftChangeSet("MODEL_MANAGER", "BENCHMARK_MODEL", "llmfit", "DRAFT_NOT_SUBMITTED benchmark intent from advisory fit data")\n            }\n            Button {\n                text: "Placement ChangeSet"\n                onClicked: fa3Repository.createDraftChangeSet("MODEL_MANAGER", "PROPOSE_PLACEMENT", "llmfit", "DRAFT_NOT_SUBMITTED placement intent; HRB remains authority")\n            }\n            Item { Layout.fillWidth: true }\n            Label { text: "DRAFT_NOT_SUBMITTED"; color: root.textMuted; font.pixelSize: 10 }\n        }\n'''
if needle in llmfit_page:
    llmfit_page = llmfit_page.replace(needle, proposal + needle)
else:
    raise SystemExit("llmfit donor marker not found")
write_text("apps/fa3-control-center/qml/LlmfitPage.qml", llmfit_page)

# ---------------------------------------------------------------------------
# 2. Reconcile shared canonical records onto the current main, never backwards.
# ---------------------------------------------------------------------------

desktop = loadj("canonical/profiles/FA3-DESKTOP-001.json")
append_unique(desktop.setdefault("scope", []), [
    "REMOTE_AI_HUB_FEATURED_PROJECTION",
    "PERSISTENT_CPU_GPU_NPU_RAM_STATUS_STRIP",
    "RESOURCE_PRESSURE_READ_PROJECTION",
])
append_unique(desktop.setdefault("excluded_authorities", []), ["DIRECT_REMOTE_PROVIDER_BYPASS"])
runtime = desktop.setdefault("runtime", {})
runtime["direct_remote_provider_execution"] = False
runtime["persistent_resource_status_strip"] = True
runtime["resource_status_placement"] = "BOTTOM"
savej("canonical/profiles/FA3-DESKTOP-001.json", desktop)

desktop_contract = loadj("canonical/contracts/FA3-DESKTOP-CONTRACTS-001.json")
append_unique(desktop_contract.setdefault("contracts", desktop_contract.get("objects", [])), []) if False else None
# Contract-family records use named interface lists on different historical revisions.
for key in ("contract_objects", "contracts", "objects", "projection_types"):
    if isinstance(desktop_contract.get(key), list):
        append_unique(desktop_contract[key], [
            "RemoteAIExecutionReadProjection",
            "HostResourceStatusStripReadProjection",
            "ResourcePressureReadProjection",
        ])
read_model = desktop_contract.setdefault("read_model", {})
read_model["remote_ai_execution_state"] = "READ_ONLY"
desktop_contract["resource_status_contract"] = {
    "visibility": "PERSISTENT",
    "placement": "BOTTOM",
    "resources": ["CPU", "GPU", "NPU", "RAM"],
    "cpu": ["UTILIZATION"],
    "ram": ["UTILIZATION", "USED_GIB", "TOTAL_GIB"],
    "gpu": ["UTILIZATION_WHEN_MEASURABLE", "VRAM_WHEN_MEASURABLE", "TEMPERATURE_WHEN_MEASURABLE"],
    "npu": ["DETECTION", "UTILIZATION_WHEN_MEASURABLE"],
    "unknown_metric_semantics": "N_A_OR_DASH_NEVER_ZERO",
    "pressure_projection": "ADVISORY_READ_ONLY",
    "admission_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    "enforcement_authority": "SYSTEMD_UNIFIED_CGROUP_V2_ONLY",
}
mutation = desktop_contract.setdefault("mutation_model", {})
mutation["direct_remote_provider_execution"] = "FORBIDDEN"
nav = desktop_contract.get("navigation_baseline")
if isinstance(nav, list) and "Remote AI Hub" not in nav:
    try:
        nav.insert(nav.index("Command Center") + 1, "Remote AI Hub")
    except ValueError:
        nav.append("Remote AI Hub")
desktop_contract["featured_navigation"] = {
    "entry": "Remote AI Hub",
    "position": 1,
    "immediately_after": "Command Center",
    "visual_emphasis": "CORE_FEATURED",
    "provider_neutral_surface": True,
    "primary_reference_provider": "FA3-PROVIDER-HF-SPACES-001",
}
validation = desktop_contract.setdefault("validation", {})
validation.update({
    "resource_strip_visual_receipt_required": True,
    "cpu_ram_runtime_receipt_required": True,
    "gpu_runtime_receipt_required_when_gpu_present": True,
    "npu_detection_or_absence_receipt_required": True,
})
savej("canonical/contracts/FA3-DESKTOP-CONTRACTS-001.json", desktop_contract)

policy = loadj("canonical/enforcement-policy.json")
if not add_to_list_containing(policy, "FA3-EXTERNAL-API-DISCOVERY-GATESET-001", "FA3-REMOTE-AI-EXEC-GATESET-001"):
    # Do not invent a new authority surface if the expected global list changes shape.
    raise SystemExit("global enforcement gateset list not found")
savej("canonical/enforcement-policy.json", policy)

gui_gate = loadj("canonical/FA3-GATE-GUI-001.json")
gui_gate["rule_count"] = max(int(gui_gate.get("rule_count", 0)), 32)
gui_gate["persistent_resource_strip_required"] = True
gui_gate["resource_strip_fields"] = ["CPU", "GPU", "NPU", "RAM"]
gui_gate["unknown_metric_must_not_be_zero"] = True
savej("canonical/FA3-GATE-GUI-001.json", gui_gate)

gui_runtime = loadj("canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json")
gui_runtime["resource_status_strip"] = {
    "required": True,
    "placement": "BOTTOM",
    "resources": ["CPU", "GPU", "NPU", "RAM"],
    "runtime_receipt_required": True,
}
append_unique(gui_runtime.setdefault("promotion_blockers", []), [
    "CURRENT_HOST_RESOURCE_STATUS_STRIP_VISUAL_RECEIPT_MISSING",
    "CURRENT_HOST_CPU_RAM_TELEMETRY_RECEIPT_MISSING",
    "CURRENT_HOST_GPU_TELEMETRY_RECEIPT_MISSING",
    "CURRENT_HOST_NPU_DETECTION_OR_EXPLICIT_NOT_PRESENT_RECEIPT_MISSING",
])
savej("canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json", gui_runtime)

voice = loadj("canonical/profiles/FA3-VOICE-001.json")
voice["language_policy"] = {
    "authority_profile": "FA3-LANGUAGE-POLICY-001",
    "fabric_profile": "FA3-LANGUAGE-FABRIC-001",
    "native_and_bridged_support_remain_distinct": True,
    "no_globally_required_voice_language": True,
}
auth = voice.setdefault("authority_bindings", voice.setdefault("authority", {}))
auth["language_selection_and_mediation"] = "FA3-LANGUAGE-POLICY-001 and FA3-LANGUAGE-FABRIC-001"
hu = voice.setdefault("hungarian_baseline", {})
hu.update({
    "locale": "hu-HU",
    "activation": "CONDITIONAL_SELECTED_SYSTEM_LANGUAGE",
    "activation_when": "hu-HU is primary_language OR secondary_language",
    "inactive_when_not_selected": True,
})
validation = voice.setdefault("validation", {})
validation["hungarian_golden_corpus_required_when"] = "hungarian_baseline.activation is active"
savej("canonical/profiles/FA3-VOICE-001.json", voice)

model_manager = loadj("canonical/profiles/FA3-MODEL-MANAGER-001.json")
append_unique(model_manager.setdefault("providers", []), ["FA3-PROVIDER-LLMFIT-001"])
append_unique(model_manager.setdefault("scope", []), [
    "hardware-aware model fit advisory projection",
    "quantization and runtime candidate recommendation",
    "native FA3 GUI model-fit projection",
])
model_manager.setdefault("provider_roles", {})["llmfit"] = "STRONG_OPTIONAL_HARDWARE_AWARE_MODEL_FIT_AND_RUNTIME_RECOMMENDATION_PROVIDER"
model_manager["llmfit_gui_extension"] = {
    "decision_id": "FA3-DEC-MODEL-MANAGER-LLMFIT-GUI-2026-09-13",
    "provider_id": "FA3-PROVIDER-LLMFIT-001",
    "gate_id": "FA3-GATE-MODEL-MANAGER-LLMFIT-GUI-001",
    "ui_surface": "FA3_CONTROL_CENTER_OPERATIONS_MODEL_LAB",
    "service_mode": "HEADLESS_USER_SERVICE",
    "transport": "HTTP_OVER_UNIX_DOMAIN_SOCKET",
    "terminal_required": False,
    "browser_required": False,
    "estimate_is_runtime_evidence": False,
    "benchmark_and_placement_requests": "TYPED_DRAFT_CHANGESET_ONLY",
    "current_host_runtime_evidence": "PENDING",
    "invariants": [
        "MODEL_FIT_ESTIMATE_NOT_RUNTIME_EVIDENCE",
        "MODEL_FIT_PROVIDER_NOT_PLACEMENT_AUTHORITY",
        "MODEL_FIT_GUI_IS_READ_ONLY_PLUS_TYPED_DRAFT_INTENT",
        "MODEL_PLACEMENT_DERIVED_FROM_CURRENT_HOST_CAPABILITIES_NOT_FIXED_GPU_ASSUMPTIONS",
    ],
}
savej("canonical/profiles/FA3-MODEL-MANAGER-001.json", model_manager)

# ---------------------------------------------------------------------------
# 3. Reconcile dispatcher and installer without overwriting newer main logic.
# ---------------------------------------------------------------------------

enforce = (ROOT / "bin/fa3-enforce").read_text(encoding="utf-8")
root_marker = 'ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"\n'
extra_dispatch = '''\nif [[ "${1:-}" == "language-gateway-current-host" ]]; then\n  shift\n  exec python3 "$ROOT/src/fa3_language_gateway_current_host_gate.py" --root "$ROOT" "$@"\nfi\nif [[ "${1:-}" == "language-gateway" ]]; then\n  shift\n  python3 "$ROOT/src/fa3_canonical_language_gate.py" --root "$ROOT" >/dev/null\n  exec python3 "$ROOT/src/fa3_language_gateway_gate.py" --root "$ROOT" "$@"\nfi\nif [[ "${1:-}" == "dev-update" ]]; then\n  shift\n  exec env PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT/src/fa3_dev_update_gate.py" "$@"\nfi\n'''
if "language-gateway-current-host" not in enforce:
    enforce = enforce.replace(root_marker, root_marker + extra_dispatch)
static_marker = 'if [[ "${1:-}" == "static" || "${1:-}" == "promote" || "${1:-}" == "all" ]]; then\n  python3 "$ROOT/src/fa3_resource_evidence_normalization_gate.py" --root "$ROOT" >/dev/null\n'
static_extra = '  env PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT/src/fa3_dev_update_gate.py" >/dev/null\n  python3 "$ROOT/src/fa3_canonical_language_gate.py" --root "$ROOT" >/dev/null\n  python3 "$ROOT/src/fa3_language_gateway_gate.py" --root "$ROOT" >/dev/null\n'
if static_marker in enforce and "fa3_dev_update_gate.py\" >/dev/null" not in enforce:
    enforce = enforce.replace(static_marker, static_marker + static_extra)
write_text("bin/fa3-enforce", enforce)

install = (ROOT / "deployment/fa3-gui/install.sh").read_text(encoding="utf-8")
if 'LANGUAGE_QML="$APP_SRC/qml/LiveInterpreterPage.qml"' not in install:
    install = install.replace('MAIN_QML="$APP_SRC/qml/Main.qml"\n', 'MAIN_QML="$APP_SRC/qml/Main.qml"\nLANGUAGE_QML="$APP_SRC/qml/LiveInterpreterPage.qml"\n')
if "language_markers=(" not in install:
    marker = 'if grep -Fq \'Qt.openUrlExternally(quickLinkRoot.targetUrl)\' "$MAIN_QML"; then'
    live_checks = '''language_markers=(\n  'text: "Élő Tolmács"'\n  'fa3Interpreter.startLive'\n  'microphoneStatus'\n  'FA3-PROVIDER-WHISPER-001'\n  'FAIL-CLOSED'\n)\nfor marker in "${language_markers[@]}"; do\n  if ! grep -Fq "$marker" "$LANGUAGE_QML"; then\n    echo "FA3 GUI live-interpreter source-contract check FAILED: missing $marker" >&2\n    exit 3\n  fi\ndone\n\n'''
    install = install.replace(marker, live_checks + marker)
if "build-essential cmake ninja-build ffmpeg" not in install:
    install = install.replace("build-essential cmake ninja-build \\", "build-essential cmake ninja-build ffmpeg \\")
write_text("deployment/fa3-gui/install.sh", install)

# ---------------------------------------------------------------------------
# 4. Native Qt wiring: current shell + non-authoritative overlays/services.
# ---------------------------------------------------------------------------

cmake_path = ROOT / "apps/fa3-control-center/CMakeLists.txt"
cmake = cmake_path.read_text(encoding="utf-8")

new_sources = [
    "    src/ResourceTelemetry.cpp",
    "    src/ResourceTelemetry.h",
    "    src/OpenModelDbService.cpp",
    "    src/OpenModelDbService.h",
    "    src/LlmfitClient.cpp",
    "    src/LlmfitClient.h",
    "    src/LanguageInterpreterService.cpp",
    "    src/LanguageInterpreterService.h",
]
exe_start = cmake.index("qt_add_executable(fa3-control-center")
exe_end = cmake.index("\n)", exe_start)
for line in new_sources:
    if line.strip() not in cmake[exe_start:exe_end]:
        cmake = cmake[:exe_end] + "\n" + line + cmake[exe_end:]
        exe_end += len(line) + 1

qml_files = [
    "ResourceStatusStrip.qml",
    "ToolsOverlay.qml",
    "ToolsPage.qml",
    "OperationsExtensionsOverlay.qml",
    "ManagerPage.qml",
    "OpenModelDbPage.qml",
    "LlmfitPage.qml",
    "UpdateCenterPage.qml",
    "LiveInterpreterPage.qml",
    "LanguagePolicyPage.qml",
]
module_start = cmake.index("qt_add_qml_module(fa3-control-center")
module_end = cmake.index("\n)", module_start)
for name in qml_files:
    alias = f"set_source_files_properties(qml/{name} PROPERTIES QT_RESOURCE_ALIAS {name})"
    if alias not in cmake:
        cmake = cmake[:module_start] + alias + "\n" + cmake[module_start:]
        module_start += len(alias) + 1
        module_end += len(alias) + 1
    qml_line = f"        qml/{name}"
    if qml_line not in cmake[module_start:module_end]:
        cmake = cmake[:module_end] + "\n" + qml_line + cmake[module_end:]
        module_end += len(qml_line) + 1

# Network is already part of current 0.3, but keep the guard explicit.
if "Qt6::Network" not in cmake:
    raise SystemExit("current CMake unexpectedly lacks Qt6::Network")
write_text("apps/fa3-control-center/CMakeLists.txt", cmake)

main_path = ROOT / "apps/fa3-control-center/src/main.cpp"
main_cpp = main_path.read_text(encoding="utf-8")
for include in [
    '#include "ResourceTelemetry.h"',
    '#include "OpenModelDbService.h"',
    '#include "LlmfitClient.h"',
    '#include "LanguageInterpreterService.h"',
]:
    if include not in main_cpp:
        first_include_end = main_cpp.index("\n", main_cpp.index("#include")) + 1
        main_cpp = main_cpp[:first_include_end] + include + "\n" + main_cpp[first_include_end:]

for include in ["#include <QQmlComponent>", "#include <QQuickItem>", "#include <QQuickWindow>"]:
    if include not in main_cpp:
        marker = "#include <QQmlContext>\n"
        if marker not in main_cpp:
            raise SystemExit("QQmlContext include marker missing")
        main_cpp = main_cpp.replace(marker, marker + include + "\n")

instance_marker = "    AppCatalogService appCatalog;\n"
if "ResourceTelemetry resourceTelemetry;" not in main_cpp:
    instances = '''    ResourceTelemetry resourceTelemetry;\n    OpenModelDbService openModelDb;\n    LlmfitClient llmfitClient;\n    LanguageInterpreterService interpreter;\n'''
    if instance_marker not in main_cpp:
        raise SystemExit("AppCatalogService instance marker missing")
    main_cpp = main_cpp.replace(instance_marker, instance_marker + instances)

context_marker = '    engine.rootContext()->setContextProperty("fa3AppCatalog", &appCatalog);\n'
if 'setContextProperty("fa3ResourceTelemetry"' not in main_cpp:
    contexts = '''    engine.rootContext()->setContextProperty("fa3ResourceTelemetry", &resourceTelemetry);\n    engine.rootContext()->setContextProperty("fa3OpenModelDb", &openModelDb);\n    engine.rootContext()->setContextProperty("llmfitClient", &llmfitClient);\n    engine.rootContext()->setContextProperty("fa3Interpreter", &interpreter);\n'''
    if context_marker not in main_cpp:
        raise SystemExit("fa3AppCatalog context marker missing")
    main_cpp = main_cpp.replace(context_marker, context_marker + contexts)

return_marker = "    return app.exec();\n"
if "attachOverlay" not in main_cpp:
    overlay_code = '''    auto *window = qobject_cast<QQuickWindow *>(engine.rootObjects().constFirst());\n    if (!window) {\n        return 3;\n    }\n\n    auto attachOverlay = [&](const QString &qmlFile) -> bool {\n        QQmlComponent component(\n            &engine,\n            QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/") + qmlFile));\n        if (component.status() != QQmlComponent::Ready) {\n            return false;\n        }\n        QObject *object = component.create(engine.rootContext());\n        auto *item = qobject_cast<QQuickItem *>(object);\n        if (!item) {\n            delete object;\n            return false;\n        }\n        item->setParent(window->contentItem());\n        item->setParentItem(window->contentItem());\n        return true;\n    };\n\n    if (!attachOverlay(QStringLiteral("ResourceStatusStrip.qml"))) {\n        return 4;\n    }\n    if (!attachOverlay(QStringLiteral("ToolsOverlay.qml"))) {\n        return 5;\n    }\n    if (!attachOverlay(QStringLiteral("OperationsExtensionsOverlay.qml"))) {\n        return 6;\n    }\n\n'''
    if return_marker not in main_cpp:
        raise SystemExit("main return marker missing")
    main_cpp = main_cpp.replace(return_marker, overlay_code + return_marker)
write_text("apps/fa3-control-center/src/main.cpp", main_cpp)

# ---------------------------------------------------------------------------
# 5. Reconciled QML wrappers. Existing Main.qml remains current-main owned.
# ---------------------------------------------------------------------------

language_wrapper = r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var preferences
    required property color panel
    required property color panelRaised
    required property color border
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property color green
    required property color orange

    // Keep mandatory system-language policy visible to the language gate while
    // the primary Tolmács surface is the live interpreter workspace.
    property string primaryLanguage: String(preferences.value("languagePolicy/primaryLanguage", ""))
    property string secondaryLanguage: String(preferences.value("languagePolicy/secondaryLanguage", ""))
    readonly property bool systemLanguageValid: primaryLanguage.length > 0
                                                && secondaryLanguage.length > 0
                                                && primaryLanguage !== secondaryLanguage
    function setPrimaryLanguage(value) {
        if (value.length > 0 && value !== secondaryLanguage) {
            primaryLanguage = value
            preferences.setValue("languagePolicy/primaryLanguage", value)
        }
    }
    function setSecondaryLanguage(value) {
        if (value.length > 0 && value !== primaryLanguage) {
            secondaryLanguage = value
            preferences.setValue("languagePolicy/secondaryLanguage", value)
        }
    }

    readonly property string truthBoundary: "ADAPTER-GATED · PENDING_BACKEND · SECRET egress denied · translation is a derived projection"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "Élő Tolmács" }
            TabButton { text: "Nyelvi policy" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            LiveInterpreterPage {
                preferences: root.preferences
                panel: root.panel
                panelRaised: root.panelRaised
                border: root.border
                textPrimary: root.textPrimary
                textMuted: root.textMuted
                accent: root.accent
                green: root.green
                orange: root.orange
            }

            LanguagePolicyPage {
                preferences: root.preferences
                panel: root.panel
                panelRaised: root.panelRaised
                border: root.border
                textPrimary: root.textPrimary
                textMuted: root.textMuted
                accent: root.accent
                green: root.green
                orange: root.orange
            }
        }
    }
}
'''
write_text("apps/fa3-control-center/qml/LanguageControlPage.qml", language_wrapper)

operations_overlay = r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: root
    anchors.fill: parent
    z: 990

    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color cyan: "#22d3ee"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    ToolButton {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 136
        anchors.bottomMargin: 54
        width: 126
        height: 38
        text: "◈  Operations"
        z: 2
        ToolTip.visible: hovered
        ToolTip.text: "Manager · Model Lab · Update Center · Ctrl+Shift+O"
        onClicked: drawer.open()
        contentItem: Label {
            text: parent.text
            color: root.textPrimary
            font.pixelSize: 10
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 8
            color: parent.hovered ? "#16334f" : "#102a43"
            border.color: root.cyan
        }
    }

    Shortcut {
        sequence: "Ctrl+Shift+O"
        context: Qt.ApplicationShortcut
        onActivated: drawer.open()
    }

    Drawer {
        id: drawer
        parent: Overlay.overlay
        edge: Qt.RightEdge
        modal: true
        interactive: true
        width: Math.min(root.width * 0.84, 1320)
        height: root.height
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: "#07111f"; border.color: root.border }

        contentItem: ColumnLayout {
            anchors.fill: parent
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                Layout.leftMargin: 14
                Layout.rightMargin: 10
                Label { text: "FA3 Operations Extensions"; color: root.textPrimary; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }
                Label { text: "projection only · authority delta 0"; color: root.textMuted; font.pixelSize: 9 }
                ToolButton { text: "×"; onClicked: drawer.close() }
            }

            TabBar {
                id: modeTabs
                Layout.fillWidth: true
                TabButton { text: "Manager" }
                TabButton { text: "Model Lab" }
                TabButton { text: "Update Center" }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: modeTabs.currentIndex

                ManagerPage {
                    repository: fa3Repository
                    surface1: root.panel
                    textPrimary: root.textPrimary
                    textMuted: root.textMuted
                    accent: root.accent
                    uiScale: 1.0
                    fontScale: 1.0
                    language: "hu"
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0
                        TabBar {
                            id: modelTabs
                            Layout.fillWidth: true
                            TabButton { text: "OpenModelDB" }
                            TabButton { text: "llmfit" }
                        }
                        StackLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            currentIndex: modelTabs.currentIndex
                            OpenModelDbPage {
                                surface0: "#07111f"
                                surface1: root.panel
                                surface2: root.panelRaised
                                accent: root.accent
                                textPrimary: root.textPrimary
                                textMuted: root.textMuted
                            }
                            LlmfitPage {
                                client: llmfitClient
                                textMuted: root.textMuted
                                accent: root.accent
                                surface1: root.panel
                            }
                        }
                    }
                }

                UpdateCenterPage {
                    panel: root.panel
                    panelRaised: root.panelRaised
                    border: root.border
                    textPrimary: root.textPrimary
                    textMuted: root.textMuted
                    accent: root.accent
                    green: root.green
                    orange: root.orange
                    magenta: root.magenta
                    onCheckRequested: fa3Repository.createDraftChangeSet("UPDATE_FABRIC", "CHECK_ALL", "ALL", "DRAFT_NOT_SUBMITTED update discovery intent")
                    onUpdateSelectedRequested: function(componentIds) { fa3Repository.createDraftChangeSet("UPDATE_FABRIC", "UPDATE_SELECTED", componentIds.join(","), "DRAFT_NOT_SUBMITTED selected update intent") }
                    onSecurityUpdateRequested: fa3Repository.createDraftChangeSet("UPDATE_FABRIC", "SECURITY_UPDATE", "RECOMMENDED", "DRAFT_NOT_SUBMITTED security update intent")
                    onRestartChoiceRequested: function(choice, schedule) { fa3Repository.createDraftChangeSet("UPDATE_RESTART", choice, schedule, "DRAFT_NOT_SUBMITTED restart intent; protected workloads remain authoritative blockers") }
                }
            }
        }
    }
}
'''
write_text("apps/fa3-control-center/qml/OperationsExtensionsOverlay.qml", operations_overlay)

# ---------------------------------------------------------------------------
# 6. Adapt old feature gates/tests to the reconciled wiring, not LegacyMain.
# ---------------------------------------------------------------------------

llm_gate_path = ROOT / "src/fa3_model_manager_llmfit_gui_gate.py"
llm_gate = llm_gate_path.read_text(encoding="utf-8")
llm_gate = llm_gate.replace('"apps/fa3-control-center/qml/Main.qml",', '"apps/fa3-control-center/qml/LlmfitPage.qml",')
llm_gate = llm_gate.replace('(root / "apps/fa3-control-center/qml/Main.qml").read_text', '(root / "apps/fa3-control-center/qml/LlmfitPage.qml").read_text')
write_text("src/fa3_model_manager_llmfit_gui_gate.py", llm_gate)

openmodel_test = r'''from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OpenModelDbBrowserDownloadTests(unittest.TestCase):
    def load_json(self, rel: str) -> dict:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_canonical_overlay_preserves_authority_boundaries(self) -> None:
        policy = self.load_json("canonical/openmodeldb-browser-download-enforcement.json")
        decision = self.load_json("canonical/decisions/FA3-DEC-OPENMODELDB-BROWSER-DOWNLOAD-2026-09-13.json")
        self.assertEqual(policy["provider_id"], "FA3-PROVIDER-OPENMODELDB-001")
        self.assertEqual(policy["parent_profile_id"], "FA3-MODEL-MANAGER-001")
        self.assertFalse(policy["architectural_authority"])
        self.assertEqual(policy["new_capabilities"], 0)
        self.assertEqual(policy["capability_count_after"], 143)
        self.assertEqual(decision["status"], "CANONICAL_CLOSED")
        self.assertFalse(decision["runtime_promotion_claim"])

    def test_download_pipeline_is_staged_and_fail_closed(self) -> None:
        policy = self.load_json("canonical/openmodeldb-browser-download-enforcement.json")
        pipeline = policy["download_pipeline"]
        self.assertEqual(pipeline["parallelism"], 1)
        self.assertTrue(pipeline["https_only"])
        self.assertTrue(pipeline["sha256_required_before_transport"])
        self.assertEqual(pipeline["runtime_directory_write"], "FORBIDDEN")

    def test_reconciled_gui_and_service_wiring(self) -> None:
        qml = (ROOT / "apps/fa3-control-center/qml/OpenModelDbPage.qml").read_text(encoding="utf-8")
        service = (ROOT / "apps/fa3-control-center/src/OpenModelDbService.cpp").read_text(encoding="utf-8")
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
        main_cpp = (ROOT / "apps/fa3-control-center/src/main.cpp").read_text(encoding="utf-8")
        overlay = (ROOT / "apps/fa3-control-center/qml/OperationsExtensionsOverlay.qml").read_text(encoding="utf-8")
        self.assertIn('text: "Hugging Face ↗"', qml)
        self.assertIn('text: "★ OpenModelDB ↗"', qml)
        self.assertIn("highlighted: true", qml)
        self.assertIn("Download manager", qml)
        self.assertIn("https://www.openmodeldb.info/api/v1/models", service)
        self.assertIn("QCryptographicHash::Sha256", service)
        self.assertIn("OpenModelDbService.cpp", cmake)
        self.assertIn("OpenModelDbPage.qml", cmake)
        self.assertIn('setContextProperty("fa3OpenModelDb"', main_cpp)
        self.assertIn("OpenModelDbPage", overlay)


if __name__ == "__main__":
    unittest.main()
'''
write_text("tests/test_openmodeldb_browser_download_manager.py", openmodel_test)

reconciliation_test = r'''from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GuiModelManagerReconciliationTests(unittest.TestCase):
    def text(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def data(self, path: str) -> dict:
        return json.loads(self.text(path))

    def test_current_main_shell_is_extended_not_replaced(self) -> None:
        main = self.text("apps/fa3-control-center/qml/Main.qml")
        self.assertIn("Remote AI Hub", main)
        self.assertIn("Models & Providers", main)
        self.assertIn("Model Manager", main)
        self.assertIn("Tolmács", main)
        self.assertNotIn("LegacyMain {", main)

    def test_resource_status_is_real_overlay(self) -> None:
        main_cpp = self.text("apps/fa3-control-center/src/main.cpp")
        qml = self.text("apps/fa3-control-center/qml/ResourceStatusStrip.qml")
        self.assertIn('setContextProperty("fa3ResourceTelemetry"', main_cpp)
        self.assertIn('attachOverlay(QStringLiteral("ResourceStatusStrip.qml"))', main_cpp)
        for token in ["cpuPercent", "gpuPercent", "npuAvailable", "ramPercent", "pressureState"]:
            self.assertIn(token, qml)

    def test_language_policy_and_live_interpreter_are_both_materialized(self) -> None:
        wrapper = self.text("apps/fa3-control-center/qml/LanguageControlPage.qml")
        live = self.text("apps/fa3-control-center/qml/LiveInterpreterPage.qml")
        policy = self.text("apps/fa3-control-center/qml/LanguagePolicyPage.qml")
        main_cpp = self.text("apps/fa3-control-center/src/main.cpp")
        self.assertIn("primaryLanguage !== secondaryLanguage", wrapper)
        self.assertIn("LiveInterpreterPage", wrapper)
        self.assertIn("LanguagePolicyPage", wrapper)
        self.assertIn("fa3Interpreter.startLive", live)
        self.assertIn("FA3-PROVIDER-WHISPER-001", live)
        self.assertIn("property string primaryLanguage", policy)
        self.assertIn('setContextProperty("fa3Interpreter"', main_cpp)

    def test_tools_update_manager_and_model_lab_are_projection_only(self) -> None:
        main_cpp = self.text("apps/fa3-control-center/src/main.cpp")
        overlay = self.text("apps/fa3-control-center/qml/OperationsExtensionsOverlay.qml")
        tools = self.text("apps/fa3-control-center/qml/ToolsOverlay.qml")
        self.assertIn('attachOverlay(QStringLiteral("ToolsOverlay.qml"))', main_cpp)
        self.assertIn('attachOverlay(QStringLiteral("OperationsExtensionsOverlay.qml"))', main_cpp)
        for token in ["ManagerPage", "OpenModelDbPage", "LlmfitPage", "UpdateCenterPage", "DRAFT_NOT_SUBMITTED"]:
            self.assertIn(token, overlay)
        self.assertIn("FA3 Tools", tools)

    def test_llmfit_remains_advisory_and_hrb_owned(self) -> None:
        profile = self.data("canonical/profiles/FA3-MODEL-MANAGER-001.json")
        provider = self.data("canonical/providers/FA3-PROVIDER-LLMFIT-001.json")
        self.assertIn("FA3-PROVIDER-LLMFIT-001", profile["providers"])
        self.assertFalse(profile["llmfit_gui_extension"]["estimate_is_runtime_evidence"])
        self.assertFalse(provider["architectural_authority"])
        self.assertEqual(provider["fa3_usage_policy"]["accelerator_placement"], "DELEGATE_TO_HOST_RESOURCE_BROKER")

    def test_capability_and_authority_baseline_is_unchanged(self) -> None:
        for path in [
            "canonical/profiles/FA3-REMOTE-AI-EXEC-001.json",
            "canonical/providers/FA3-PROVIDER-LLMFIT-001.json",
            "canonical/FA3-TOOLS-FABRIC-001.json",
        ]:
            data = self.data(path)
            serialized = json.dumps(data)
            self.assertIn("143", serialized)
        self.assertFalse(self.data("canonical/providers/FA3-PROVIDER-LLMFIT-001.json")["architectural_authority"])


if __name__ == "__main__":
    unittest.main()
'''
write_text("tests/test_gui_model_manager_reconciliation_2026_09_17.py", reconciliation_test)

print("FA3 GUI/Model Manager semantic reconciliation materialized.")
