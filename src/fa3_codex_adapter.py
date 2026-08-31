#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from fa3_developer_agent_coordination import AgentTask, Coordinator, ProviderAdapter

PROVIDER_ID = "FA3-PROVIDER-CODEX-001"
ADAPTER_ID = "FA3-CODEX-ADAPTER-001"
CODEX_VERSION = "0.151.0"
CODEX_VERSION_OUTPUT = f"codex-cli {CODEX_VERSION}"
UPSTREAM_TAG = "rust-v0.151.0"
UPSTREAM_COMMIT = "78c290807ce710180111df227df3b7a4fe845452"
ARCHIVE_NAME = "codex-x86_64-unknown-linux-musl.tar.gz"
ARCHIVE_SHA256 = "605b4b183f22c645f5def63a5b7191767407fb66a6feaec4eaf10b5b7e0058f6"

FORBIDDEN_FLAGS = {
    "--approve-for-me",
    "--not-so-yolo",
    "--dangerously-bypass-approvals-and-sandbox",
    "--yolo",
    "--dangerously-bypass-hook-trust",
    "--add-dir",
}
CONFIG_OVERRIDES = (
    'web_search="disabled"',
    "mcp_servers={}",
    "allow_login_shell=false",
    "features.multi_agent=false",
    "features.multi_agent_v2=false",
    "features.plugins=false",
    "features.remote_plugin=false",
    "features.plugin_hooks=false",
    "features.memories=false",
    "features.memory_tool=false",
)
FORBIDDEN_ITEM_TYPES = {"mcp_tool_call", "collab_tool_call", "web_search"}
FATAL_EVENT_TYPES = {"turn.failed", "error"}

_ENV_ALLOWLIST = {
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "SHELL",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "CODEX_HOME",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
}
_SECRET_ENV_PATTERN = re.compile(
    r"(API[_-]?KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH[_-]?KEY|PRIVATE[_-]?KEY)",
    re.IGNORECASE,
)


