#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "fa3.plasma-secret-service-current-host-diagnostic.v3"
ALIAS = "org.kde.secretservicecompat"
STANDARD = "org.freedesktop.secrets"
KSECRETD_BUS = "org.kde.ksecretd"
KWALLETD_BUS = "org.kde.kwalletd6"
OBJECT_PATH = "/org/freedesktop/secrets"
STANDARD_INTERFACE = "org.freedesktop.Secret.Service"

ACTIVATION_CANDIDATES = (
    Path("/usr/share/dbus-1/services/org.kde.secretservicecompat.service"),
    Path("/usr/local/share/dbus-1/services/org.kde.secretservicecompat.service"),
)


def _parse_kde_bool(raw: str | None, default: bool) -> tuple[bool, str]:
    if raw is None:
        return default, "UPSTREAM_DEFAULT"
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True, "EXPLICIT_CONFIG"
    if value in {"0", "false", "no", "off"}:
        return False, "EXPLICIT_CONFIG"
    return default, "INVALID_CONFIG_FALLBACK_TO_UPSTREAM_DEFAULT"


def _config_path(env: Mapping[str, str]) -> Path | None:
    if env.get("XDG_CONFIG_HOME"):
        return Path(env["XDG_CONFIG_HOME"]) / "kwalletrc"
    if env.get("HOME"):
        return Path(env["HOME"]) / ".config" / "kwalletrc"
    return None


def _read_config_state(env: Mapping[str, str]) -> dict[str, Any]:
    path = _config_path(env)
    parser = configparser.RawConfigParser(interpolation=None, strict=False)
    file_present = bool(path and path.is_file())
    parse_ok = False
    if file_present and path is not None:
        try:
            parser.read(path, encoding="utf-8")
            parse_ok = True
        except (OSError, configparser.Error, UnicodeError):
            parse_ok = False

    def raw(section: str, option: str) -> str | None:
        if not parse_ok or not parser.has_section(section) or not parser.has_option(section, option):
            return None
        try:
            return parser.get(section, option, raw=True)
        except (configparser.Error, OSError):
            return None

    ksecret_enabled, ksecret_source = _parse_kde_bool(raw("KSecretD", "Enabled"), True)
    fdo_enabled, fdo_source = _parse_kde_bool(raw("org.freedesktop.secrets", "apiEnabled"), True)
    return {
        "config_file_present": file_present,
        "config_parse_ok": parse_ok if file_present else None,
        "ksecretd_enabled_effective": ksecret_enabled,
        "ksecretd_enabled_source": ksecret_source,
        "fdo_secrets_api_enabled_effective": fdo_enabled,
        "fdo_secrets_api_enabled_source": fdo_source,
    }


