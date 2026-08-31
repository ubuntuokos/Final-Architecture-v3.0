#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_codex_adapter import (
    ADAPTER_ID,
    ARCHIVE_NAME,
    ARCHIVE_SHA256,
    CODEX_VERSION,
    PROVIDER_ID,
    CodexAdapter,
    codex_preflight,
    sha256_file,
)
from fa3_developer_agent_coordination import AgentTask, Coordinator

UPSTREAM_TAG = "rust-v0.151.0"
UPSTREAM_COMMIT = "78c290807ce710180111df227df3b7a4fe845452"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_extract(archive: Path, destination: Path) -> list[Path]:
    destination = destination.resolve()
    extracted: list[Path] = []
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        for member in members:
            target = (destination / member.name).resolve(strict=False)
            if target != destination and destination not in target.parents:
                raise RuntimeError(f"archive path traversal denied: {member.name}")
            if member.issym() or member.islnk():
                raise RuntimeError(f"archive link member denied: {member.name}")
        tf.extractall(destination)
        for member in members:
            if member.isfile():
                extracted.append((destination / member.name).resolve())
    return extracted


def verify_installed_binary_against_archive(binary: Path, archive: Path) -> dict:
    if sha256_file(archive) != ARCHIVE_SHA256:
        raise RuntimeError("cached Codex archive SHA256 does not match canonical pin")
    with tempfile.TemporaryDirectory(prefix="fa3-codex-reextract-") as td:
        files = _safe_extract(archive, Path(td))
        candidates = [
            p for p in files
            if p.name in {"codex", "codex-x86_64-unknown-linux-musl"}
            or p.name.startswith("codex-x86_64-unknown-linux")
        ]
        if not candidates:
            raise RuntimeError("pinned Codex archive does not contain a recognizable executable")
        installed_hash = sha256_file(binary)
        matching = [p for p in candidates if sha256_file(p) == installed_hash]
        if len(matching) != 1:
            raise RuntimeError("installed Codex binary does not reproduce from pinned archive")
        return {
            "archive": str(archive.resolve()),
            "archive_sha256": ARCHIVE_SHA256,
            "archive_integrity": "PASS",
            "installed_binary": str(binary.resolve()),
            "installed_binary_sha256": installed_hash,
            "reextracted_binary_sha256": installed_hash,
            "installed_binary_matches_pinned_archive": True,
            "matched_archive_member": matching[0].name,
        }


