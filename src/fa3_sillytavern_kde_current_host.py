#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-SILLYTAVERN-KDE-001"
PROFILE_ID = "FA3-SILLYTAVERN-KDE-DESKTOP-001"
CONTRACT_ID = "FA3-LOCAL-CONVERSATION-DESKTOP-CONTRACTS-001"
PARENT_GATESET_ID = "FA3-SILLYTAVERN-KDE-GATESET-001"
CONFORMANCE_ID = "FA3-SILLYTAVERN-KDE-RUNTIME-CONFORMANCE-001"
GATE_ID = "FA3-GATE-SILLYTAVERN-KDE-CURRENT-HOST-001"
GATESET_ID = "FA3-SILLYTAVERN-KDE-CURRENT-HOST-GATESET-001"
DECISION_ID = "FA3-DEC-SILLYTAVERN-KDE-CURRENT-HOST-2026-09-12"
CAPABILITY_COUNT = 143
CAPABILITY = "CAP-008"
PASS_STATUS = "CURRENT_HOST_PRODUCTION_E2E_PASS"
RELEASE = "1.18.0"
COMMIT = "51ad27fb86d39a3daca3adaa970375c9670c12df"
ROOT_LOCK = "95b4dbc33c62829e2aff383f286889ebdcc15ffd"
ROOT_NPMRC = "2143f3df2fc935fce293d1ee5b3c073fd187e135"
ENTRY = "6126ef45ca881e30e7fceb134270dfb52d883b4b"
ELECTRON_LOCK = "de71cacfc097733f36d79f103bfd9fb2686778a6"
RUNNER_LABELS = {"self-hosted", "linux", "x64", "fa3-current-host"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def static_check(root: Path) -> dict[str, Any]:
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-SILLYTAVERN-KDE-001.json",
        "parent": root / "canonical/sillytavern-kde-enforcement.json",
        "conformance": root / "canonical/FA3-SILLYTAVERN-KDE-RUNTIME-CONFORMANCE-001.json",
        "gate": root / "canonical/FA3-GATE-SILLYTAVERN-KDE-CURRENT-HOST-001.json",
        "enforcement": root / "canonical/sillytavern-kde-current-host-enforcement.json",
        "decision": root / "canonical/decisions/FA3-DEC-SILLYTAVERN-KDE-CURRENT-HOST-2026-09-12.json",
        "installer": root / "bin/fa3-sillytavern-kde-install-user-integration.sh",
        "launcher": root / "deployment/sillytavern-kde/bin/sillytavern-kde-launch",
        "collector": root / "evidence/collect-sillytavern-kde-current-host.sh",
        "workflow": root / ".github/workflows/fa3-sillytavern-kde-current-host.yml",
    }
    findings: list[str] = []
    for name, path in paths.items():
        if not path.exists():
            findings.append(f"missing:{name}:{path.relative_to(root)}")
    if findings:
        return {"result": "FAIL", "checks": {}, "findings": findings}

    provider = load(paths["provider"])
    parent = load(paths["parent"])
    conformance = load(paths["conformance"])
    gate = load(paths["gate"])
    enforcement = load(paths["enforcement"])
    decision = load(paths["decision"])
    installer = paths["installer"].read_text(encoding="utf-8")
    launcher = paths["launcher"].read_text(encoding="utf-8")
    collector = paths["collector"].read_text(encoding="utf-8")
    workflow = paths["workflow"].read_text(encoding="utf-8")
    immutable = provider.get("immutable_component_tuple", {})

    checks = {
        "provider_non_authority": provider.get("architectural_authority") is False and provider.get("new_capability") is False,
        "capability_invariant": provider.get("capability_count") == CAPABILITY_COUNT and provider.get("capability_projection") == [CAPABILITY],
        "provider_pending": provider.get("runtime_activation_status") == "NOT_PROMOTED_PENDING_CURRENT_HOST_KDE_WAYLAND_E2E" and provider.get("current_host_runtime_evidence") == "NOT_CLAIMED",
        "immutable_release": immutable.get("release") == RELEASE and immutable.get("commit") == COMMIT,
        "root_dependency_identity": immutable.get("root_lockfile_blob_sha") == ROOT_LOCK and immutable.get("root_npmrc_blob_sha") == ROOT_NPMRC,
        "electron_identity": immutable.get("electron_entrypoint_blob_sha") == ENTRY and immutable.get("electron_lockfile_blob_sha") == ELECTRON_LOCK,
        "parent_child_gate": GATE_ID in parent.get("child_gates", []),
        "conformance_pending": conformance.get("id") == CONFORMANCE_ID and conformance.get("status") == "PENDING_REAL_CURRENT_HOST_E2E" and conformance.get("current_host_production_claim") is False,
        "gate_fail_closed": gate.get("id") == GATE_ID and gate.get("fail_closed") is True and gate.get("ci_fixture_can_claim_current_host_pass") is False,
        "enforcement_identity": enforcement.get("id") == GATESET_ID and enforcement.get("fail_closed") is True and enforcement.get("production_promotion_claim") is False,
        "decision_pending": decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_PENDING_CURRENT_HOST" and decision.get("current_host_production_claim") is False,
        "installer_root_ci": "cd \"$root\"" in installer and "npm ci --omit=dev" in installer and ROOT_LOCK in installer and ROOT_NPMRC in installer,
        "installer_electron_ci": "cd \"$root/src/electron\"" in installer and "npm ci --no-audit" in installer,
        "launcher_mutation_free": "npm ci" not in launcher and "npm install" not in launcher and "npm i " not in launcher,
        "launcher_identity": all(x in launcher for x in (COMMIT, ROOT_LOCK, ROOT_NPMRC, ENTRY, ELECTRON_LOCK)),
        "collector_real_session": "XDG_SESSION_TYPE" in collector and "WAYLAND_DISPLAY" in collector and "graphical-session.target" in collector,
        "collector_dynamic_listener": "fixed_port_assumed" in collector and "ss -H -ltnp" in collector,
        "collector_rollback": "--uninstall" in collector and "rollback" in collector,
        "workflow_real_runner": "[self-hosted, linux, x64, fa3-current-host]" in workflow,
        "workflow_receipt": "sillytavern-kde-current-host.json" in workflow,
    }
    for key, ok in checks.items():
        if not ok:
            findings.append(f"check_failed:{key}")
    return {"result": "PASS" if not findings else "FAIL", "checks": checks, "findings": findings}


