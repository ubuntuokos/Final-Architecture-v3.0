#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import time
import xml.etree.ElementTree as ET
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


def _reference_secret_service_activation_aliases(env: Mapping[str, str]) -> list[str]:
    """Return reference-desktop activation aliases without making them core dependencies."""
    if classify_desktop(env).get("desktop") != "KDE_PLASMA":
        return []
    path = Path(__file__).resolve().parents[1] / "canonical/FA3-DESKTOP-PLASMA-001.json"
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    activation = profile.get("secret_service_activation", {})
    alias = activation.get("activation_bus_name")
    if not (
        profile.get("id") == PLASMA_ID
        and activation.get("mode") == "REFERENCE_PROVIDER_SECRET_SERVICE_ADAPTER"
        and activation.get("core_requirement") is False
        and activation.get("architectural_authority") is False
        and activation.get("standard_interface_required") is True
        and activation.get("standard_bus_name_preferred") is True
        and activation.get("compatibility_bus_name_allowed") is True
        and activation.get("compatibility_endpoint_may_satisfy_fa3_secret_backend") is True
        and activation.get("activation_alias_semantics") == "FA3_REFERENCE_ADAPTER_ONLY_NO_SYSTEM_SECRET_SERVICE_CLAIM"
        and activation.get("preferred_standard_bus_name") == "org.freedesktop.secrets"
        and activation.get("object_path") == "/org/freedesktop/secrets"
        and activation.get("interface") == "org.freedesktop.Secret.Service"
        and isinstance(alias, str)
        and alias.count(".") >= 2
        and not alias.startswith(".")
        and not alias.endswith(".")
    ):
        return []
    return [alias]


