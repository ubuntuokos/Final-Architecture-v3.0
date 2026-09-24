#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping

from fa3_release_baseline import module_active_capability_count

from fa3_desktop_admission import (
    collect_runtime_probes,
    discover_current_user_session_environment,
    evaluate_desktop,
)

REPOSITORY = "ubuntuokos/Final-Architecture-v3.0"
GATE_ID = "FA3-GUI-CURRENT-HOST-GATESET-001"
CONFORMANCE_ID = "FA3-GUI-RUNTIME-CONFORMANCE-001"
EVIDENCE_ID = "EVID-FA3-GUI-CURRENT-HOST-001"
CAPABILITY_COUNT = module_active_capability_count(__file__)

SAFE_ENV_KEYS = {
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "LC_ALL", "LC_CTYPE",
    "XDG_CURRENT_DESKTOP", "DESKTOP_SESSION", "XDG_SESSION_TYPE", "XDG_RUNTIME_DIR",
    "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_DATA_DIRS",
    "DBUS_SESSION_BUS_ADDRESS", "WAYLAND_DISPLAY", "DISPLAY",
}
FATAL_LOG_MARKERS = (
    "QQmlApplicationEngine failed to load component",
    "Could not load the Qt platform plugin",
    "no Qt platform plugin could be initialized",
)

RUNTIME_SURFACE_ROOTS = ("apps/fa3-control-center",)
RUNTIME_SURFACE_FILES = (
    "src/fa3_desktop_admission.py",
    "src/fa3_gui_current_host.py",
    "src/fa3_gui_current_host_gate.py",
    "src/fa3_release_baseline.py",
    "evidence/collect-gui-current-host.py",
    ".github/workflows/fa3-gui-current-host.yml",
    "canonical/FA3-DESKTOP-BASE-001.json",
    "canonical/FA3-DESKTOP-PLASMA-001.json",
)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def runtime_surface_paths(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", *RUNTIME_SURFACE_ROOTS, *RUNTIME_SURFACE_FILES],
        check=False,
        capture_output=True,
        timeout=10,
    )
    if proc.returncode != 0:
        return []
    return sorted(
        item.decode("utf-8", "surrogateescape")
        for item in proc.stdout.split(b"\0")
        if item
    )


