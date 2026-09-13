#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

GATE_ID = "FA3-GATE-MODEL-MANAGER-LLMFIT-GUI-001"
PROFILE_ID = "FA3-MODEL-MANAGER-001"
PROVIDER_ID = "FA3-PROVIDER-LLMFIT-001"
DECISION_ID = "FA3-DEC-MODEL-MANAGER-LLMFIT-GUI-2026-09-13"

REQUIRED_INVARIANTS = [
    "MODEL_FIT_ESTIMATE_NOT_RUNTIME_EVIDENCE",
    "LLMFIT_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY",
    "LLMFIT_NOT_MODEL_ROUTER",
    "LLMFIT_NOT_HOST_RESOURCE_BROKER",
    "GUI_IS_READ_ONLY_PLUS_TYPED_DRAFT_INTENT",
    "SAME_HOST_HEADLESS_PROVIDER_USES_UNIX_SOCKET_BY_DEFAULT",
    "TCP_LISTENER_NOT_REQUIRED_FOR_GUI_INTEGRATION",
    "RUNTIME_PROMOTION_REQUIRES_MEASURED_EVIDENCE",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_provider(provider: dict) -> list[dict]:
    findings: list[dict] = []
    if provider.get("id") != PROVIDER_ID:
        findings.append({"code": "LLMFIT-GUI-001", "message": "provider id mismatch"})
    if provider.get("parent_profile") != PROFILE_ID:
        findings.append({"code": "LLMFIT-GUI-002", "message": "provider is not attached to Model Manager"})
    if provider.get("architectural_authority") is not False:
        findings.append({"code": "LLMFIT-GUI-003", "message": "provider must not be an architectural authority"})
    if provider.get("new_capability") is not False or provider.get("capability_count") != 143:
        findings.append({"code": "LLMFIT-GUI-004", "message": "capability baseline changed"})

    release = str(provider.get("upstream_release", ""))
    commit = str(provider.get("upstream_release_commit", ""))
    if release.lower() in {"latest", "main", "master", "head", ""}:
        findings.append({"code": "LLMFIT-GUI-005", "message": "upstream release must be pinned"})
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        findings.append({"code": "LLMFIT-GUI-006", "message": "upstream commit must be immutable"})

    transport = provider.get("transport", {})
    if transport.get("mode") != "HTTP_OVER_UNIX_DOMAIN_SOCKET" or transport.get("tcp_listener_required") is not False:
        findings.append({"code": "LLMFIT-GUI-007", "message": "same-host GUI transport must default to Unix socket"})

    policy = provider.get("fa3_usage_policy", {})
    if policy.get("model_fit_estimate") != "ADVISORY_ONLY_NOT_RUNTIME_EVIDENCE":
        findings.append({"code": "LLMFIT-GUI-008", "message": "fit estimate cannot be runtime evidence"})
    if policy.get("accelerator_placement") != "DELEGATE_TO_HOST_RESOURCE_BROKER":
        findings.append({"code": "LLMFIT-GUI-009", "message": "placement must remain with HRB"})
    return findings


def gate(root: Path) -> dict:
    findings: list[dict] = []
    profile = _load(root / "canonical/profiles/FA3-MODEL-MANAGER-001.json")
    provider = _load(root / "canonical/providers/FA3-PROVIDER-LLMFIT-001.json")
    decision = _load(root / "canonical/decisions/FA3-DEC-MODEL-MANAGER-LLMFIT-GUI-2026-09-13.json")
    enforcement = _load(root / "canonical/model-manager-llmfit-gui-enforcement.json")

    findings.extend(validate_provider(provider))

    if profile.get("version") != "2.1.0" or PROVIDER_ID not in profile.get("providers", []):
        findings.append({"code": "LLMFIT-GUI-010", "message": "Model Manager profile does not materialize llmfit"})
    for invariant in (
        "MODEL_FIT_ESTIMATE_NOT_RUNTIME_EVIDENCE",
        "MODEL_FIT_PROVIDER_NOT_PLACEMENT_AUTHORITY",
        "MODEL_FIT_GUI_IS_READ_ONLY_PLUS_TYPED_DRAFT_INTENT",
    ):
        if invariant not in profile.get("invariants", []):
            findings.append({"code": "LLMFIT-GUI-011", "message": f"missing profile invariant: {invariant}"})

    if decision.get("id") != DECISION_ID or decision.get("status") != "CANONICAL_CLOSED":
        findings.append({"code": "LLMFIT-GUI-012", "message": "canonical decision is not closed"})
    if decision.get("new_capabilities") != 0 or decision.get("new_architectural_authorities") != 0:
        findings.append({"code": "LLMFIT-GUI-013", "message": "decision changes capability or authority baseline"})

    if enforcement.get("gate_id") != GATE_ID:
        findings.append({"code": "LLMFIT-GUI-014", "message": "enforcement gate id mismatch"})
    if enforcement.get("p0_invariants") != REQUIRED_INVARIANTS:
        findings.append({"code": "LLMFIT-GUI-015", "message": "enforcement invariant set drift"})
    if enforcement.get("evidence_policy", {}).get("estimate_is_evidence") is not False:
        findings.append({"code": "LLMFIT-GUI-016", "message": "enforcement permits estimate as evidence"})

    required_paths = [
        "apps/fa3-control-center/src/LlmfitClient.h",
        "apps/fa3-control-center/src/LlmfitClient.cpp",
        "apps/fa3-control-center/qml/Main.qml",
        "deployment/model-manager/llmfit/fa3-llmfit.service",
        "deployment/model-manager/llmfit/install.sh",
    ]
    for rel in required_paths:
        if not (root / rel).is_file():
            findings.append({"code": "LLMFIT-GUI-017", "message": f"missing materialization: {rel}"})

    cmake = (root / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
    main_cpp = (root / "apps/fa3-control-center/src/main.cpp").read_text(encoding="utf-8")
    client_cpp = (root / "apps/fa3-control-center/src/LlmfitClient.cpp").read_text(encoding="utf-8")
    qml = (root / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
    service = (root / "deployment/model-manager/llmfit/fa3-llmfit.service").read_text(encoding="utf-8")
    installer = (root / "deployment/model-manager/llmfit/install.sh").read_text(encoding="utf-8")

    static_requirements = [
        ("Qt6::Network" in cmake and "LlmfitClient.cpp" in cmake, "LLMFIT-GUI-018", "Qt client is not linked"),
        ("setContextProperty(\"llmfitClient\"" in main_cpp, "LLMFIT-GUI-019", "QML context does not expose llmfit client"),
        ("QLocalSocket" in client_cpp and "/api/v1/models/top" in client_cpp, "LLMFIT-GUI-020", "client does not use local socket model-fit API"),
        ("Model Manager" in qml and "Benchmark ChangeSet" in qml and "Placement ChangeSet" in qml, "LLMFIT-GUI-021", "GUI Model Manager projection is incomplete"),
        ("--unix-socket %t/fa3/llmfit.sock" in service and "--host 0.0.0.0" not in service, "LLMFIT-GUI-022", "service transport is not local Unix socket"),
        ("v1.1.15" in installer and "sha256sum --check" in installer, "LLMFIT-GUI-023", "installer is not release-pinned with integrity verification"),
    ]
    for ok, code, message in static_requirements:
        if not ok:
            findings.append({"code": code, "message": message})

    return {
        "schema": "fa3.model-manager-llmfit-gui-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "provider_id": PROVIDER_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "current_host_runtime_promotion_claim": False,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = gate(root)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
