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
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_modular_runtime import (
    DEFAULT_MODEL,
    MAX_PROVIDER_ID,
    MOJO_PROVIDER_ID,
    RUNTIME_ID,
    MaxServeRequest,
    allowed_model,
    build_max_serve_command,
    compiled_artifact_identity,
    evidence_complete,
    load_allowlist,
    validate_hrb_lease,
    validate_request,
    version_channel,
)

def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def run(argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)

def binary_version(binary: str) -> str:
    proc = run([binary, "--version"], 30)
    if proc.returncode:
        raise RuntimeError(f"{binary} --version failed: {proc.stderr.strip()}")
    return (proc.stdout or proc.stderr).strip()

def host_fingerprint() -> dict:
    uname = platform.uname()
    return {
        "system": uname.system,
        "release": uname.release,
        "machine": uname.machine,
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "hostname_sha256": sha256_bytes(uname.node.encode("utf-8")),
    }

def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def post_json(url: str, payload: dict, timeout: int = 120) -> bytes:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()

def nvidia_inventory(ordinal: int) -> tuple[str, int]:
    proc = run([
        "nvidia-smi", f"--id={ordinal}",
        "--query-gpu=uuid,memory.total", "--format=csv,noheader,nounits",
    ], 20)
    if proc.returncode:
        raise RuntimeError("nvidia-smi inventory failed")
    parts = [x.strip() for x in proc.stdout.strip().split(",")]
    if len(parts) != 2:
        raise RuntimeError("unexpected nvidia-smi inventory format")
    return parts[0], int(parts[1]) * 1024 * 1024

def resolve_model_snapshot(model: str, revision: str, allow_network: bool) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:
        raise RuntimeError(f"huggingface_hub unavailable in Modular runtime: {exc}") from exc
    return Path(snapshot_download(
        repo_id=model,
        revision=revision,
        local_files_only=not allow_network,
    )).resolve()

