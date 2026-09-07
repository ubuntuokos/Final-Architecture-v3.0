#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = 143
CAPABILITY_IDS = ("CAP-008",)
PROFILE_ID = "FA3-SILLYTAVERN-KDE-DESKTOP-001"
PROVIDER_ID = "FA3-PROVIDER-SILLYTAVERN-KDE-001"
CONTRACT_ID = "FA3-LOCAL-CONVERSATION-DESKTOP-CONTRACTS-001"
DECISION_ID = "FA3-DEC-SILLYTAVERN-KDE-DESKTOP-2026-09-07"
REFERENCE_ID = "FA3-SILLYTAVERN-UPSTREAM-REFERENCE-2026-09-07"
GATESET_ID = "FA3-SILLYTAVERN-KDE-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-SILLYTAVERN-KDE-001"
EVIDENCE_ID = "FA3-EVID-SILLYTAVERN-KDE-CI-2026-09-07"
PINNED_RELEASE = "1.18.0"
PINNED_COMMIT = "51ad27fb86d39a3daca3adaa970375c9670c12df"
PINNED_ENTRY_BLOB = "6126ef45ca881e30e7fceb134270dfb52d883b4b"
PINNED_LOCK_BLOB = "de71cacfc097733f36d79f103bfd9fb2686778a6"

RULES = [
    "SILLYTAVERN_KDE_OPTIONAL_NON_AUTHORITY_PROVIDER",
    "SILLYTAVERN_KDE_PROJECTS_ONLY_TO_CAP_008",
    "SILLYTAVERN_KDE_NO_NEW_CAPABILITY_OR_AUTHORITY_COUNT_143",
    "SILLYTAVERN_KDE_IMMUTABLE_UPSTREAM_RELEASE_COMMIT_AND_ELECTRON_LOCK",
    "SILLYTAVERN_KDE_UPSTREAM_ELECTRON_PREFERRED_NO_SECOND_WRAPPER",
    "SILLYTAVERN_KDE_RUNTIME_DEPENDENCY_INSTALL_FORBIDDEN",
    "SILLYTAVERN_KDE_DEPENDENCY_PREPARE_REQUIRES_EXPLICIT_ADMISSION",
    "SILLYTAVERN_KDE_USER_SESSION_ON_DEMAND_ONLY",
    "SILLYTAVERN_KDE_ELECTRON_OWNS_SERVER_CHILD_LIFECYCLE",
    "SILLYTAVERN_KDE_LOOPBACK_EVENT_DERIVED_URL_NO_FIXED_PORT",
    "SILLYTAVERN_KDE_KDE6_WAYLAND_FIRST_CLASS",
    "SILLYTAVERN_KDE_ELECTRON_SANDBOX_DISABLE_FORBIDDEN",
    "SILLYTAVERN_KDE_NO_FIXED_GPU_IDENTITY_OR_COUNT",
    "SILLYTAVERN_KDE_MODEL_ROUTING_AUTHORITY_PRESERVED",
    "SILLYTAVERN_KDE_PROMPT_OR_PERCENTAGE_ROUTING_FORBIDDEN",
    "SILLYTAVERN_KDE_CENTRAL_MCP_GATEWAY_PRESERVED",
    "SILLYTAVERN_KDE_ARBITRARY_SHELL_AND_FAKE_SANDBOX_FORBIDDEN",
    "SILLYTAVERN_KDE_SIDE_EFFECTS_REQUIRE_HUMAN_GATE",
    "SILLYTAVERN_KDE_LOCAL_STATE_NOT_SHARED_MEMORY_AUTHORITY",
    "SILLYTAVERN_KDE_VOICE_AUTHORITIES_PRESERVED",
    "SILLYTAVERN_KDE_RESOURCE_TELEMETRY_READ_ONLY_HRB_PRESERVED",
    "SILLYTAVERN_KDE_THIRD_PARTY_EXTENSIONS_SEPARATELY_ADMITTED",
    "SILLYTAVERN_KDE_NO_AI_OS_SWARM_OR_SELF_IMPROVING_AUTHORITY",
    "SILLYTAVERN_KDE_CURRENT_HOST_PROMOTION_REQUIRES_REAL_E2E_AND_ROLLBACK",
]

