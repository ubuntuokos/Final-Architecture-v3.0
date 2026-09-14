#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from fa3_release_baseline import module_active_capability_count

BASE_ID = "FA3-DESKTOP-BASE-001"
PLASMA_ID = "FA3-DESKTOP-PLASMA-001"
GATE_ID = "FA3-GATE-DESKTOP-PORTABILITY-001"
CAPABILITY_COUNT = module_active_capability_count(__file__)

SUPPORTED_TIER_2 = {
    "COSMIC": "COSMIC",
    "GNOME": "GNOME",
    "CINNAMON": "CINNAMON",
    "XFCE": "XFCE",
    "LXQT": "LXQT",
}
COMPATIBLE_TIER_3 = {
    "SWAY": "SWAY",
    "HYPRLAND": "HYPRLAND",
    "MATE": "MATE",
}


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "available", "pass"}


def _desktop_token(env: Mapping[str, str]) -> str:
    raw = ":".join(
        part for part in (
            env.get("XDG_CURRENT_DESKTOP", ""),
            env.get("DESKTOP_SESSION", ""),
        ) if part
    )
    return raw.upper().replace("-", "_").replace(" ", "_")


def classify_desktop(env: Mapping[str, str]) -> dict[str, Any]:
    token = _desktop_token(env)
    if "KDE" in token or "PLASMA" in token:
        return {"desktop": "KDE_PLASMA", "tier": 1, "support": "REFERENCE"}
    for marker, name in SUPPORTED_TIER_2.items():
        if marker in token:
            return {"desktop": name, "tier": 2, "support": "SUPPORTED_TARGET"}
    for marker, name in COMPATIBLE_TIER_3.items():
        if marker in token:
            return {"desktop": name, "tier": 3, "support": "COMPATIBLE"}
    return {
        "desktop": "GENERIC_XDG" if token else "UNKNOWN",
        "tier": 3,
        "support": "COMPATIBLE_IF_BASELINE_PASSES",
    }