class CodexAdapterDenied(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_codex_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    source = dict(os.environ if source is None else source)
    env = {key: value for key, value in source.items() if key in _ENV_ALLOWLIST and value}
    leaked = [key for key in env if _SECRET_ENV_PATTERN.search(key)]
    if leaked:
        raise CodexAdapterDenied(f"secret-like environment key reached Codex allowlist: {leaked}")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def mutation_path(workspace: Path, relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise CodexAdapterDenied("Codex mutation path must be non-empty and relative")
    rel = Path(relative_path)
    if ".." in rel.parts:
        raise CodexAdapterDenied("Codex mutation path traversal denied")
    root = workspace.resolve()
    target = (root / rel).resolve(strict=False)
    if target == root or root not in target.parents:
        raise CodexAdapterDenied("Codex mutation path escaped delegated workspace")
    if target.exists() and target.is_symlink():
        raise CodexAdapterDenied("Codex mutation target may not be a symlink")
    return target


def build_prompt(task: AgentTask) -> str:
    payload = {
        "task_id": task.task_id,
        "allowed_relative_path": task.relative_path,
        "exact_utf8_content": task.content,
        "content_sha256": sha256_bytes(task.content.encode("utf-8")),
    }
    return (
        "You are a delegated FA3 developer worker inside an isolated Git worktree.\n"
        "Do exactly one bounded mutation. Do not commit. Do not create branches. "
        "Do not use network/web search, MCP, plugins, skills, subagents or delegation. "
        "Modify ONLY the allowed_relative_path from the JSON payload. Replace the entire file "
        "with exact_utf8_content. Do not change any other file. After the edit, verify the file "
        "content and stop.\n"
        "FA3_CODEX_TASK_JSON="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "\n"
    )


def build_codex_exec_command(codex_binary: Path, workspace: Path, last_message: Path) -> list[str]:
    binary = codex_binary.resolve()
    root = workspace.resolve()
    command = [
        str(binary),
        "exec",
        "--strict-config",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--json",
        "--color",
        "never",
        "--sandbox",
        "workspace-write",
        "-C",
        str(root),
        "--output-last-message",
        str(last_message.resolve()),
    ]
    for override in CONFIG_OVERRIDES:
        command.extend(["-c", override])
    command.append("-")
    validate_codex_command(command, root)
    return command


def validate_codex_command(command: list[str], workspace: Path) -> None:
    tokens = set(command)
    forbidden = sorted(tokens & FORBIDDEN_FLAGS)
    if forbidden:
        raise CodexAdapterDenied(f"forbidden Codex flags present: {forbidden}")
    required = {
        "exec",
        "--strict-config",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--json",
        "--sandbox",
        "workspace-write",
        "-C",
        str(workspace.resolve()),
    }
    missing = sorted(required - tokens)
    if missing:
        raise CodexAdapterDenied(f"required Codex execution controls missing: {missing}")
    joined = "\n".join(command)
    for override in CONFIG_OVERRIDES:
        if override not in joined:
            raise CodexAdapterDenied(f"required Codex config override missing: {override}")
    if command[-1] != "-":
        raise CodexAdapterDenied("Codex prompt must be delivered over stdin")


def parse_codex_jsonl(text: str) -> dict[str, Any]:
    event_types: list[str] = []
    item_types: list[str] = []
    thread_id: str | None = None
    usage = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    command_count = 0
    file_change_count = 0
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception as exc:
            raise CodexAdapterDenied(f"Codex JSONL line {lineno} is invalid: {exc}") from exc
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise CodexAdapterDenied(f"Codex JSONL line {lineno} lacks typed event")
        event_type = event["type"]
        event_types.append(event_type)
        if event_type in FATAL_EVENT_TYPES:
            raise CodexAdapterDenied(f"Codex emitted fatal event: {event_type}")
        if event_type == "thread.started":
            thread_id = str(event.get("thread_id") or "")
        if event_type == "turn.completed":
            raw_usage = event.get("usage") or {}
            for key in usage:
                value = raw_usage.get(key, 0)
                if isinstance(value, int) and value >= 0:
                    usage[key] += value
        if event_type in {"item.started", "item.updated", "item.completed"}:
            item = event.get("item") or {}
            item_type = item.get("type")
            if isinstance(item_type, str):
                item_types.append(item_type)
                if item_type in FORBIDDEN_ITEM_TYPES:
                    raise CodexAdapterDenied(f"forbidden Codex tool surface observed: {item_type}")
                if item_type == "command_execution" and event_type == "item.completed":
                    command_count += 1
                if item_type == "file_change" and event_type == "item.completed":
                    file_change_count += 1
    if not thread_id:
        raise CodexAdapterDenied("Codex event stream has no thread.started identity")
    if "turn.completed" not in event_types:
        raise CodexAdapterDenied("Codex event stream has no successful turn.completed")
    return {
        "thread_id": thread_id,
        "event_count": len(event_types),
        "event_types": sorted(set(event_types)),
        "item_types": sorted(set(item_types)),
        "command_count": command_count,
        "file_change_count": file_change_count,
        "usage": usage,
        "forbidden_surface_observed": False,
    }


def _run_capture(command: list[str], *, env: dict[str, str], input_text: str | None = None,
                 cwd: Path | None = None, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
        cwd=str(cwd) if cwd else None,
        env=env,
        timeout=timeout,
        check=False,
    )


def codex_preflight(codex_binary: Path, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    binary = codex_binary.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise CodexAdapterDenied(f"Codex binary is not executable: {binary}")
    safe_env = safe_codex_environment(env)
    version = _run_capture([str(binary), "--version"], env=safe_env, timeout=15)
    version_text = (version.stdout + "\n" + version.stderr).strip()
    if version.returncode != 0 or CODEX_VERSION_OUTPUT not in version_text:
        raise CodexAdapterDenied(f"Codex version mismatch: {version_text!r}")
    login = _run_capture(
        [str(binary), "login", "status", "--ignore-user-config"],
        env=safe_env,
        timeout=30,
    )
    login_text = (login.stdout + "\n" + login.stderr).strip()
    if login.returncode != 0 or "Logged in using ChatGPT" not in login_text:
        raise CodexAdapterDenied(
            "FA3 Codex v0.1 requires persisted ChatGPT login; API-key/access-token mode is not admitted"
        )
    return {
        "binary": str(binary),
        "version": CODEX_VERSION,
        "version_output": CODEX_VERSION_OUTPUT,
        "auth_mode": "CHATGPT",
        "credential_material_captured": False,
    }


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise CodexAdapterDenied(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def codex_worker_main(request_path: Path, result_path: Path) -> int:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if request.get("provider_id") != PROVIDER_ID:
        raise CodexAdapterDenied("Codex worker provider identity mismatch")
    task_id = str(request["task_id"])
    agent_id = str(request["agent_id"])
    workspace = Path(request["workspace"]).resolve()
    relative_path = str(request["relative_path"])
    exact_content = str(request["content"])
    timeout_seconds = int(request.get("timeout_seconds", 600))
    if not 30 <= timeout_seconds <= 1800:
        raise CodexAdapterDenied("Codex timeout outside FA3 bounded range")
    target = mutation_path(workspace, relative_path)
    if not target.is_file():
        raise CodexAdapterDenied("Codex production adapter v0.1 only mutates pre-existing files")
    binary = Path(request["codex_binary"]).resolve()
    expected_head = _git(workspace, "rev-parse", "HEAD")
    last_message = result_path.with_suffix(".last-message.txt")
    command = build_codex_exec_command(binary, workspace, last_message)
    prompt = build_prompt(
        AgentTask(
            task_id=task_id,
            agent_id=agent_id,
            provider_id=PROVIDER_ID,
            relative_path=relative_path,
            content=exact_content,
        )
    )
    safe_env = safe_codex_environment()
    proc = _run_capture(
        command,
        env=safe_env,
        input_text=prompt,
        cwd=workspace,
        timeout=timeout_seconds,
    )
    stdout_bytes = proc.stdout.encode("utf-8", errors="replace")
    stderr_bytes = proc.stderr.encode("utf-8", errors="replace")
    if proc.returncode != 0:
        result = {
            "schema": "fa3.codex-adapter-worker-result.v1",
            "task_id": task_id,
            "agent_id": agent_id,
            "provider_id": PROVIDER_ID,
            "adapter_id": ADAPTER_ID,
            "status": "FAIL",
            "codex_returncode": proc.returncode,
            "stdout_sha256": sha256_bytes(stdout_bytes),
            "stderr_sha256": sha256_bytes(stderr_bytes),
            "stderr_tail_redacted": proc.stderr[-1000:],
        }
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 2
    summary = parse_codex_jsonl(proc.stdout)
    if _git(workspace, "rev-parse", "HEAD") != expected_head:
        raise CodexAdapterDenied("Codex worker committed instead of returning an uncommitted diff")
    changed = [x for x in _git(workspace, "diff", "--name-only", "HEAD", "--").splitlines() if x]
    if changed != [relative_path]:
        raise CodexAdapterDenied(f"Codex changed paths outside delegated scope: {changed}")
    if target.read_text(encoding="utf-8") != exact_content:
        raise CodexAdapterDenied("Codex target content does not match exact delegated probe content")
    result = {
        "schema": "fa3.codex-adapter-worker-result.v1",
        "task_id": task_id,
        "agent_id": agent_id,
        "provider_id": PROVIDER_ID,
        "adapter_id": ADAPTER_ID,
        "status": "PASS",
        "runtime_version": CODEX_VERSION,
        "changed_paths": changed,
        "target_sha256": sha256_file(target),
        "stdout_sha256": sha256_bytes(stdout_bytes),
        "stderr_sha256": sha256_bytes(stderr_bytes),
        "last_message_sha256": sha256_file(last_message) if last_message.is_file() else None,
        "event_summary": summary,
        "execution_controls": {
            "sandbox": "workspace-write",
            "approval_policy": "never",
            "ignore_user_config": True,
            "ignore_rules": True,
            "ephemeral": True,
            "strict_config": True,
            "web_search": False,
            "mcp": False,
            "nested_multi_agent": False,
            "plugins": False,
            "login_shell": False,
            "auto_review": False,
            "dangerous_bypass": False,
            "secret_env_passthrough": False,
        },
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if last_message.exists():
        last_message.unlink()
    return 0


class CodexAdapter(ProviderAdapter):
    provider_id = PROVIDER_ID

    def __init__(self, codex_binary: Path, *, timeout_seconds: int = 600):
        self.codex_binary = codex_binary.resolve()
        self.timeout_seconds = timeout_seconds

    def spawn(
        self,
        *,
        task: AgentTask,
        workspace: Path,
        request_path: Path,
        result_path: Path,
    ) -> subprocess.Popen[str]:
        if task.provider_id != PROVIDER_ID:
            raise CodexAdapterDenied("task provider is not FA3-PROVIDER-CODEX-001")
        mutation_path(workspace, task.relative_path)
        request = {
            "schema": "fa3.codex-adapter-worker-request.v1",
            "provider_id": PROVIDER_ID,
            "adapter_id": ADAPTER_ID,
            "task_id": task.task_id,
            "agent_id": task.agent_id,
            "workspace": str(workspace.resolve()),
            "relative_path": task.relative_path,
            "content": task.content,
            "codex_binary": str(self.codex_binary),
            "timeout_seconds": self.timeout_seconds,
        }
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
        return subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "worker",
                "--request",
                str(request_path),
                "--result",
                str(result_path),
            ],
            cwd=str(workspace),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=safe_codex_environment(),
        )


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(path), "init", "-b", "main"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "FA3 Codex Fixture"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "fa3-codex-fixture@localhost"], check=True)
    for rel in ("work/a.txt", "work/b.txt"):
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "baseline"], check=True, capture_output=True, text=True)


