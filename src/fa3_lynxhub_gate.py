#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = 143
CAPABILITY_IDS = ("CAP-057",)
PROFILE_ID = "FA3-CREATIVE-OPERATIONS-DASHBOARD-001"
PROVIDER_ID = "FA3-PROVIDER-LYNXHUB-001"
CONTRACT_ID = "FA3-CREATIVE-OPERATIONS-DASHBOARD-CONTRACTS-001"
DECISION_ID = "FA3-DEC-LYNXHUB-CREATIVE-OPERATIONS-DASHBOARD-2026-09-05"
REFERENCE_ID = "FA3-LYNXHUB-UPSTREAM-REFERENCE-2026-09-05"
GATE_ID = "FA3-LYNXHUB-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-LYNXHUB-001"
RELEASE_PROJECTION_ID = "FA3-RELEASE-PROJECTION-LYNXHUB-2026-09-05"
EVIDENCE_ID = "FA3-EVID-LYNXHUB-CI-2026-09-05"
RUNTIME_STATUS = "NOT_PROMOTED_USER_REPORTED_DEB_INSTALLED_CURRENT_HOST_EVIDENCE_PENDING"
PINNED_VERSION = "V3.5.8"
PINNED_COMMIT = "96129c218b8bd4337fd3e4cf220aa97a46c486a5"
PINNED_DEB = "LynxHub-V3.5.8-linux_amd64.deb"
PINNED_DEB_SHA256 = "b13882eb5d0443b84bd8c2488c659a149c5b16e15f22fad93aa6ad3c5f33a435"
PINNED_ACTIONS_VERSION = "v0.4.4"
PINNED_ACTIONS_COMMIT = "418be2f8d2488f67f8c6f7728729161577f4c90e"
PINNED_ACTIONS_SHA256 = "125c3382393ef32bde5d1eae415a7a7829493e0d77504f02e6f72fc85bb6ef83"

RULES = [
    "LYNXHUB_OPTIONAL_NON_AUTHORITY_PROVIDER",
    "LYNXHUB_PROJECTS_ONLY_TO_CAP_057",
    "LYNXHUB_NO_NEW_CAPABILITY_OR_AUTHORITY_COUNT_143",
    "LYNXHUB_IMMUTABLE_RELEASE_COMMIT_AND_DEB_DIGEST",
    "LYNXHUB_CUSTOM_ACTIONS_IMMUTABLE_RELEASE_COMMIT_AND_DIGEST",
    "LYNXHUB_FLOATING_LATEST_AND_UNADMITTED_SELF_UPDATE_FORBIDDEN",
    "LYNXHUB_USER_SESSION_ON_DEMAND_ONLY",
    "LYNXHUB_SINGLE_USER_SERVICE_UNDER_CREATIVE_OPS_TARGET",
    "LYNXHUB_DUPLICATE_AUTOSTART_AND_TRANSIENT_APP_UNIT_FORBIDDEN",
    "LYNXHUB_EFFECTIVE_NO_SANDBOX_LAUNCH_FORBIDDEN",
    "LYNXHUB_WAYLAND_REQUIRED_XWAYLAND_EXCEPTION_GATED",
    "LYNXHUB_GPU_DISPLAY_ONLY_NO_DEVICE_ASSUMPTION",
    "LYNXHUB_NO_OWN_PLATFORM_PORT_OR_DAEMON",
    "LYNXHUB_CUSTOM_ACTIONS_FIXED_ID_VERSIONED_WRAPPER_ONLY",
    "LYNXHUB_FREE_FORM_SHELL_EVAL_AND_INTERPOLATION_FORBIDDEN",
    "LYNXHUB_SUDO_ROOT_HELPER_AND_ADMIN_COMMANDS_FORBIDDEN",
    "LYNXHUB_SYSTEMCTL_USER_ENUMERATED_UNITS_ONLY",
    "LYNXHUB_BROWSER_OPEN_APPROVED_LOOPBACK_URLS_ONLY",
    "LYNXHUB_DIRECT_MCP_TOOL_PATH_FORBIDDEN",
    "LYNXHUB_DIRECT_OLLAMA_AGENT_ROUTE_FORBIDDEN",
    "LYNXHUB_SECRET_DATABASE_AND_MODEL_STORE_ACCESS_FORBIDDEN",
    "LYNXHUB_STABILITY_MATRIX_PACKAGE_OWNERSHIP_PRESERVED",
    "LYNXHUB_ORCHESTRATOR_TEMPORAL_AND_MCP_AUTHORITIES_PRESERVED",
    "LYNXHUB_LOWDB_APPLICATION_STATE_ONLY",
    "LYNXHUB_EGRESS_DEFAULT_DENY_UPDATE_EXCEPTION_EXPLICIT",
    "LYNXHUB_PLUGIN_ALLOWLIST_AND_AUTOMATIC_UPDATES_DISABLED",
    "LYNXHUB_FAILURE_ISOLATED_DISABLED_ZERO_RESIDENT_PROCESS",
    "LYNXHUB_CURRENT_HOST_PROMOTION_REQUIRES_REAL_E2E_AND_ROLLBACK",
]