def receipt_valid(receipt: dict[str, Any], *, require_real_runner: bool = True) -> bool:
    if receipt.get("schema") != "fa3.sillytavern-kde-current-host-receipt.v1":
        return False
    if receipt.get("provider_id") != PROVIDER_ID or receipt.get("gate_id") != GATE_ID or receipt.get("conformance_id") != CONFORMANCE_ID:
        return False
    if receipt.get("result_status") != PASS_STATUS:
        return False
    if receipt.get("capability_scope") != [CAPABILITY]:
        return False
    if receipt.get("candidate", {}).get("release") != RELEASE or receipt.get("candidate", {}).get("commit") != COMMIT:
        return False
    source = receipt.get("source", {})
    if not all(source.get(k) is True for k in ("commit_revalidated", "root_lock_revalidated", "root_npmrc_revalidated", "electron_entry_revalidated", "electron_lock_revalidated")):
        return False
    runtime = receipt.get("runtime", {})
    if runtime.get("node_major", 0) < 20 or runtime.get("root_dependencies_prepared") is not True or runtime.get("electron_dependencies_prepared") is not True:
        return False
    session = receipt.get("session", {})
    if session.get("xdg_session_type") != "wayland" or session.get("wayland_socket_exists") is not True or session.get("graphical_session_active") is not True:
        return False
    process = receipt.get("process", {})
    if process.get("no_sandbox_present") is not False or process.get("ozone_wayland_present") is not True:
        return False
    network = receipt.get("network", {})
    if network.get("fixed_port_assumed") is not False or network.get("all_service_listeners_loopback") is not True or network.get("ui_probe_sillytavern") is not True:
        return False
    if receipt.get("negative", {}).get("invalid_source_refused") is not True:
        return False
    authority = receipt.get("authority", {})
    if not all(authority.get(k) is True for k in ("model_router_preserved", "mcp_gateway_preserved", "memory_authority_preserved", "hrb_preserved")):
        return False
    stop = receipt.get("stop", {})
    if stop.get("clean_stop") is not True or stop.get("resident_provider_processes_after") != 0:
        return False
    rollback = receipt.get("rollback", {})
    if not all(rollback.get(k) is True for k in ("uninstall_pass", "reinstall_pass", "service_inactive_after")):
        return False
    if receipt.get("ci_fixture") is True:
        return False
    if require_real_runner:
        labels = set(receipt.get("runner", {}).get("labels", []))
        if not RUNNER_LABELS.issubset(labels):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 SillyTavern KDE current-host admission gate")
    parser.add_argument("mode", choices=["static", "verify"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--receipt", default="evidence/receipts/sillytavern-kde-current-host.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.mode == "static":
        report = static_check(root)
    else:
        receipt_path = root / args.receipt
        if not receipt_path.exists():
            report = {"result": "FAIL", "findings": [f"missing_receipt:{args.receipt}"]}
        else:
            receipt = load(receipt_path)
            report = {"result": "PASS" if receipt_valid(receipt) else "FAIL", "receipt_status": receipt.get("result_status")}
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
