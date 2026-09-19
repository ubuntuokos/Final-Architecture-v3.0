#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
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


def _owned_socket(path: Path, uid: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISSOCK(info.st_mode) and info.st_uid == uid


def _safe_runtime_dir(uid: int) -> Path | None:
    path = Path(f"/run/user/{uid}")
    try:
        info = path.lstat()
    except OSError:
        return None
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid:
        return None
    return path


def _systemd_user_environment_snapshot(env: Mapping[str, str]) -> dict[str, str]:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return {}
    try:
        proc = subprocess.run(
            [systemctl, "--user", "show-environment"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if proc.returncode != 0:
        return {}
    wanted = {
        "XDG_CURRENT_DESKTOP",
        "DESKTOP_SESSION",
        "XDG_SESSION_TYPE",
        "XDG_RUNTIME_DIR",
        "DBUS_SESSION_BUS_ADDRESS",
        "WAYLAND_DISPLAY",
        "DISPLAY",
    }
    out: dict[str, str] = {}
    for raw in proc.stdout.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key in wanted and value:
            out[key] = value
    return out


def _loginctl_session_properties(uid: int) -> dict[str, str]:
    loginctl = shutil.which("loginctl")
    if not loginctl:
        return {}

    session_ids: list[str] = []
    try:
        preferred = subprocess.run(
            [loginctl, "show-user", str(uid), "-p", "Display", "--value"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if preferred.returncode == 0 and preferred.stdout.strip():
            session_ids.append(preferred.stdout.strip())

        listed = subprocess.run(
            [loginctl, "list-sessions", "--no-legend", "--no-pager"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if listed.returncode == 0:
            for raw in listed.stdout.splitlines():
                parts = raw.split()
                if len(parts) >= 2 and parts[1] == str(uid) and parts[0] not in session_ids:
                    session_ids.append(parts[0])
    except (OSError, subprocess.SubprocessError):
        return {}

    for session_id in session_ids:
        try:
            proc = subprocess.run(
                [
                    loginctl,
                    "show-session",
                    session_id,
                    "-p", "Id",
                    "-p", "User",
                    "-p", "Type",
                    "-p", "Remote",
                    "-p", "Active",
                    "-p", "State",
                    "-p", "Class",
                    "-p", "Desktop",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode != 0:
            continue
        props: dict[str, str] = {}
        for raw in proc.stdout.splitlines():
            if "=" in raw:
                key, value = raw.split("=", 1)
                props[key] = value
        if (
            props.get("User") == str(uid)
            and props.get("Type", "").lower() in {"wayland", "x11"}
            and props.get("Remote", "").lower() == "no"
            and props.get("Active", "").lower() == "yes"
        ):
            return props
    return {}


def _user_bus_names(env: Mapping[str, str]) -> set[str]:
    if not shutil.which("busctl") or not env.get("DBUS_SESSION_BUS_ADDRESS"):
        return set()
    try:
        proc = subprocess.run(
            ["busctl", "--user", "--no-pager", "--list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode != 0:
        return set()
    return {
        line.split()[0]
        for line in proc.stdout.splitlines()
        if line.split()
    }


def discover_current_user_session_environment(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    merged = dict(os.environ if env is None else env)
    uid = os.getuid()
    sources: dict[str, str] = {}

    runtime = _safe_runtime_dir(uid)
    if runtime is not None:
        if not merged.get("XDG_RUNTIME_DIR"):
            merged["XDG_RUNTIME_DIR"] = str(runtime)
            sources["xdg_runtime"] = "OWNED_RUN_USER_DIRECTORY"
        bus = runtime / "bus"
        if not merged.get("DBUS_SESSION_BUS_ADDRESS") and _owned_socket(bus, uid):
            merged["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus}"
            sources["dbus_session"] = "OWNED_USER_BUS_SOCKET"

    for key, value in _systemd_user_environment_snapshot(merged).items():
        if not merged.get(key):
            merged[key] = value
            sources[key.lower()] = "SYSTEMD_USER_ENVIRONMENT"

    session = _loginctl_session_properties(uid)
    if session:
        if not merged.get("XDG_SESSION_TYPE"):
            merged["XDG_SESSION_TYPE"] = session.get("Type", "").lower()
            sources["xdg_session_type"] = "LOGINCTL_ACTIVE_LOCAL_SESSION"
        desktop = session.get("Desktop", "").strip()
        if desktop and not merged.get("XDG_CURRENT_DESKTOP"):
            merged["XDG_CURRENT_DESKTOP"] = desktop
            sources["xdg_current_desktop"] = "LOGINCTL_ACTIVE_LOCAL_SESSION"

    if (
        runtime is not None
        and merged.get("XDG_SESSION_TYPE", "").lower() == "wayland"
        and not merged.get("WAYLAND_DISPLAY")
    ):
        for candidate in sorted(runtime.glob("wayland-*")):
            if candidate.name.endswith(".lock"):
                continue
            if _owned_socket(candidate, uid):
                merged["WAYLAND_DISPLAY"] = candidate.name
                sources["wayland_display"] = "OWNED_RUNTIME_WAYLAND_SOCKET"
                break

    bus_names = _user_bus_names(merged)
    kde_bus_identity = "org.kde.KWin" in bus_names or "org.kde.plasmashell" in bus_names
    if kde_bus_identity and not merged.get("XDG_CURRENT_DESKTOP"):
        merged["XDG_CURRENT_DESKTOP"] = "KDE"
        sources["xdg_current_desktop"] = "USER_DBUS_KDE_IDENTITY"

    evidence = {
        "uid": uid,
        "runtime_dir_proven": runtime is not None,
        "user_bus_socket_proven": bool(merged.get("DBUS_SESSION_BUS_ADDRESS")),
        "active_local_graphical_session_proven": bool(session),
        "session_type": merged.get("XDG_SESSION_TYPE", "").lower() or None,
        "desktop_class": classify_desktop(merged).get("desktop"),
        "wayland_socket_proven": bool(merged.get("WAYLAND_DISPLAY")) if merged.get("XDG_SESSION_TYPE", "").lower() == "wayland" else None,
        "kde_bus_identity_proven": kde_bus_identity,
        "portal_bus_identity_proven": "org.freedesktop.portal.Desktop" in bus_names,
        "secret_service_bus_identity_proven": "org.freedesktop.secrets" in bus_names,
        "sources": sources,
    }
    return {"environment": merged, "evidence": evidence}


def _dbus_name_present(name: str, env: Mapping[str, str] | None = None) -> bool:
    if not shutil.which("busctl"):
        return False
    try:
        proc = subprocess.run(
            ["busctl", "--user", "--no-pager", "--list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
            env=dict(os.environ if env is None else env),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and name in proc.stdout


def _secret_service_probe(env: Mapping[str, str]) -> dict[str, bool]:
    live_name = _dbus_name_present("org.freedesktop.secrets", env)
    if live_name:
        return {
            "available": True,
            "live_name": True,
            "standard_interface": True,
            "dbus_activation_attempted": False,
        }

    busctl = shutil.which("busctl")
    if not busctl or not env.get("DBUS_SESSION_BUS_ADDRESS"):
        return {
            "available": False,
            "live_name": False,
            "standard_interface": False,
            "dbus_activation_attempted": False,
        }

    # A standards-only Introspect call is intentionally used here: D-Bus may
    # activate an installed Secret Service provider, but no secret is read,
    # written, unlocked, or provider-specific API invoked.
    try:
        proc = subprocess.run(
            [
                busctl,
                "--user",
                "introspect",
                "org.freedesktop.secrets",
                "/org/freedesktop/secrets",
                "org.freedesktop.Secret.Service",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return {
            "available": False,
            "live_name": False,
            "standard_interface": False,
            "dbus_activation_attempted": True,
        }

    standard_interface = (
        proc.returncode == 0
        and "org.freedesktop.Secret.Service" in proc.stdout
    )
    return {
        "available": standard_interface,
        "live_name": False,
        "standard_interface": standard_interface,
        "dbus_activation_attempted": True,
    }


def collect_runtime_probes(env: Mapping[str, str] | None = None) -> dict[str, bool]:
    env = dict(os.environ if env is None else env)
    portal_override = env.get("FA3_DESKTOP_PORTAL_AVAILABLE")
    secret_override = env.get("FA3_SECRET_SERVICE_AVAILABLE")
    portal = _truthy(portal_override) if portal_override is not None else _dbus_name_present("org.freedesktop.portal.Desktop", env)
    secret_probe = (
        {
            "available": _truthy(secret_override),
            "live_name": _truthy(secret_override),
            "standard_interface": _truthy(secret_override),
            "dbus_activation_attempted": False,
        }
        if secret_override is not None
        else _secret_service_probe(env)
    )
    secret_service = secret_probe["available"]
    return {
        "linux_host": platform.system().lower() == "linux",
        "xdg_runtime": bool(env.get("XDG_RUNTIME_DIR")),
        "dbus_session": bool(env.get("DBUS_SESSION_BUS_ADDRESS")),
        "portal": portal,
        "secret_service": secret_service,
        "secret_service_live_name": secret_probe["live_name"],
        "secret_service_standard_interface": secret_probe["standard_interface"],
        "secret_service_dbus_activation_attempted": secret_probe["dbus_activation_attempted"],
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
