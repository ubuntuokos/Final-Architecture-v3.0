#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import shlex
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "fa3.plasma-secret-service-current-host-diagnostic.v4"
ALIAS = "org.kde.secretservicecompat"
STANDARD = "org.freedesktop.secrets"
OBJECT_PATH = "/org/freedesktop/secrets"
STANDARD_INTERFACE = "org.freedesktop.Secret.Service"
KDE_REFERENCE_BUS_NAMES = (
    "org.kde.kwalletd6",
    "org.kde.kwalletd5",
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


def _user_bus_names(env: Mapping[str, str]) -> set[str]:
    proc = _run_busctl(env, ["--no-pager", "--list"])
    if proc is None or proc.returncode != 0:
        return set()
    return {line.split()[0] for line in proc.stdout.splitlines() if line.split()}


_SYSTEMD_SHOW_PROPERTIES = (
    "LoadState",
    "ActiveState",
    "SubState",
    "Result",
    "ExecMainCode",
    "ExecMainStatus",
    "UnitFileState",
    "NRestarts",
)
_SECRET_UNIT_RE = re.compile(r"(?:ksecret|secretservice|secret-service|kwallet|freedesktop.*secret)", re.IGNORECASE)


def _run_systemctl_user(
    env: Mapping[str, str],
    argv: list[str],
    *,
    timeout: int = 5,
) -> subprocess.CompletedProcess[str] | None:
    systemctl = shutil.which("systemctl")
    if (
        not systemctl
        or Path(systemctl).name != "systemctl"
        or not env.get("DBUS_SESSION_BUS_ADDRESS")
    ):
        return None
    try:
        return subprocess.run(
            [systemctl, "--user", *argv],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _systemd_show_fields(text: str) -> dict[str, Any]:
    allowed = set(_SYSTEMD_SHOW_PROPERTIES)
    out: dict[str, Any] = {}
    for raw in (text or "").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key not in allowed:
            continue
        value = value.strip()
        if key in {"ExecMainCode", "ExecMainStatus", "NRestarts"}:
            try:
                out[key] = int(value)
            except ValueError:
                out[key] = None
        else:
            out[key] = value[:128]
    return out


def _activation_search_roots(env: Mapping[str, str]) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = [
        ("SYSTEM_USR_LOCAL", Path("/usr/local/share/dbus-1/services")),
        ("SYSTEM_USR", Path("/usr/share/dbus-1/services")),
    ]
    data_home = env.get("XDG_DATA_HOME")
    if data_home:
        roots.append(("USER_XDG_DATA_HOME", Path(data_home) / "dbus-1/services"))
    elif env.get("HOME"):
        roots.append(("USER_DEFAULT_DATA_HOME", Path(env["HOME"]) / ".local/share/dbus-1/services"))
    seen: set[str] = set()
    out: list[tuple[str, Path]] = []
    for scope, path in roots:
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append((scope, path))
    return out


def _exec_basename(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        parts = shlex.split(raw, posix=True)
    except ValueError:
        return None
    if not parts:
        return None
    return Path(parts[0]).name[:128] or None


def _dbus_activation_descriptors(env: Mapping[str, str]) -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    targets = {ALIAS, STANDARD, *KDE_REFERENCE_BUS_NAMES}
    for scope, root in _activation_search_roots(env):
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.service")):
            parser = configparser.RawConfigParser(interpolation=None, strict=False)
            try:
                parser.read(path, encoding="utf-8")
            except (OSError, configparser.Error, UnicodeError):
                continue
            section = "D-BUS Service"
            if not parser.has_section(section):
                continue
            name = parser.get(section, "Name", fallback="").strip()
            if name not in targets:
                continue
            systemd_service = parser.get(section, "SystemdService", fallback="").strip()
            exec_raw = parser.get(section, "Exec", fallback="").strip()
            descriptors.append(
                {
                    "name": name,
                    "source_scope": scope,
                    "service_file": path.name[:160],
                    "systemd_service": systemd_service[:160] or None,
                    "exec_basename": _exec_basename(exec_raw),
                    "exec_arguments_emitted": False,
                }
            )
    return descriptors[:16]


def _systemd_unit_search_roots(env: Mapping[str, str]) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    runtime_dir = env.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        roots.append(("USER_RUNTIME", Path(runtime_dir) / "systemd/user"))
    config_home = env.get("XDG_CONFIG_HOME")
    if config_home:
        roots.append(("USER_CONFIG", Path(config_home) / "systemd/user"))
    elif env.get("HOME"):
        roots.append(("USER_CONFIG", Path(env["HOME"]) / ".config/systemd/user"))
    roots.extend(
        [
            ("ADMIN_RUNTIME", Path("/run/systemd/user")),
            ("ADMIN", Path("/etc/systemd/user")),
            ("LOCAL_VENDOR", Path("/usr/local/lib/systemd/user")),
            ("VENDOR", Path("/usr/lib/systemd/user")),
            ("VENDOR_COMPAT", Path("/lib/systemd/user")),
        ]
    )
    seen: set[str] = set()
    result: list[tuple[str, Path]] = []
    for scope, path in roots:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append((scope, path))
    return result


def _unit_entry_descriptor(scope: str, path: Path) -> dict[str, Any] | None:
    try:
        if not os.path.lexists(path):
            return None
        is_symlink = path.is_symlink()
        is_regular = path.is_file() and not is_symlink
        is_dev_null_mask = False
        if is_symlink:
            try:
                is_dev_null_mask = os.path.realpath(path) == "/dev/null"
            except OSError:
                is_dev_null_mask = False
        return {
            "scope": scope,
            "entry_present": True,
            "entry_type": "SYMLINK" if is_symlink else "REGULAR_FILE" if is_regular else "OTHER",
            "is_dev_null_mask": is_dev_null_mask,
            "path_emitted": False,
            "symlink_target_emitted": False,
            "content_read": False,
        }
    except OSError:
        return {
            "scope": scope,
            "entry_present": True,
            "entry_type": "UNREADABLE",
            "is_dev_null_mask": False,
            "path_emitted": False,
            "symlink_target_emitted": False,
            "content_read": False,
        }


def _systemd_user_mask_origins(
    env: Mapping[str, str],
    units: list[str] | set[str] | tuple[str, ...],
) -> dict[str, Any]:
    roots = _systemd_unit_search_roots(env)
    rows: list[dict[str, Any]] = []
    for unit in sorted({str(unit) for unit in units if str(unit).endswith(".service")}):
        entries: list[dict[str, Any]] = []
        for scope, root in roots:
            descriptor = _unit_entry_descriptor(scope, root / unit)
            if descriptor is not None:
                entries.append(descriptor)
        masking_scopes = [
            str(entry["scope"])
            for entry in entries
            if entry.get("is_dev_null_mask") is True
        ]
        rows.append(
            {
                "unit": unit,
                "entries": entries,
                "masking_scopes": masking_scopes,
                "effective_mask_origin": masking_scopes[0] if masking_scopes else None,
            }
        )
    return {
        "unit_count": len(rows),
        "units": rows,
        "scope_precedence": [scope for scope, _ in roots],
        "paths_emitted": False,
        "symlink_targets_emitted": False,
        "unit_contents_read": False,
    }


def _systemd_user_service_diagnostic(
    env: Mapping[str, str],
    activation_descriptors: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_units: set[str] = {
        str(item.get("systemd_service"))
        for item in activation_descriptors
        if isinstance(item.get("systemd_service"), str)
        and str(item.get("systemd_service")).endswith(".service")
    }

    listed = _run_systemctl_user(
        env,
        ["list-units", "--all", "--type=service", "--no-legend", "--plain", "--no-pager"],
    )
    if listed is not None and listed.returncode == 0:
        for raw in listed.stdout.splitlines():
            parts = raw.split()
            if parts and parts[0].endswith(".service") and _SECRET_UNIT_RE.search(parts[0]):
                candidate_units.add(parts[0])

    unit_files = _run_systemctl_user(
        env,
        ["list-unit-files", "--type=service", "--no-legend", "--no-pager"],
    )
    unit_file_states: dict[str, str] = {}
    if unit_files is not None and unit_files.returncode == 0:
        for raw in unit_files.stdout.splitlines():
            parts = raw.split()
            if not parts or not parts[0].endswith(".service"):
                continue
            unit = parts[0]
            if _SECRET_UNIT_RE.search(unit) or unit in candidate_units:
                candidate_units.add(unit)
                unit_file_states[unit] = parts[1][:64] if len(parts) > 1 else ""

    units: list[dict[str, Any]] = []
    for unit in sorted(candidate_units)[:32]:
        show_args = ["show", unit, "--no-pager"]
        for prop in _SYSTEMD_SHOW_PROPERTIES:
            show_args.extend(["--property", prop])
        proc = _run_systemctl_user(env, show_args)
        row: dict[str, Any] = {
            "unit": unit,
            "show_returncode": None if proc is None else proc.returncode,
        }
        if proc is not None and proc.returncode == 0:
            row.update(_systemd_show_fields(proc.stdout))
        if unit in unit_file_states and "UnitFileState" not in row:
            row["UnitFileState"] = unit_file_states[unit]
        units.append(row)

    return {
        "queried": listed is not None or unit_files is not None,
        "list_units_returncode": None if listed is None else listed.returncode,
        "list_unit_files_returncode": None if unit_files is None else unit_files.returncode,
        "candidate_count": len(candidate_units),
        "units": units,
        "mask_origins": _systemd_user_mask_origins(env, candidate_units),
        "raw_journal_collected": False,
        "process_argv_collected": False,
        "environment_collected": False,
    }


def _redact_unique_names(text: str) -> str:
    value = re.sub(r":[A-Za-z0-9_.-]+", "<UNIQUE_NAME>", text or "")
    return " ".join(value.split())[:300]


def _name_owner_diagnostic(
    env: Mapping[str, str],
    bus_name: str,
    *,
    live_names: set[str],
) -> dict[str, Any]:
    if bus_name not in live_names:
        return {
            "queried": False,
            "reason": "WELL_KNOWN_NAME_NOT_LIVE",
            "returncode": None,
            "owner_parse_ok": False,
            "unique_owner": None,
            "stdout_shape": None,
        }
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
    if proc is None:
        return {
            "queried": True,
            "reason": "BUSCTL_UNAVAILABLE_OR_CALL_FAILED",
            "returncode": None,
            "owner_parse_ok": False,
            "unique_owner": None,
            "stdout_shape": None,
        }
    stdout = proc.stdout or ""
    match = re.fullmatch(r'\s*s\s+"?(:[A-Za-z0-9_.-]+)"?\s*', stdout)
    owner = match.group(1) if match else None
    return {
        "queried": True,
        "reason": None if proc.returncode == 0 else "GET_NAME_OWNER_NONZERO",
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
    target_live: bool,
) -> dict[str, Any]:
    if not target or not target_live:
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


def collect_plasma_secret_service_diagnostic(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    supplied = dict(os.environ if env is None else env)
    names = _user_bus_names(supplied)
    state = _read_config_state(supplied)

    alias_live = ALIAS in names
    standard_live = STANDARD in names
    alias_owner = _name_owner_diagnostic(supplied, ALIAS, live_names=names)
    standard_owner = _name_owner_diagnostic(supplied, STANDARD, live_names=names)
    alias_owner_name = alias_owner.get("unique_owner")
    standard_owner_name = standard_owner.get("unique_owner")
    activation_descriptors = _dbus_activation_descriptors(supplied)
    systemd_user_services = _systemd_user_service_diagnostic(
        supplied,
        activation_descriptors,
    )

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
        "reference_alias_live": alias_live,
        "standard_secret_service_live": standard_live,
        "reference_alias_owner": alias_owner,
        "standard_name_owner": standard_owner,
        "reference_alias_introspection": _introspection_diagnostic(
            supplied,
            ALIAS,
            target_live=alias_live,
        ),
        "reference_owner_introspection": _introspection_diagnostic(
            supplied,
            alias_owner_name if isinstance(alias_owner_name, str) else None,
            target_live=isinstance(alias_owner_name, str) and bool(alias_owner_name),
        ),
        "standard_name_introspection": _introspection_diagnostic(
            supplied,
            STANDARD,
            target_live=standard_live,
        ),
        "standard_owner_introspection": _introspection_diagnostic(
            supplied,
            standard_owner_name if isinstance(standard_owner_name, str) else None,
            target_live=isinstance(standard_owner_name, str) and bool(standard_owner_name),
        ),
        "dbus_activation_descriptors": activation_descriptors,
        "systemd_user_services": systemd_user_services,
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
