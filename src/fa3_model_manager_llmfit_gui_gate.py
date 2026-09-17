#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

GATE_ID = "FA3-GATE-MODEL-MANAGER-LLMFIT-GUI-001"
PROFILE_ID = "FA3-MODEL-MANAGER-001"
PROVIDER_ID = "FA3-PROVIDER-LLMFIT-001"
OPENMODELDB_PROVIDER_ID = "FA3-PROVIDER-OPENMODELDB-001"
DECISION_ID = "FA3-DEC-MODEL-MANAGER-LLMFIT-GUI-2026-09-13"
CAPABILITY_COUNT = module_active_capability_count(__file__)

REQUIRED_INVARIANTS = [
    "MODEL_FIT_ESTIMATE_NOT_RUNTIME_EVIDENCE",
    "LLMFIT_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY",
    "LLMFIT_NOT_MODEL_ROUTER",
    "LLMFIT_NOT_HOST_RESOURCE_BROKER",
    "LLMFIT_HARDWARE_OBSERVATION_NON_AUTHORITATIVE",
    "RAW_PROVIDER_PROBE_NEVER_ADMISSION_AUTHORITY",
    "REQUESTED_RESOURCE_CLASSES_ARE_WORKLOAD_DERIVED",
    "CPU_ONLY_WORKLOAD_DOES_NOT_REQUIRE_ACCELERATOR",
    "ACCELERATOR_WORKLOAD_REQUIRES_CURRENT_SCOPE_BOUND_HRB_ACCELERATOR_LEASE",
    "ACCELERATOR_CONFLICT_RESPECTS_FA3_ACCEL_GUARD",
    "PROVIDER_VENDOR_REQUIREMENTS_ARE_CONDITIONAL_NOT_GLOBAL",
    "GUI_IS_READ_ONLY_PLUS_TYPED_DRAFT_INTENT",
    "SAME_HOST_HEADLESS_PROVIDER_USES_UNIX_SOCKET_BY_DEFAULT",
    "RUNTIME_PROMOTION_REQUIRES_MEASURED_EVIDENCE",
]

