#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any

from fa3_accelerator_backend_probe import enrich_accelerator_backends
from fa3_application_runtime_resolver import discover_inventory
from fa3_desktop_admission import collect_runtime_probes, discover_current_user_session_environment, evaluate_desktop
from fa3_hardware_discovery import discover_accelerator_devices, discover_cpu_topology
from fa3_release_baseline import module_active_capability_count

PROFILE_ID = "FA3-HOST-ADAPTATION-001"
CONTRACT_ID = "FA3-HOST-ADAPTATION-CONTRACTS-001"
DECISION_ID = "FA3-DEC-HOST-ADAPTATION-2026-09-27"
CAPABILITY_COUNT = module_active_capability_count(__file__)
DRIFT_ORDER = {
    "NO_DRIFT": 0, "OBSERVATIONAL_DRIFT": 1, "RUNTIME_REBIND": 2,
    "CONFIG_RECONCILE": 3, "COMPONENT_ADMISSION": 4, "SAFETY_BLOCK": 5,
}


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def os_release() -> dict[str, Any]:
    values: dict[str, str] = {}
    path = Path("/etc/os-release")
    if path.is_file():
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in raw and not raw.lstrip().startswith("#"):
                key, value = raw.split("=", 1)
                values[key] = value.strip().strip('"')
    return {
        "id": values.get("ID", "unknown"),
        "id_like": values.get("ID_LIKE", "").split(),
        "version_id": values.get("VERSION_ID"),
    }


def package_managers() -> dict[str, Any]:
    native_candidates = ("apt-get", "dnf", "zypper", "pacman")
    native_available = [name for name in native_candidates if shutil.which(name)]
    application_frontends = [name for name in ("flatpak", "snap") if shutil.which(name)]
    return {
        "available": native_available,
        "primary": native_available[0] if native_available else None,
        "application_distribution_frontends": application_frontends,
        "portable_application_discovery": ["APPIMAGE", "PORTABLE", "MANUAL"],
        "authority": False,
    }


def capture_live_snapshot(root: Path) -> dict[str, Any]:
    session = discover_current_user_session_environment()
    env = session["environment"]
    desktop = evaluate_desktop(env, collect_runtime_probes(env), require_gui=False)
    devices = enrich_accelerator_backends(discover_accelerator_devices(), include_framework_probes=False)
    snapshot = {
        "schema": "fa3.live-host-snapshot.v1",
        "profile_id": PROFILE_ID,
        "capability_count": CAPABILITY_COUNT,
        "os": os_release(),
        "package_managers": package_managers(),
        "application_runtimes": discover_inventory(root, probe=False),
        "kernel_release": platform.release(),
        "cpu": discover_cpu_topology(),
        "accelerators": [device.as_dict() for device in devices],
        "desktop": desktop,
        "session_discovery": session.get("evidence", {}),
        "authority_semantics": {
            "discovery_is_authority": False,
            "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "evidence_authority": "FA3-AUTH-OBS-EVIDENCE-001",
        },
        "current_host_promotion_claim": False,
    }
    snapshot["snapshot_sha256"] = digest(snapshot)
    return snapshot


def accelerator_identity(row: dict[str, Any]) -> str:
    for key in ("stable_device_id", "device_uuid", "pci_bdf", "discovery_id"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return f"{key}:{value}"
    return f"unidentified:{digest(row)}"


def accel_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        accelerator_identity(row): row
        for row in snapshot.get("accelerators", [])
        if isinstance(row, dict)
    }


def add_change(changes: list[dict[str, Any]], classification: str, domain: str, code: str, before: Any, after: Any, action: str) -> None:
    changes.append({
        "classification": classification, "domain": domain, "code": code,
        "before": before, "after": after, "recommended_action": action,
    })