PATHS = {
    "profile": "canonical/profiles/FA3-SILLYTAVERN-KDE-DESKTOP-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-SILLYTAVERN-KDE-001.json",
    "contract": "canonical/contracts/FA3-LOCAL-CONVERSATION-DESKTOP-CONTRACTS-001.json",
    "decision": "canonical/decisions/FA3-DEC-SILLYTAVERN-KDE-DESKTOP-2026-09-07.json",
    "reference": "canonical/references/FA3-SILLYTAVERN-UPSTREAM-REFERENCE-2026-09-07.json",
    "gate": "canonical/FA3-GATE-SILLYTAVERN-KDE-001.json",
    "enforcement": "canonical/sillytavern-kde-enforcement.json",
    "evidence": "evidence/reference/sillytavern-kde-ci-2026-09-07.json",
}

DEPLOYMENT_PATHS = (
    "deployment/sillytavern-kde/bin/sillytavern-kde-launch",
    "deployment/sillytavern-kde/bin/sillytavern-kde-start",
    "deployment/sillytavern-kde/systemd/user/sillytavern-kde.service",
    "deployment/sillytavern-kde/applications/fa3-sillytavern-kde.desktop.in",
    "deployment/sillytavern-kde/sillytavern-kde.env.example",
    "deployment/sillytavern-kde/README.md",
    "bin/fa3-sillytavern-kde-install-user-integration.sh",
    "docs/sillytavern-kde-integration.md",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def provider_boundary_valid(*, optional: bool, authority: bool, hard_dependency: bool) -> bool:
    return optional and not authority and not hard_dependency


def immutable_component_tuple_valid(value: dict[str, Any]) -> bool:
    return (
        value.get("repository") == "SillyTavern/SillyTavern"
        and value.get("release") == PINNED_RELEASE
        and value.get("commit") == PINNED_COMMIT
        and value.get("license") == "AGPL-3.0"
        and value.get("electron_entrypoint") == "src/electron/index.js"
        and value.get("electron_entrypoint_blob_sha") == PINNED_ENTRY_BLOB
        and value.get("electron_lockfile") == "src/electron/package-lock.json"
        and value.get("electron_lockfile_blob_sha") == PINNED_LOCK_BLOB
        and all(value.get(key) not in {"", "main", "master", "latest", "*", "floating"}
                for key in ("release", "commit", "electron_entrypoint_blob_sha", "electron_lockfile_blob_sha"))
    )


def lifecycle_valid(*, user_session: bool, on_demand: bool, desktop_owns_server: bool, separate_backend: bool) -> bool:
    return user_session and on_demand and desktop_owns_server and not separate_backend


def endpoint_valid(*, loopback: bool, event_derived: bool, fixed_port: bool) -> bool:
    return loopback and event_derived and not fixed_port


def desktop_valid(*, wayland: bool, no_sandbox: bool, second_wrapper: bool, fixed_gpu: bool) -> bool:
    return wayland and not no_sandbox and not second_wrapper and not fixed_gpu


def dependency_valid(*, runtime_install: bool, explicit_prepare: bool, pinned_lock: bool) -> bool:
    return not runtime_install and explicit_prepare and pinned_lock


def model_valid(*, existing_router: bool, prompt_keyword: bool, percentage_router: bool, direct_runtime: bool) -> bool:
    return existing_router and not prompt_keyword and not percentage_router and not direct_runtime


def tool_valid(*, central_gateway: bool, free_shell: bool, fake_sandbox: bool, privileged: bool, side_effect_human_gate: bool) -> bool:
    return central_gateway and side_effect_human_gate and not any((free_shell, fake_sandbox, privileged))


def state_valid(*, application_only: bool, canonical_memory: bool) -> bool:
    return application_only and not canonical_memory


def voice_valid(*, existing_authority: bool, parallel_authority: bool) -> bool:
    return existing_authority and not parallel_authority


def telemetry_valid(*, read_only: bool, hrb_preserved: bool, scheduler: bool) -> bool:
    return read_only and hrb_preserved and not scheduler


def extension_valid(*, separate_admission: bool, auto_install: bool, auto_update: bool) -> bool:
    return separate_admission and not auto_install and not auto_update


def autonomy_valid(*, global_orchestrator: bool, ai_os: bool, unbounded_swarm: bool, self_improving: bool) -> bool:
    return not any((global_orchestrator, ai_os, unbounded_swarm, self_improving))


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
        "repository": "SillyTavern/SillyTavern",
        "release": PINNED_RELEASE,
        "commit": PINNED_COMMIT,
        "license": "AGPL-3.0",
        "electron_entrypoint": "src/electron/index.js",
        "electron_entrypoint_blob_sha": PINNED_ENTRY_BLOB,
        "electron_lockfile": "src/electron/package-lock.json",
        "electron_lockfile_blob_sha": PINNED_LOCK_BLOB,
    }
    life = dict(user_session=True, on_demand=True, desktop_owns_server=True, separate_backend=False)
    endpoint = dict(loopback=True, event_derived=True, fixed_port=False)
    desktop = dict(wayland=True, no_sandbox=False, second_wrapper=False, fixed_gpu=False)
    deps = dict(runtime_install=False, explicit_prepare=True, pinned_lock=True)
    model = dict(existing_router=True, prompt_keyword=False, percentage_router=False, direct_runtime=False)
    tool = dict(central_gateway=True, free_shell=False, fake_sandbox=False, privileged=False, side_effect_human_gate=True)
    state = dict(application_only=True, canonical_memory=False)
    voice = dict(existing_authority=True, parallel_authority=False)
    telemetry = dict(read_only=True, hrb_preserved=True, scheduler=False)
    ext = dict(separate_admission=True, auto_install=False, auto_update=False)
    autonomy = dict(global_orchestrator=False, ai_os=False, unbounded_swarm=False, self_improving=False)

    add(0, "optional provider remains non-authoritative", provider_boundary_valid(optional=True, authority=False, hard_dependency=False), not provider_boundary_valid(optional=True, authority=True, hard_dependency=False))
    add(1, "provider projects only to CAP-008", CAPABILITY_IDS == ("CAP-008",), "CAP-011" not in CAPABILITY_IDS)
    add(2, "capability and authority count stays frozen", CAPABILITY_COUNT == 143, CAPABILITY_COUNT != 144)
    add(3, "upstream release, commit and Electron files are immutable", immutable_component_tuple_valid(component), not immutable_component_tuple_valid({**component, "release": "latest"}))
    add(4, "upstream Electron is preferred over a second wrapper", desktop_valid(**desktop), not desktop_valid(**{**desktop, "second_wrapper": True}))
    add(5, "normal runtime performs no dependency install", dependency_valid(**deps), not dependency_valid(**{**deps, "runtime_install": True}))
    add(6, "dependency preparation is explicit and lock-pinned", dependency_valid(**deps), not dependency_valid(**{**deps, "explicit_prepare": False, "pinned_lock": False}))
    add(7, "lifecycle is on-demand in the user session", lifecycle_valid(**life), not lifecycle_valid(**{**life, "on_demand": False}))
    add(8, "Electron owns the SillyTavern server child lifecycle", lifecycle_valid(**life), not lifecycle_valid(**{**life, "desktop_owns_server": False, "separate_backend": True}))
    add(9, "server URL is loopback and event-derived without a fixed port", endpoint_valid(**endpoint), not endpoint_valid(**{**endpoint, "event_derived": False, "fixed_port": True}))
    add(10, "KDE6 Wayland is first-class", desktop_valid(**desktop), not desktop_valid(**{**desktop, "wayland": False}))
    add(11, "Electron sandbox disable is denied", desktop_valid(**desktop), not desktop_valid(**{**desktop, "no_sandbox": True}))
    add(12, "no fixed GPU identity or count is assumed", desktop_valid(**desktop), not desktop_valid(**{**desktop, "fixed_gpu": True}))
    add(13, "existing FA3 model router remains authority", model_valid(**model), not model_valid(**{**model, "existing_router": False, "direct_runtime": True}))
    add(14, "prompt-keyword and percentage routing are denied", model_valid(**model), not model_valid(**{**model, "prompt_keyword": True, "percentage_router": True}))
    add(15, "central MCP gateway remains authority", tool_valid(**tool), not tool_valid(**{**tool, "central_gateway": False}))
    add(16, "free shell and fake subprocess sandbox are denied", tool_valid(**tool), not tool_valid(**{**tool, "free_shell": True, "fake_sandbox": True}))
    add(17, "side effects require a human gate and no privilege", tool_valid(**tool), not tool_valid(**{**tool, "side_effect_human_gate": False, "privileged": True}))
    add(18, "local state is application state, not shared-memory authority", state_valid(**state), not state_valid(**{**state, "canonical_memory": True}))
    add(19, "existing STT/TTS authorities are preserved", voice_valid(**voice), not voice_valid(**{**voice, "parallel_authority": True}))
    add(20, "resource telemetry is read-only and HRB remains authority", telemetry_valid(**telemetry), not telemetry_valid(**{**telemetry, "scheduler": True, "read_only": False}))
    add(21, "third-party extensions require separate admission", extension_valid(**ext), not extension_valid(**{**ext, "auto_install": True, "auto_update": True}))
    add(22, "AI OS, unbounded swarm and self-improving authority are denied", autonomy_valid(**autonomy), not autonomy_valid(**{**autonomy, "ai_os": True, "unbounded_swarm": True, "self_improving": True}))
    add(23, "runtime promotion requires real current-host E2E and rollback", promotion_valid(reference_pass=True, current_host_e2e=False, rollback_pass=False, claims_runtime=False), not promotion_valid(reference_pass=True, current_host_e2e=False, rollback_pass=False, claims_runtime=True))
    return cases