def _dbus_name_present(name: str) -> bool:
    if not shutil.which("busctl"):
        return False
    try:
        proc = subprocess.run(
            ["busctl", "--user", "--no-pager", "--list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and name in proc.stdout


def collect_runtime_probes(env: Mapping[str, str] | None = None) -> dict[str, bool]:
    env = dict(os.environ if env is None else env)
    portal_override = env.get("FA3_DESKTOP_PORTAL_AVAILABLE")
    secret_override = env.get("FA3_SECRET_SERVICE_AVAILABLE")
    portal = _truthy(portal_override) if portal_override is not None else _dbus_name_present("org.freedesktop.portal.Desktop")
    secret_service = _truthy(secret_override) if secret_override is not None else _dbus_name_present("org.freedesktop.secrets")
    return {
        "linux_host": platform.system().lower() == "linux",
        "xdg_runtime": bool(env.get("XDG_RUNTIME_DIR")),
        "dbus_session": bool(env.get("DBUS_SESSION_BUS_ADDRESS")),
        "portal": portal,
        "secret_service": secret_service,
        "fa3_vault": _truthy(env.get("FA3_VAULT_AVAILABLE")),
        "uri_open": bool(shutil.which("xdg-open")) or portal,
        "notifications": bool(shutil.which("notify-send")) or portal,
        "clipboard": any(shutil.which(cmd) for cmd in ("wl-copy", "xclip", "xsel")),
        "power_inhibit": bool(shutil.which("systemd-inhibit")) or portal,
        "system_tray": _truthy(env.get("FA3_SYSTEM_TRAY_AVAILABLE")),
        "global_shortcuts": _truthy(env.get("FA3_GLOBAL_SHORTCUT_AVAILABLE")),
        "screen_capture_portal": portal,
    }


def _capability(state: bool, required: bool = False) -> str:
    if state:
        return "PASS"
    return "FAIL" if required else "LIMITED"


def evaluate_desktop(
    env: Mapping[str, str] | None = None,
    probes: Mapping[str, bool] | None = None,
    *,
    require_gui: bool = False,
) -> dict[str, Any]:
    env = dict(os.environ if env is None else env)
    probes = dict(collect_runtime_probes(env) if probes is None else probes)
    desktop = classify_desktop(env)
    session_type = env.get("XDG_SESSION_TYPE", "").strip().lower()
    local_gui = session_type in {"wayland", "x11"} or bool(env.get("WAYLAND_DISPLAY") or env.get("DISPLAY"))

    if not local_gui and not require_gui:
        return {
            "gate_id": GATE_ID,
            "result": "PASS",
            "mode": "HEADLESS_COMPATIBLE",
            "local_gui_required": False,
            "desktop": desktop,
            "session": {"type": session_type or "headless", "support": "NOT_APPLICABLE"},
            "capabilities": {"desktop_integration": "NOT_APPLICABLE"},
            "findings": [],
            "capability_count": CAPABILITY_COUNT,
        }

    required = {
        "linux_host": bool(probes.get("linux_host")),
        "xdg_runtime": bool(probes.get("xdg_runtime")),
        "dbus_session": bool(probes.get("dbus_session")),
        "uri_open": bool(probes.get("uri_open")),
        "secret_backend": bool(probes.get("secret_service")) or bool(probes.get("fa3_vault")),
        "local_gui_session": local_gui,
    }
    optional = {
        "xdg_desktop_portal": bool(probes.get("portal")),
        "notifications": bool(probes.get("notifications")),
        "clipboard": bool(probes.get("clipboard")),
        "power_inhibit": bool(probes.get("power_inhibit")),
        "system_tray": bool(probes.get("system_tray")),
        "global_shortcuts": bool(probes.get("global_shortcuts")),
        "screen_capture_portal": bool(probes.get("screen_capture_portal")),
    }
    failed = [name for name, ok in required.items() if not ok]
    findings = [
        {"severity": "P0", "code": "DESKTOP_REQUIRED_CAPABILITY_MISSING", "capability": name}
        for name in failed
    ]
    for name, ok in optional.items():
        if not ok:
            findings.append({"severity": "INFO", "code": "DESKTOP_OPTIONAL_CAPABILITY_LIMITED", "capability": name})

    if session_type == "wayland":
        session_support = "PREFERRED"
    elif session_type == "x11":
        session_support = "SUPPORTED_COMPATIBILITY"
    else:
        session_support = "UNKNOWN_OR_INFERRED"

    return {
        "gate_id": GATE_ID,
        "result": "FAIL" if failed else "PASS",
        "mode": "LOCAL_GUI",
        "local_gui_required": require_gui,
        "desktop": desktop,
        "session": {"type": session_type or "inferred", "support": session_support},
        "capabilities": {
            **{name: _capability(ok, required=True) for name, ok in required.items()},
            **{name: _capability(ok, required=False) for name, ok in optional.items()},
        },
        "findings": findings,
        "capability_count": CAPABILITY_COUNT,
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_check(root: Path) -> dict[str, Any]:
    root = Path(root)
    paths = {
        "base": root / "canonical/FA3-DESKTOP-BASE-001.json",
        "plasma": root / "canonical/FA3-DESKTOP-PLASMA-001.json",
        "gate": root / "canonical/FA3-GATE-DESKTOP-PORTABILITY-001.json",
    }
    missing = [str(path.relative_to(root)) for path in paths.values() if not path.is_file()]
    if missing:
        return {"result": "FAIL", "findings": [{"code": "DESKTOP_CANONICAL_ARTIFACT_MISSING", "path": p} for p in missing]}

    base = _load_json(paths["base"])
    plasma = _load_json(paths["plasma"])
    gate = _load_json(paths["gate"])
    findings: list[dict[str, Any]] = []

    forbidden = set(base.get("policy", {}).get("direct_core_dependencies_forbidden", []))
    required_forbidden = {"KWALLET_DIRECT_API", "KIO_DIRECT_API", "KWIN_PRIVATE_API", "PLASMA_PRIVATE_DBUS_API"}
    tier2 = set(base.get("support_tiers", {}).get("tier_2_supported_targets", []))

    if not (
        base.get("id") == BASE_ID
        and base.get("priority") == "P0"
        and base.get("architectural_authority") is False
        and base.get("new_capabilities") == 0
        and base.get("new_architectural_authorities") == 0
        and base.get("capability_count") == CAPABILITY_COUNT
        and base.get("policy", {}).get("plasma_is_reference_not_core_dependency") is True
        and base.get("policy", {}).get("wayland") == "PREFERRED"
        and base.get("policy", {}).get("x11") == "SUPPORTED_COMPATIBILITY"
        and base.get("policy", {}).get("system_tray") == "OPTIONAL_ENHANCEMENT"
        and base.get("policy", {}).get("global_shortcuts") == "OPTIONAL_ENHANCEMENT"
        and required_forbidden.issubset(forbidden)
        and {"COSMIC_WAYLAND", "GNOME_WAYLAND", "CINNAMON", "XFCE", "LXQT"}.issubset(tier2)
    ):
        findings.append({"code": "DESKTOP_BASE_POLICY_DRIFT", "severity": "P0"})

    if not (
        plasma.get("id") == PLASMA_ID
        and plasma.get("base_profile") == BASE_ID
        and plasma.get("priority") == "P1"
        and plasma.get("architectural_authority") is False
        and plasma.get("new_capabilities") == 0
        and plasma.get("capability_count") == CAPABILITY_COUNT
        and plasma.get("constraints", {}).get("enhancements_must_not_become_core_requirements") is True
        and plasma.get("appearance", {}).get("runtime_dependency") is False
    ):
        findings.append({"code": "DESKTOP_PLASMA_REFERENCE_DRIFT", "severity": "P0"})

    if not (
        gate.get("id") == GATE_ID
        and gate.get("priority") == "P0"
        and gate.get("fail_closed") is True
        and gate.get("base_profile") == BASE_ID
        and gate.get("reference_profile") == PLASMA_ID
        and gate.get("new_capabilities") == 0
        and gate.get("new_architectural_authorities") == 0
        and gate.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append({"code": "DESKTOP_GATE_RECORD_DRIFT", "severity": "P0"})

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def regression_check() -> dict[str, Any]:
    full = {
        "linux_host": True,
        "xdg_runtime": True,
        "dbus_session": True,
        "portal": True,
        "secret_service": True,
        "fa3_vault": False,
        "uri_open": True,
        "notifications": True,
        "clipboard": True,
        "power_inhibit": True,
        "system_tray": True,
        "global_shortcuts": True,
        "screen_capture_portal": True,
    }
    cases: dict[str, bool] = {}

    plasma = evaluate_desktop(
        {"XDG_CURRENT_DESKTOP": "KDE", "XDG_SESSION_TYPE": "wayland", "XDG_RUNTIME_DIR": "/run/user/1000", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
        full,
        require_gui=True,
    )
    cases["plasma_wayland_reference_pass"] = plasma["result"] == "PASS" and plasma["desktop"]["tier"] == 1 and plasma["session"]["support"] == "PREFERRED"

    cosmic = evaluate_desktop(
        {"XDG_CURRENT_DESKTOP": "COSMIC", "XDG_SESSION_TYPE": "wayland", "XDG_RUNTIME_DIR": "/run/user/1000", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
        {**full, "system_tray": False, "global_shortcuts": False},
        require_gui=True,
    )
    cases["cosmic_generic_xdg_pass"] = cosmic["result"] == "PASS" and cosmic["desktop"]["tier"] == 2 and cosmic["capabilities"]["system_tray"] == "LIMITED"

    gnome_x11 = evaluate_desktop(
        {"XDG_CURRENT_DESKTOP": "GNOME", "XDG_SESSION_TYPE": "x11", "XDG_RUNTIME_DIR": "/run/user/1000", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus", "DISPLAY": ":0"},
        {**full, "portal": False},
        require_gui=True,
    )
    cases["x11_compatibility_pass"] = gnome_x11["result"] == "PASS" and gnome_x11["session"]["support"] == "SUPPORTED_COMPATIBILITY"

    no_dbus = evaluate_desktop(
        {"XDG_CURRENT_DESKTOP": "XFCE", "XDG_SESSION_TYPE": "x11", "XDG_RUNTIME_DIR": "/run/user/1000", "DISPLAY": ":0"},
        {**full, "dbus_session": False},
        require_gui=True,
    )
    cases["missing_required_dbus_fails_closed"] = no_dbus["result"] == "FAIL" and no_dbus["capabilities"]["dbus_session"] == "FAIL"

    vault_fallback = evaluate_desktop(
        {"XDG_CURRENT_DESKTOP": "LXQt", "XDG_SESSION_TYPE": "wayland", "XDG_RUNTIME_DIR": "/run/user/1000", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"},
        {**full, "secret_service": False, "fa3_vault": True},
        require_gui=True,
    )
    cases["fa3_vault_satisfies_secret_backend"] = vault_fallback["result"] == "PASS" and vault_fallback["capabilities"]["secret_backend"] == "PASS"

    headless = evaluate_desktop({}, {key: False for key in full}, require_gui=False)
    cases["headless_without_local_gui_requirement_pass"] = headless["result"] == "PASS" and headless["mode"] == "HEADLESS_COMPATIBLE"

    passed = sum(bool(value) for value in cases.values())
    return {"result": "PASS" if passed == len(cases) else "FAIL", "passed": passed, "total": len(cases), "cases": cases}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def self_test(root: Path | None = None) -> dict[str, Any]:
    root = repository_root() if root is None else Path(root)
    canonical = canonical_check(root)
    regression = regression_check()
    result = "PASS" if canonical["result"] == "PASS" and regression["result"] == "PASS" else "FAIL"
    return {
        "gate_id": GATE_ID,
        "result": result,
        "canonical": canonical,
        "regression": regression,
        "current_host_production_evidence": False,
        "capability_count": CAPABILITY_COUNT,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Generic Linux desktop admission and portability gate")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--require-gui", action="store_true", help="fail closed when a local GUI baseline is unavailable")
    parser.add_argument("--self-test", action="store_true", help="run canonical and deterministic regression checks")
    parser.add_argument("--root", type=Path, default=repository_root(), help="repository root for self-test")
    args = parser.parse_args()

    report = self_test(args.root) if args.self_test else evaluate_desktop(require_gui=args.require_gui)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"{report['gate_id']}: {report['result']}")
        for finding in report.get("findings", []):
            print(f"- {finding.get('severity', 'INFO')}: {finding.get('code')}: {finding.get('capability', '')}")
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