def compare_snapshots(accepted: dict[str, Any], live: dict[str, Any], *, physical_core_min: int) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    if accepted.get("capability_count") != live.get("capability_count"):
        add_change(changes, "SAFETY_BLOCK", "governance", "CAPABILITY_BASELINE_CHANGED",
                   accepted.get("capability_count"), live.get("capability_count"),
                   "RUN_CANONICAL_RELEASE_RECONCILIATION")

    acpu, lcpu = accepted.get("cpu", {}), live.get("cpu", {})
    asum, lsum = acpu.get("summary", {}), lcpu.get("summary", {})
    visible = int(lsum.get("physical_cores_visible", 0) or 0)
    if visible < physical_core_min:
        add_change(changes, "SAFETY_BLOCK", "cpu", "CPU_VISIBLE_CORE_FLOOR_VIOLATION",
                   asum.get("physical_cores_visible"), visible, "REQUIRE_HARDWARE_AUDIT")
    for key in ("packages_total", "physical_cores_total", "numa_domains_total"):
        if asum.get(key) != lsum.get(key):
            add_change(changes, "CONFIG_RECONCILE", "cpu", f"CPU_TOPOLOGY_{key.upper()}",
                       asum.get(key), lsum.get(key), "REVALIDATE_HRB_CPU_NUMA_TOPOLOGY")
    if acpu.get("effective_logical_cpus") != lcpu.get("effective_logical_cpus"):
        add_change(changes, "RUNTIME_REBIND", "cpu", "CPUSET_EFFECTIVE_CHANGED",
                   acpu.get("effective_logical_cpus"), lcpu.get("effective_logical_cpus"),
                   "REFRESH_HRB_VISIBLE_CPU_INVENTORY")

    before_accel, after_accel = accel_map(accepted), accel_map(live)
    for identity in sorted(set(after_accel) - set(before_accel)):
        add_change(changes, "COMPONENT_ADMISSION", "accelerator", "ACCELERATOR_ADDED", None, identity,
                   "PLAN_RELEVANT_PROVIDER_MATERIALIZATION_THEN_NORMAL_ADMISSION")
    for identity in sorted(set(before_accel) - set(after_accel)):
        add_change(changes, "RUNTIME_REBIND", "accelerator", "ACCELERATOR_MISSING", identity, None,
                   "MARK_DEPENDENT_PROVIDER_INACTIVE_REFRESH_HRB_NO_AUTOMATIC_UNINSTALL")
    for identity in sorted(set(before_accel) & set(after_accel)):
        before, after = before_accel[identity], after_accel[identity]
        before_backends = sorted((x.get("name"), x.get("available"), x.get("binding_scope"))
                                 for x in before.get("backends", []) if isinstance(x, dict))
        after_backends = sorted((x.get("name"), x.get("available"), x.get("binding_scope"))
                                for x in after.get("backends", []) if isinstance(x, dict))
        if before.get("kernel_driver") != after.get("kernel_driver") or before_backends != after_backends:
            add_change(changes, "CONFIG_RECONCILE", "accelerator", "ACCELERATOR_RUNTIME_CHANGED",
                       {"driver": before.get("kernel_driver"), "backends": before_backends},
                       {"driver": after.get("kernel_driver"), "backends": after_backends},
                       "REQUALIFY_ONLY_AFFECTED_PROVIDER_BACKENDS")

    adesk, ldesk = accepted.get("desktop", {}), live.get("desktop", {})
    aname = adesk.get("desktop", {}).get("desktop")
    lname = ldesk.get("desktop", {}).get("desktop")
    if aname != lname:
        add_change(changes, "CONFIG_RECONCILE", "desktop", "DESKTOP_CHANGED", aname, lname,
                   "REBIND_DESKTOP_INTEGRATION_MATERIALIZE_ONLY_MISSING_OPTIONAL_ADAPTERS")
    asession = adesk.get("session", {}).get("type")
    lsession = ldesk.get("session", {}).get("type")
    if asession != lsession:
        add_change(changes, "RUNTIME_REBIND", "desktop", "SESSION_TYPE_CHANGED", asession, lsession,
                   "REBIND_QT_PLATFORM_AND_XDG_SESSION_INTEGRATION")
    astrategy = adesk.get("integration", {}).get("strategy")
    lstrategy = ldesk.get("integration", {}).get("strategy")
    if astrategy != lstrategy:
        add_change(changes, "CONFIG_RECONCILE", "desktop", "DESKTOP_INTEGRATION_STRATEGY_CHANGED",
                   astrategy, lstrategy, "RECONCILE_QT_NATIVE_KF6_OR_XDG_ADAPTER_SELECTION")

    def application_instances(snapshot: dict[str, Any]) -> set[str]:
        inventory = snapshot.get("application_runtimes", {})
        identities: set[str] = set()
        for app in inventory.get("applications", []) if isinstance(inventory, dict) else []:
            if not isinstance(app, dict):
                continue
            for candidate in app.get("candidates", []):
                if isinstance(candidate, dict) and candidate.get("identity"):
                    identities.add(str(candidate["identity"]))
        return identities

    before_apps = application_instances(accepted)
    after_apps = application_instances(live)
    for identity in sorted(after_apps - before_apps):
        add_change(
            changes, "COMPONENT_ADMISSION", "application_runtime", "APPLICATION_RUNTIME_INSTANCE_ADDED",
            None, identity, "REVALIDATE_APPLICATION_RUNTIME_WITHOUT_AUTOMATIC_ACTIVATION",
        )
    for identity in sorted(before_apps - after_apps):
        add_change(
            changes, "RUNTIME_REBIND", "application_runtime", "APPLICATION_RUNTIME_INSTANCE_REMOVED",
            identity, None, "MARK_INSTANCE_UNAVAILABLE_AND_REQUIRE_EXPLICIT_RESELECTION",
        )

    aos, los = accepted.get("os", {}), live.get("os", {})
    if aos.get("id") != los.get("id"):
        add_change(changes, "COMPONENT_ADMISSION", "distribution", "DISTRIBUTION_FAMILY_CHANGED",
                   aos.get("id"), los.get("id"), "RESELECT_NATIVE_PACKAGE_MANAGER_ADAPTER")
    apm = accepted.get("package_managers", {}).get("primary")
    lpm = live.get("package_managers", {}).get("primary")
    if apm != lpm:
        add_change(changes, "COMPONENT_ADMISSION", "distribution", "PACKAGE_MANAGER_CHANGED",
                   apm, lpm, "RESELECT_NATIVE_PACKAGE_MANAGER_ADAPTER")
    if accepted.get("kernel_release") != live.get("kernel_release"):
        add_change(changes, "OBSERVATIONAL_DRIFT", "host", "KERNEL_RELEASE_CHANGED",
                   accepted.get("kernel_release"), live.get("kernel_release"),
                   "LOG_AND_REVALIDATE_ONLY_AFFECTED_BINDINGS")

    classification = "NO_DRIFT" if not changes else max(
        (item["classification"] for item in changes), key=lambda value: DRIFT_ORDER[value]
    )
    return {
        "schema": "fa3.host-drift-report.v1", "classification": classification,
        "changes": changes, "changed_domains": sorted({x["domain"] for x in changes}),
        "discovery_is_authority": False, "current_host_promotion_claim": False,
    }