def deployment_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for rel in DEPLOYMENT_PATHS:
        if not (root / rel).exists():
            findings.append(_finding("SILLYKDE-DEP-001", "required deployment file missing", path=rel))

    if findings:
        return {"result": "FAIL", "findings": findings}

    launch = (root / "deployment/sillytavern-kde/bin/sillytavern-kde-launch").read_text(encoding="utf-8")
    unit = (root / "deployment/sillytavern-kde/systemd/user/sillytavern-kde.service").read_text(encoding="utf-8")
    desktop = (root / "deployment/sillytavern-kde/applications/fa3-sillytavern-kde.desktop.in").read_text(encoding="utf-8")
    installer = (root / "bin/fa3-sillytavern-kde-install-user-integration.sh").read_text(encoding="utf-8")

    forbidden_runtime_tokens = ("--no-sandbox", "npm install", "npm i ", "npm ci", "sudo ", "pkexec")
    if any(token in launch for token in forbidden_runtime_tokens):
        findings.append(_finding("SILLYKDE-DEP-002", "normal launcher contains forbidden mutation or privilege token"))
    if PINNED_COMMIT not in launch or PINNED_ENTRY_BLOB not in launch or PINNED_LOCK_BLOB not in launch:
        findings.append(_finding("SILLYKDE-DEP-003", "normal launcher does not enforce immutable source/Electron pins"))
    if "--ozone-platform=wayland" not in launch or "XDG_SESSION_TYPE" not in launch:
        findings.append(_finding("SILLYKDE-DEP-004", "Wayland preflight/launch semantics missing"))
    if "[Install]" in unit or "WantedBy=" in unit:
        findings.append(_finding("SILLYKDE-DEP-005", "user service became enableable/autostarted by default"))
    if "NoNewPrivileges=true" not in unit or "PrivateTmp=true" not in unit:
        findings.append(_finding("SILLYKDE-DEP-006", "user service hardening drift"))
    if "@START_WRAPPER@" not in desktop or "Terminal=false" not in desktop:
        findings.append(_finding("SILLYKDE-DEP-007", "KDE desktop template does not use the version-controlled starter"))
    if "--prepare-deps" not in installer or "npm ci" not in installer or "verify_source" not in installer:
        findings.append(_finding("SILLYKDE-DEP-008", "explicit dependency admission path missing"))
    if "systemctl --user enable" in installer:
        findings.append(_finding("SILLYKDE-DEP-009", "installer silently enables desktop autostart"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    missing = [rel for rel in PATHS.values() if not (root / rel).exists()]
    if missing:
        return {"result": "FAIL", "findings": [_finding("SILLYKDE-REF-001", "canonical/reference file missing", paths=missing)]}

    profile = _load(root / PATHS["profile"])
    provider = _load(root / PATHS["provider"])
    contract = _load(root / PATHS["contract"])
    decision = _load(root / PATHS["decision"])
    reference = _load(root / PATHS["reference"])
    gate_record = _load(root / PATHS["gate"])
    enforcement = _load(root / PATHS["enforcement"])
    evidence = _load(root / PATHS["evidence"])

    if profile.get("id") != PROFILE_ID or profile.get("capability_projection") != list(CAPABILITY_IDS) or profile.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("SILLYKDE-REF-002", "profile identity/capability invariant mismatch"))
    if provider.get("id") != PROVIDER_ID or provider.get("capability_projection") != list(CAPABILITY_IDS):
        findings.append(_finding("SILLYKDE-REF-003", "provider identity/capability projection mismatch"))
    if not provider_boundary_valid(optional="OPTIONAL_PROVIDER" in provider.get("classification", []), authority=bool(provider.get("architectural_authority")), hard_dependency=bool(provider.get("hard_dependency"))):
        findings.append(_finding("SILLYKDE-REF-004", "provider authority boundary drift"))
    if provider.get("capability_count") != CAPABILITY_COUNT or provider.get("new_capability") is not False or provider.get("new_architectural_authority") is not False:
        findings.append(_finding("SILLYKDE-REF-005", "provider changed capability/authority count semantics"))
    if not immutable_component_tuple_valid(provider.get("immutable_component_tuple", {})):
        findings.append(_finding("SILLYKDE-REF-006", "immutable upstream component tuple invalid"))
    if contract.get("id") != CONTRACT_ID or contract.get("provider_neutral") is not True or contract.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("SILLYKDE-REF-007", "provider-neutral desktop contract invariant mismatch"))
    if contract.get("deployment", {}).get("runtime_dependency_install_or_update") != "FORBIDDEN":
        findings.append(_finding("SILLYKDE-REF-008", "runtime dependency mutation prohibition missing"))
    if contract.get("model_access", {}).get("prompt_keyword_backend_routing") != "FORBIDDEN" or contract.get("model_access", {}).get("ram_or_vram_percentage_as_routing_authority") != "FORBIDDEN":
        findings.append(_finding("SILLYKDE-REF-009", "ad-hoc model routing prohibition missing"))
    if contract.get("mcp_and_tools", {}).get("tempfile_subprocess_claimed_as_sandbox") != "FORBIDDEN":
        findings.append(_finding("SILLYKDE-REF-010", "fake sandbox prohibition missing"))
    if decision.get("id") != DECISION_ID or decision.get("mandatory_rules") != RULES or decision.get("capability_count_after") != CAPABILITY_COUNT:
        findings.append(_finding("SILLYKDE-REF-011", "architecture decision/rule-set mismatch"))
    if reference.get("id") != REFERENCE_ID or reference.get("release") != PINNED_RELEASE or reference.get("commit") != PINNED_COMMIT:
        findings.append(_finding("SILLYKDE-REF-012", "upstream reference pin mismatch"))
    wrapper = reference.get("desktop_wrapper", {})
    if wrapper.get("entrypoint_blob_sha") != PINNED_ENTRY_BLOB or wrapper.get("lockfile_blob_sha") != PINNED_LOCK_BLOB:
        findings.append(_finding("SILLYKDE-REF-013", "upstream Electron file identity mismatch"))
    if gate_record.get("id") != EXECUTABLE_GATE_ID or gate_record.get("gate_set_id") != GATESET_ID or gate_record.get("rule_count") != len(RULES):
        findings.append(_finding("SILLYKDE-REF-014", "gate record mismatch"))
    if enforcement.get("id") != GATESET_ID or enforcement.get("rules") != RULES or enforcement.get("fail_closed") is not True:
        findings.append(_finding("SILLYKDE-REF-015", "enforcement rule set mismatch"))

    regressions = regression_cases()
    if len(regressions) != len(RULES) or not all(case["result"] == "PASS" for case in regressions):
        findings.append(_finding("SILLYKDE-REG-001", "positive/negative regression suite failed", regressions=regressions))

    deployment = deployment_check(root)
    if deployment["result"] != "PASS":
        findings.append(_finding("SILLYKDE-DEP-010", "deployment static conformance failed", deployment=deployment))

    if evidence.get("id") != EVIDENCE_ID or evidence.get("status") != "PASS":
        findings.append(_finding("SILLYKDE-EVID-001", "reference CI evidence is missing or not PASS"))
    if evidence.get("regressions") != {"passed": len(RULES), "total": len(RULES)}:
        findings.append(_finding("SILLYKDE-EVID-002", "reference evidence regression count mismatch"))
    if evidence.get("current_host_runtime_evidence") != "NOT_CLAIMED" or evidence.get("current_host_runtime_promotion_claimed") is not False or evidence.get("production_provider_admission_claimed") is not False:
        findings.append(_finding("SILLYKDE-EVID-003", "reference evidence improperly claims current-host production promotion"))

    return {
        "schema": "fa3.sillytavern-kde-gate-report.v1",
        "gate_id": EXECUTABLE_GATE_ID,
        "gate_set_id": GATESET_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "regressions": {
            "passed": sum(case["result"] == "PASS" for case in regressions),
            "total": len(regressions),
        },
        "deployment": deployment,
        "current_host_runtime_promotion_claimed": False,
        "capability_count": CAPABILITY_COUNT,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 SillyTavern KDE canonical/executable regression gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