PROFILE_EXTENSION_INVARIANTS = [
    "MODEL_FIT_ESTIMATE_NOT_RUNTIME_EVIDENCE",
    "MODEL_FIT_PROVIDER_NOT_PLACEMENT_AUTHORITY",
    "MODEL_FIT_GUI_IS_READ_ONLY_PLUS_TYPED_DRAFT_INTENT",
    "LLMFIT_HARDWARE_OBSERVATION_NON_AUTHORITATIVE",
    "REQUESTED_RESOURCE_CLASSES_ARE_WORKLOAD_DERIVED",
    "CPU_ONLY_WORKLOAD_DOES_NOT_REQUIRE_ACCELERATOR",
    "ACCELERATOR_WORKLOAD_REQUIRES_CURRENT_SCOPE_BOUND_HRB_ACCELERATOR_LEASE",
    "PROVIDER_VENDOR_REQUIREMENTS_ARE_CONDITIONAL_NOT_GLOBAL",
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def workload_draft_semantics(accelerator_required: bool) -> dict[str, Any]:
    classes = ["CPU", "MEMORY"]
    if accelerator_required:
        classes.append("ACCELERATOR")
    return {
        "requested_resource_classes": classes,
        "accelerator_required": accelerator_required,
        "hrb_authorization_required": True,
        "accelerator_discovery_required": accelerator_required,
        "accelerator_lease_required": accelerator_required,
        "accelerator_guard_required": accelerator_required,
    }


def validate_provider(provider: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if provider.get("id") != PROVIDER_ID:
        findings.append({"code": "LLMFIT-GUI-001", "message": "provider id mismatch"})
    if provider.get("parent_profile") != PROFILE_ID:
        findings.append({"code": "LLMFIT-GUI-002", "message": "provider is not attached to Model Manager"})
    if provider.get("architectural_authority") is not False:
        findings.append({"code": "LLMFIT-GUI-003", "message": "provider must not be an architectural authority"})
    if provider.get("new_capability") is not False or provider.get("capability_count") != CAPABILITY_COUNT:
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
    if policy.get("hardware_detection") != "OBSERVED_NON_AUTHORITATIVE_FIT_INPUT_ONLY":
        findings.append({"code": "LLMFIT-GUI-010", "message": "provider hardware observation became authoritative"})
    if policy.get("resource_class_derivation") != "FROM_DECLARED_WORKLOAD_REQUIREMENTS":
        findings.append({"code": "LLMFIT-GUI-011", "message": "resource classes are not workload-derived"})
    if policy.get("cpu_memory_only_workload") != "NO_ACCELERATOR_DISCOVERY_OR_ACCELERATOR_LEASE":
        findings.append({"code": "LLMFIT-GUI-012", "message": "CPU-only workload incorrectly implies accelerator"})
    if policy.get("accelerator_workload") != "CURRENT_SCOPE_BOUND_HRB_ACCELERATOR_LEASE_REQUIRED":
        findings.append({"code": "LLMFIT-GUI-013", "message": "accelerator workload is not HRB lease-bound"})
    if policy.get("accelerator_conflict") != "FA3_ACCEL_GUARD_RECOMMEND_PENDING_USER_DECISION":
        findings.append({"code": "LLMFIT-GUI-014", "message": "accelerator conflict bypasses Accelerator Guard"})
    if policy.get("generic_global_nvidia_cuda_requirement") is not False:
        findings.append({"code": "LLMFIT-GUI-015", "message": "provider redefines generic global hardware admission"})
    return findings


def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    profile = _load(root / "canonical/profiles/FA3-MODEL-MANAGER-001.json")
    provider = _load(root / "canonical/providers/FA3-PROVIDER-LLMFIT-001.json")
    decision = _load(root / "canonical/decisions/FA3-DEC-MODEL-MANAGER-LLMFIT-GUI-2026-09-13.json")
    enforcement = _load(root / "canonical/model-manager-llmfit-gui-enforcement.json")

    findings.extend(validate_provider(provider))

    providers = profile.get("providers", [])
    if profile.get("version") != "2.0.0" or PROVIDER_ID not in providers:
        findings.append({"code": "LLMFIT-GUI-020", "message": "Model Manager v2 profile does not materialize llmfit"})
    if OPENMODELDB_PROVIDER_ID not in providers:
        findings.append({"code": "LLMFIT-GUI-021", "message": "clean reconciliation dropped existing OpenModelDB provider"})
    extension = profile.get("provider_extensions", {}).get("llmfit", {})
    if extension.get("invariants") != PROFILE_EXTENSION_INVARIANTS:
        findings.append({"code": "LLMFIT-GUI-022", "message": "llmfit profile extension invariant set drift"})
    if extension.get("provider_id") != PROVIDER_ID or extension.get("gate_id") != GATE_ID:
        findings.append({"code": "LLMFIT-GUI-023", "message": "llmfit profile extension binding drift"})
    if extension.get("estimate_is_runtime_evidence") is not False:
        findings.append({"code": "LLMFIT-GUI-024", "message": "profile extension permits estimate as runtime evidence"})
    if extension.get("hardware_observation_semantics") != "OBSERVED_NON_AUTHORITATIVE":
        findings.append({"code": "LLMFIT-GUI-025", "message": "profile extension hardware observation authority drift"})

    if decision.get("id") != DECISION_ID or decision.get("status") != "CANONICAL_CLOSED":
        findings.append({"code": "LLMFIT-GUI-026", "message": "canonical decision is not closed"})
    if decision.get("new_capabilities") != 0 or decision.get("new_architectural_authorities") != 0:
        findings.append({"code": "LLMFIT-GUI-027", "message": "decision changes capability or authority baseline"})

    if enforcement.get("gate_id") != GATE_ID:
        findings.append({"code": "LLMFIT-GUI-028", "message": "enforcement gate id mismatch"})
    if enforcement.get("p0_invariants") != REQUIRED_INVARIANTS:
        findings.append({"code": "LLMFIT-GUI-029", "message": "enforcement invariant set drift"})
    if enforcement.get("mandatory_rule_count") != len(REQUIRED_INVARIANTS):
        findings.append({"code": "LLMFIT-GUI-030", "message": "enforcement mandatory rule count drift"})
    if enforcement.get("evidence_policy", {}).get("estimate_is_evidence") is not False:
        findings.append({"code": "LLMFIT-GUI-031", "message": "enforcement permits estimate as evidence"})

    cpu = workload_draft_semantics(False)
    accel = workload_draft_semantics(True)
    if cpu["accelerator_required"] or cpu["accelerator_discovery_required"] or cpu["accelerator_lease_required"]:
        findings.append({"code": "LLMFIT-GUI-032", "message": "CPU-only workload implies accelerator"})
    if "ACCELERATOR" in cpu["requested_resource_classes"]:
        findings.append({"code": "LLMFIT-GUI-033", "message": "CPU-only resource classes contain accelerator"})
    if not (accel["accelerator_required"] and accel["accelerator_lease_required"] and accel["accelerator_guard_required"]):
        findings.append({"code": "LLMFIT-GUI-034", "message": "accelerator workload is not HRB/Guard bound"})

    required_paths = [
        "apps/fa3-control-center/src/LlmfitClient.h",
        "apps/fa3-control-center/src/LlmfitClient.cpp",
        "apps/fa3-control-center/qml/ModelsProvidersPage.qml",
        "deployment/model-manager/llmfit/fa3-llmfit.service",
        "deployment/model-manager/llmfit/install.sh",
    ]
    for rel in required_paths:
        if not (root / rel).is_file():
            findings.append({"code": "LLMFIT-GUI-040", "message": f"missing materialization: {rel}"})

    cmake = (root / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
    main_cpp = (root / "apps/fa3-control-center/src/main.cpp").read_text(encoding="utf-8")
    client_cpp = (root / "apps/fa3-control-center/src/LlmfitClient.cpp").read_text(encoding="utf-8")
    qml = (root / "apps/fa3-control-center/qml/ModelsProvidersPage.qml").read_text(encoding="utf-8")
    service = (root / "deployment/model-manager/llmfit/fa3-llmfit.service").read_text(encoding="utf-8")
    installer = (root / "deployment/model-manager/llmfit/install.sh").read_text(encoding="utf-8")

    static_requirements = [
        ("Qt6::Network" in cmake and "LlmfitClient.cpp" in cmake, "LLMFIT-GUI-041", "Qt client is not linked"),
        ("setContextProperty(\"fa3Llmfit\"" in main_cpp, "LLMFIT-GUI-042", "QML context does not expose llmfit client"),
        ("QLocalSocket" in client_cpp and "/api/v1/models/top" in client_cpp, "LLMFIT-GUI-043", "client does not use local socket model-fit API"),
        ("OBSERVED_NON_AUTHORITATIVE" in client_cpp, "LLMFIT-GUI-044", "client does not label hardware observations non-authoritative"),
        ("requested_resource_classes" in client_cpp and "accelerator_lease_required" in client_cpp, "LLMFIT-GUI-045", "client does not emit workload resource envelope semantics"),
        ("Model Manager / Hardware Fit" in qml and "Benchmark ChangeSet" in qml and "Placement ChangeSet" in qml, "LLMFIT-GUI-046", "GUI Model Manager projection is incomplete"),
        ("fa3Llmfit.observationAuthority" in qml and "resourceClass.currentValue === \"ACCELERATOR\"" in qml, "LLMFIT-GUI-047", "GUI does not expose observation/workload boundaries"),
        ("--unix-socket %t/fa3/llmfit.sock" in service and "--host 0.0.0.0" not in service, "LLMFIT-GUI-048", "service transport is not local Unix socket"),
        ("RuntimeDirectoryMode=0700" in service and "UMask=0077" in service, "LLMFIT-GUI-049", "user socket runtime permissions are not hardened"),
        ("v1.1.15" in installer and "sha256sum --check" in installer, "LLMFIT-GUI-050", "installer is not release-pinned with integrity verification"),
    ]
    for ok, code, message in static_requirements:
        if not ok:
            findings.append({"code": code, "message": message})

    return {
        "schema": "fa3.model-manager-llmfit-gui-gate-report.v2",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "provider_id": PROVIDER_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "current_host_runtime_promotion_claim": False,
        "scope": "STATIC_SEMANTIC_AND_GUI_MATERIALIZATION_NOT_CURRENT_HOST_RUNTIME",
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = gate(root)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