def _secret_service_introspect(busctl: str, bus_name: str, env: Mapping[str, str]):
    try:
        return subprocess.run(
            [
                busctl,
                "--user",
                "--xml-interface",
                "introspect",
                bus_name,
                "/org/freedesktop/secrets",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _secret_service_interface_proven(proc: subprocess.CompletedProcess[str] | None) -> bool:
    if proc is None or proc.returncode != 0 or not proc.stdout.strip():
        return False
    try:
        root = ET.fromstring(proc.stdout)
    except ET.ParseError:
        return False
    return any(
        node.tag == "interface"
        and node.attrib.get("name") == "org.freedesktop.Secret.Service"
        for node in root.iter()
    )


def _dbus_start_service_by_name(
    busctl: str,
    bus_name: str,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str] | None:
    """Ask the user bus to activate a provider by name without trusting that alias as capability evidence."""
    try:
        return subprocess.run(
            [
                busctl,
                "--user",
                "call",
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "StartServiceByName",
                "su",
                bus_name,
                "0",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _activation_diagnostic(proc: subprocess.CompletedProcess[str] | None) -> tuple[bool, str | None]:
    if proc is None:
        return False, "activation invocation unavailable"
    if proc.returncode == 0:
        return True, None
    detail = (proc.stderr or proc.stdout or f"returncode={proc.returncode}").strip()
    return False, detail[:500] or f"returncode={proc.returncode}"


def _dbus_name_owner(
    busctl: str,
    bus_name: str,
    env: Mapping[str, str],
) -> str | None:
    """Resolve a live well-known D-Bus name to its unique owner without trusting provider APIs."""
    try:
        proc = subprocess.run(
            [
                busctl,
                "--user",
                "call",
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "GetNameOwner",
                "s",
                bus_name,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    match = re.fullmatch(r'\s*s\s+"(:[A-Za-z0-9_.-]+)"\s*', proc.stdout or "")
    return match.group(1) if match else None


def _secret_service_probe(env: Mapping[str, str]) -> dict[str, Any]:
    busctl = shutil.which("busctl")
    if not busctl or not env.get("DBUS_SESSION_BUS_ADDRESS"):
        return {
            "available": False,
            "live_name": False,
            "standard_interface": False,
            "dbus_activation_attempted": False,
            "reference_activation_attempted": False,
            "standard_name_verified": False,
            "compatibility_endpoint_verified": False,
            "introspection_format": "BUSCTL_XML_INTERFACE",
        }

    standard_name = "org.freedesktop.secrets"
    # A standard bus name is not trusted by name alone. It must expose the
    # standard interface on the standard Secret Service object path.
    live_name = _dbus_name_present(standard_name, env)
    if live_name:
        verify = _secret_service_introspect(busctl, standard_name, env)
        verified_interface = _secret_service_interface_proven(verify)
        if verified_interface:
            return {
                "available": True,
                "live_name": True,
                "standard_interface": True,
                "dbus_activation_attempted": False,
                "reference_activation_attempted": False,
                "standard_name_verified": True,
                "compatibility_endpoint_verified": False,
                "introspection_format": "BUSCTL_XML_INTERFACE",
            }

    # Standards-only D-Bus activation remains the preferred portable route.
    proc = _secret_service_introspect(busctl, standard_name, env)
    standard_interface = _secret_service_interface_proven(proc)
    if standard_interface:
        return {
            "available": True,
            "live_name": True,
            "standard_interface": True,
            "dbus_activation_attempted": True,
            "reference_activation_attempted": False,
            "standard_name_verified": True,
            "compatibility_endpoint_verified": False,
            "introspection_format": "BUSCTL_XML_INTERFACE",
        }

    # The Tier-1 reference desktop may expose the same Secret Service API
    # under a provider-specific compatibility bus name. This is not system-wide
    # Secret Service interoperability and must never imply that the standard
    # org.freedesktop.secrets name is present. It may satisfy only FA3's logical
    # SECRET_BACKEND through the canonical reference adapter, and only when
    # exact XML introspection proves org.freedesktop.Secret.Service on the
    # standard object path.
    aliases = _reference_secret_service_activation_aliases(env)
    reference_activation_succeeded = False
    activation_errors: list[str] = []
    for alias in aliases:
        activation_proc = _dbus_start_service_by_name(busctl, alias, env)
        activation_ok, activation_error = _activation_diagnostic(activation_proc)
        reference_activation_succeeded = reference_activation_succeeded or activation_ok
        if activation_error:
            activation_errors.append(f"{alias}: {activation_error}")

        # Activation may complete asynchronously. Prefer the standard endpoint.
        # If the provider intentionally exposes only its reference alias, prove
        # the exact standard interface there and scope that proof to the FA3
        # reference adapter only.
        for _ in range(5):
            verify = _secret_service_introspect(busctl, standard_name, env)
            verified_standard = _secret_service_interface_proven(verify)
            if verified_standard:
                return {
                    "available": True,
                    "live_name": True,
                    "standard_interface": True,
                    "dbus_activation_attempted": True,
                    "reference_activation_attempted": True,
                    "reference_activation_succeeded": reference_activation_succeeded,
                    "reference_activation_method": "DBUS_START_SERVICE_BY_NAME",
                    "reference_activation_errors": activation_errors,
                    "standard_name_verified": True,
                    "compatibility_endpoint_verified": False,
                    "fa3_reference_adapter_only": False,
                    "introspection_format": "BUSCTL_XML_INTERFACE",
                }

            alias_verify = _secret_service_introspect(busctl, alias, env)
            alias_interface = _secret_service_interface_proven(alias_verify)
            if alias_interface:
                return {
                    "available": True,
                    "live_name": False,
                    "standard_interface": True,
                    "dbus_activation_attempted": True,
                    "reference_activation_attempted": True,
                    "reference_activation_succeeded": reference_activation_succeeded,
                    "reference_activation_method": "DBUS_START_SERVICE_BY_NAME",
                    "reference_activation_errors": activation_errors,
                    "standard_name_verified": False,
                    "compatibility_endpoint_verified": True,
                    "reference_owner_verified": False,
                    "reference_owner_unique_name": None,
                    "fa3_reference_adapter_only": True,
                    "introspection_format": "BUSCTL_XML_INTERFACE",
                }

            # Some D-Bus implementations can expose an activation alias whose
            # well-known name is transient during startup. Bind fallback proof
            # to the alias' live unique owner, then require the exact standard
            # Secret Service interface on the standard object path. This does
            # not trust any provider-private interface or claim system-wide
            # org.freedesktop.secrets interoperability.
            if activation_ok:
                owner = _dbus_name_owner(busctl, alias, env)
                if owner:
                    owner_verify = _secret_service_introspect(busctl, owner, env)
                    owner_interface = _secret_service_interface_proven(owner_verify)
                    if owner_interface:
                        return {
                            "available": True,
                            "live_name": False,
                            "standard_interface": True,
                            "dbus_activation_attempted": True,
                            "reference_activation_attempted": True,
                            "reference_activation_succeeded": reference_activation_succeeded,
                            "reference_activation_method": "DBUS_START_SERVICE_BY_NAME",
                            "reference_activation_errors": activation_errors,
                            "standard_name_verified": False,
                            "compatibility_endpoint_verified": True,
                            "reference_owner_verified": True,
                            "reference_owner_unique_name": owner,
                            "fa3_reference_adapter_only": True,
                            "introspection_format": "BUSCTL_XML_INTERFACE",
                        }
            time.sleep(0.2)

    return {
        "available": False,
        "live_name": live_name,
        "standard_interface": False,
        "dbus_activation_attempted": True,
        "reference_activation_attempted": bool(aliases),
        "reference_activation_succeeded": reference_activation_succeeded,
        "reference_activation_method": "DBUS_START_SERVICE_BY_NAME" if aliases else None,
        "reference_activation_errors": activation_errors,
        "standard_name_verified": False,
        "compatibility_endpoint_verified": False,
        "reference_owner_verified": False,
        "reference_owner_unique_name": None,
        "fa3_reference_adapter_only": False,
        "introspection_format": "BUSCTL_XML_INTERFACE",
    }

def collect_runtime_probes(env: Mapping[str, str] | None = None) -> dict[str, Any]:
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
        "secret_service_reference_activation_attempted": secret_probe.get("reference_activation_attempted", False),
        "secret_service_reference_activation_succeeded": secret_probe.get("reference_activation_succeeded", False),
        "secret_service_reference_activation_method": secret_probe.get("reference_activation_method"),
        "secret_service_reference_activation_errors": secret_probe.get("reference_activation_errors", []),
        "secret_service_standard_name_verified": secret_probe.get("standard_name_verified", secret_service),
        "secret_service_compatibility_endpoint_verified": secret_probe.get("compatibility_endpoint_verified", False),
        "secret_service_reference_owner_verified": secret_probe.get("reference_owner_verified", False),
        "secret_service_reference_owner_unique_name": secret_probe.get("reference_owner_unique_name"),
        "secret_service_fa3_reference_adapter_only": secret_probe.get("fa3_reference_adapter_only", False),
        "secret_service_introspection_format": secret_probe.get("introspection_format"),
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
        "secret_backend_evidence": {
            "secret_service_available": bool(probes.get("secret_service")),
            "standard_name_verified": bool(probes.get("secret_service_standard_name_verified")),
            "standard_interface_verified": bool(probes.get("secret_service_standard_interface")),
            "standard_activation_attempted": bool(probes.get("secret_service_dbus_activation_attempted")),
            "reference_activation_attempted": bool(probes.get("secret_service_reference_activation_attempted")),
            "reference_activation_succeeded": bool(probes.get("secret_service_reference_activation_succeeded")),
            "reference_activation_method": probes.get("secret_service_reference_activation_method"),
            "reference_activation_errors": probes.get("secret_service_reference_activation_errors", []),
            "compatibility_endpoint_verified": bool(probes.get("secret_service_compatibility_endpoint_verified")),
            "reference_owner_verified": bool(probes.get("secret_service_reference_owner_verified")),
            "reference_owner_unique_name": probes.get("secret_service_reference_owner_unique_name"),
            "fa3_reference_adapter_only": bool(probes.get("secret_service_fa3_reference_adapter_only")),
            "system_secret_service_interop": "PASS" if bool(probes.get("secret_service_standard_name_verified")) else "LIMITED",
            "introspection_format": probes.get("secret_service_introspection_format"),
            "fa3_vault_available": bool(probes.get("fa3_vault")),
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

    secret_activation = plasma.get("secret_service_activation", {})
    if not (
        plasma.get("id") == PLASMA_ID
        and plasma.get("base_profile") == BASE_ID
        and plasma.get("priority") == "P1"
        and plasma.get("architectural_authority") is False
        and plasma.get("new_capabilities") == 0
        and plasma.get("capability_count") == CAPABILITY_COUNT
        and plasma.get("constraints", {}).get("enhancements_must_not_become_core_requirements") is True
        and plasma.get("appearance", {}).get("runtime_dependency") is False
        and secret_activation.get("mode") == "REFERENCE_PROVIDER_SECRET_SERVICE_ADAPTER"
        and secret_activation.get("core_requirement") is False
        and secret_activation.get("architectural_authority") is False
        and secret_activation.get("standard_interface_required") is True
        and secret_activation.get("standard_bus_name_preferred") is True
        and secret_activation.get("compatibility_bus_name_allowed") is True
        and secret_activation.get("compatibility_endpoint_may_satisfy_fa3_secret_backend") is True
        and secret_activation.get("activation_alias_semantics") == "FA3_REFERENCE_ADAPTER_ONLY_NO_SYSTEM_SECRET_SERVICE_CLAIM"
        and secret_activation.get("standard_bus_name_required_for_system_interop") is True
        and secret_activation.get("compatibility_endpoint_scope") == "FA3_REFERENCE_ADAPTER_ONLY"
        and secret_activation.get("activation_method") == "DBUS_START_SERVICE_BY_NAME"
        and secret_activation.get("preferred_standard_bus_name") == "org.freedesktop.secrets"
        and secret_activation.get("object_path") == "/org/freedesktop/secrets"
        and secret_activation.get("interface") == "org.freedesktop.Secret.Service"
        and isinstance(secret_activation.get("activation_bus_name"), str)
        and bool(secret_activation.get("activation_bus_name"))
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