def materialization_plan(snapshot: dict[str, Any]) -> dict[str, Any]:
    desktop = snapshot.get("desktop", {})
    integration = desktop.get("integration", {})
    components = ["FA3_QT6_QML_CORE", "FA3_XDG_FREEDESKTOP_INTEROP"]
    if integration.get("qt_desktop_native_integration"):
        components.append("FA3_QT_NATIVE_DESKTOP_ADAPTER")
    if integration.get("kf6_enhancement"):
        components.append("FA3_KF6_ENHANCEMENT_ADAPTER")
    if desktop.get("capabilities", {}).get("xdg_desktop_portal") == "PASS":
        components.append("FA3_XDG_DESKTOP_PORTAL_ADAPTER")
    selectors: list[str] = []
    for row in snapshot.get("accelerators", []):
        if isinstance(row, dict):
            selector = f"ACCELERATOR_VENDOR:{str(row.get('vendor', 'UNKNOWN')).upper()}"
            if selector not in selectors:
                selectors.append(selector)
    return {
        "schema": "fa3.selective-materialization-plan.v1",
        "components": components,
        "accelerator_provider_selectors": selectors,
        "cpu_only": len(snapshot.get("accelerators", [])) == 0,
        "package_manager": snapshot.get("package_managers", {}).get("primary"),
        "application_distribution_frontends": snapshot.get("package_managers", {}).get("application_distribution_frontends", []),
        "application_runtime_registry": "FA3-APPLICATION-RUNTIME-DISCOVERY-001",
        "plan_is_install_authority": False, "automatic_uninstall": False,
        "global_environment_mutation": False, "fixed_default_port_claim": False,
        "capability_count": snapshot.get("capability_count"),
    }


def installation_profile(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "fa3.installation-host-profile.v1", "profile_id": PROFILE_ID,
        "profile_kind": "INSTALLATION_BASELINE", "immutable": True,
        "snapshot": snapshot, "snapshot_sha256": digest(snapshot),
        "current_host_promotion_claim": False,
    }


def default_state_root() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".local/state") / "fa3/host-adaptation"


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    os.replace(tmp, path)


def initialize(root: Path, state_root: Path) -> dict[str, Any]:
    path = state_root / "installation-host-profile.json"
    if path.exists():
        return {"status": "ALREADY_INITIALIZED", "path": str(path), "profile": loadj(path),
                "current_host_promotion_claim": False}
    profile = installation_profile(capture_live_snapshot(root))
    atomic_write(path, profile)
    return {"status": "INITIALIZED", "path": str(path), "profile": profile,
            "current_host_promotion_claim": False}


def cpu_floor(root: Path) -> int:
    profile = loadj(root / "canonical/profiles/FA3-HARDWARE-BASELINE-001.json")
    return int(profile["portable_minimum"]["cpu"]["physical_cores_per_qualifying_cpu_min"])