def init_probe_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(path), "init", "-b", "main"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "FA3 Codex Current Host"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "fa3-codex-current-host@localhost"], check=True)
    files = {
        "work/architecture.txt": "baseline architecture\n",
        "work/security.txt": "baseline security\n",
    }
    for rel, content in files.items():
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "baseline"], check=True, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect real FA3 Codex current-host production E2E evidence")
    default_root = Path.home() / ".local/lib/fa3/codex" / CODEX_VERSION
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--codex-binary", default=str(default_root / "bin/codex"))
    ap.add_argument("--archive", default=str(default_root / "source" / ARCHIVE_NAME))
    ap.add_argument("--timeout-seconds", type=int, default=600)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    binary = Path(args.codex_binary).expanduser().resolve()
    archive = Path(args.archive).expanduser().resolve()
    if os.name != "posix" or platform.system() != "Linux":
        raise RuntimeError("FA3 Codex v0.1 current-host evidence requires Linux")
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("FA3 Codex v0.1 pinned artifact is Linux x86_64 only")
    if os.geteuid() == 0:
        raise RuntimeError("FA3 Codex current-host evidence must run as a non-root user")
    if not shutil.which("git"):
        raise RuntimeError("git is required")
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError(f"pinned Codex binary is missing or not executable: {binary}")
    if not archive.is_file():
        raise RuntimeError(f"pinned Codex archive is missing: {archive}")
    if not 60 <= args.timeout_seconds <= 1800:
        raise RuntimeError("timeout is outside canonical range")

    started = now()
    supply = verify_installed_binary_against_archive(binary, archive)
    preflight = codex_preflight(binary)
    with tempfile.TemporaryDirectory(prefix="fa3-codex-current-host-") as td:
        base = Path(td)
        repo = base / "repo"
        control = base / "control"
        init_probe_repo(repo)
        tasks = [
            AgentTask(
                "CODEX-HOST-ARCH",
                "codex-architecture",
                PROVIDER_ID,
                "work/architecture.txt",
                "FA3 Codex current-host architecture worker PASS\n",
            ),
            AgentTask(
                "CODEX-HOST-SEC",
                "codex-security",
                PROVIDER_ID,
                "work/security.txt",
                "FA3 Codex current-host security worker PASS\n",
            ),
        ]
        coord = Coordinator(repo, control, max_message_hops=4)
        result = coord.run(tasks, CodexAdapter(binary, timeout_seconds=args.timeout_seconds))
        worker_results = [
            json.loads((control / "results" / f"{task.task_id}.json").read_text(encoding="utf-8"))
            for task in tasks
        ]
        if not all(x.get("status") == "PASS" for x in worker_results):
            raise RuntimeError("one or more real Codex workers did not produce PASS results")
        event_summaries = [x.get("event_summary", {}) for x in worker_results]
        forbidden = any(
            summary.get("forbidden_surface_observed") is not False
            or any(item in {"mcp_tool_call", "collab_tool_call", "web_search"} for item in summary.get("item_types", []))
            for summary in event_summaries
        )
        if forbidden:
            raise RuntimeError("forbidden Codex provider tool surface was observed")
        exact_scope = all(x.get("changed_paths") == [task.relative_path] for x, task in zip(worker_results, tasks))
        if not exact_scope:
            raise RuntimeError("real Codex worker changed paths outside delegated scope")
        controls = worker_results[0]["execution_controls"]
        if any(x.get("execution_controls") != controls for x in worker_results[1:]):
            raise RuntimeError("Codex worker execution-control projection is inconsistent")

        receipt = {
            "schema": "fa3.codex-current-host-receipt.v1",
            "provider_id": PROVIDER_ID,
            "adapter_id": ADAPTER_ID,
            "status": "PASS",
            "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS",
            "collector_mode": "REAL_CODEX_CLI_CURRENT_HOST",
            "synthetic": False,
            "started_at": started,
            "completed_at": now(),
            "host": {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "machine": platform.machine(),
                "effective_uid": os.geteuid(),
            },
            "upstream": {
                "version": CODEX_VERSION,
                "release_tag": UPSTREAM_TAG,
                "release_commit": UPSTREAM_COMMIT,
            },
            "supply_chain": supply,
            "runtime": {
                "binary": preflight["binary"],
                "version": preflight["version"],
                "version_output": preflight["version_output"],
            },
            "authentication": {
                "mode": preflight["auth_mode"],
                "credential_material_captured": False,
                "api_key_env_passthrough": False,
            },
            "execution_controls": controls,
            "production_e2e": {
                "worker_count": result["worker_count"],
                "workspace_count": result["workspace_count"],
                "worker_heads_unchanged": result["worker_heads_unchanged"],
                "integration_commit": result["integration_commit"],
                "integration_author": result["integration_author"],
                "changed_paths": result["changed_paths"],
                "exact_mutation_scope": exact_scope,
                "forbidden_provider_surface_observed": forbidden,
                "event_summaries": event_summaries,
                "cleanup": result["cleanup"],
                "event_log_sha256": result["event_log_sha256"],
            },
        }

    receipt_path = root / "evidence/receipts/codex-current-host.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    runtime_dir = root / "evidence/runtime/codex-current-host"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "last-run-summary.json").write_text(
        json.dumps(
            {
                "provider_id": PROVIDER_ID,
                "status": "PASS",
                "completed_at": receipt["completed_at"],
                "binary_sha256": supply["installed_binary_sha256"],
                "integration_commit": receipt["production_e2e"]["integration_commit"],
                "event_log_sha256": receipt["production_e2e"]["event_log_sha256"],
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FA3 CODEX CURRENT-HOST EVIDENCE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)
