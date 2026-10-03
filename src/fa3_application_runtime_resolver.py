#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("canonical/FA3-APPLICATION-RUNTIME-DISCOVERY-001.json")
ALLOWED_PACKAGING = {"NATIVE", "DEB", "RPM", "PACMAN", "FLATPAK", "SNAP", "APPIMAGE", "PORTABLE", "MANUAL"}


class ApplicationRuntimeDiscoveryError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ApplicationRuntimeDiscoveryError(f"JSON object required: {path}")
    return value


def load_registry(root: Path) -> dict[str, Any]:
    registry = _load(root / REGISTRY_REL)
    if (
        registry.get("id") != "FA3-APPLICATION-RUNTIME-DISCOVERY-001"
        or registry.get("authority") is not False
        or registry.get("source_of_execution_truth") is not False
        or registry.get("capability_count") != 175
    ):
        raise ApplicationRuntimeDiscoveryError("application runtime discovery registry invariant mismatch")
    packaging = registry.get("supported_packaging_classes")
    if not isinstance(packaging, list) or set(packaging) != ALLOWED_PACKAGING:
        raise ApplicationRuntimeDiscoveryError("application runtime packaging classes mismatch")
    return registry


def application_spec(root: Path, application_id: str) -> dict[str, Any]:
    registry = load_registry(root)
    for row in registry.get("applications", []):
        if isinstance(row, dict) and row.get("application_id") == application_id:
            return row
    raise ApplicationRuntimeDiscoveryError(f"unknown application runtime identity: {application_id}")


def group_spec(root: Path, group_id: str) -> dict[str, Any]:
    registry = load_registry(root)
    for row in registry.get("groups", []):
        if isinstance(row, dict) and row.get("group_id") == group_id:
            return row
    raise ApplicationRuntimeDiscoveryError(f"unknown application runtime group: {group_id}")


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


def _bounded(value: str, limit: int = 600) -> str:
    value = value.strip().replace("\x00", "")
    return value[-limit:]


def _package_class_for_path(path: str) -> tuple[str, str | None]:
    resolved = str(Path(path).resolve())
    if shutil.which("dpkg-query"):
        proc = _run(["dpkg-query", "-S", resolved], 10)
        if proc.returncode == 0:
            package = proc.stdout.split(":", 1)[0].strip() or None
            return "DEB", package
    if shutil.which("rpm"):
        proc = _run(["rpm", "-qf", resolved], 10)
        if proc.returncode == 0:
            package = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else None
            return "RPM", package
    if shutil.which("pacman"):
        proc = _run(["pacman", "-Qo", resolved], 10)
        if proc.returncode == 0:
            package = proc.stdout.strip().split()[4] if len(proc.stdout.strip().split()) >= 5 else None
            return "PACMAN", package
    return "NATIVE", None


def _desktop_roots() -> list[Path]:
    roots: list[Path] = []
    data_home = os.environ.get("XDG_DATA_HOME")
    roots.append((Path(data_home).expanduser() if data_home else Path.home() / ".local/share") / "applications")
    for raw in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":"):
        if raw:
            roots.append(Path(raw).expanduser() / "applications")
    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            out.append(root)
    return out


def _desktop_exec(path: Path) -> list[str] | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    in_entry = False
    exec_value: str | None = None
    for raw in lines:
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_entry = line == "[Desktop Entry]"
            continue
        if in_entry and line.startswith("Exec="):
            exec_value = line[5:].strip()
            break
    if not exec_value:
        return None
    try:
        tokens = shlex.split(exec_value)
    except ValueError:
        return None
    tokens = [token for token in tokens if not token.startswith("%")]
    if not tokens:
        return None
    command = tokens[0]
    resolved = command if Path(command).is_absolute() and Path(command).is_file() else shutil.which(command)
    if not resolved:
        return None
    return [str(Path(resolved).resolve()), *tokens[1:]]


def _candidate(
    *,
    application_id: str,
    display_name: str,
    packaging: str,
    launch_prefix: list[str],
    identity: str,
    source: str,
    package_id: str | None = None,
) -> dict[str, Any]:
    if packaging not in ALLOWED_PACKAGING:
        raise ApplicationRuntimeDiscoveryError(f"unsupported packaging class: {packaging}")
    return {
        "application_id": application_id,
        "display_name": display_name,
        "packaging": packaging,
        "launch_prefix": launch_prefix,
        "identity": identity,
        "source": source,
        "package_id": package_id,
        "health": "UNPROBED",
        "selectable": False,
    }


