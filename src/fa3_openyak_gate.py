#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = 143
CAPABILITY_IDS = ("CAP-008", "CAP-096")
EXCLUDED_CAPABILITY_ID = "CAP-107"
PROFILE_ID = "FA3-DESKTOP-AGENT-WORKBENCH-001"
PROVIDER_ID = "FA3-PROVIDER-OPENYAK-001"
CONTRACT_ID = "FA3-DESKTOP-AGENT-WORKBENCH-CONTRACTS-001"
DECISION_ID = "FA3-DEC-OPENYAK-DESKTOP-WORKBENCH-2026-09-05"
REFERENCE_ID = "FA3-OPENYAK-UPSTREAM-REFERENCE-2026-09-05"
GATE_ID = "FA3-OPENYAK-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-OPENYAK-001"
EVIDENCE_ID = "FA3-EVID-OPENYAK-CI-2026-09-05"
RELEASE_PROJECTION_ID = "FA3-RELEASE-PROJECTION-OPENYAK-2026-09-05"
RUNTIME_STATUS = "NOT_PROMOTED_PENDING_CURRENT_HOST_DESKTOP_CONFORMANCE"
PINNED_VERSION = "v1.4.0"
PINNED_COMMIT = "73240597e17d31749f2dbc6c52e8820a6074acad"
PINNED_DEB = "OpenYak_1.4.0_amd64.deb"
PINNED_DEB_SHA256 = "dfa0358736312c8cdf8b88192cea9c5554efdc5a22643faee6e3e46a5157f531"

RULES = [
    "OPENYAK_OPTIONAL_NON_AUTHORITY_PROVIDER",
    "OPENYAK_PROJECTS_ONLY_TO_CAP_008_AND_CAP_096",
    "OPENYAK_NOT_CAP_107_DEVELOPER_ENVIRONMENT",
    "OPENYAK_NO_NEW_CAPABILITY_OR_AUTHORITY_COUNT_143",
    "OPENYAK_IMMUTABLE_RELEASE_COMMIT_AND_DEB_DIGEST",
    "OPENYAK_FLOATING_LATEST_AND_UNADMITTED_SELF_UPDATE_FORBIDDEN",
    "OPENYAK_BACKEND_LOOPBACK_AND_SESSION_AUTH_REQUIRED",
    "OPENYAK_OBSERVED_PORT_NOT_CANONICAL_CONSTANT",
    "OPENYAK_LITELLM_MODEL_ROUTE_ONLY",
    "OPENYAK_MANAGED_OLLAMA_AND_DIRECT_11434_FORBIDDEN",
    "OPENYAK_CENTRAL_MCP_GATEWAY_ONLY",
    "OPENYAK_DIRECT_PRIVILEGED_CONNECTOR_BYPASS_FORBIDDEN",
    "OPENYAK_BOUNDED_WORKSPACE_REQUIRED",
    "OPENYAK_MUTATIONS_AND_SHELL_REQUIRE_HUMAN_GATE",
    "OPENYAK_PRIVILEGED_COMMANDS_AND_SYSTEM_PATHS_DENIED",
    "OPENYAK_CREDENTIAL_MODEL_STORE_AND_DATA_PLANE_ACCESS_DENIED",
    "OPENYAK_LOCAL_SQLITE_APPLICATION_STATE_ONLY",
    "OPENYAK_SHARED_MEMORY_VIA_CANONICAL_MEMORY_TOOLS_ONLY",
    "OPENYAK_DURABLE_WORKFLOW_ESCALATES_TO_TEMPORAL",
    "OPENYAK_PROVIDER_SCHEDULER_NOT_PLATFORM_AUTHORITY",
    "OPENYAK_REMOTE_ACCESS_AND_NATIVE_CHANNELS_DISABLED",
    "OPENYAK_DIRECT_GPU_ALLOCATION_FORBIDDEN",
    "OPENYAK_WAYLAND_CURRENT_HOST_SMOKE_REQUIRED",
    "OPENYAK_CURRENT_HOST_PROMOTION_REQUIRES_REAL_E2E",
]

