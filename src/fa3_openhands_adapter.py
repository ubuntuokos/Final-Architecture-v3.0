#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-OPENHANDS-001"
RUNTIME_ID = "FA3-OPENHANDS-RUNTIME-CONFORMANCE-001"
CURRENT_HOST_GATE_ID = "FA3-OPENHANDS-CURRENT-HOST-GATESET-001"
PINNED_COMMIT = "a9e0a8a1aab2164b46bae00a18157a343aaa94c9"
PINNED_TREE = "342a369f498b826cf51d1644bcbef8d503af7628"
COMPONENT_VERSION = "1.44.1"
COMPONENTS = (
    "openhands-sdk",
    "openhands-agent-server",
    "openhands-tools",
    "openhands-workspace",
)
PRODUCTION_EVIDENCE_LEVEL = "CURRENT_HOST_OPENHANDS_PRODUCTION_E2E_PASS"
ISOLATED_EVIDENCE_LEVEL = "CURRENT_HOST_OPENHANDS_ISOLATED_RUNTIME_PASS"
EXPECTED_AUTH_ISSUER = "FA3-AUTH-MCP-GATEWAY-001"
DEFAULT_MODEL_ALIAS = "developer-agent-primary"
SECRET_KEY_RE = re.compile(r"(token|secret|password|api[_-]?key|credential|private[_-]?key)", re.I)


class OpenHandsAdmissionError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def host_fingerprint() -> dict[str, Any]:
    u = platform.uname()
    return {
        "system": u.system,
        "release": u.release,
        "machine": u.machine,
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "hostname_sha256": sha256_bytes(u.node.encode("utf-8")),
    }


def require_current_host() -> None:
    machine = platform.machine().lower()
    if platform.system() != "Linux" or machine not in {"x86_64", "amd64"}:
        raise OpenHandsAdmissionError("OpenHands current-host evidence requires Linux x86_64")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise OpenHandsAdmissionError("OpenHands current-host evidence must not run as root")


def find_bwrap() -> Path:
    binary = shutil.which("bwrap")
    if not binary:
        raise OpenHandsAdmissionError("bubblewrap (bwrap) is required")
    return Path(binary).resolve()


def validate_source_checkout(source: Path) -> dict[str, str]:
    source = source.resolve()
    if not (source / ".git").exists():
        raise OpenHandsAdmissionError(f"OpenHands source checkout missing .git: {source}")
    def git(*args: str) -> str:
        p = subprocess.run(
            ["git", "-C", str(source), *args],
            text=True, capture_output=True, check=False, timeout=30,
        )
        if p.returncode != 0:
            raise OpenHandsAdmissionError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
        return p.stdout.strip()
    commit = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    dirty = git("status", "--porcelain")
    if commit != PINNED_COMMIT:
        raise OpenHandsAdmissionError(f"OpenHands source commit mismatch: {commit}")
    if tree != PINNED_TREE:
        raise OpenHandsAdmissionError(f"OpenHands source tree mismatch: {tree}")
    if dirty:
        raise OpenHandsAdmissionError("OpenHands source checkout is dirty")
    return {"commit": commit, "tree": tree}


def venv_python(venv: Path) -> Path:
    py = (venv.resolve() / "bin/python")
    if not py.is_file():
        raise OpenHandsAdmissionError(f"OpenHands venv python missing: {py}")
    return py


def inspect_component_versions(venv: Path) -> dict[str, str]:
    py = venv_python(venv)
    script = (
        "import importlib.metadata,json;"
        f"names={list(COMPONENTS)!r};"
        "print(json.dumps({n:importlib.metadata.version(n) for n in names},sort_keys=True))"
    )
    p = subprocess.run([str(py), "-c", script], text=True, capture_output=True, check=False, timeout=60)
    if p.returncode != 0:
        raise OpenHandsAdmissionError(f"OpenHands component inspection failed: {p.stderr.strip()}")
    versions = json.loads(p.stdout)
    if set(versions) != set(COMPONENTS):
        raise OpenHandsAdmissionError("OpenHands component tuple incomplete")
    if any(v != COMPONENT_VERSION for v in versions.values()):
        raise OpenHandsAdmissionError(f"OpenHands component version mismatch: {versions}")
    return versions


def assert_no_conda(venv: Path) -> None:
    text = str(venv.resolve()).lower()
    if "conda" in text or "mamba" in text:
        raise OpenHandsAdmissionError("conda/mamba path is forbidden for OpenHands runtime")
    for key in ("CONDA_PREFIX", "CONDA_DEFAULT_ENV", "MAMBA_ROOT_PREFIX"):
        if os.environ.get(key):
            raise OpenHandsAdmissionError(f"{key} must not be active for OpenHands runtime")


def validate_relative_path(relative_path: str) -> str:
    rel = Path(relative_path)
    if not relative_path or rel.is_absolute() or ".." in rel.parts or relative_path.startswith("~"):
        raise OpenHandsAdmissionError("delegated path must be a bounded relative path")
    normalized = rel.as_posix()
    if normalized in {".", ""}:
        raise OpenHandsAdmissionError("delegated path cannot be workspace root")
    return normalized