def _write_fake_codex(path: Path) -> None:
    script = r'''#!/usr/bin/env python3
import json, pathlib, sys
args=sys.argv[1:]
if args == ["--version"]:
    print("codex-cli 0.151.0")
    raise SystemExit(0)
if len(args) >= 2 and args[0:2] == ["login","status"]:
    print("Logged in using ChatGPT", file=sys.stderr)
    raise SystemExit(0)
if not args or args[0] != "exec":
    raise SystemExit(2)
workspace=pathlib.Path(args[args.index("-C")+1])
prompt=sys.stdin.read()
line=next(x for x in prompt.splitlines() if x.startswith("FA3_CODEX_TASK_JSON="))
payload=json.loads(line.split("=",1)[1])
target=workspace / payload["allowed_relative_path"]
target.write_text(payload["exact_utf8_content"], encoding="utf-8")
if "--output-last-message" in args:
    pathlib.Path(args[args.index("--output-last-message")+1]).write_text("fixture complete\n", encoding="utf-8")
events=[
 {"type":"thread.started","thread_id":"ci-fixture-thread"},
 {"type":"turn.started"},
 {"type":"item.completed","item":{"id":"f1","type":"file_change","changes":[{"path":payload["allowed_relative_path"],"kind":"update"}],"status":"completed"}},
 {"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"cache_write_input_tokens":0,"output_tokens":1,"reasoning_output_tokens":0}},
]
for event in events:
    print(json.dumps(event))
'''
    path.write_text(script, encoding="utf-8")
    path.chmod(0o755)