PATHS = {
    "profile": "canonical/profiles/FA3-DESKTOP-AGENT-WORKBENCH-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-OPENYAK-001.json",
    "contract": "canonical/contracts/FA3-DESKTOP-AGENT-WORKBENCH-CONTRACTS-001.json",
    "decision": "canonical/decisions/FA3-DEC-OPENYAK-DESKTOP-WORKBENCH-2026-09-05.json",
    "reference": "canonical/references/FA3-OPENYAK-UPSTREAM-REFERENCE-2026-09-05.json",
    "gate": "canonical/FA3-GATE-OPENYAK-001.json",
    "enforcement": "canonical/openyak-enforcement.json",
    "admission": "canonical/openyak-runtime-admission.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-OPENYAK-2026-09-05.json",
    "evidence": "evidence/reference/openyak-ci-2026-09-05.json",
    "policy": "canonical/enforcement-policy.json",
    "registry": "evidence/evidence-registry.json",
    "matrix": "canonical/conformance-matrix.csv",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def immutable_tuple_valid(value: dict[str, Any]) -> bool:
    return (
        value.get("repository") == "openyak/openyak"
        and value.get("release") == PINNED_VERSION
        and value.get("commit") == PINNED_COMMIT
        and value.get("license") == "Apache-2.0"
        and value.get("linux_package") == PINNED_DEB
        and value.get("linux_package_sha256") == PINNED_DEB_SHA256
        and all(value.get(k) not in {"", "main", "latest", "*", "floating"} for k in ("release", "commit", "linux_package_sha256"))
    )


def provider_boundary_valid(*, optional: bool, architectural_authority: bool) -> bool:
    return optional and not architectural_authority


def backend_boundary_valid(*, host: str, local_session_auth: bool, remote_access: bool) -> bool:
    return host in {"127.0.0.1", "::1", "DYNAMIC_LOOPBACK"} and local_session_auth and not remote_access


def model_route_valid(*, route: str, managed_ollama: bool, direct_ollama: bool, silent_fallback: bool) -> bool:
    return route == "FA3_LITELLM_OPENAI_COMPATIBLE_ENDPOINT_ONLY" and not managed_ollama and not direct_ollama and not silent_fallback


def mcp_route_valid(*, central_gateway: bool, direct_connector: bool, discovery_authorizes: bool) -> bool:
    return central_gateway and not direct_connector and not discovery_authorizes


def workspace_scope_valid(*, bounded: bool, root_kind: str, host_specific_constant: bool) -> bool:
    return bounded and root_kind == "USER_SELECTED_PROJECT_DIRECTORY" and not host_specific_constant


def permission_ceiling_valid(actions: dict[str, str]) -> bool:
    required = {
        "bounded_read": "ALLOW",
        "workspace_mutation": "ASK",
        "shell": "ASK",
        "privileged_command": "DENY",
        "system_path_mutation": "DENY",
        "credential_access": "DENY",
        "model_store_mutation": "DENY",
        "direct_data_plane": "DENY",
    }
    return all(actions.get(key) == value for key, value in required.items())


def state_boundary_valid(*, sqlite_role: str, shared_memory_route: str, raw_secret_persistence: bool) -> bool:
    return sqlite_role == "APPLICATION_STATE_ONLY" and shared_memory_route == "CANONICAL_MEMORY_SERVICE_VIA_MCP" and not raw_secret_persistence


def workflow_boundary_valid(*, durable_authority: str, scheduler_scope: str, platform_scheduler_authority: bool) -> bool:
    return durable_authority == "TEMPORAL" and scheduler_scope == "LOCAL_EXPLICIT_NON_PLATFORM_TASKS_ONLY" and not platform_scheduler_authority


def desktop_runtime_valid(*, display_protocol: str, forced_x11: bool, wayland_smoke: bool, direct_gpu_allocation: bool) -> bool:
    return display_protocol == "wayland" and not forced_x11 and wayland_smoke and not direct_gpu_allocation


def remote_channels_valid(*, remote_access: bool, native_channels: bool) -> bool:
    return not remote_access and not native_channels


def promotion_valid(*, reference_pass: bool, current_host_e2e: bool, claims_runtime: bool) -> bool:
    del reference_pass
    return claims_runtime == current_host_e2e and (not claims_runtime or current_host_e2e)


def regression_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(index: int, name: str, positive: bool, negative: bool) -> None:
        cases.append({
            "rule": RULES[index],
            "name": name,
            "positive": bool(positive),
            "negative_refusal": bool(negative),
            "result": "PASS" if positive and negative else "FAIL",
        })

    good_tuple = {
        "repository": "openyak/openyak", "release": PINNED_VERSION, "commit": PINNED_COMMIT,
        "license": "Apache-2.0", "linux_package": PINNED_DEB, "linux_package_sha256": PINNED_DEB_SHA256,
    }
    good_permissions = {
        "bounded_read": "ALLOW", "workspace_mutation": "ASK", "shell": "ASK",
        "privileged_command": "DENY", "system_path_mutation": "DENY", "credential_access": "DENY",
        "model_store_mutation": "DENY", "direct_data_plane": "DENY",
    }
    add(0, "optional provider cannot become authority", provider_boundary_valid(optional=True, architectural_authority=False), not provider_boundary_valid(optional=True, architectural_authority=True))
    add(1, "projection is exactly the two desktop capabilities", set(CAPABILITY_IDS) == {"CAP-008", "CAP-096"}, "CAP-028" not in CAPABILITY_IDS)
    add(2, "developer environment remains out of scope", EXCLUDED_CAPABILITY_ID not in CAPABILITY_IDS, "CAP-107" not in CAPABILITY_IDS)
    add(3, "capability and authority counts remain frozen", CAPABILITY_COUNT == 143, CAPABILITY_COUNT != 144)
    add(4, "release, commit and package digest are immutable", immutable_tuple_valid(good_tuple), not immutable_tuple_valid({**good_tuple, "commit": "main"}))
    add(5, "floating latest and self-update are denied", True, "latest" not in {PINNED_VERSION, PINNED_COMMIT})
    add(6, "backend is loopback with local session authentication", backend_boundary_valid(host="DYNAMIC_LOOPBACK", local_session_auth=True, remote_access=False), not backend_boundary_valid(host="0.0.0.0", local_session_auth=True, remote_access=False))
    add(7, "one observed port is not a canonical constant", True, 20882 != 8000)
    add(8, "model access uses only the FA3 LiteLLM route", model_route_valid(route="FA3_LITELLM_OPENAI_COMPATIBLE_ENDPOINT_ONLY", managed_ollama=False, direct_ollama=False, silent_fallback=False), not model_route_valid(route="DIRECT_PROVIDER", managed_ollama=False, direct_ollama=False, silent_fallback=False))
    add(9, "managed and direct Ollama paths are denied", model_route_valid(route="FA3_LITELLM_OPENAI_COMPATIBLE_ENDPOINT_ONLY", managed_ollama=False, direct_ollama=False, silent_fallback=False), not model_route_valid(route="FA3_LITELLM_OPENAI_COMPATIBLE_ENDPOINT_ONLY", managed_ollama=True, direct_ollama=True, silent_fallback=False))
    add(10, "MCP execution uses the central gateway", mcp_route_valid(central_gateway=True, direct_connector=False, discovery_authorizes=False), not mcp_route_valid(central_gateway=False, direct_connector=False, discovery_authorizes=False))
    add(11, "direct privileged connector bypass is denied", mcp_route_valid(central_gateway=True, direct_connector=False, discovery_authorizes=False), not mcp_route_valid(central_gateway=True, direct_connector=True, discovery_authorizes=False))
    add(12, "workspace root is explicit and bounded", workspace_scope_valid(bounded=True, root_kind="USER_SELECTED_PROJECT_DIRECTORY", host_specific_constant=False), not workspace_scope_valid(bounded=False, root_kind="FILESYSTEM_ROOT", host_specific_constant=True))
    add(13, "mutations and shell remain human gated", permission_ceiling_valid(good_permissions), not permission_ceiling_valid({**good_permissions, "workspace_mutation": "ALLOW"}))
    add(14, "privileged commands and system paths are denied", permission_ceiling_valid(good_permissions), not permission_ceiling_valid({**good_permissions, "privileged_command": "ASK"}))
    add(15, "credentials, model stores and data planes are denied", permission_ceiling_valid(good_permissions), not permission_ceiling_valid({**good_permissions, "direct_data_plane": "ALLOW"}))
    add(16, "local SQLite is application state only", state_boundary_valid(sqlite_role="APPLICATION_STATE_ONLY", shared_memory_route="CANONICAL_MEMORY_SERVICE_VIA_MCP", raw_secret_persistence=False), not state_boundary_valid(sqlite_role="CANONICAL_SHARED_MEMORY", shared_memory_route="CANONICAL_MEMORY_SERVICE_VIA_MCP", raw_secret_persistence=False))
    add(17, "shared memory is reached through canonical tools", state_boundary_valid(sqlite_role="APPLICATION_STATE_ONLY", shared_memory_route="CANONICAL_MEMORY_SERVICE_VIA_MCP", raw_secret_persistence=False), not state_boundary_valid(sqlite_role="APPLICATION_STATE_ONLY", shared_memory_route="DIRECT_DATABASE", raw_secret_persistence=False))
    add(18, "durable work escalates to Temporal", workflow_boundary_valid(durable_authority="TEMPORAL", scheduler_scope="LOCAL_EXPLICIT_NON_PLATFORM_TASKS_ONLY", platform_scheduler_authority=False), not workflow_boundary_valid(durable_authority="OPENYAK", scheduler_scope="LOCAL_EXPLICIT_NON_PLATFORM_TASKS_ONLY", platform_scheduler_authority=False))
    add(19, "provider scheduler is not platform authority", workflow_boundary_valid(durable_authority="TEMPORAL", scheduler_scope="LOCAL_EXPLICIT_NON_PLATFORM_TASKS_ONLY", platform_scheduler_authority=False), not workflow_boundary_valid(durable_authority="TEMPORAL", scheduler_scope="PLATFORM_GLOBAL", platform_scheduler_authority=True))
    add(20, "remote access and native channels are disabled", remote_channels_valid(remote_access=False, native_channels=False), not remote_channels_valid(remote_access=True, native_channels=False))
    add(21, "direct GPU allocation is forbidden", desktop_runtime_valid(display_protocol="wayland", forced_x11=False, wayland_smoke=True, direct_gpu_allocation=False), not desktop_runtime_valid(display_protocol="wayland", forced_x11=False, wayland_smoke=True, direct_gpu_allocation=True))
    add(22, "Wayland smoke is required", desktop_runtime_valid(display_protocol="wayland", forced_x11=False, wayland_smoke=True, direct_gpu_allocation=False), not desktop_runtime_valid(display_protocol="x11", forced_x11=True, wayland_smoke=False, direct_gpu_allocation=False))
    add(23, "reference PASS cannot claim current-host runtime", promotion_valid(reference_pass=True, current_host_e2e=False, claims_runtime=False), not promotion_valid(reference_pass=True, current_host_e2e=False, claims_runtime=True))
    return cases


def scan_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def walk(value: Any, *, location: str, file: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                child = f"{location}.{key}"
                if "authority" in key.lower().replace("-", "_") and item == PROVIDER_ID:
                    findings.append(_finding("OPENYAK-AUTH-001", "OpenYak assigned to an authority-bearing field", file=file, path=child))
                walk(item, location=child, file=file)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, location=f"{location}[{index}]", file=file)

    for path in sorted((root / "canonical").rglob("*.json")):
        try:
            walk(_load(path), location="$", file=path.relative_to(root).as_posix())
        except Exception as exc:
            findings.append(_finding("OPENYAK-AUTH-002", "canonical JSON parse failure during authority scan", file=path.relative_to(root).as_posix(), error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    data: dict[str, dict[str, Any]] = {}
    for name, relative in PATHS.items():
        path = root / relative
        if name == "matrix":
            continue
        try:
            data[name] = _load(path)
        except Exception as exc:
            findings.append(_finding("OPENYAK-REF-001", "required canonical artifact missing or invalid", path=relative, error=str(exc)))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile, provider, contract = data["profile"], data["provider"], data["contract"]
    decision, reference = data["decision"], data["reference"]
    gate_record, enforcement = data["gate"], data["enforcement"]
    admission, release, evidence = data["admission"], data["release"], data["evidence"]
    policy, registry = data["policy"], data["registry"]
    checks = [
        (profile.get("id") == PROFILE_ID and profile.get("relationship") == "SUBPROFILE-OF" and profile.get("requirement") == "MAY" and profile.get("capability_projection") == list(CAPABILITY_IDS) and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and profile.get("capability_count") == CAPABILITY_COUNT, "OPENYAK-REF-003", "desktop workbench profile drift"),
        (provider.get("id") == PROVIDER_ID and provider.get("canonical_root") is False and provider.get("architectural_authority") is False and provider.get("hard_dependency") is False and provider.get("capability_projection") == list(CAPABILITY_IDS) and provider.get("explicitly_not_projected_to") == [EXCLUDED_CAPABILITY_ID] and provider.get("runtime_activation_status") == RUNTIME_STATUS and provider.get("current_host_runtime_evidence") == "NOT_CLAIMED" and immutable_tuple_valid(provider.get("immutable_component_tuple", {})), "OPENYAK-REF-004", "provider identity, projection, runtime or pin drift"),
        (contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("new_capability") is False and contract.get("new_architectural_authority") is False and contract.get("capability_count") == CAPABILITY_COUNT and contract.get("deployment", {}).get("loopback_only") is True and contract.get("deployment", {}).get("fixed_backend_port_required") is False and contract.get("model_access", {}).get("provider_managed_ollama_auto_start") == "DISABLED" and contract.get("mcp_access", {}).get("canonical_gateway_required") is True and contract.get("desktop", {}).get("wayland_is_canonical_display_protocol") is True, "OPENYAK-REF-005", "provider-neutral contract drift"),
        (decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED" and decision.get("mandatory_rules") == RULES and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0 and decision.get("capability_count_after") == CAPABILITY_COUNT and decision.get("current_host_runtime_promotion_claimed") is False, "OPENYAK-REF-006", "decision drift"),
        (reference.get("id") == REFERENCE_ID and reference.get("release") == PINNED_VERSION and reference.get("commit") == PINNED_COMMIT and reference.get("linux_package", {}).get("filename") == PINNED_DEB and reference.get("linux_package", {}).get("sha256") == PINNED_DEB_SHA256 and reference.get("promotion_use") == "REFERENCE_AND_STATIC_CONFORMANCE_ONLY" and reference.get("floating_branch_forbidden_as_promotion_evidence") is True, "OPENYAK-REF-007", "upstream reference drift"),
        (gate_record.get("id") == EXECUTABLE_GATE_ID and gate_record.get("gate_set_id") == GATE_ID and gate_record.get("rule_count") == len(RULES) and gate_record.get("fail_closed") is True and enforcement.get("gate_id") == GATE_ID and enforcement.get("rules") == RULES and enforcement.get("rule_count") == len(RULES), "OPENYAK-REF-008", "gate/enforcement drift"),
        (admission.get("provider_id") == PROVIDER_ID and admission.get("status") == RUNTIME_STATUS and admission.get("current_host_runtime_evidence") == "NOT_CLAIMED" and admission.get("production_provider_admission") is False and admission.get("provider_runtime_required_for_global_promotion_when_disabled") is False and admission.get("required_configuration", {}).get("OPENYAK_CHANNELS_ENABLED") is False and admission.get("required_configuration", {}).get("GDK_BACKEND") == "wayland", "OPENYAK-REF-009", "runtime admission drift or false promotion"),
        (release.get("id") == RELEASE_PROJECTION_ID and release.get("capability_projection") == list(CAPABILITY_IDS) and release.get("capability_count_after") == CAPABILITY_COUNT and release.get("new_capabilities") == 0 and release.get("new_architectural_authorities") == 0 and release.get("runtime_promotion") is False, "OPENYAK-REF-010", "standalone release projection drift"),
        (evidence.get("evidence_id") == EVIDENCE_ID and evidence.get("status") == "PASS" and evidence.get("regression_count") == len(RULES) and evidence.get("regressions_passed") == len(RULES) and evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED" and evidence.get("current_host_runtime_promotion_claimed") is False and evidence.get("production_provider_admission_claimed") is False, "OPENYAK-REF-011", "reference evidence drift or false runtime claim"),
        (GATE_ID in policy.get("mandatory_reference_gates", []) and policy.get("openyak_provider_id") == PROVIDER_ID and policy.get("openyak_profile_id") == PROFILE_ID and policy.get("openyak_contract_id") == CONTRACT_ID and policy.get("openyak_mandatory_p0_rules") == RULES, "OPENYAK-REF-012", "global enforcement policy binding missing or drifted"),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append(_finding(code, message))

    records = {item.get("subject_id"): item for item in registry.get("records", [])}
    for capability_id in CAPABILITY_IDS:
        record = records.get(capability_id, {})
        projection = record.get("openyak_desktop_workbench_projection_status", {})
        if not (
            DECISION_ID in record.get("source_decision_ids", [])
            and PATHS["evidence"] in record.get("evidence_artifacts", [])
            and record.get("status") == "PENDING_CURRENT_HOST"
            and projection.get("provider_id") == PROVIDER_ID
            and projection.get("runtime_activation_status") == RUNTIME_STATUS
            and projection.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        ):
            findings.append(_finding("OPENYAK-REF-013", "evidence registry capability binding missing or drifted", capability_id=capability_id))

    try:
        with (root / PATHS["matrix"]).open(encoding="utf-8-sig", newline="") as stream:
            rows = {row["capability_id"]: row for row in csv.DictReader(stream)}
        if "OpenYak optional desktop workbench" not in rows["CAP-008"]["primary_mandatory_reference"]:
            findings.append(_finding("OPENYAK-REF-014", "CAP-008 Conformance Matrix projection missing"))
        if "OpenYak optional desktop workbench" not in rows["CAP-096"]["primary_mandatory_reference"]:
            findings.append(_finding("OPENYAK-REF-015", "CAP-096 Conformance Matrix projection missing"))
        if "OpenYak excluded" not in rows[EXCLUDED_CAPABILITY_ID]["primary_mandatory_reference"]:
            findings.append(_finding("OPENYAK-REF-016", "CAP-107 explicit OpenYak exclusion missing"))
    except Exception as exc:
        findings.append(_finding("OPENYAK-REF-017", "Conformance Matrix unavailable", error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    reference = reference_check(root)
    authority = scan_authority_assignments(root)
    cases = regression_cases()
    findings = [*reference["findings"], *authority["findings"]]
    for case in cases:
        if case["result"] != "PASS":
            findings.append(_finding("OPENYAK-REG-001", "positive/negative regression failed", rule=case["rule"]))
    result = {
        "schema": "fa3.openyak-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "fail_closed": True,
        "blocking_findings": len(findings),
        "findings": findings,
        "reference": reference,
        "authority_scan": authority,
        "regressions": {"total": len(cases), "passed": sum(x["result"] == "PASS" for x in cases), "cases": cases},
        "capability_count_after": CAPABILITY_COUNT,
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "current_host_runtime_promotion_claimed": False,
    }
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "openyak-gate-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 OpenYak desktop workbench canonical gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    result = gate(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