def _run_busctl(
    env: Mapping[str, str],
    argv: list[str],
    *,
    timeout: int = 5,
) -> subprocess.CompletedProcess[str] | None:
    busctl = shutil.which("busctl")
    if not busctl or not env.get("DBUS_SESSION_BUS_ADDRESS"):
        return None
    try:
        return subprocess.run(
            [busctl, "--user", *argv],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _redact_unique_names(text: str) -> str:
    value = re.sub(r":[A-Za-z0-9_.-]+", "<UNIQUE_NAME>", text or "")
    return " ".join(value.split())[:300]


def _bus_inventory(env: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    proc = _run_busctl(env, ["--no-pager", "--no-legend", "--list"])
    if proc is None or proc.returncode != 0:
        return {}
    inventory: dict[str, dict[str, Any]] = {}
    for raw in proc.stdout.splitlines():
        parts = raw.split()
        if len(parts) < 3:
            continue
        name, pid_token, process = parts[:3]
        inventory[name] = {
            "listed": True,
            "pid_present": pid_token.isdigit(),
            "process": process[:128],
        }
    return inventory


def _user_bus_names(env: Mapping[str, str]) -> set[str]:
    """Compatibility helper: listed names may be activatable and are not proof of ownership."""
    return set(_bus_inventory(env))


def _name_owner_diagnostic(
    env: Mapping[str, str],
    bus_name: str,
    *,
    inventory: Mapping[str, Mapping[str, Any]] | None = None,
    live_names: set[str] | None = None,
) -> dict[str, Any]:
    proc = _run_busctl(
        env,
        [
            "call",
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "GetNameOwner",
            "s",
            bus_name,
        ],
    )
    listed = bus_name in (inventory or {}) or (live_names is not None and bus_name in live_names)
    inventory_row = dict((inventory or {}).get(bus_name, {}))
    if proc is None:
        return {
            "listed": listed,
            "inventory": inventory_row,
            "queried": False,
            "returncode": None,
            "owner_parse_ok": False,
            "unique_owner": None,
            "stdout_shape": None,
            "stderr_summary": "",
        }
    stdout = proc.stdout or ""
    match = re.fullmatch(r'\s*s\s+"?(:[A-Za-z0-9_.-]+)"?\s*', stdout)
    owner = match.group(1) if proc.returncode == 0 and match else None
    return {
        "listed": listed,
        "inventory": inventory_row,
        "queried": True,
        "returncode": proc.returncode,
        "owner_parse_ok": owner is not None,
        "unique_owner": owner,
        "stdout_shape": _redact_unique_names(stdout),
        "stderr_summary": _redact_unique_names(proc.stderr or "") if proc.returncode != 0 else "",
    }


def _introspection_diagnostic(
    env: Mapping[str, str],
    target: str | None,
    *,
    target_live: bool | None = None,
) -> dict[str, Any]:
    if not target or target_live is False:
        return {
            "queried": False,
            "returncode": None,
            "xml_parse_ok": False,
            "standard_interface_present": False,
            "interface_names": [],
            "stderr_summary": "",
        }
    proc = _run_busctl(
        env,
        ["--xml-interface", "introspect", target, OBJECT_PATH],
    )
    if proc is None:
        return {
            "queried": True,
            "returncode": None,
            "xml_parse_ok": False,
            "standard_interface_present": False,
            "interface_names": [],
            "stderr_summary": "BUSCTL_UNAVAILABLE_OR_INTROSPECTION_FAILED",
        }
    interfaces: list[str] = []
    parse_ok = False
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            root = ET.fromstring(proc.stdout)
            interfaces = sorted({
                str(node.attrib.get("name"))
                for node in root.iter()
                if node.tag == "interface" and node.attrib.get("name")
            })[:64]
            parse_ok = True
        except ET.ParseError:
            parse_ok = False
    return {
        "queried": True,
        "returncode": proc.returncode,
        "xml_parse_ok": parse_ok,
        "standard_interface_present": STANDARD_INTERFACE in interfaces,
        "interface_names": interfaces,
        "stderr_summary": _redact_unique_names(proc.stderr or "") if proc.returncode != 0 else "",
    }


def _process_count(name: str) -> dict[str, Any]:
    pgrep = shutil.which("pgrep")
    if not pgrep or Path(pgrep).name != "pgrep":
        return {"probe_available": False, "count": None}
    try:
        proc = subprocess.run(
            [pgrep, "-u", str(os.getuid()), "-x", name],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return {"probe_available": True, "count": None}
    pids = [line for line in proc.stdout.splitlines() if line.strip().isdigit()]
    return {
        "probe_available": True,
        "count": len(pids),
        "returncode": proc.returncode,
    }


def _activation_entry() -> dict[str, Any]:
    path = next((candidate for candidate in ACTIVATION_CANDIDATES if candidate.is_file()), None)
    if path is None:
        return {
            "present": False,
            "path": None,
            "name": None,
            "exec": None,
        }
    parser = configparser.RawConfigParser(interpolation=None, strict=False)
    try:
        parser.read(path, encoding="utf-8")
        name = parser.get("D-BUS Service", "Name", raw=True, fallback=None)
        exec_value = parser.get("D-BUS Service", "Exec", raw=True, fallback=None)
    except (OSError, configparser.Error, UnicodeError):
        name = None
        exec_value = None
    return {
        "present": True,
        "path": str(path),
        "name": name,
        "exec": exec_value,
    }


def _package_versions() -> dict[str, Any]:
    dpkg = shutil.which("dpkg-query")
    packages = ("kwallet6", "libpam-kwallet5", "plasma-workspace")
    if not dpkg or Path(dpkg).name != "dpkg-query":
        return {name: None for name in packages}
    out: dict[str, Any] = {}
    for package in packages:
        try:
            proc = subprocess.run(
                [dpkg, "-W", "-f=${Version}", package],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            out[package] = None
            continue
        value = proc.stdout.strip() if proc.returncode == 0 else ""
        out[package] = value[:128] or None
    return out


def _environment_presence(env: Mapping[str, str]) -> dict[str, bool]:
    keys = (
        "DBUS_SESSION_BUS_ADDRESS",
        "XDG_RUNTIME_DIR",
        "XDG_SESSION_TYPE",
        "WAYLAND_DISPLAY",
        "DISPLAY",
        "QT_QPA_PLATFORM",
        "PAM_KWALLET5_LOGIN",
    )
    return {key: bool(env.get(key)) for key in keys}


def collect_plasma_secret_service_diagnostic(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    supplied = dict(os.environ if env is None else env)
    inventory = _bus_inventory(supplied)
    state = _read_config_state(supplied)

    owners = {
        ALIAS: _name_owner_diagnostic(supplied, ALIAS, inventory=inventory),
        STANDARD: _name_owner_diagnostic(supplied, STANDARD, inventory=inventory),
    }
    if supplied.get("DBUS_SESSION_BUS_ADDRESS"):
        owners[KSECRETD_BUS] = _name_owner_diagnostic(supplied, KSECRETD_BUS, inventory=inventory)
        owners[KWALLETD_BUS] = _name_owner_diagnostic(supplied, KWALLETD_BUS, inventory=inventory)
    else:
        owners[KSECRETD_BUS] = {"queried": False, "owner_parse_ok": False, "unique_owner": None}
        owners[KWALLETD_BUS] = {"queried": False, "owner_parse_ok": False, "unique_owner": None}
    alias_owner = owners[ALIAS].get("unique_owner")
    standard_owner = owners[STANDARD].get("unique_owner")

    return {
        "schema": SCHEMA,
        "read_only": True,
        "secret_values_read": False,
        "secret_values_emitted": False,
        "provider_specific_diagnostic_only": True,
        "admission_effect": "NONE_DIAGNOSTIC_ONLY",
        "promotion_effect": "NONE_DIAGNOSTIC_ONLY",
        "object_path": OBJECT_PATH,
        "required_standard_interface": STANDARD_INTERFACE,
        "ksecretd_binary_present": shutil.which("ksecretd") is not None,
        "reference_alias_listed": ALIAS in inventory,
        "reference_alias_live": bool(alias_owner),
        "standard_secret_service_listed": STANDARD in inventory,
        "standard_secret_service_live": bool(standard_owner),
        "bus_name_owners": owners,
        "reference_alias_owner": owners[ALIAS],
        "standard_name_owner": owners[STANDARD],
        "reference_alias_introspection": _introspection_diagnostic(
            supplied,
            ALIAS if alias_owner else None,
        ),
        "reference_owner_introspection": _introspection_diagnostic(
            supplied,
            alias_owner if isinstance(alias_owner, str) else None,
        ),
        "standard_name_introspection": _introspection_diagnostic(
            supplied,
            STANDARD if standard_owner else None,
        ),
        "standard_owner_introspection": _introspection_diagnostic(
            supplied,
            standard_owner if isinstance(standard_owner, str) else None,
        ),
        "runtime_processes": {
            "ksecretd": _process_count("ksecretd"),
            "kwalletd6": _process_count("kwalletd6"),
        },
        "activation_entry": _activation_entry(),
        "package_versions": _package_versions(),
        "environment_presence": _environment_presence(supplied),
        **state,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect read-only KDE Plasma Secret Service current-host diagnostics"
    )
    parser.add_argument(
        "--output",
        default=".fa3-current-host/global-closure/diagnostics/cap013-plasma-secret-service.json",
    )
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = Path.cwd() / output
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        from fa3_desktop_admission import discover_current_user_session_environment

        session = discover_current_user_session_environment()
        report = collect_plasma_secret_service_diagnostic(session["environment"])
        report["session_discovery"] = session["evidence"]
        report["collection_status"] = "PASS"
    except Exception as exc:
        report = {
            "schema": SCHEMA,
            "read_only": True,
            "secret_values_read": False,
            "secret_values_emitted": False,
            "provider_specific_diagnostic_only": True,
            "admission_effect": "NONE_DIAGNOSTIC_ONLY",
            "promotion_effect": "NONE_DIAGNOSTIC_ONLY",
            "collection_status": "INCOMPLETE",
            "collection_error_type": type(exc).__name__,
        }

    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
