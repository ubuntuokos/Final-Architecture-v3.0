#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "profile": ROOT / "canonical/profiles/FA3-DESKTOP-001.json",
    "contract": ROOT / "canonical/contracts/FA3-DESKTOP-CONTRACTS-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-GUI-2026-09-12.json",
    "resource_decision": ROOT / "canonical/decisions/FA3-DEC-GUI-RESOURCE-STATUS-2026-09-13.json",
    "gate": ROOT / "canonical/FA3-GATE-GUI-001.json",
    "runtime": ROOT / "canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json",
    "cmake": ROOT / "apps/fa3-control-center/CMakeLists.txt",
    "main_cpp": ROOT / "apps/fa3-control-center/src/main.cpp",
    "model_cpp": ROOT / "apps/fa3-control-center/src/Fa3RepositoryModel.cpp",
    "telemetry_cpp": ROOT / "apps/fa3-control-center/src/ResourceTelemetry.cpp",
    "telemetry_h": ROOT / "apps/fa3-control-center/src/ResourceTelemetry.h",
    "qml": ROOT / "apps/fa3-control-center/qml/Main.qml",
    "resource_strip_qml": ROOT / "apps/fa3-control-center/qml/ResourceStatusStrip.qml",
    "desktop": ROOT / "apps/fa3-control-center/packaging/org.fa3.ControlCenter.desktop",
    "installer": ROOT / "deployment/fa3-gui/install.sh",
}