def validate_external_tool_authorization(
    receipt: dict[str, Any],
    *,
    task_id: str,
    relative_path: str,
    content_sha256: str,
    now: datetime | None = None,
) -> None:
    if receipt.get("schema") != "fa3.canonical-tool-authorization-receipt.v1":
        raise OpenHandsAdmissionError("external tool authorization schema mismatch")
    if receipt.get("issuer_id") != EXPECTED_AUTH_ISSUER:
        raise OpenHandsAdmissionError("external tool authorization issuer mismatch")
    if receipt.get("provider_id") != PROVIDER_ID:
        raise OpenHandsAdmissionError("external tool authorization provider mismatch")
    if receipt.get("task_id") != task_id:
        raise OpenHandsAdmissionError("external tool authorization task mismatch")
    if receipt.get("authorized") is not True:
        raise OpenHandsAdmissionError("external tool authorization denied")
    scope = receipt.get("scope") or {}
    if scope.get("operation") != "workspace.write.exact":
        raise OpenHandsAdmissionError("external tool authorization operation mismatch")
    if scope.get("relative_path") != validate_relative_path(relative_path):
        raise OpenHandsAdmissionError("external tool authorization path mismatch")
    if scope.get("content_sha256") != content_sha256:
        raise OpenHandsAdmissionError("external tool authorization content hash mismatch")
    expires_at = receipt.get("expires_at")
    if not isinstance(expires_at, str) or not expires_at.endswith("Z"):
        raise OpenHandsAdmissionError("external tool authorization expiry missing")
    current = now or datetime.now(timezone.utc)
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OpenHandsAdmissionError("external tool authorization expiry invalid") from exc
    if expiry <= current:
        raise OpenHandsAdmissionError("external tool authorization expired")
    if receipt.get("single_use") is not True:
        raise OpenHandsAdmissionError("external tool authorization must be single-use")


def sanitized_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if SECRET_KEY_RE.search(str(key)):
                out[key] = "<redacted>"
            else:
                out[key] = sanitized_metadata(item)
        return out
    if isinstance(value, list):
        return [sanitized_metadata(x) for x in value]
    return value


def build_bwrap_command(
    *,
    root: Path,
    venv: Path,
    workspace: Path,
    mode: str,
    task_id: str,
    relative_path: str,
    expected_content: str,
    result_path: Path,
    auth_receipt: Path | None = None,
    router_socket: Path | None = None,
    router_key_file: Path | None = None,
    model_alias: str = DEFAULT_MODEL_ALIAS,
) -> list[str]:
    if mode not in {"isolated", "production"}:
        raise OpenHandsAdmissionError("mode must be isolated or production")
    relative_path = validate_relative_path(relative_path)
    bwrap = find_bwrap()
    root = root.resolve()
    venv = venv.resolve()
    workspace = workspace.resolve()
    result_path = result_path.resolve()
    if not workspace.is_dir():
        raise OpenHandsAdmissionError("workspace directory missing")
    if root == workspace or root in workspace.parents:
        raise OpenHandsAdmissionError("workspace must not contain repository root")
    expected_hash = sha256_bytes(expected_content.encode("utf-8"))

    cmd = [
        str(bwrap),
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--dir", "/tmp/home",
        "--dir", "/run",
        "--dir", "/run/fa3",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/bin", "/bin",
    ]
    for path in ("/lib", "/lib64"):
        if Path(path).exists():
            cmd += ["--ro-bind", path, path]
    for path in ("/etc/ld.so.cache", "/etc/passwd", "/etc/group", "/etc/localtime"):
        if Path(path).exists():
            cmd += ["--ro-bind", path, path]

    cmd += [
        "--ro-bind", str(venv), "/venv",
        "--ro-bind", str(root), "/fa3",
        "--bind", str(workspace), "/workspace",
        "--clearenv",
        "--setenv", "PATH", "/venv/bin:/usr/bin:/bin",
        "--setenv", "HOME", "/tmp/home",
        "--setenv", "PYTHONNOUSERSITE", "1",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
        "--setenv", "FA3_OPENHANDS_MODE", mode,
        "--setenv", "FA3_TASK_ID", task_id,
        "--setenv", "FA3_ALLOWED_RELATIVE_PATH", relative_path,
        "--setenv", "FA3_EXPECTED_CONTENT_SHA256", expected_hash,
        "--setenv", "FA3_EXPECTED_CONTENT", expected_content,
        "--setenv", "FA3_MODEL_ALIAS", model_alias,
        "--chdir", "/workspace",
    ]

    if mode == "production":
        if not auth_receipt or not router_socket or not router_key_file:
            raise OpenHandsAdmissionError("production mode requires auth receipt, router socket and key file")
        for p, dest in (
            (auth_receipt, "/run/fa3/tool-auth.json"),
            (router_socket, "/run/fa3/model-router.sock"),
            (router_key_file, "/run/fa3/model-key"),
        ):
            p = p.resolve()
            if not p.exists():
                raise OpenHandsAdmissionError(f"production input missing: {p}")
            cmd += ["--ro-bind", str(p), dest]
        cmd += [
            "--setenv", "FA3_TOOL_AUTH_RECEIPT", "/run/fa3/tool-auth.json",
            "--setenv", "FA3_ROUTER_SOCKET", "/run/fa3/model-router.sock",
            "--setenv", "FA3_ROUTER_KEY_FILE", "/run/fa3/model-key",
        ]

    cmd += [
        "/venv/bin/python",
        "/fa3/src/fa3_openhands_current_host_worker.py",
        "--result", "/workspace/" + result_path.name,
    ]
    return cmd


def command_contains_secret_value(command: list[str], secret_value: str | None) -> bool:
    if not secret_value:
        return False
    return any(secret_value in token for token in command)