def check_startup(root: Path, state_root: Path) -> dict[str, Any]:
    installation = state_root / "installation-host-profile.json"
    accepted = state_root / "accepted-host-profile.json"
    if not installation.is_file():
        return {
            "schema": "fa3.host-adaptation-startup-report.v1",
            "classification": "SAFETY_BLOCK", "findings": ["INSTALLATION_HOST_PROFILE_MISSING"],
            "recommended_action": "RUN_INSTALLER_HOST_INITIALIZATION",
            "current_host_promotion_claim": False, "action_authority_exercised": False,
        }
    baseline_path = accepted if accepted.is_file() else installation
    baseline = loadj(baseline_path)
    baseline_snapshot = baseline.get("snapshot")
    if not isinstance(baseline_snapshot, dict):
        raise RuntimeError(f"baseline snapshot missing: {baseline_path}")
    live = capture_live_snapshot(root)
    drift = compare_snapshots(baseline_snapshot, live, physical_core_min=cpu_floor(root))
    return {
        "schema": "fa3.host-adaptation-startup-report.v1", "profile_id": PROFILE_ID,
        "comparison_baseline": str(baseline_path),
        "comparison_baseline_kind": baseline.get("profile_kind", "EXTERNAL_ACCEPTED_PROFILE"),
        "classification": drift["classification"], "drift": drift,
        "materialization_plan": materialization_plan(live),
        "live_snapshot_sha256": live["snapshot_sha256"],
        "current_host_promotion_claim": False, "action_authority_exercised": False,
        "accepted_profile_written": False,
    }


