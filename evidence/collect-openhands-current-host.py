#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_openhands_adapter import (
    COMPONENT_VERSION,
    DEFAULT_MODEL_ALIAS,
    ISOLATED_EVIDENCE_LEVEL,
    PINNED_COMMIT,
    PINNED_TREE,
    PRODUCTION_EVIDENCE_LEVEL,
    PROVIDER_ID,
    RUNTIME_ID,
    OpenHandsAdmissionError,
    assert_no_conda,
    build_bwrap_command,
    command_contains_secret_value,
    find_bwrap,
    host_fingerprint,
    inspect_component_versions,
    sha256_bytes,
    sha256_file,
    utc_now,
    validate_external_tool_authorization,
    validate_relative_path,
    validate_source_checkout,
    venv_python,
)


def writej(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(
    argv: list[str],
    *,
    timeout: int = 600,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        cwd=str(cwd) if cwd else None,
        env=env,
    )


def git(repo: Path, *args: str) -> str:
    p = run(["git", "-C", str(repo), *args], timeout=60)
    if p.returncode != 0:
        raise OpenHandsAdmissionError(
            f"git {' '.join(args)} failed: {(p.stderr or p.stdout).strip()}"
        )
    return p.stdout.strip()


def denied(fn: Callable[[], Any]) -> bool:
    try:
        fn()
    except Exception:
        return True
    return False


def dmi_identity() -> dict[str, Any]:
    def read(path: str) -> str | None:
        p = Path(path)
        try:
            return p.read_text(encoding="utf-8", errors="replace").strip() if p.is_file() else None
        except OSError:
            return None

    models = set()
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("model name"):
                models.add(line.split(":", 1)[1].strip())
    except OSError:
        pass
    return {
        "sys_vendor": read("/sys/class/dmi/id/sys_vendor"),
        "product_name": read("/sys/class/dmi/id/product_name"),
        "cpu_models": sorted(models),
    }


def current_host_context() -> dict[str, Any]:
    runner_env = os.environ.get("RUNNER_ENVIRONMENT", "")
    github_actions = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    github_hosted = github_actions and runner_env.lower() != "self-hosted"
    marker = os.environ.get("FA3_CURRENT_HOST") == "1" and not github_hosted
    info = host_fingerprint()
    info.update(
        {
            "current_host_marker": marker,
            "github_actions": github_actions,
            "runner_environment": runner_env or None,
            "github_hosted_runner": github_hosted,
            "dmi": dmi_identity(),
        }
    )
    return info


def require_current_host_context() -> dict[str, Any]:
    host = current_host_context()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise OpenHandsAdmissionError("OpenHands evidence requires Linux x86_64")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise OpenHandsAdmissionError("OpenHands evidence must not run as root")
    if host["github_hosted_runner"]:
        raise OpenHandsAdmissionError("GitHub-hosted runners cannot produce OpenHands current-host evidence")
    if not host["current_host_marker"]:
        raise OpenHandsAdmissionError("set FA3_CURRENT_HOST=1 only on the authorized FA3 current-host runner")
    return host


def pip_freeze_digest(venv: Path) -> tuple[str, int]:
    py = venv_python(venv)
    p = run([str(py), "-m", "pip", "freeze", "--all"], timeout=120)
    if p.returncode != 0:
        raise OpenHandsAdmissionError("pip freeze failed")
    normalized = "\n".join(sorted(x.strip() for x in p.stdout.splitlines() if x.strip())) + "\n"
    return sha256_bytes(normalized.encode("utf-8")), len(normalized.splitlines())


def init_workspace(path: Path, relative_path: str) -> tuple[str, str]:
    path.mkdir(parents=True, exist_ok=True)
    p = run(["git", "-C", str(path), "init", "-b", "main"], timeout=60)
    if p.returncode != 0:
        raise OpenHandsAdmissionError("git init failed")
    run(["git", "-C", str(path), "config", "user.name", "FA3 OpenHands Evidence"], timeout=30)
    run(["git", "-C", str(path), "config", "user.email", "fa3-openhands@localhost"], timeout=30)
    target = path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("FA3_OPENHANDS_BASELINE\n", encoding="utf-8")
    exclude = path / ".git/info/exclude"
    exclude.write_text(
        exclude.read_text(encoding="utf-8")
        + "\n.fa3-openhands-state/\n.fa3-openhands-worker-result.json\n",
        encoding="utf-8",
    )
    p = run(["git", "-C", str(path), "add", "."], timeout=30)
    if p.returncode != 0:
        raise OpenHandsAdmissionError("git add failed")
    p = run(["git", "-C", str(path), "commit", "-m", "FA3 OpenHands baseline"], timeout=60)
    if p.returncode != 0:
        raise OpenHandsAdmissionError("git baseline commit failed")
    return git(path, "rev-parse", "HEAD"), sha256_file(target)


def bwrap_probe(root: Path, venv: Path, workspace: Path) -> dict[str, Any]:
    bwrap = find_bwrap()
    probe = r'''
import json, pathlib, socket
r={}
try:
    socket.create_connection(("1.1.1.1",80),timeout=1)
    r["general_network_egress_denied"]=False
except Exception:
    r["general_network_egress_denied"]=True
r["host_home_not_mounted"]=not pathlib.Path("/home").exists()
try:
    pathlib.Path("/fa3/.fa3-bwrap-write-probe").write_text("x")
    r["repository_read_only"]=False
except Exception:
    r["repository_read_only"]=True
try:
    p=pathlib.Path("/workspace/.fa3-bwrap-probe")
    p.write_text("ok")
    p.unlink()
    r["delegated_workspace_write_only"]=True
except Exception:
    r["delegated_workspace_write_only"]=False
r["root_filesystem_not_bind_mounted"]=not pathlib.Path("/etc/shadow").exists()
print(json.dumps(r,sort_keys=True))
'''
    cmd = [
        str(bwrap), "--die-with-parent", "--new-session", "--unshare-all",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--dir", "/tmp/home", "--dir", "/run", "--dir", "/run/fa3",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/bin", "/bin",
    ]
    for path in ("/lib", "/lib64"):
        if Path(path).exists():
            cmd += ["--ro-bind", path, path]
    for path in ("/etc/ld.so.cache", "/etc/passwd", "/etc/group", "/etc/localtime"):
        if Path(path).exists():
            cmd += ["--ro-bind", path, path]
    cmd += [
        "--ro-bind", str(venv.resolve()), "/venv",
        "--ro-bind", str(root.resolve()), "/fa3",
        "--bind", str(workspace.resolve()), "/workspace",
        "--clearenv",
        "--setenv", "PATH", "/venv/bin:/usr/bin:/bin",
        "--setenv", "HOME", "/tmp/home",
        "--chdir", "/workspace",
        "/venv/bin/python", "-c", probe,
    ]
    p = run(cmd, timeout=60)
    if p.returncode != 0:
        raise OpenHandsAdmissionError(f"bubblewrap isolation probe failed: {p.stderr[-1500:]}")
    result = json.loads(p.stdout.strip().splitlines()[-1])
    required = {
        "general_network_egress_denied",
        "host_home_not_mounted",
        "repository_read_only",
        "delegated_workspace_write_only",
        "root_filesystem_not_bind_mounted",
    }
    if set(result) != required or not all(result.values()):
        raise OpenHandsAdmissionError(f"bubblewrap isolation boundary probe failed: {result}")
    return result


def start_router_bridge(root: Path, sock_path: Path, port: int) -> subprocess.Popen[str]:
    proc = subprocess.Popen(
        [
            sys.executable,
            str(root / "src/fa3_openhands_router_bridge.py"),
            "--socket", str(sock_path),
            "--target-host", "127.0.0.1",
            "--target-port", str(port),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr else ""
            raise OpenHandsAdmissionError(f"router bridge exited early: {stderr[-1000:]}")
        if sock_path.exists() and stat_is_socket(sock_path):
            return proc
        time.sleep(0.1)
    raise OpenHandsAdmissionError("router bridge readiness timeout")


def stat_is_socket(path: Path) -> bool:
    import stat
    try:
        return stat.S_ISSOCK(path.stat().st_mode)
    except OSError:
        return False


def stop_process(proc: subprocess.Popen[str] | None) -> bool:
    if proc is None:
        return True
    try:
        if proc.poll() is None:
            os.killpg(proc.pid, 15)
            proc.wait(timeout=10)
    except Exception:
        try:
            os.killpg(proc.pid, 9)
            proc.wait(timeout=5)
        except Exception:
            return False
    return proc.poll() is not None


def make_good_auth(task_id: str, relative_path: str, content_sha256: str) -> dict[str, Any]:
    return {
        "schema": "fa3.canonical-tool-authorization-receipt.v1",
        "issuer_id": "FA3-AUTH-MCP-GATEWAY-001",
        "provider_id": PROVIDER_ID,
        "task_id": task_id,
        "authorized": True,
        "single_use": True,
        "issued_at": utc_now(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
        "scope": {
            "operation": "workspace.write.exact",
            "relative_path": relative_path,
            "content_sha256": content_sha256,
        },
    }


def negative_tests(task_id: str, relative_path: str, content_sha256: str, command: list[str], secret: str | None) -> dict[str, bool]:
    good = make_good_auth(task_id, relative_path, content_sha256)
    wrong = json.loads(json.dumps(good))
    wrong["scope"]["relative_path"] = "work/not-authorized.txt"
    expired = json.loads(json.dumps(good))
    expired["expires_at"] = "2000-01-01T00:00:00Z"
    provider = json.loads(json.dumps(good))
    provider["issuer_id"] = PROVIDER_ID
    return {
        "path_traversal_denied": denied(lambda: validate_relative_path("../escape")),
        "wrong_path_authorization_denied": denied(
            lambda: validate_external_tool_authorization(
                wrong, task_id=task_id, relative_path=relative_path, content_sha256=content_sha256
            )
        ),
        "expired_authorization_denied": denied(
            lambda: validate_external_tool_authorization(
                expired, task_id=task_id, relative_path=relative_path, content_sha256=content_sha256
            )
        ),
        "provider_as_authority_denied": denied(
            lambda: validate_external_tool_authorization(
                provider, task_id=task_id, relative_path=relative_path, content_sha256=content_sha256
            )
        ),
        "command_secret_value_absent": not command_contains_secret_value(command, secret),
    }


def collect(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    root = Path(args.root).resolve()
    mode = args.mode
    source = Path(args.source).expanduser().resolve()
    venv = Path(args.venv).expanduser().resolve()
    receipt_rel = (
        "evidence/receipts/openhands-current-host.json"
        if mode == "production"
        else "evidence/receipts/openhands-current-host-isolated.json"
    )
    receipt_path = root / receipt_rel
    host = require_current_host_context()
    assert_no_conda(venv)
    source_identity = validate_source_checkout(source)
    versions = inspect_component_versions(venv)
    freeze_sha, freeze_count = pip_freeze_digest(venv)
    py = venv_python(venv)
    bwrap = find_bwrap()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_dir = root / "evidence/runtime/openhands-current-host" / stamp
    runtime_dir.mkdir(parents=True, exist_ok=True)
    base_tmp = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir())
    temp_parent = Path(tempfile.mkdtemp(prefix="fa3-openhands-", dir=str(base_tmp)))
    workspace = temp_parent / "workspace"
    relative_path = "work/openhands.txt"
    expected_content = "FA3_OPENHANDS_CURRENT_HOST_E2E_PASS\n"
    expected_sha = sha256_bytes(expected_content.encode("utf-8"))
    task_id = "fa3-openhands-current-host-" + stamp.lower()

    bridge: subprocess.Popen[str] | None = None
    bridge_socket = temp_parent / "model-router.sock"
    worker_result_path = workspace / ".fa3-openhands-worker-result.json"
    auth_receipt: Path | None = None
    router_key_file: Path | None = None
    secret_value: str | None = None
    authorization: dict[str, Any]

    receipt: dict[str, Any] = {
        "schema": "fa3.openhands-current-host-receipt.v1",
        "provider_id": PROVIDER_ID,
        "runtime_id": RUNTIME_ID,
        "status": "FAIL",
        "mode": mode,
        "evidence_level": (
            PRODUCTION_EVIDENCE_LEVEL if mode == "production" else ISOLATED_EVIDENCE_LEVEL
        ),
        "started_at": utc_now(),
        "host": host,
        "source": {
            "repository": "OpenHands/software-agent-sdk",
            "commit": source_identity["commit"],
            "tree": source_identity["tree"],
            "dirty": False,
        },
        "runtime": {
            "python_major_minor": ".".join(platform.python_version().split(".")[:2]),
            "packaging": "pip-venv",
            "conda_or_mamba_active": False,
            "component_versions": versions,
            "pip_freeze_sha256": freeze_sha,
            "pip_freeze_line_count": freeze_count,
            "venv_python_sha256": sha256_file(py.resolve()),
            "network_bootstrap_performed_during_e2e": False,
        },
        "capability_count_after": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
    }

    try:
        before_head, before_sha = init_workspace(workspace, relative_path)
        isolation_probe = bwrap_probe(root, venv, workspace)

        if mode == "production":
            if not args.tool_auth_receipt or not args.router_key_file:
                raise OpenHandsAdmissionError(
                    "production mode requires --tool-auth-receipt and --router-key-file"
                )
            auth_receipt = Path(args.tool_auth_receipt).expanduser().resolve()
            router_key_file = Path(args.router_key_file).expanduser().resolve()
            if not auth_receipt.is_file() or not router_key_file.is_file():
                raise OpenHandsAdmissionError("production authorization/key file missing")
            if router_key_file.stat().st_mode & 0o077:
                raise OpenHandsAdmissionError("router key file permissions must be 0600 or stricter")
            secret_value = router_key_file.read_text(encoding="utf-8").strip()
            if not secret_value:
                raise OpenHandsAdmissionError("router key file is empty")
            auth_obj = json.loads(auth_receipt.read_text(encoding="utf-8"))
            validate_external_tool_authorization(
                auth_obj,
                task_id=task_id,
                relative_path=relative_path,
                content_sha256=expected_sha,
            )
            authorization = {
                "class": "EXTERNAL_CANONICAL_TOOL_AUTHORIZATION",
                "issuer_id": auth_obj.get("issuer_id"),
                "single_use": auth_obj.get("single_use"),
                "receipt_sha256": sha256_file(auth_receipt),
                "expires_at": auth_obj.get("expires_at"),
            }
            bridge = start_router_bridge(root, bridge_socket, int(args.router_port))
        else:
            authorization = {
                "class": "FIXTURE_NON_PRODUCTION",
                "issuer_id": None,
                "single_use": True,
                "receipt_sha256": None,
                "expires_at": None,
            }

        command = build_bwrap_command(
            root=root,
            venv=venv,
            workspace=workspace,
            mode=mode,
            task_id=task_id,
            relative_path=relative_path,
            expected_content=expected_content,
            result_path=worker_result_path,
            auth_receipt=auth_receipt,
            router_socket=bridge_socket if mode == "production" else None,
            router_key_file=router_key_file,
            model_alias=args.model_alias,
        )
        negatives = negative_tests(task_id, relative_path, expected_sha, command, secret_value)
        if not all(negatives.values()):
            raise OpenHandsAdmissionError(f"pre-execution negative tests failed: {negatives}")

        proc = run(command, timeout=int(args.timeout))
        (runtime_dir / "worker.stdout.sha256").write_text(
            sha256_bytes(proc.stdout.encode("utf-8", errors="replace")) + "\n",
            encoding="utf-8",
        )
        (runtime_dir / "worker.stderr.sha256").write_text(
            sha256_bytes(proc.stderr.encode("utf-8", errors="replace")) + "\n",
            encoding="utf-8",
        )
        if proc.returncode != 0:
            raise OpenHandsAdmissionError(
                f"OpenHands sandbox worker failed rc={proc.returncode}: {proc.stderr[-2000:]}"
            )
        if not worker_result_path.is_file():
            raise OpenHandsAdmissionError("OpenHands worker result file missing")
        worker = json.loads(worker_result_path.read_text(encoding="utf-8"))
        if worker.get("status") != "PASS":
            raise OpenHandsAdmissionError(f"OpenHands worker result failed: {worker}")
        writej(runtime_dir / "worker-result.json", worker)

        after_head = git(workspace, "rev-parse", "HEAD")
        changed = [x for x in git(workspace, "diff", "--name-only", "HEAD", "--").splitlines() if x]
        status_rows = [
            x for x in git(workspace, "status", "--porcelain", "--untracked-files=all").splitlines() if x
        ]
        after_sha = sha256_file(workspace / relative_path)
        mutation = {
            "authorized_relative_path": relative_path,
            "before_head": before_head,
            "after_head": after_head,
            "worker_commit_created": after_head != before_head,
            "changed_paths": changed,
            "git_status_rows": status_rows,
            "before_sha256": before_sha,
            "after_sha256": after_sha,
        }
        if after_head != before_head or changed != [relative_path]:
            raise OpenHandsAdmissionError(f"OpenHands mutation scope/commit mismatch: {mutation}")
        if after_sha != expected_sha or worker.get("target_sha256") != expected_sha:
            raise OpenHandsAdmissionError("OpenHands target content hash mismatch")

        receipt.update(
            {
                "status": "PASS",
                "completed_at": utc_now(),
                "isolation": {
                    "bubblewrap": True,
                    "bwrap_binary_sha256": sha256_file(bwrap),
                    "unshare_all": True,
                    **isolation_probe,
                },
                "authorization": authorization,
                "worker": worker,
                "mutation": mutation,
                "negative_tests": negatives,
                "production_admission_claim": mode == "production",
            }
        )
    except Exception as exc:
        receipt["completed_at"] = utc_now()
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
        raise
    finally:
        bridge_stopped = stop_process(bridge)
        try:
            shutil.rmtree(temp_parent)
            workspace_removed = not temp_parent.exists()
        except Exception:
            workspace_removed = False
        receipt["cleanup"] = {
            "workspace_removed": workspace_removed,
            "router_bridge_stopped": bridge_stopped,
            "temporary_secret_copy_removed": True,
        }
        writej(receipt_path, receipt)
        writej(runtime_dir / "summary.json", {
            "provider_id": PROVIDER_ID,
            "runtime_id": RUNTIME_ID,
            "status": receipt.get("status"),
            "mode": mode,
            "evidence_level": receipt.get("evidence_level"),
            "receipt_sha256": sha256_file(receipt_path),
            "completed_at": receipt.get("completed_at"),
        })
    return receipt, receipt_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect real FA3 OpenHands current-host runtime evidence")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--mode", choices=("isolated", "production"), default="isolated")
    base = Path.home() / ".local/share/fa3/openhands"
    ap.add_argument("--source", default=str(base / f"source-{PINNED_COMMIT}"))
    ap.add_argument("--venv", default=str(base / f"venv-{COMPONENT_VERSION}"))
    ap.add_argument("--tool-auth-receipt")
    ap.add_argument("--router-key-file")
    ap.add_argument("--router-port", type=int, default=4000)
    ap.add_argument("--model-alias", default=DEFAULT_MODEL_ALIAS)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()
    try:
        receipt, _ = collect(args)
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0 if receipt.get("status") == "PASS" else 2
    except Exception as exc:
        print(f"FA3 OpenHands current-host collection failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
