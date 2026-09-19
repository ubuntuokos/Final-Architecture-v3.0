#!/usr/bin/env python3
from __future__ import annotations

import configparser
import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any, Mapping

MAX_CONFIG_BYTES = 256 * 1024
STANDARD_NAME = "org.freedesktop.secrets"


def _boolean_state(value: str | None) -> str:
    if value is None:
        return "UNSET"
    norm = value.strip().lower()
    if norm in {"1", "true", "yes", "on"}:
        return "TRUE"
    if norm in {"0", "false", "no", "off"}:
        return "FALSE"
    return "INVALID"


def _config_diagnostics(env: Mapping[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": "KWALLETRC_NON_SECRET_FLAGS_ONLY",
        "authoritative_for_pass": False,
        "file_status": "UNRESOLVED",
        "ksecret_backend_enabled": "UNSET",
        "standard_secret_service_api_enabled": "UNSET",
    }
    home = env.get("HOME", "").strip()
    if not home or not Path(home).is_absolute():
        result["file_status"] = "HOME_UNAVAILABLE"
        return result

    path = Path(home) / ".config" / "kwalletrc"
    try:
        info = path.lstat()
    except FileNotFoundError:
        result["file_status"] = "ABSENT"
        return result
    except OSError:
        result["file_status"] = "UNREADABLE"
        return result

    if stat.S_ISLNK(info.st_mode):
        result["file_status"] = "REJECTED_SYMLINK"
        return result
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        result["file_status"] = "REJECTED_OWNERSHIP_OR_TYPE"
        return result
    if info.st_size > MAX_CONFIG_BYTES:
        result["file_status"] = "REJECTED_OVERSIZE"
        return result

    try:
        text = path.read_text(encoding="utf-8")
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read_string(text)
    except (OSError, UnicodeError, configparser.Error):
        result["file_status"] = "UNREADABLE_OR_INVALID"
        return result

    result["file_status"] = "READABLE"
    result["ksecret_backend_enabled"] = _boolean_state(
        parser.get("KSecretD", "Enabled", fallback=None)
        if parser.has_section("KSecretD")
        else None
    )
    result["standard_secret_service_api_enabled"] = _boolean_state(
        parser.get("org.freedesktop.secrets", "apiEnabled", fallback=None)
        if parser.has_section("org.freedesktop.secrets")
        else None
    )
    return result


def _busctl(env: Mapping[str, str], args: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str] | None:
    binary = shutil.which("busctl")
    if not binary or not env.get("DBUS_SESSION_BUS_ADDRESS"):
        return None
    try:
        return subprocess.run(
            [binary, "--user", *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _name_has_owner(env: Mapping[str, str], name: str) -> dict[str, Any]:
    proc = _busctl(
        env,
        [
            "call",
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "NameHasOwner",
            "s",
            name,
        ],
    )
    if proc is None:
        return {"query_status": "UNAVAILABLE", "has_owner": False}
    return {
        "query_status": "PASS" if proc.returncode == 0 else "FAIL",
        "has_owner": proc.returncode == 0 and proc.stdout.strip().lower().endswith("true"),
        "returncode": proc.returncode,
    }


def _activatable_targets(env: Mapping[str, str], targets: set[str]) -> dict[str, Any]:
    proc = _busctl(
        env,
        [
            "call",
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "ListActivatableNames",
        ],
    )
    if proc is None:
        return {
            "query_status": "UNAVAILABLE",
            "targets": {name: False for name in sorted(targets)},
        }

    names: set[str] = set()
    if proc.returncode == 0:
        try:
            tokens = shlex.split(proc.stdout)
        except ValueError:
            tokens = []
        if tokens and tokens[0] == "as":
            tokens = tokens[2:] if len(tokens) >= 2 and tokens[1].isdigit() else tokens[1:]
        names = {token for token in tokens if isinstance(token, str) and "." in token}

    return {
        "query_status": "PASS" if proc.returncode == 0 else "FAIL",
        "returncode": proc.returncode,
        "targets": {name: name in names for name in sorted(targets)},
    }


def collect_kde_secret_service_reference_diagnostics(
    env: Mapping[str, str],
    *,
    alias: str | None,
) -> dict[str, Any]:
    """Read-only, non-authoritative diagnostics. Never reads wallet contents or secret values."""
    targets = {STANDARD_NAME}
    if isinstance(alias, str) and alias:
        targets.add(alias)

    owners = {name: _name_has_owner(env, name) for name in sorted(targets)}
    activatable = _activatable_targets(env, targets)
    return {
        "schema": "fa3.kde-secret-service-reference-diagnostics.v1",
        "diagnostic_only": True,
        "authoritative_for_pass": False,
        "mutation_performed": False,
        "secret_material_read": False,
        "configuration": _config_diagnostics(env),
        "dbus": {
            "owners": owners,
            "activatable": activatable,
        },
    }