def canonical_check(root: Path) -> dict[str, Any]:
    findings: list[str] = []
    profile = loadj(root / "canonical/profiles/FA3-HOST-ADAPTATION-001.json")
    contract = loadj(root / "canonical/contracts/FA3-HOST-ADAPTATION-CONTRACTS-001.json")
    decision = loadj(root / "canonical/decisions/FA3-DEC-HOST-ADAPTATION-2026-09-27.json")
    hardware = loadj(root / "canonical/profiles/FA3-HARDWARE-BASELINE-001.json")
    desktop = loadj(root / "canonical/FA3-DESKTOP-BASE-001.json")
    if not (
        profile.get("id") == PROFILE_ID and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False
        and profile.get("authority", {}).get("resource_admission_placement_lease") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        and profile.get("lifecycle", {}).get("startup_live_discovery_required") is True
        and profile.get("lifecycle", {}).get("discovery_may_mutate_host") is False
        and profile.get("selective_materialization", {}).get("install_only_host_relevant_implementations") is True
        and profile.get("selective_materialization", {}).get("missing_device_does_not_trigger_automatic_uninstall") is True
        and profile.get("desktop_integration", {}).get("application_core") == "QT6_QML_NATIVE"
        and profile.get("desktop_integration", {}).get("lowest_common_denominator_restriction") is False
        and profile.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append("HOST_ADAPTATION_PROFILE_DRIFT")
    if not (
        contract.get("id") == CONTRACT_ID and contract.get("capability_count") == CAPABILITY_COUNT
        and contract.get("materialization_semantics", {}).get("output_is_plan_not_install_authority") is True
        and contract.get("evidence_semantics", {}).get("discovery_snapshot_is_current_host_fact_not_promotion") is True
    ):
        findings.append("HOST_ADAPTATION_CONTRACT_DRIFT")
    if not (
        decision.get("id") == DECISION_ID and decision.get("capability_count") == CAPABILITY_COUNT
        and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0
        and decision.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append("HOST_ADAPTATION_DECISION_DRIFT")
    if hardware.get("authority", {}).get("admission_placement_reservation_lease") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
        findings.append("HRB_AUTHORITY_DRIFT")
    if hardware.get("portable_minimum", {}).get("accelerator", {}).get("qualifying_device_count_min") != 0:
        findings.append("CPU_ONLY_BASELINE_DRIFT")
    if not (
        desktop.get("policy", {}).get("application_toolkit") == "QT6_QML_NATIVE"
        and desktop.get("policy", {}).get("qt_native_desktop_integration") == "PREFERRED_WHEN_AVAILABLE"
        and desktop.get("policy", {}).get("qt_native_feature_downleveling") == "FORBIDDEN_WHEN_SAFE_AND_AVAILABLE"
    ):
        findings.append("QT6_DESKTOP_POLICY_DRIFT")
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def synthetic_snapshot(*, kernel: str = "k1", session: str = "wayland", desktop: str = "KDE_PLASMA",
                       strategy: str = "QT6_NATIVE_KF6_ENHANCED",
                       accelerators: list[dict[str, Any]] | None = None, cores: int = 16) -> dict[str, Any]:
    return {
        "capability_count": CAPABILITY_COUNT,
        "os": {"id": "linux-a", "id_like": [], "version_id": "1"},
        "package_managers": {"primary": "apt-get", "available": ["apt-get"]},
        "kernel_release": kernel,
        "cpu": {"effective_logical_cpus": list(range(cores)),
                "summary": {"packages_total": 1, "physical_cores_total": cores,
                            "physical_cores_visible": cores, "numa_domains_total": 1}},
        "accelerators": accelerators or [],
        "desktop": {"result": "PASS", "desktop": {"desktop": desktop}, "session": {"type": session},
                    "integration": {"strategy": strategy,
                                    "qt_desktop_native_integration": desktop in {"KDE_PLASMA", "LXQT"},
                                    "kf6_enhancement": desktop == "KDE_PLASMA"},
                    "capabilities": {"xdg_desktop_portal": "PASS"}},
    }


def regression_check() -> dict[str, Any]:
    base = synthetic_snapshot()
    cases: dict[str, bool] = {}
    cases["no_drift"] = compare_snapshots(base, base, physical_core_min=8)["classification"] == "NO_DRIFT"
    cases["kernel_observational"] = compare_snapshots(base, synthetic_snapshot(kernel="k2"), physical_core_min=8)["classification"] == "OBSERVATIONAL_DRIFT"
    cases["session_rebind"] = compare_snapshots(base, synthetic_snapshot(session="x11"), physical_core_min=8)["classification"] == "RUNTIME_REBIND"
    amd = {
        "discovery_id": "synthetic:accelerator-a",
        "stable_device_id": "synthetic-accelerator-a",
        "vendor": "AMD",
        "pci_bdf": None,
        "kernel_driver": "amdgpu",
        "workload_compatible": True,
        "backends": [],
    }
    cases["new_accelerator_admission"] = compare_snapshots(base, synthetic_snapshot(accelerators=[amd]), physical_core_min=8)["classification"] == "COMPONENT_ADMISSION"
    missing = compare_snapshots(synthetic_snapshot(accelerators=[amd]), base, physical_core_min=8)
    cases["missing_accelerator_no_uninstall"] = (
        missing["classification"] == "RUNTIME_REBIND"
        and any("NO_AUTOMATIC_UNINSTALL" in x["recommended_action"] for x in missing["changes"])
    )
    cases["cpu_floor_safety"] = compare_snapshots(base, synthetic_snapshot(cores=4), physical_core_min=8)["classification"] == "SAFETY_BLOCK"
    cases["cpu_only_plan"] = materialization_plan(base)["accelerator_provider_selectors"] == []
    gnome = synthetic_snapshot(desktop="GNOME", strategy="QT6_XDG_FREEDESKTOP")
    cases["non_qt_keeps_qt_core"] = "FA3_QT6_QML_CORE" in materialization_plan(gnome)["components"]
    passed = sum(bool(x) for x in cases.values())
    return {"result": "PASS" if passed == len(cases) else "FAIL", "passed": passed, "total": len(cases), "cases": cases}


def self_test(root: Path) -> dict[str, Any]:
    canonical, regression = canonical_check(root), regression_check()
    return {
        "schema": "fa3.host-adaptation-self-test.v1", "profile_id": PROFILE_ID,
        "result": "PASS" if canonical["result"] == "PASS" and regression["result"] == "PASS" else "FAIL",
        "canonical": canonical, "regression": regression, "capability_count": CAPABILITY_COUNT,
        "current_host_production_evidence": False, "current_host_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 host-adaptive discovery, drift and materialization planner")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--initialize", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--snapshot", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--state-root", type=Path, default=default_state_root())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            report = self_test(args.root.resolve())
        elif args.snapshot:
            report = capture_live_snapshot(args.root.resolve())
        elif args.initialize:
            report = initialize(args.root.resolve(), args.state_root.expanduser())
        else:
            report = check_startup(args.root.resolve(), args.state_root.expanduser())
    except Exception as exc:
        report = {"schema": "fa3.host-adaptation-error.v1", "result": "FAIL",
                  "classification": "SAFETY_BLOCK", "findings": [str(exc)],
                  "current_host_promotion_claim": False}
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) if args.json
          else f"FA3 host adaptation: {report.get('result', report.get('classification', report.get('status', 'UNKNOWN')))}")
    return 2 if report.get("result") == "FAIL" or report.get("classification") == "SAFETY_BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
