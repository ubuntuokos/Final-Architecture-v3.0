#!/usr/bin/env python3
from __future__ import annotations

import configparser
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "fa3.plasma-secret-service-current-host-diagnostic.v1"
ALIAS = "org.kde.secretservicecompat"
STANDARD = "org.freedesktop.secrets"


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


def _user_bus_names(env: Mapping[str, str]) -> set[str]:
    busctl = shutil.which("busctl")
    if not busctl or not env.get("DBUS_SESSION_BUS_ADDRESS"):
        return set()
    try:
        proc = subprocess.run(
            [busctl, "--user", "--no-pager", "--list"],
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
    return {line.split()[0] for line in proc.stdout.splitlines() if line.split()}


def collect_plasma_secret_service_diagnostic(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    supplied = dict(os.environ if env is None else env)
    names = _user_bus_names(supplied)
    state = _read_config_state(supplied)
    return {
        "schema": SCHEMA,
        "read_only": True,
        "secret_values_read": False,
        "secret_values_emitted": False,
        "provider_specific_diagnostic_only": True,
        "ksecretd_binary_present": shutil.which("ksecretd") is not None,
        "reference_alias_live": ALIAS in names,
        "standard_secret_service_live": STANDARD in names,
        **state,
    }
