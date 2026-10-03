#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

REGISTRY_REL = "canonical/FA3-APPLICATION-INSTALLATION-REGISTRY-001.json"
SUPPORTED_PACKAGING = {"NATIVE", "DEB", "RPM", "FLATPAK", "SNAP", "APPIMAGE", "PORTABLE", "MANUAL"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def _run(argv: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        shell=False,
        check=False,
    )


def _candidate(
    application_id: str,
    display_name: str,
    packaging: str,
    locator: str,
    command_prefix: list[str],
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "application_id": application_id,
        "display_name": display_name,
        "packaging": packaging,
        "locator": locator,
        "command_prefix": command_prefix,
        "provenance": provenance or {},
        "health": "UNKNOWN",
        "health_returncode": None,
        "health_sentinel_observed": None,
        "health_stderr_summary": "",
        "discovery_is_authority": False,
        "selection_is_authority": False,
        "automatic_install": False,
        "automatic_fallback": False,
    }


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (
            str(row.get("application_id")),
            str(row.get("packaging")),
            json.dumps(row.get("command_prefix", []), separators=(",", ":")),
        )
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def _native_candidates(spec: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name in spec.get("native_executables", []):
        if not isinstance(name, str) or not name:
            continue
        path = shutil.which(name)
        if path:
            rows.append(_candidate(spec["application_id"], spec["display_name"], "NATIVE", path, [path]))
    return rows


def _deb_candidates(spec: dict[str, Any]) -> list[dict[str, Any]]:
    if not shutil.which("dpkg-query"):
        return []
    basenames = set(spec.get("deb_executable_basenames", []))
    rows = []
    for package in spec.get("deb_packages", []):
        if not isinstance(package, str) or not package:
            continue
        proc = _run(["dpkg-query", "-L", package])
        if proc.returncode != 0:
            continue
        for raw in proc.stdout.splitlines():
            path = Path(raw.strip())
            if not path.is_absolute() or not path.is_file():
                continue
            if basenames and path.name not in basenames:
                continue
            if os.access(path, os.X_OK):
                rows.append(_candidate(
                    spec["application_id"], spec["display_name"], "DEB", str(path), [str(path)],
                    {"package": package},
                ))
    return rows


def _rpm_candidates(spec: dict[str, Any]) -> list[dict[str, Any]]:
    if not shutil.which("rpm"):
        return []
    basenames = set(spec.get("rpm_executable_basenames", []))
    rows = []
    for package in spec.get("rpm_packages", []):
        if not isinstance(package, str) or not package:
            continue
        proc = _run(["rpm", "-ql", package])
        if proc.returncode != 0:
            continue
        for raw in proc.stdout.splitlines():
            path = Path(raw.strip())
            if not path.is_absolute() or not path.is_file():
                continue
            if basenames and path.name not in basenames:
                continue
            if os.access(path, os.X_OK):
                rows.append(_candidate(
                    spec["application_id"], spec["display_name"], "RPM", str(path), [str(path)],
                    {"package": package},
                ))
    return rows


def _flatpak_candidates(spec: dict[str, Any]) -> list[dict[str, Any]]:
    if not shutil.which("flatpak"):
        return []
    rows = []
    for app_id in spec.get("flatpak_app_ids", []):
        if not isinstance(app_id, str) or not app_id:
            continue
        proc = _run(["flatpak", "info", app_id])
        if proc.returncode == 0:
            rows.append(_candidate(
                spec["application_id"], spec["display_name"], "FLATPAK", app_id,
                ["flatpak", "run", app_id], {"flatpak_app_id": app_id},
            ))
    return rows


def _snap_candidates(spec: dict[str, Any]) -> list[dict[str, Any]]:
    if not shutil.which("snap"):
        return []
    rows = []
    for snap_name in spec.get("snap_names", []):
        if not isinstance(snap_name, str) or not snap_name:
            continue
        proc = _run(["snap", "list", snap_name])
        if proc.returncode == 0:
            rows.append(_candidate(
                spec["application_id"], spec["display_name"], "SNAP", snap_name,
                ["snap", "run", snap_name], {"snap_name": snap_name},
            ))
    return rows


def _portable_candidates(spec: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for pattern in spec.get("portable_globs", []):
        if not isinstance(pattern, str) or not pattern:
            continue
        expanded = os.path.expandvars(os.path.expanduser(pattern))
        for raw in sorted(glob.glob(expanded)):
            path = Path(raw)
            if path.is_file() and os.access(path, os.X_OK):
                packaging = "APPIMAGE" if path.name.lower().endswith(".appimage") else "PORTABLE"
                rows.append(_candidate(
                    spec["application_id"], spec["display_name"], packaging, str(path), [str(path)]
                ))
    return rows


def _manual_candidates(spec: dict[str, Any]) -> list[dict[str, Any]]:
    env_name = spec.get("manual_executable_env")
    if not isinstance(env_name, str) or not env_name:
        return []
    rows = []
    for raw in os.environ.get(env_name, "").split(os.pathsep):
        if not raw:
            continue
        path = Path(raw).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            rows.append(_candidate(
                spec["application_id"], spec["display_name"], "MANUAL", str(path), [str(path)],
                {"environment_variable": env_name},
            ))
    return rows


def _health(row: dict[str, Any], spec: dict[str, Any], runner: Callable[[list[str], int], subprocess.CompletedProcess[str]]) -> dict[str, Any]:
    health_argv = spec.get("health_argv", [])
    if not isinstance(health_argv, list) or any(not isinstance(x, str) for x in health_argv):
        row["health"] = "INVALID_SPEC"
        return row
    timeout = int(spec.get("health_timeout_seconds", 30))
    proc = runner([*row["command_prefix"], *health_argv], timeout)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    sentinel = spec.get("health_sentinel")
    sentinel_ok = True if not sentinel else isinstance(sentinel, str) and sentinel in combined
    row["health_returncode"] = proc.returncode
    row["health_sentinel_observed"] = sentinel_ok
    row["health_stderr_summary"] = (proc.stderr or "")[-800:]
    row["health"] = "HEALTHY" if proc.returncode == 0 and sentinel_ok else "UNHEALTHY"
    return row


def registry(root: Path) -> dict[str, Any]:
    data = _load(root / REGISTRY_REL)
    if data.get("id") != "FA3-APPLICATION-INSTALLATION-REGISTRY-001":
        raise RuntimeError("application installation registry id mismatch")
    if data.get("authority") is not False or data.get("automatic_install") is not False:
        raise RuntimeError("application installation registry authority invariant")
    if data.get("supported_packaging") != sorted(SUPPORTED_PACKAGING):
        raise RuntimeError("supported packaging invariant")
    return data


def application_spec(root: Path, application_id: str) -> dict[str, Any]:
    data = registry(root)
    row = next((x for x in data.get("applications", []) if x.get("application_id") == application_id), None)
    if not isinstance(row, dict):
        raise KeyError(application_id)
    return row


def discover_registered_application(
    root: Path,
    application_id: str,
    *,
    perform_health_check: bool = True,
    runner: Callable[[list[str], int], subprocess.CompletedProcess[str]] = _run,
) -> list[dict[str, Any]]:
    spec = application_spec(root, application_id)
    rows = _dedupe([
        *_native_candidates(spec),
        *_deb_candidates(spec),
        *_rpm_candidates(spec),
        *_flatpak_candidates(spec),
        *_snap_candidates(spec),
        *_portable_candidates(spec),
        *_manual_candidates(spec),
    ])
    if perform_health_check:
        rows = [_health(row, spec, runner) for row in rows]
    return rows


def discover_group(root: Path, group: str, *, perform_health_check: bool = True) -> list[dict[str, Any]]:
    data = registry(root)
    ids = [x.get("application_id") for x in data.get("applications", []) if group in x.get("groups", [])]
    rows: list[dict[str, Any]] = []
    for application_id in ids:
        if isinstance(application_id, str):
            rows.extend(discover_registered_application(root, application_id, perform_health_check=perform_health_check))
    return rows