def run_ci_adapter_contract_e2e() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="fa3-codex-adapter-ci-") as td:
        base = Path(td)
        repo = base / "repo"
        _init_repo(repo)
        fake = base / "codex"
        _write_fake_codex(fake)
        preflight = codex_preflight(fake, env={"PATH": os.environ.get("PATH", ""), "HOME": str(base)})
        tasks = [
            AgentTask("CODEX-CI-A", "codex-a", PROVIDER_ID, "work/a.txt", "codex-a-pass\n"),
            AgentTask("CODEX-CI-B", "codex-b", PROVIDER_ID, "work/b.txt", "codex-b-pass\n"),
        ]
        control = base / "control"
        result = Coordinator(repo, control).run(tasks, CodexAdapter(fake, timeout_seconds=60))
        worker_results = [
            json.loads((control / "results" / f"{task.task_id}.json").read_text(encoding="utf-8"))
            for task in tasks
        ]
        ok = (
            result.get("status") == "PASS"
            and result.get("worker_count") == 2
            and result.get("integration_author") == "FA3 Integration"
            and all(item.get("status") == "PASS" for item in worker_results)
            and all(not item["event_summary"]["forbidden_surface_observed"] for item in worker_results)
        )
        return {
            "schema": "fa3.codex-adapter-ci-e2e.v1",
            "provider_id": PROVIDER_ID,
            "adapter_id": ADAPTER_ID,
            "result": "PASS" if ok else "FAIL",
            "status": "CI_ADAPTER_CONTRACT_PASS" if ok else "FAIL",
            "synthetic_provider_fixture": True,
            "current_host_production_claim": False,
            "preflight": preflight,
            "coordination": result,
            "workers": [
                {
                    "task_id": item["task_id"],
                    "event_summary": item["event_summary"],
                    "execution_controls": item["execution_controls"],
                }
                for item in worker_results
            ],
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    worker = sub.add_parser("worker")
    worker.add_argument("--request", required=True)
    worker.add_argument("--result", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--codex-binary", required=True)
    sub.add_parser("ci-e2e")
    args = ap.parse_args()
    if args.command == "worker":
        try:
            return codex_worker_main(Path(args.request), Path(args.result))
        except Exception as exc:
            print(f"FA3 CODEX WORKER FAILED: {exc}", file=sys.stderr)
            return 2
    if args.command == "preflight":
        try:
            print(json.dumps(codex_preflight(Path(args.codex_binary)), indent=2))
            return 0
        except Exception as exc:
            print(f"FA3 CODEX PREFLIGHT FAILED: {exc}", file=sys.stderr)
            return 2
    report = run_ci_adapter_contract_e2e()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