def main() -> int:
    ap = argparse.ArgumentParser(description="Collect FA3 MAX/Mojo current-host production E2E evidence")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--model-revision", required=True)
    ap.add_argument("--devices", default="cpu")
    ap.add_argument("--hrb-lease")
    ap.add_argument("--hrb-bin", default="/usr/local/bin/fa3-host-resource-broker")
    ap.add_argument("--evidence-channel", choices=("stable", "nightly"), default="stable")
    ap.add_argument("--allow-network-model-fetch", action="store_true")
    ap.add_argument("--timeout-seconds", type=int, default=900)
    ap.add_argument("--receipt", default="evidence/receipts/modular-current-host.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_dir = root / "evidence/runtime/modular-current-host" / stamp
    runtime_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = Path(args.receipt)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path

    base = {
        "schema": "fa3.modular-current-host-receipt.v1",
        "runtime_id": RUNTIME_ID,
        "status": "FAIL",
        "evidence_level": "CURRENT_HOST_E2E_FAIL",
        "started_at": now(),
        "host": host_fingerprint(),
        "evidence_channel": args.evidence_channel,
        "runtime_dir": str(runtime_dir),
    }

    try:
        for binary in ("max", "mojo"):
            if not shutil.which(binary):
                raise RuntimeError(f"missing runtime binary: {binary}")

        max_version = binary_version("max")
        mojo_version = binary_version("mojo")
        if version_channel(max_version) != args.evidence_channel or version_channel(mojo_version) != args.evidence_channel:
            raise RuntimeError("MAX/Mojo version channel does not match requested evidence channel")

        allowlist = load_allowlist(root)
        model_policy = allowed_model(allowlist, args.model)
        snapshot = resolve_model_snapshot(args.model, args.model_revision, args.allow_network_model_fetch)
        model_weights = snapshot / "model.safetensors"
        if not model_weights.is_file():
            raise RuntimeError("allowlisted MAX smoke model does not resolve to model.safetensors")
        model_sha = sha256_file(model_weights)
        expected_model_sha = str(model_policy.get("reference_weight_sha256", ""))
        if not expected_model_sha or model_sha != expected_model_sha:
            raise RuntimeError("local model.safetensors SHA-256 does not match canonical allowlist")

        port = free_port()
        hrb = None
        memory_guard = None
        memory_fraction = None

        if args.devices.startswith("gpu:"):
            if not args.hrb_lease:
                raise RuntimeError("GPU current-host evidence requires --hrb-lease")
            ordinal = int(args.devices.split(":", 1)[1])
            gpu_uuid, total_memory = nvidia_inventory(ordinal)
            lease_path = Path(args.hrb_lease).resolve()
            lease = json.loads(lease_path.read_text(encoding="utf-8"))
            lease_bytes = int(lease.get("memory_max_bytes", 0))
            memory_fraction = min(0.95, lease_bytes / total_memory) if total_memory > 0 else 0.0
            request = MaxServeRequest(
                model=args.model,
                model_revision=args.model_revision,
                devices=args.devices,
                port=port,
                hrb_lease_path=str(lease_path),
                evidence_channel=args.evidence_channel,
                device_memory_utilization=memory_fraction,
            )
            validate_request(request, allowlist)
            validate_hrb_lease(lease, request)
            if gpu_uuid != lease.get("accelerator_uuid"):
                raise RuntimeError("current GPU ordinal UUID differs from HRB lease")
            verify = run([args.hrb_bin, "validate-lease", str(lease_path)], 30)
            if verify.returncode or "VALID" not in verify.stdout:
                raise RuntimeError("HRB broker validation failed")
            hrb = {
                "lease_id": lease.get("lease_id"),
                "accelerator_uuid": gpu_uuid,
                "memory_max_bytes": lease_bytes,
                "broker_validation": "VALID",
            }
            memory_guard = {
                "mechanism": "max --device-memory-utilization",
                "fraction": memory_fraction,
                "source": "HRB lease memory_max_bytes / current device memory.total",
            }
        else:
            request = MaxServeRequest(
                model=args.model,
                model_revision=args.model_revision,
                devices=args.devices,
                port=port,
                evidence_channel=args.evidence_channel,
            )
            validate_request(request, allowlist)

        mojo_source = runtime_dir / "fa3_modular_e2e.mojo"
        mojo_binary = runtime_dir / "fa3_modular_e2e"
        mojo_source.write_text('fn main():\n    print("FA3_MOJO_E2E_PASS")\n', encoding="utf-8")
        build = run(["mojo", "build", str(mojo_source), "-o", str(mojo_binary)], 120)
        if build.returncode:
            raise RuntimeError("mojo build failed: " + build.stderr[-2000:])
        execute = run([str(mojo_binary)], 30)
        if execute.returncode or "FA3_MOJO_E2E_PASS" not in execute.stdout:
            raise RuntimeError("compiled Mojo executable failed")

        server_log = runtime_dir / "max-server.log"
        response_file = runtime_dir / "max-response.json"
        env = os.environ.copy()
        if not args.allow_network_model_fetch:
            env["HF_HUB_OFFLINE"] = "1"
        command = build_max_serve_command(request)
        with server_log.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True, env=env)

        payload = {
            "model": args.model,
            "messages": [{"role": "user", "content": "Reply briefly with FA3_MAX_E2E_PASS."}],
            "max_completion_tokens": request.max_new_tokens,
        }
        body = None
        last_error = None
        try:
            deadline = time.time() + args.timeout_seconds
            while time.time() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("MAX server exited before successful inference")
                try:
                    body = post_json(f"http://127.0.0.1:{port}/v1/chat/completions", payload, 120)
                    break
                except Exception as exc:
                    last_error = exc
                    time.sleep(2)
            if body is None:
                raise RuntimeError(f"MAX inference readiness/E2E timeout: {last_error}")
            response_file.write_bytes(body)
            response = json.loads(body)
            content = str((((response.get("choices") or [{}])[0].get("message") or {}).get("content", "")))
            if not content.strip():
                raise RuntimeError("MAX returned empty completion")
        finally:
            process.terminate()
            try:
                process.wait(20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(10)

        source_sha = sha256_file(mojo_source)
        binary_sha = sha256_file(mojo_binary)

        max_evidence = {
            "status": "PASS",
            "provider_id": MAX_PROVIDER_ID,
            "version": max_version,
            "model_id": args.model,
            "model_revision": args.model_revision,
            "model_snapshot_path": str(snapshot),
            "model_artifact_sha256": model_sha,
            "expected_model_artifact_sha256": expected_model_sha,
            "devices": args.devices,
            "bind_host": "127.0.0.1",
            "port": port,
            "openai_endpoint": "/v1/chat/completions",
            "response_sha256": sha256_file(response_file),
            "response_content_sha256": sha256_bytes(content.encode("utf-8")),
            "hrb": hrb,
            "resource_guard": memory_guard,
        }
        mojo_evidence = {
            "status": "PASS",
            "provider_id": MOJO_PROVIDER_ID,
            "version": mojo_version,
            "target": platform.machine(),
            "source_sha256": source_sha,
            "binary_sha256": binary_sha,
            "compiled_artifact_id": compiled_artifact_identity(source_sha, mojo_version, platform.machine(), binary_sha),
            "stdout_sha256": sha256_bytes(execute.stdout.encode("utf-8")),
        }

        base.update({
            "status": "PASS",
            "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS",
            "completed_at": now(),
            "max": max_evidence,
            "mojo": mojo_evidence,
            "artifacts": {
                "server_log": {"path": str(server_log), "sha256": sha256_file(server_log)},
                "response_file": {"path": str(response_file), "sha256": sha256_file(response_file)},
                "mojo_source": {"path": str(mojo_source), "sha256": source_sha},
                "mojo_binary": {"path": str(mojo_binary), "sha256": binary_sha},
            },
        })
        if not evidence_complete(base):
            raise RuntimeError("combined evidence contract incomplete")
        write_json(receipt_path, base)
        print(json.dumps(base, indent=2))
        return 0
    except Exception as exc:
        base.update({"completed_at": now(), "error_type": type(exc).__name__, "error": str(exc)})
        write_json(receipt_path, base)
        print(json.dumps(base, indent=2), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