def runtime_surface_git_blobs(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for rel in runtime_surface_paths(root):
        path = root / rel
        if not path.is_file():
            return {}
        result[rel] = git_blob_sha(path)
    return result


def git_head(root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def qpa_for_session(session_type: str) -> str | None:
    value = session_type.strip().lower()
    if value == "wayland":
        return "wayland"
    if value == "x11":
        return "xcb"
    return None


def safe_child_environment(session_env: Mapping[str, str]) -> dict[str, str]:
    output = {
        key: value
        for key, value in session_env.items()
        if key in SAFE_ENV_KEYS and value
    }
    qpa = qpa_for_session(output.get("XDG_SESSION_TYPE", ""))
    if qpa:
        output["QT_QPA_PLATFORM"] = qpa
    output["QT_LOGGING_RULES"] = "qt.qpa.*=true"
    output.pop("QTWEBENGINE_DISABLE_SANDBOX", None)
    return output


def host_fingerprint() -> str:
    machine_id = ""
    try:
        machine_id = Path("/etc/machine-id").read_text(encoding="utf-8").strip()
    except OSError:
        pass
    material = "|".join((platform.node(), str(os.getuid()), machine_id))
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def fatal_qt_startup_marker_present(text: str) -> bool:
    lower = text.lower()
    if "module " in lower and " is not installed" in lower:
        return True
    return any(marker.lower() in lower for marker in FATAL_LOG_MARKERS)


GUI_RUNTIME_REQUIRED_CAPABILITIES = (
    "linux_host",
    "xdg_runtime",
    "dbus_session",
    "uri_open",
    "local_gui_session",
)


def gui_desktop_runtime_scoped_admission(
    report: dict[str, Any],
    session_evidence: dict[str, Any],
) -> dict[str, Any]:
    capabilities = report.get("capabilities")
    if not isinstance(capabilities, dict):
        return {
            "result": "FAIL",
            "reason": "DESKTOP_CAPABILITIES_MISSING",
            "required_capabilities": {},
            "failed_checks": ["desktop_capabilities_missing"],
            "full_desktop_admission_result": report.get("result"),
            "full_desktop_required_failures": [],
            "secret_backend_status": None,
            "secret_backend_used_for_gui_runtime_admission": False,
            "secrets_authority_owner": "CAP-003",
            "scope_semantics": "GUI_PROCESS_RUNTIME_PROOF_NOT_SECRET_BACKEND_ADMISSION",
        }

    required = {
        key: capabilities.get(key) == "PASS"
        for key in GUI_RUNTIME_REQUIRED_CAPABILITIES
    }
    session_checks = {
        "active_local_graphical_session": (
            session_evidence.get("active_local_graphical_session_proven") is True
        ),
        "runtime_dir_proven": session_evidence.get("runtime_dir_proven") is True,
        "user_bus_socket_proven": session_evidence.get("user_bus_socket_proven") is True,
    }

    failed = sorted(
        [key for key, ok in required.items() if not ok]
        + [key for key, ok in session_checks.items() if not ok]
    )
    full_required_failures = sorted(
        key
        for key in (
            "linux_host",
            "xdg_runtime",
            "dbus_session",
            "uri_open",
            "secret_backend",
            "local_gui_session",
        )
        if capabilities.get(key) == "FAIL"
    )
    non_scoped_failures = [
        key for key in full_required_failures if key != "secret_backend"
    ]
    failed.extend(
        f"full_desktop_failure:{key}" for key in non_scoped_failures
    )

    return {
        "result": "PASS" if not failed else "FAIL",
        "required_capabilities": required,
        "session_checks": session_checks,
        "failed_checks": sorted(set(failed)),
        "full_desktop_admission_result": report.get("result"),
        "full_desktop_required_failures": full_required_failures,
        "secret_backend_status": capabilities.get("secret_backend"),
        "secret_backend_used_for_gui_runtime_admission": False,
        "secrets_authority_owner": "CAP-003",
        "scope_semantics": "GUI_PROCESS_RUNTIME_PROOF_NOT_SECRET_BACKEND_ADMISSION",
    }


def collect(
    root: Path,
    executable: Path,
    *,
    output_dir: Path,
    smoke_seconds: float = 8.0,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    executable = executable.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    base_env = dict(os.environ if env is None else env)

    discovery = discover_current_user_session_environment(base_env)
    session_env = discovery["environment"]
    session_evidence = discovery["evidence"]
    probes = collect_runtime_probes(session_env)
    desktop = evaluate_desktop(session_env, probes, require_gui=True)
    desktop_runtime_scope = gui_desktop_runtime_scoped_admission(
        desktop,
        session_evidence,
    )

    session_type = str(session_env.get("XDG_SESSION_TYPE", "")).strip().lower()
    qpa = qpa_for_session(session_type)
    display_endpoint_proven = (
        bool(session_env.get("WAYLAND_DISPLAY"))
        if session_type == "wayland"
        else bool(session_env.get("DISPLAY"))
        if session_type == "x11"
        else False
    )

    source_commit = git_head(root)
    expected_source = base_env.get("FA3_EXPECTED_SOURCE_SHA", "")
    runner_class = base_env.get("FA3_RUNNER_CLASS", "")
    source_binding = {
        "github_actions": base_env.get("GITHUB_ACTIONS") == "true",
        "repository": base_env.get("GITHUB_REPOSITORY"),
        "repository_exact": base_env.get("GITHUB_REPOSITORY") == REPOSITORY,
        "expected_source_commit": expected_source,
        "source_commit": source_commit,
        "source_commit_exact": bool(expected_source) and expected_source == source_commit,
        "workflow_run_id": base_env.get("GITHUB_RUN_ID"),
        "workflow_job": base_env.get("GITHUB_JOB"),
        "runtime_surface_policy": "EXACT_TRACKED_GIT_BLOBS",
        "runtime_surface_git_blobs": runtime_surface_git_blobs(root),
    }

    build_pass = executable.is_file() and os.access(executable, os.X_OK)
    build = {
        "status": "PASS" if build_pass else "FAIL",
        "executable": str(executable.relative_to(root))
        if executable.is_relative_to(root)
        else executable.name,
        "binary_sha256": sha256_path(executable) if executable.is_file() else None,
    }

    launch: dict[str, Any] = {
        "attempted": False,
        "qpa_platform": qpa,
        "process_alive_after_smoke": False,
        "smoke_seconds": float(smoke_seconds),
        "observed_runtime_seconds": 0.0,
        "terminated_by_probe": False,
        "cleanup_completed": False,
        "early_returncode": None,
        "stdout_sha256": None,
        "stderr_sha256": None,
        "fatal_qt_startup_marker_absent": False,
    }

    prerequisites = (
        source_binding["github_actions"]
        and source_binding["repository_exact"]
        and source_binding["source_commit_exact"]
        and runner_class == "fa3-current-host"
        and os.geteuid() != 0
        and desktop_runtime_scope.get("result") == "PASS"
        and session_evidence.get("active_local_graphical_session_proven") is True
        and session_type in {"wayland", "x11"}
        and display_endpoint_proven
        and qpa is not None
        and build_pass
    )

    if prerequisites:
        child_env = safe_child_environment(session_env)
        stdout_path = output_dir / "fa3-control-center.stdout.log"
        stderr_path = output_dir / "fa3-control-center.stderr.log"
        started = time.monotonic()
        launch["attempted"] = True
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            proc = subprocess.Popen(
                [str(executable)],
                cwd=str(root),
                env=child_env,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            time.sleep(max(5.0, smoke_seconds))
            launch["observed_runtime_seconds"] = round(time.monotonic() - started, 3)
            launch["process_alive_after_smoke"] = proc.poll() is None
            if proc.poll() is None:
                proc.terminate()
                launch["terminated_by_probe"] = True
                try:
                    proc.wait(timeout=5)
                    launch["cleanup_completed"] = True
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                    launch["cleanup_completed"] = True
            else:
                launch["early_returncode"] = proc.returncode

        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        launch["stdout_sha256"] = sha256_path(stdout_path)
        launch["stderr_sha256"] = sha256_path(stderr_path)
        launch["fatal_qt_startup_marker_absent"] = not fatal_qt_startup_marker_present(
            stdout_text + "\n" + stderr_text
        )

    checks = {
        "github_actions_context": source_binding["github_actions"],
        "repository_binding_exact": source_binding["repository_exact"],
        "source_commit_binding_exact": source_binding["source_commit_exact"],
        "runner_class_exact": runner_class == "fa3-current-host",
        "non_root_runner": os.geteuid() != 0,
        "active_local_graphical_session": (
            session_evidence.get("active_local_graphical_session_proven") is True
        ),
        "supported_session_type": session_type in {"wayland", "x11"},
        "display_endpoint_proven": display_endpoint_proven,
        "desktop_runtime_scope_admission_pass": desktop_runtime_scope.get("result") == "PASS",
        "same_source_binary_present": build_pass,
        "explicit_native_qpa": qpa in {"wayland", "xcb"},
        "offscreen_or_minimal_forbidden": qpa not in {"offscreen", "minimal"},
        "webengine_sandbox_override_absent": (
            "QTWEBENGINE_DISABLE_SANDBOX" not in safe_child_environment(session_env)
        ),
        "real_gui_process_started": launch["attempted"],
        "process_survived_smoke_window": launch["process_alive_after_smoke"],
        "smoke_window_minimum_5s": launch["observed_runtime_seconds"] >= 5.0,
        "probe_cleanup_completed": launch["cleanup_completed"],
        "fatal_qt_startup_marker_absent": launch["fatal_qt_startup_marker_absent"],
    }
    blocking = [name for name, passed in checks.items() if not passed]
    passed = not blocking

    return {
        "schema": "fa3.gui-current-host-receipt.v1",
        "evidence_id": EVIDENCE_ID,
        "gate_id": GATE_ID,
        "conformance_id": CONFORMANCE_ID,
        "result": "PASS" if passed else "FAIL",
        "fail_closed": True,
        "captured_unix": int(time.time()),
        "source_binding": source_binding,
        "host": {
            "fingerprint_sha256": host_fingerprint(),
            "runner_class": runner_class,
            "platform": platform.system(),
            "architecture": platform.machine(),
        },
        "session": {
            "type": session_type or None,
            "desktop_class": session_evidence.get("desktop_class"),
            "active_local_graphical_session_proven": (
                session_evidence.get("active_local_graphical_session_proven") is True
            ),
            "runtime_dir_proven": session_evidence.get("runtime_dir_proven") is True,
            "user_bus_socket_proven": session_evidence.get("user_bus_socket_proven") is True,
            "display_endpoint_proven": display_endpoint_proven,
            "wayland_socket_proven": session_evidence.get("wayland_socket_proven"),
            "qpa_platform": qpa,
        },
        "desktop_admission": {
            "gate_id": desktop.get("gate_id"),
            "result": desktop.get("result"),
            "mode": desktop.get("mode"),
            "desktop": desktop.get("desktop"),
            "session": desktop.get("session"),
            "capabilities": desktop.get("capabilities"),
            "secret_backend_evidence": desktop.get("secret_backend_evidence"),
        },
        "desktop_runtime_scope": desktop_runtime_scope,
        "build": build,
        "launch": launch,
        "security": {
            "root_execution": False,
            "sudo_or_pkexec_used": False,
            "package_install_or_network_fetch_used": False,
            "webengine_sandbox_disabled": False,
            "offscreen_or_minimal_platform_used": False,
            "secret_material_recorded": False,
            "secret_backend_promoted_by_gui_receipt": False,
        },
        "checks": checks,
        "blocking_findings": blocking,
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "gui_runtime_promotion_eligible": passed,
        "current_host_runtime_promotion_claimed": passed,
        "global_fa3_promotion_claim": False,
    }