NAVIGATION = ["Command Center", "Projects", "AI Studio", "Agents & Workflows", "Models & Providers", "Architecture", "Resources", "Security & Approvals", "Observability", "Evidence", "Integrations", "System"]
FORBIDDEN_BACKEND_TOKENS = ["QProcess", "std::system(", "popen(", "/bin/sh", "/bin/bash", "pkexec", "setuid("]
FORBIDDEN_TELEMETRY_TOKENS = ["std::system(", "popen(", "/bin/sh", "/bin/bash", "pkexec", "sudo ", "setuid(", "--gpu-reset", "--reset-gpu", "-pl ", "-lgc ", "-pm "]


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
    resource_decision = load_json(REQUIRED["resource_decision"])
    gate = load_json(REQUIRED["gate"])
    runtime = load_json(REQUIRED["runtime"])

    status_contract = contract.get("resource_status_contract", {})
    checks = [
        (profile.get("id") == "FA3-DESKTOP-001", "profile-id"),
        (profile.get("new_capability") is False, "profile-no-new-capability"),
        (profile.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (profile.get("capability_count") == 143, "profile-capability-count"),
        ("PERSISTENT_CPU_GPU_NPU_RAM_STATUS_STRIP" in profile.get("scope", []), "profile-resource-strip-scope"),
        (contract.get("provider_neutral") is True, "contract-provider-neutral"),
        ("HostResourceStatusStripReadProjection" in contract.get("contracts", []), "contract-resource-strip-projection"),
        (status_contract.get("visibility") == "PERSISTENT", "resource-strip-persistent"),
        (status_contract.get("placement") == "BOTTOM", "resource-strip-bottom"),
        (status_contract.get("resources") == ["CPU", "GPU", "NPU", "RAM"], "resource-strip-fields"),
        (status_contract.get("unknown_metric_semantics") == "N_A_OR_DASH_NEVER_ZERO", "unknown-metric-not-zero"),
        (status_contract.get("admission_authority") == "FA3-AUTH-HOST-RESOURCE-BROKER-001", "host-resource-broker-authority"),
        (contract.get("mutation_model", {}).get("direct_canonical_write") == "FORBIDDEN", "no-direct-canonical-write"),
        (contract.get("mutation_model", {}).get("direct_systemd_or_cgroup_mutation") == "FORBIDDEN", "no-direct-host-enforcement"),
        (contract.get("mutation_model", {}).get("sudo_su_pkexec") == "FORBIDDEN", "no-privilege-bypass"),
        (decision.get("new_capabilities") == 0, "decision-no-new-capability"),
        (decision.get("new_architectural_authorities") == 0, "decision-no-new-authority"),
        (decision.get("capability_count_after") == 143, "decision-capability-count"),
        (resource_decision.get("new_capabilities") == 0, "resource-decision-no-new-capability"),
        (resource_decision.get("new_architectural_authorities") == 0, "resource-decision-no-new-authority"),
        (resource_decision.get("resources") == ["CPU", "GPU", "NPU", "RAM"], "resource-decision-fields"),
        (gate.get("fail_closed") is True, "gate-fail-closed"),
        (gate.get("persistent_resource_strip_required") is True, "gate-resource-strip-required"),
        (runtime.get("status") == "PENDING_CURRENT_HOST", "runtime-not-falsely-promoted"),
        (runtime.get("production_admitted") is False, "runtime-production-not-admitted"),
    ]
    failures.extend(name for ok, name in checks if not ok)

    qml = REQUIRED["qml"].read_text(encoding="utf-8")
    for label in NAVIGATION:
        if label not in qml: failures.append(f"qml-navigation-missing:{label}")
    for module in ["Image", "Video", "Animation", "3D / VFX", "Audio", "Music", "Story / Screenplay"]:
        if module not in qml: failures.append(f"qml-studio-module-missing:{module}")
    if "createDraftChangeSet" not in qml: failures.append("qml-changeset-intent-missing")

    status_qml = REQUIRED["resource_strip_qml"].read_text(encoding="utf-8")
    for token in ["CPU", "GPU", "NPU", "RAM", "fa3ResourceTelemetry", "pressureState", "read-only"]:
        if token not in status_qml: failures.append(f"resource-strip-token-missing:{token}")
    if '"N/A"' not in status_qml or '"—"' not in status_qml:
        failures.append("resource-strip-unknown-semantics-missing")

    model_cpp = REQUIRED["model_cpp"].read_text(encoding="utf-8")
    if "DRAFT_NOT_SUBMITTED" not in model_cpp: failures.append("backend-draft-status-missing")
    if '"direct_execution_allowed", false' not in model_cpp: failures.append("backend-direct-execution-denial-missing")
    if '"canonical_write_allowed", false' not in model_cpp: failures.append("backend-canonical-write-denial-missing")
    for token in FORBIDDEN_BACKEND_TOKENS:
        if token in model_cpp: failures.append(f"backend-forbidden-token:{token}")

    telemetry_cpp = REQUIRED["telemetry_cpp"].read_text(encoding="utf-8")
    telemetry_h = REQUIRED["telemetry_h"].read_text(encoding="utf-8")
    if "nvidia-smi" not in telemetry_cpp: failures.append("telemetry-nvidia-read-probe-missing")
    if "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu" not in telemetry_cpp:
        failures.append("telemetry-gpu-fixed-query-missing")
    for token in FORBIDDEN_TELEMETRY_TOKENS:
        if token in telemetry_cpp: failures.append(f"telemetry-forbidden-token:{token}")
    for prop in ["cpuPercent", "ramPercent", "gpuPercent", "npuPercent", "pressureState"]:
        if prop not in telemetry_h: failures.append(f"telemetry-property-missing:{prop}")

    main_cpp = REQUIRED["main_cpp"].read_text(encoding="utf-8")
    if 'setContextProperty("fa3ResourceTelemetry"' not in main_cpp: failures.append("telemetry-context-missing")
    if "ResourceStatusStrip.qml" not in main_cpp: failures.append("resource-strip-load-missing")

    cmake = REQUIRED["cmake"].read_text(encoding="utf-8")
    if "Qt6" not in cmake or "qt_add_qml_module" not in cmake: failures.append("qt6-qml-build-contract-missing")
    for token in ["ResourceTelemetry.cpp", "ResourceTelemetry.h", "ResourceStatusStrip.qml"]:
        if token not in cmake: failures.append(f"cmake-resource-component-missing:{token}")

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
    print("profile=FA3-DESKTOP-001 capabilities=143 new_authorities=0 resource_strip=CPU,GPU,NPU,RAM runtime=PENDING_CURRENT_HOST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
