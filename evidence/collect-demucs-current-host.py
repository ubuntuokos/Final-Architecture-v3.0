#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import struct
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_demucs_provider import (
    DEFAULT_HRB_VERIFY_COMMAND,
    HRB_LEASE_SCHEMA,
    HRB_PROFILE_ID,
    PROVIDER_ID,
    PROVIDER_VERSION,
    SeparationRequest,
    execute_separation,
    evidence_complete,
    run_executable_conformance,
)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()

def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None

def host_fingerprint() -> dict[str, Any]:
    uname = platform.uname()
    host_hash = sha256_bytes(uname.node.encode("utf-8")) if uname.node else None
    return {
        "system": uname.system,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "hostname_sha256": host_hash,
    }

def nvidia_inventory() -> list[dict[str, Any]]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,name,uuid,driver_version,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if p.returncode != 0:
        return []
    rows = []
    for line in p.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) != 5:
            continue
        rows.append({
            "index": int(parts[0]),
            "name": parts[1],
            "uuid": parts[2],
            "driver_version": parts[3],
            "memory_total_mib": int(parts[4]),
        })
    return rows

def resolve_device(
    requested: str,
    hrb_lease_path: str | None,
    inventory: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    try:
        import torch
    except Exception as exc:
        raise RuntimeError(f"torch import failed: {exc}") from exc
    runtime = {
        "torch_version": getattr(torch, "__version__", "unknown"),
        "cuda_available": bool(torch.cuda.is_available()),
        "torch_cuda_version": getattr(torch.version, "cuda", None),
        "cuda_device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
    }
    if requested != "auto":
        if requested == "cuda":
            raise RuntimeError("bare 'cuda' is forbidden; use explicit cuda:N or --device auto with an HRB lease")
        return requested, runtime
    if not torch.cuda.is_available():
        return "cpu", runtime
    if not hrb_lease_path:
        raise RuntimeError(
            "CUDA is available, but --device auto cannot self-place: supply --hrb-lease "
            "or explicitly choose --device cpu"
        )
    lease_path = Path(hrb_lease_path).resolve()
    if not lease_path.is_file():
        raise RuntimeError("HRB lease file not found")
    lease = json.loads(lease_path.read_text(encoding="utf-8"))
    if lease.get("schema") != HRB_LEASE_SCHEMA or lease.get("issuer") != HRB_PROFILE_ID:
        raise RuntimeError("HRB lease schema/issuer mismatch")
    uuid = str(lease.get("accelerator_uuid", ""))
    matches = [row for row in inventory if row.get("uuid") == uuid]
    if len(matches) != 1:
        raise RuntimeError("HRB lease accelerator UUID does not resolve to exactly one current NVIDIA ordinal")
    return f"cuda:{matches[0]['index']}", runtime

def make_synthetic_mix(path: Path, seconds: float = 3.0, samplerate: int = 44100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    total = int(seconds * samplerate)
    for i in range(total):
        t = i / samplerate
        left = 0.22 * math.sin(2 * math.pi * 220 * t) + 0.12 * math.sin(2 * math.pi * 440 * t)
        right = 0.20 * math.sin(2 * math.pi * 330 * t) + 0.10 * math.sin(2 * math.pi * 660 * t)
        li = max(-32767, min(32767, int(left * 32767)))
        ri = max(-32767, min(32767, int(right * 32767)))
        frames.extend(struct.pack("<hh", li, ri))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(samplerate)
        wav.writeframes(bytes(frames))

def fail_receipt(base: dict[str, Any], receipt_path: Path, error: Exception | str) -> int:
    base["status"] = "FAIL"
    base["evidence_level"] = "CURRENT_HOST_E2E_FAIL"
    base["error_type"] = type(error).__name__ if isinstance(error, Exception) else "RuntimeError"
    base["error"] = str(error)
    base["completed_at"] = utc_now()
    write_json(receipt_path, base)
    print(json.dumps(base, indent=2), file=sys.stderr)
    return 2

def main() -> int:
    ap = argparse.ArgumentParser(description="Collect real FA3 Demucs current-host provider evidence")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--input", help="Real audio input. If omitted, a deterministic synthetic mixture is generated.")
    ap.add_argument("--model", default="htdemucs")
    ap.add_argument("--stems", default="drums,bass,other,vocals")
    ap.add_argument("--device", default="auto", help="auto, cpu or explicit cuda:N")
    ap.add_argument("--hrb-lease", help="Canonical AcceleratorExecutionLease@1 JSON from FA3 Host Resource Broker")
    ap.add_argument(
        "--hrb-verify-command-json",
        default=json.dumps(list(DEFAULT_HRB_VERIFY_COMMAND)),
        help='JSON argv array; default is the canonical broker validate-lease command and must contain "{lease}"',
    )
    ap.add_argument("--allow-network-model-fetch", action="store_true",
                    help="Permit HuggingFace fetch when trusted model is absent from the local cache.")
    ap.add_argument("--segment", type=float, default=7.0)
    ap.add_argument("--overlap", type=float, default=0.25)
    ap.add_argument("--shifts", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=0)
    ap.add_argument("--clipping", default="rescale")
    ap.add_argument("--timeout-seconds", type=float, default=3600.0)
    ap.add_argument("--runtime-dir")
    ap.add_argument("--receipt", default="evidence/receipts/demucs-current-host.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    receipt_path = Path(args.receipt)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_dir = Path(args.runtime_dir).resolve() if args.runtime_dir else root / "evidence/runtime/demucs-current-host" / stamp
    runtime_dir.mkdir(parents=True, exist_ok=True)

    base: dict[str, Any] = {
        "schema": "fa3.demucs-current-host-receipt.v1",
        "provider_id": PROVIDER_ID,
        "provider_version": PROVIDER_VERSION,
        "started_at": utc_now(),
        "host": host_fingerprint(),
        "packages": {
            "demucs": package_version("demucs"),
            "torch": package_version("torch"),
            "safetensors": package_version("safetensors"),
            "huggingface-hub": package_version("huggingface-hub"),
            "sphn": package_version("sphn"),
        },
        "nvidia_inventory": nvidia_inventory(),
        "hrb_contract": {
            "profile_id": HRB_PROFILE_ID,
            "lease_schema": HRB_LEASE_SCHEMA,
            "validation": "broker validate-lease + current ordinal-to-UUID revalidation",
        },
        "synthetic_input": args.input is None,
        "model": args.model,
        "requested_stems": [s.strip() for s in args.stems.split(",") if s.strip()],
        "runtime_dir": str(runtime_dir),
    }

    missing = [name for name in ("demucs", "torch", "safetensors", "huggingface-hub", "sphn") if not base["packages"][name]]
    if missing:
        return fail_receipt(base, receipt_path, "missing runtime packages: " + ",".join(missing))

    conformance = run_executable_conformance(root)
    base["executable_conformance"] = conformance
    if conformance.get("result") != "PASS":
        return fail_receipt(base, receipt_path, "provider executable conformance failed")

    try:
        device, torch_runtime = resolve_device(args.device, args.hrb_lease, base["nvidia_inventory"])
        base["device"] = device
        base["torch_runtime"] = torch_runtime
        try:
            hrb_command_raw = json.loads(args.hrb_verify_command_json)
        except Exception as exc:
            raise RuntimeError("invalid --hrb-verify-command-json") from exc
        if not isinstance(hrb_command_raw, list) or not all(isinstance(x, str) for x in hrb_command_raw):
            raise RuntimeError("--hrb-verify-command-json must be a JSON string array")
        hrb_command = tuple(hrb_command_raw)
        if device.startswith("cuda:") and not args.hrb_lease:
            raise RuntimeError("CUDA current-host evidence requires a canonical HRB lease; no implicit CPU fallback is permitted")
        if device.startswith("cuda:") and "{lease}" not in hrb_command:
            raise RuntimeError("HRB verifier command must contain {lease}")

        if args.input:
            input_path = Path(args.input).resolve()
            if not input_path.is_file():
                raise RuntimeError("input audio file not found")
        else:
            input_path = runtime_dir / "synthetic-mixture.wav"
            make_synthetic_mix(input_path)

        output_dir = runtime_dir / "stems"
        request = SeparationRequest(
            input_path=str(input_path),
            output_dir=str(output_dir),
            model=args.model,
            stems=tuple(base["requested_stems"]),
            device=device,
            hrb_lease_path=args.hrb_lease,
            hrb_verify_command=hrb_command,
            segment=args.segment,
            overlap=args.overlap,
            shifts=args.shifts,
            jobs=args.jobs,
            clipping=args.clipping,
            offline=not args.allow_network_model_fetch,
            allow_experimental_stems=False,
            timeout_seconds=args.timeout_seconds,
        )
        evidence = execute_separation(root, request)
        if not evidence_complete(evidence):
            raise RuntimeError("execution evidence contract incomplete")
        execution_path = runtime_dir / "execution-evidence.json"
        write_json(execution_path, evidence)

        base["status"] = "PASS"
        base["evidence_level"] = (
            "CURRENT_HOST_SYNTHETIC_E2E_PASS"
            if args.input is None
            else "CURRENT_HOST_PRODUCTION_E2E_PASS"
        )
        base["input"] = {
            "path": str(input_path),
            "sha256": sha256_file(input_path),
        }
        base["execution_evidence"] = {
            "path": str(execution_path),
            "sha256": sha256_file(execution_path),
            "model_hash": evidence["model_hash"],
            "output_hashes": evidence["output_hashes"],
            "device_lease": evidence["device_lease"],
            "hrb": evidence.get("hrb"),
            "resource_guard": evidence.get("resource_guard"),
            "model_classes": evidence["model_classes"],
        }
        base["security_regression_pass"] = conformance["result"] == "PASS"
        base["hrb_enforced"] = (
            not device.startswith("cuda:")
            or (
                bool(evidence["device_lease"])
                and evidence.get("hrb", {}).get("schema") == HRB_LEASE_SCHEMA
                and evidence.get("hrb", {}).get("issuer") == HRB_PROFILE_ID
                and evidence.get("hrb", {}).get("broker_validation") == "VALID"
                and evidence.get("resource_guard", {}).get("mechanism") == "torch.cuda.set_per_process_memory_fraction"
            )
        )
        base["model_trust_enforced"] = bool(evidence.get("model_trust", {}).get("class_allowlisted"))
        base["completed_at"] = utc_now()
        write_json(receipt_path, base)
        print(json.dumps(base, indent=2))
        return 0
    except Exception as exc:
        return fail_receipt(base, receipt_path, exc)

if __name__ == "__main__":
    raise SystemExit(main())