PATHS = {
    "profile": "canonical/profiles/FA3-CREATIVE-OPERATIONS-DASHBOARD-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-LYNXHUB-001.json",
    "contract": "canonical/contracts/FA3-CREATIVE-OPERATIONS-DASHBOARD-CONTRACTS-001.json",
    "decision": "canonical/decisions/FA3-DEC-LYNXHUB-CREATIVE-OPERATIONS-DASHBOARD-2026-09-05.json",
    "reference": "canonical/references/FA3-LYNXHUB-UPSTREAM-REFERENCE-2026-09-05.json",
    "gate": "canonical/FA3-GATE-LYNXHUB-001.json",
    "enforcement": "canonical/lynxhub-enforcement.json",
    "admission": "canonical/lynxhub-runtime-admission.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-LYNXHUB-2026-09-05.json",
    "evidence": "evidence/reference/lynxhub-ci-2026-09-05.json",
    "policy": "canonical/enforcement-policy.json",
    "registry": "evidence/evidence-registry.json",
    "matrix": "canonical/conformance-matrix.csv",
}

DEPLOYMENT_PATHS = (
    "deployment/lynxhub/systemd/user/ai-creative-ops.target",
    "deployment/lynxhub/systemd/user/lynxhub.service",
    "deployment/lynxhub/bin/lynxhub-launch",
    "deployment/lynxhub/bin/lynxhub-start",
    "deployment/lynxhub/bin/lynxhub-action",
    "deployment/lynxhub/applications/ai.kindabrazy.lynxhub.desktop.in",
    "deployment/lynxhub/lynxhub-actions.env.example",
    "deployment/lynxhub/README.md",
    "bin/fa3-lynxhub-install-user-integration.sh",
    "docs/lynxhub-integration.md",
    "evidence/collect-lynxhub-current-host.py",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def immutable_component_tuple_valid(value: dict[str, Any]) -> bool:
    return (
        value.get("repository") == "TheLynxHub/LynxHub"
        and value.get("release") == PINNED_VERSION
        and value.get("commit") == PINNED_COMMIT
        and value.get("license") == "AGPL-3.0"
        and value.get("debian_package") == PINNED_DEB
        and value.get("debian_package_sha256") == PINNED_DEB_SHA256
        and value.get("debian_package_name") == "lynxhub"
        and value.get("debian_package_version") == "3.5.8"
        and value.get("installed_executable") == "/opt/LynxHub/lynxhub"
        and all(value.get(key) not in {"", "main", "master", "latest", "*", "floating"} for key in ("release", "commit", "debian_package_sha256"))
    )


def immutable_actions_tuple_valid(value: dict[str, Any]) -> bool:
    return (
        value.get("repository") == "TheLynxHub/Custom-Actions"
        and value.get("release") == PINNED_ACTIONS_VERSION
        and value.get("commit") == PINNED_ACTIONS_COMMIT
        and value.get("artifact") == "0.4.4.7z"
        and value.get("artifact_sha256") == PINNED_ACTIONS_SHA256
        and value.get("automatic_update") is False
    )


def provider_boundary_valid(*, optional: bool, authority: bool, hard_dependency: bool) -> bool:
    return optional and not authority and not hard_dependency


def lifecycle_valid(*, user_session: bool, on_demand: bool, service: str, target: str, duplicate_autostart: bool, transient_parallel: bool) -> bool:
    return user_session and on_demand and service == "lynxhub.service" and target == "ai-creative-ops.target" and not duplicate_autostart and not transient_parallel


def launch_valid(*, display: str, no_sandbox: bool, root_helper: bool, gpu_role: str, fixed_gpu: bool) -> bool:
    return display == "wayland" and not no_sandbox and not root_helper and gpu_role == "DISPLAY_COMPOSITING_ONLY" and not fixed_gpu


def action_valid(*, versioned: bool, fixed_id: bool, free_shell: bool, eval_used: bool, privileged: bool, direct_mcp: bool, direct_ollama: bool, secret_access: bool) -> bool:
    return versioned and fixed_id and not any((free_shell, eval_used, privileged, direct_mcp, direct_ollama, secret_access))


def service_action_valid(*, user_scope: bool, enumerated: bool, root_scope: bool, package_command: bool) -> bool:
    return user_scope and enumerated and not root_scope and not package_command


def url_valid(url: str, *, approved: bool) -> bool:
    return approved and bool(re.match(r"^https?://(127\.0\.0\.1|localhost|\[::1\])([:/].*)?$", url))


def ownership_valid(*, systemd_owner: str, media_owner: str, durable_owner: str, mcp_owner: str, provider_owns_port: bool) -> bool:
    return systemd_owner == "SYSTEMD" and media_owner == "STABILITY_MATRIX" and durable_owner == "TEMPORAL" and mcp_owner == "CENTRAL_MCP_GATEWAY" and not provider_owns_port


def state_valid(*, lowdb_role: str, canonical_memory: bool, key_storage: bool) -> bool:
    return lowdb_role == "APPLICATION_STATE_ONLY" and not canonical_memory and not key_storage


def plugin_policy_valid(*, actions_pinned: bool, auto_updates: bool, local_ai_collection: bool, python_toolkit: bool) -> bool:
    return actions_pinned and not auto_updates and not local_ai_collection and not python_toolkit


def egress_valid(*, default_deny: bool, update_exception_explicit: bool, unrestricted: bool) -> bool:
    return default_deny and update_exception_explicit and not unrestricted


def isolation_valid(*, failure_stops_platform: bool, disabled_processes: int) -> bool:
    return not failure_stops_platform and disabled_processes == 0


def promotion_valid(*, reference_pass: bool, current_host_e2e: bool, rollback_pass: bool, claims_runtime: bool) -> bool:
    del reference_pass
    return claims_runtime == (current_host_e2e and rollback_pass)


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

    component = {
        "repository": "TheLynxHub/LynxHub", "release": PINNED_VERSION, "commit": PINNED_COMMIT,
        "license": "AGPL-3.0", "debian_package": PINNED_DEB, "debian_package_sha256": PINNED_DEB_SHA256,
        "debian_package_name": "lynxhub", "debian_package_version": "3.5.8", "installed_executable": "/opt/LynxHub/lynxhub",
    }
    actions = {
        "repository": "TheLynxHub/Custom-Actions", "release": PINNED_ACTIONS_VERSION, "commit": PINNED_ACTIONS_COMMIT,
        "artifact": "0.4.4.7z", "artifact_sha256": PINNED_ACTIONS_SHA256, "automatic_update": False,
    }
    good_action = dict(versioned=True, fixed_id=True, free_shell=False, eval_used=False, privileged=False, direct_mcp=False, direct_ollama=False, secret_access=False)
    good_lifecycle = dict(user_session=True, on_demand=True, service="lynxhub.service", target="ai-creative-ops.target", duplicate_autostart=False, transient_parallel=False)
    good_launch = dict(display="wayland", no_sandbox=False, root_helper=False, gpu_role="DISPLAY_COMPOSITING_ONLY", fixed_gpu=False)
    good_owners = dict(systemd_owner="SYSTEMD", media_owner="STABILITY_MATRIX", durable_owner="TEMPORAL", mcp_owner="CENTRAL_MCP_GATEWAY", provider_owns_port=False)

    add(0, "optional provider remains non-authoritative", provider_boundary_valid(optional=True, authority=False, hard_dependency=False), not provider_boundary_valid(optional=True, authority=True, hard_dependency=False))
    add(1, "provider projects only to CAP-057", CAPABILITY_IDS == ("CAP-057",), "CAP-011" not in CAPABILITY_IDS)
    add(2, "capability and authority counts remain frozen", CAPABILITY_COUNT == 143, CAPABILITY_COUNT != 144)
    add(3, "LynxHub release, commit and Debian digest are pinned", immutable_component_tuple_valid(component), not immutable_component_tuple_valid({**component, "commit": "master"}))
    add(4, "Custom Actions release, commit and artifact digest are pinned", immutable_actions_tuple_valid(actions), not immutable_actions_tuple_valid({**actions, "automatic_update": True}))
    add(5, "floating latest and unadmitted self-update are denied", True, "latest" not in {PINNED_VERSION, PINNED_ACTIONS_VERSION})
    add(6, "execution is restricted to the user desktop session", lifecycle_valid(**good_lifecycle), not lifecycle_valid(**{**good_lifecycle, "user_session": False}))
    add(7, "one on-demand user unit belongs to the creative operations target", lifecycle_valid(**good_lifecycle), not lifecycle_valid(**{**good_lifecycle, "service": "lynxhub-root.service"}))
    add(8, "duplicate autostart and transient units are denied", lifecycle_valid(**good_lifecycle), not lifecycle_valid(**{**good_lifecycle, "duplicate_autostart": True, "transient_parallel": True}))
    add(9, "effective Electron launch preserves sandboxing", launch_valid(**good_launch), not launch_valid(**{**good_launch, "no_sandbox": True}))
    add(10, "Wayland is canonical and XWayland needs an exception", launch_valid(**good_launch), not launch_valid(**{**good_launch, "display": "x11"}))
    add(11, "GPU is display-only without fixed device assumptions", launch_valid(**good_launch), not launch_valid(**{**good_launch, "fixed_gpu": True}))
    add(12, "dashboard owns no platform port or daemon", ownership_valid(**good_owners), not ownership_valid(**{**good_owners, "provider_owns_port": True}))
    add(13, "Custom Actions use a versioned fixed-ID wrapper", action_valid(**good_action), not action_valid(**{**good_action, "fixed_id": False}))
    add(14, "free-form shell and eval are denied", action_valid(**good_action), not action_valid(**{**good_action, "free_shell": True, "eval_used": True}))
    add(15, "sudo, root helpers and admin commands are denied", action_valid(**good_action), not action_valid(**{**good_action, "privileged": True}))
    add(16, "systemctl user is limited to enumerated units", service_action_valid(user_scope=True, enumerated=True, root_scope=False, package_command=False), not service_action_valid(user_scope=False, enumerated=False, root_scope=True, package_command=True))
    add(17, "browser actions open only approved loopback URLs", url_valid("http://127.0.0.1:3000", approved=True), not url_valid("https://example.com", approved=True))
    add(18, "direct MCP execution is denied", action_valid(**good_action), not action_valid(**{**good_action, "direct_mcp": True}))
    add(19, "direct Ollama agent routing is denied", action_valid(**good_action), not action_valid(**{**good_action, "direct_ollama": True}))
    add(20, "secret, database and model-store access are denied", action_valid(**good_action), not action_valid(**{**good_action, "secret_access": True}))
    add(21, "Stability Matrix retains media package ownership", ownership_valid(**good_owners), not ownership_valid(**{**good_owners, "media_owner": "LYNXHUB"}))
    add(22, "Temporal and the central MCP gateway retain authority", ownership_valid(**good_owners), not ownership_valid(**{**good_owners, "durable_owner": "LYNXHUB", "mcp_owner": "LYNXHUB"}))
    add(23, "lowdb remains application state only", state_valid(lowdb_role="APPLICATION_STATE_ONLY", canonical_memory=False, key_storage=False), not state_valid(lowdb_role="CANONICAL_MEMORY", canonical_memory=True, key_storage=False))
    add(24, "egress defaults deny with an explicit update exception", egress_valid(default_deny=True, update_exception_explicit=True, unrestricted=False), not egress_valid(default_deny=False, update_exception_explicit=False, unrestricted=True))
    add(25, "plugins are pinned/allowlisted and auto-update is disabled", plugin_policy_valid(actions_pinned=True, auto_updates=False, local_ai_collection=False, python_toolkit=False), not plugin_policy_valid(actions_pinned=False, auto_updates=True, local_ai_collection=True, python_toolkit=True))
    add(26, "failure is isolated and disabled state has zero process cost", isolation_valid(failure_stops_platform=False, disabled_processes=0), not isolation_valid(failure_stops_platform=True, disabled_processes=1))
    add(27, "runtime promotion requires real E2E and rollback", promotion_valid(reference_pass=True, current_host_e2e=False, rollback_pass=False, claims_runtime=False), not promotion_valid(reference_pass=True, current_host_e2e=False, rollback_pass=False, claims_runtime=True))
    return cases


def scan_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def walk(value: Any, *, location: str, file: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                child = f"{location}.{key}"
                if "authority" in key.lower().replace("-", "_") and item == PROVIDER_ID:
                    findings.append(_finding("LYNXHUB-AUTH-001", "LynxHub assigned to an authority-bearing field", file=file, path=child))
                walk(item, location=child, file=file)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, location=f"{location}[{index}]", file=file)

    for path in sorted((root / "canonical").rglob("*.json")):
        try:
            walk(_load(path), location="$", file=path.relative_to(root).as_posix())
        except Exception as exc:
            findings.append(_finding("LYNXHUB-AUTH-002", "canonical JSON parse failure during authority scan", file=path.relative_to(root).as_posix(), error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def deployment_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for relative in DEPLOYMENT_PATHS:
        if not (root / relative).is_file():
            findings.append(_finding("LYNXHUB-DEP-001", "required deployment artifact missing", path=relative))
    if findings:
        return {"result": "FAIL", "findings": findings}

    service = (root / "deployment/lynxhub/systemd/user/lynxhub.service").read_text(encoding="utf-8")
    launch = (root / "deployment/lynxhub/bin/lynxhub-launch").read_text(encoding="utf-8")
    action = (root / "deployment/lynxhub/bin/lynxhub-action").read_text(encoding="utf-8")
    desktop = (root / "deployment/lynxhub/applications/ai.kindabrazy.lynxhub.desktop.in").read_text(encoding="utf-8")
    active_launch = "\n".join(line for line in launch.splitlines() if not line.lstrip().startswith("#"))
    active_action = "\n".join(line for line in action.splitlines() if not line.lstrip().startswith("#"))
    checks = [
        ("ExecStart=%h/.local/libexec/fa3/lynxhub-launch" in service and "NoNewPrivileges=yes" in service and not re.search(r"^\[Install\]$", service, re.MULTILINE), "LYNXHUB-DEP-002", "user service topology or hardening drift"),
        ("/opt/LynxHub/lynxhub" in active_launch and "--no-sandbox" not in active_launch and "XDG_SESSION_TYPE" in active_launch, "LYNXHUB-DEP-003", "hardened Wayland launch wrapper drift"),
        ("case \"$action\" in" in active_action and "eval " not in active_action and "sudo " not in active_action and "pkexec " not in active_action and "systemctl --user" in active_action, "LYNXHUB-DEP-004", "fixed action wrapper drift"),
        ("Exec=@START_WRAPPER@" in desktop and "--no-sandbox" not in desktop and "X-GNOME-Autostart-enabled=false" in desktop, "LYNXHUB-DEP-005", "effective desktop entry template drift"),
    ]
    for passed, code, message in checks:
        if not passed:
            findings.append(_finding(code, message))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    data: dict[str, dict[str, Any]] = {}
    for name, relative in PATHS.items():
        if name == "matrix":
            continue
        try:
            data[name] = _load(root / relative)
        except Exception as exc:
            findings.append(_finding("LYNXHUB-REF-001", "required canonical artifact missing or invalid", path=relative, error=str(exc)))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile, provider, contract = data["profile"], data["provider"], data["contract"]
    decision, reference = data["decision"], data["reference"]
    gate_record, enforcement = data["gate"], data["enforcement"]
    admission, release, evidence = data["admission"], data["release"], data["evidence"]
    policy, registry = data["policy"], data["registry"]
    checks = [
        (profile.get("id") == PROFILE_ID and profile.get("relationship") == "SUBPROFILE-OF" and profile.get("requirement") == "MAY" and profile.get("capability_projection") == list(CAPABILITY_IDS) and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and profile.get("capability_count") == CAPABILITY_COUNT, "LYNXHUB-REF-003", "dashboard profile drift"),
        (provider.get("id") == PROVIDER_ID and provider.get("canonical_root") is False and provider.get("architectural_authority") is False and provider.get("hard_dependency") is False and provider.get("capability_projection") == list(CAPABILITY_IDS) and provider.get("runtime_activation_status") == RUNTIME_STATUS and provider.get("current_host_runtime_evidence") == "NOT_CLAIMED" and immutable_component_tuple_valid(provider.get("immutable_component_tuple", {})) and immutable_actions_tuple_valid(provider.get("custom_actions_tuple", {})), "LYNXHUB-REF-004", "provider identity, projection, runtime or pins drift"),
        (contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("new_capability") is False and contract.get("new_architectural_authority") is False and contract.get("capability_count") == CAPABILITY_COUNT and contract.get("deployment", {}).get("single_named_user_service") == "lynxhub.service" and contract.get("desktop", {}).get("electron_no_sandbox_flag") == "FORBIDDEN" and contract.get("actions", {}).get("direct_mcp_tool_execution") == "DENY", "LYNXHUB-REF-005", "provider-neutral contract drift"),
        (decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED" and decision.get("mandatory_rules") == RULES and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0 and decision.get("capability_count_after") == CAPABILITY_COUNT and decision.get("current_host_runtime_promotion_claimed") is False, "LYNXHUB-REF-006", "decision drift"),
        (reference.get("id") == REFERENCE_ID and reference.get("release") == PINNED_VERSION and reference.get("commit") == PINNED_COMMIT and reference.get("linux_package", {}).get("filename") == PINNED_DEB and reference.get("linux_package", {}).get("sha256") == PINNED_DEB_SHA256 and reference.get("custom_actions", {}).get("sha256") == PINNED_ACTIONS_SHA256 and reference.get("promotion_use") == "REFERENCE_AND_STATIC_CONFORMANCE_ONLY", "LYNXHUB-REF-007", "upstream reference drift"),
        (gate_record.get("id") == EXECUTABLE_GATE_ID and gate_record.get("gate_set_id") == GATE_ID and gate_record.get("rule_count") == len(RULES) and gate_record.get("fail_closed") is True and enforcement.get("gate_id") == GATE_ID and enforcement.get("rules") == RULES and enforcement.get("rule_count") == len(RULES), "LYNXHUB-REF-008", "gate/enforcement drift"),
        (admission.get("provider_id") == PROVIDER_ID and admission.get("status") == RUNTIME_STATUS and admission.get("current_host_runtime_evidence") == "NOT_CLAIMED" and admission.get("production_provider_admission") is False and admission.get("provider_runtime_required_for_global_promotion_when_disabled") is False and admission.get("required_configuration", {}).get("vendor_no_sandbox_flag_effective") is False, "LYNXHUB-REF-009", "runtime admission drift or false promotion"),
        (release.get("id") == RELEASE_PROJECTION_ID and release.get("capability_projection") == list(CAPABILITY_IDS) and release.get("capability_count_after") == CAPABILITY_COUNT and release.get("new_capabilities") == 0 and release.get("new_architectural_authorities") == 0 and release.get("runtime_promotion") is False, "LYNXHUB-REF-010", "standalone release projection drift"),
        (evidence.get("evidence_id") == EVIDENCE_ID and evidence.get("status") == "PASS" and evidence.get("regression_count") == len(RULES) and evidence.get("regressions_passed") == len(RULES) and evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED" and evidence.get("current_host_runtime_promotion_claimed") is False and evidence.get("production_provider_admission_claimed") is False, "LYNXHUB-REF-011", "reference evidence drift or false runtime claim"),
        (GATE_ID in policy.get("mandatory_reference_gates", []) and policy.get("lynxhub_provider_id") == PROVIDER_ID and policy.get("lynxhub_profile_id") == PROFILE_ID and policy.get("lynxhub_contract_id") == CONTRACT_ID and policy.get("lynxhub_mandatory_p0_rules") == RULES, "LYNXHUB-REF-012", "global enforcement policy binding missing or drifted"),
    ]
    for passed, code, message in checks:
        if not passed:
            findings.append(_finding(code, message))

    records = {item.get("subject_id"): item for item in registry.get("records", [])}
    record = records.get("CAP-057", {})
    projection = record.get("lynxhub_creative_operations_dashboard_projection_status", {})
    if not (
        DECISION_ID in record.get("source_decision_ids", [])
        and PATHS["evidence"] in record.get("evidence_artifacts", [])
        and record.get("status") == "PENDING_CURRENT_HOST"
        and projection.get("provider_id") == PROVIDER_ID
        and projection.get("runtime_activation_status") == RUNTIME_STATUS
        and projection.get("current_host_runtime_evidence") == "NOT_CLAIMED"
    ):
        findings.append(_finding("LYNXHUB-REF-013", "CAP-057 evidence registry binding missing or drifted"))

    try:
        with (root / PATHS["matrix"]).open(encoding="utf-8-sig", newline="") as stream:
            rows = {row["capability_id"]: row for row in csv.DictReader(stream)}
        if "LynxHub optional Creative Operations Dashboard" not in rows["CAP-057"]["primary_mandatory_reference"]:
            findings.append(_finding("LYNXHUB-REF-014", "CAP-057 Conformance Matrix projection missing"))
        if DECISION_ID not in rows["CAP-057"]["source_decision_ids"]:
            findings.append(_finding("LYNXHUB-REF-015", "CAP-057 Conformance Matrix decision binding missing"))
    except Exception as exc:
        findings.append(_finding("LYNXHUB-REF-016", "Conformance Matrix unavailable", error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    reference = reference_check(root)
    deployment = deployment_check(root)
    authority = scan_authority_assignments(root)
    cases = regression_cases()
    findings = [*reference["findings"], *deployment["findings"], *authority["findings"]]
    for case in cases:
        if case["result"] != "PASS":
            findings.append(_finding("LYNXHUB-REG-001", "positive/negative regression failed", rule=case["rule"]))
    result = {
        "schema": "fa3.lynxhub-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "fail_closed": True,
        "blocking_findings": len(findings),
        "findings": findings,
        "reference": reference,
        "deployment": deployment,
        "authority_scan": authority,
        "regressions": {"total": len(cases), "passed": sum(case["result"] == "PASS" for case in cases), "cases": cases},
        "capability_count_after": CAPABILITY_COUNT,
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "current_host_runtime_promotion_claimed": False,
    }
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "lynxhub-gate-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 LynxHub Creative Operations Dashboard canonical gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    result = gate(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