def discover_candidates(root: Path, application_id: str) -> list[dict[str, Any]]:
    spec = application_spec(root, application_id)
    display_name = str(spec.get("display_name") or application_id)
    rows: list[dict[str, Any]] = []

    for env_name in spec.get("portable_env", []):
        if not isinstance(env_name, str):
            continue
        raw = os.environ.get(env_name)
        if not raw:
            continue
        path = Path(raw).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            packaging = "APPIMAGE" if path.name.lower().endswith(".appimage") else "PORTABLE"
            rows.append(_candidate(
                application_id=application_id,
                display_name=display_name,
                packaging=packaging,
                launch_prefix=[str(path.resolve())],
                identity=f"{packaging}:{path.resolve()}",
                source=f"PORTABLE_ENV:{env_name}",
            ))

    for env_name in spec.get("manual_env", []):
        if not isinstance(env_name, str):
            continue
        raw = os.environ.get(env_name)
        if not raw:
            continue
        path = Path(raw).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            rows.append(_candidate(
                application_id=application_id,
                display_name=display_name,
                packaging="MANUAL",
                launch_prefix=[str(path.resolve())],
                identity=f"MANUAL:{path.resolve()}",
                source=f"ENV:{env_name}",
            ))

    for alias in spec.get("command_aliases", []):
        if not isinstance(alias, str):
            continue
        found = shutil.which(alias)
        if not found:
            continue
        resolved = str(Path(found).resolve())
        packaging, package_id = _package_class_for_path(resolved)
        rows.append(_candidate(
            application_id=application_id,
            display_name=display_name,
            packaging=packaging,
            launch_prefix=[resolved],
            identity=f"{packaging}:{resolved}",
            source=f"PATH:{alias}",
            package_id=package_id,
        ))

    seen_desktop: set[str] = set()
    for desktop_root in _desktop_roots():
        if not desktop_root.is_dir():
            continue
        for pattern in spec.get("desktop_file_globs", []):
            if not isinstance(pattern, str):
                continue
            for desktop_file in desktop_root.glob(pattern):
                key = str(desktop_file.resolve())
                if key in seen_desktop:
                    continue
                seen_desktop.add(key)
                launch = _desktop_exec(desktop_file)
                if not launch:
                    continue
                packaging, package_id = _package_class_for_path(launch[0])
                rows.append(_candidate(
                    application_id=application_id,
                    display_name=display_name,
                    packaging=packaging,
                    launch_prefix=launch,
                    identity=f"{packaging}:DESKTOP:{desktop_file.resolve()}",
                    source=f"DESKTOP:{desktop_file.resolve()}",
                    package_id=package_id,
                ))

    flatpak = shutil.which("flatpak")
    if flatpak:
        for app_id in spec.get("flatpak_ids", []):
            if not isinstance(app_id, str):
                continue
            proc = _run([flatpak, "info", app_id], 15)
            if proc.returncode == 0:
                rows.append(_candidate(
                    application_id=application_id,
                    display_name=display_name,
                    packaging="FLATPAK",
                    launch_prefix=[flatpak, "run", app_id],
                    identity=f"FLATPAK:{app_id}",
                    source="FLATPAK",
                    package_id=app_id,
                ))

    snap = shutil.which("snap")
    if snap:
        for snap_name in spec.get("snap_names", []):
            if not isinstance(snap_name, str):
                continue
            proc = _run([snap, "list", snap_name], 15)
            if proc.returncode == 0:
                rows.append(_candidate(
                    application_id=application_id,
                    display_name=display_name,
                    packaging="SNAP",
                    launch_prefix=[snap, "run", snap_name],
                    identity=f"SNAP:{snap_name}",
                    source="SNAP",
                    package_id=snap_name,
                ))

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        key = tuple(row["launch_prefix"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def probe_candidate(candidate: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    row = dict(candidate)
    smoke = spec.get("smoke_argv", [])
    if not isinstance(smoke, list) or any(not isinstance(x, str) for x in smoke):
        raise ApplicationRuntimeDiscoveryError("smoke_argv must be a list of strings")
    timeout = spec.get("smoke_timeout_seconds", 30)
    if not isinstance(timeout, int) or not 1 <= timeout <= 180:
        raise ApplicationRuntimeDiscoveryError("smoke timeout outside 1..180 seconds")
    sentinel = spec.get("smoke_stdout_sentinel")
    try:
        proc = _run([*row["launch_prefix"], *smoke], timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        row.update({
            "health": "UNHEALTHY",
            "selectable": False,
            "probe_returncode": None,
            "probe_summary": type(exc).__name__,
        })
        return row
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    healthy = proc.returncode == 0 and (not sentinel or str(sentinel) in combined)
    row.update({
        "health": "HEALTHY" if healthy else "UNHEALTHY",
        "selectable": healthy,
        "probe_returncode": proc.returncode,
        "probe_summary": _bounded(combined),
    })
    return row


def discover_application(root: Path, application_id: str, *, probe: bool = True) -> dict[str, Any]:
    spec = application_spec(root, application_id)
    candidates = discover_candidates(root, application_id)
    if probe:
        candidates = [probe_candidate(row, spec) for row in candidates]
    healthy = [row for row in candidates if row.get("health") == "HEALTHY"]
    return {
        "schema": "fa3.application-runtime-discovery-result.v1",
        "application_id": application_id,
        "display_name": spec.get("display_name"),
        "groups": list(spec.get("groups", [])),
        "installed_instance_count": len(candidates),
        "healthy_instance_count": len(healthy) if probe else None,
        "candidates": candidates,
        "discovery_is_authority": False,
        "runtime_selection_authority_exercised": False,
        "current_host_promotion_claim": False,
    }


def discover_inventory(root: Path, *, probe: bool = False) -> dict[str, Any]:
    registry = load_registry(root)
    rows = [
        discover_application(root, str(spec["application_id"]), probe=probe)
        for spec in registry.get("applications", [])
        if isinstance(spec, dict) and spec.get("application_id")
    ]
    return {
        "schema": "fa3.application-runtime-inventory.v1",
        "applications": rows,
        "probe_performed": probe,
        "discovery_is_authority": False,
        "current_host_promotion_claim": False,
    }


def discover_group(root: Path, group_id: str, *, probe: bool = True) -> dict[str, Any]:
    group = group_spec(root, group_id)
    registry = load_registry(root)
    app_ids = [
        str(row["application_id"])
        for row in registry.get("applications", [])
        if isinstance(row, dict) and group_id in row.get("groups", [])
    ]
    applications = [discover_application(root, app_id, probe=probe) for app_id in app_ids]
    healthy: list[dict[str, Any]] = []
    for app in applications:
        for candidate in app.get("candidates", []):
            if candidate.get("health") == "HEALTHY":
                healthy.append(candidate)
    return {
        "schema": "fa3.application-runtime-group-discovery.v1",
        "group_id": group_id,
        "minimum_healthy_instances": group.get("minimum_healthy_instances", 0),
        "applications": applications,
        "healthy_candidates": healthy,
        "healthy_instance_count": len(healthy) if probe else None,
        "discovery_is_authority": False,
        "runtime_selection_authority_exercised": False,
        "current_host_promotion_claim": False,
    }


def qualification_candidate_for_group(root: Path, group_id: str) -> dict[str, Any] | None:
    group = group_spec(root, group_id)
    result = discover_group(root, group_id, probe=True)
    healthy = list(result.get("healthy_candidates", []))
    requested = os.environ.get(str(group.get("selection_env", ""))) if group.get("selection_env") else None
    if requested:
        matches = [row for row in healthy if row.get("application_id") == requested]
        if not matches:
            return None
        selected = matches[0]
        reason = "EXPLICIT_CURRENT_HOST_QUALIFICATION_SELECTION"
    else:
        preference = [str(x) for x in group.get("qualification_preference", [])]
        selected = None
        for app_id in preference:
            selected = next((row for row in healthy if row.get("application_id") == app_id), None)
            if selected is not None:
                break
        if selected is None and healthy:
            selected = healthy[0]
        reason = "QUALIFICATION_PROBE_ONLY_NOT_USER_RUNTIME_SELECTION"
    if selected is None:
        return None
    row = dict(selected)
    row["qualification_selection_reason"] = reason
    row["healthy_group_instance_count"] = len(healthy)
    row["runtime_selection_authority_exercised"] = False
    return row


def dcc_qualification_candidate(root: Path) -> dict[str, Any] | None:
    return qualification_candidate_for_group(root, "DCC_3D")
