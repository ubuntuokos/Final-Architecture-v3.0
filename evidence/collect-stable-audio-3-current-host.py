#!/usr/bin/env python3
from __future__ import annotations

import argparse
import array
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

UPSTREAM_PIN = "779434a908193105335fd8d833418603625b2859"
PROVIDER_ID = "FA3-PROVIDER-STABLE-AUDIO-3-001"
PROFILE_ID = "FA3-MUSIC-001"
REQUIRED_CASES = {
    "SA3-CH-001-small-sfx-cpu-text-to-audio",
    "SA3-CH-002-small-music-cpu-text-to-audio",
    "SA3-CH-003-medium-pytorch-cuda-hrb",
    "SA3-CH-004-medium-tensorrt-live-sm-pinned-engine",
    "SA3-CH-005-audio-to-audio",
    "SA3-CH-006-inpainting-and-continuation",
    "SA3-CH-007-wav-44k1-stereo-limiter-metadata",
}
IDENTITY_FIELDS = {
    "backend", "model_revision", "model_variant", "decoder_variant", "precision",
    "engine_compute_capability", "chunking_mode", "limiter_identity", "codec_revision",
    "seed", "runtime_revision", "quantization", "pcm_conversion_semantics",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wav_facts(path: Path) -> dict:
    with wave.open(str(path), "rb") as w:
        channels = w.getnchannels()
        sample_rate = w.getframerate()
        sample_width = w.getsampwidth()
        frames = w.getnframes()
        raw = w.readframes(frames)
    if channels != 2 or sample_rate != 44100 or frames <= 0:
        raise RuntimeError(f"WAV contract failed for {path}: {sample_rate} Hz / {channels} ch / {frames} frames")
    if sample_width != 2:
        raise RuntimeError(f"WAV must be PCM16 for deterministic limiter verification: {path}")
    samples = array.array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max((abs(x) for x in samples), default=0) / 32767.0
    if peak > 0.978:
        raise RuntimeError(f"limiter ceiling exceeded: peak={peak:.8f} path={path}")
    return {
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "frame_count": frames,
        "sample_peak": peak,
        "sha256": sha256_file(path),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Stable Audio 3 real current-host production E2E collector")
    ap.add_argument("--plan", required=True, help="Absolute fa3.stable-audio-3-current-host-plan.v1 JSON")
    ap.add_argument("--output", default="evidence/receipts/stable-audio-3-current-host.json")
    args = ap.parse_args()

    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and os.environ.get("FA3_CURRENT_HOST_RUNNER") != "1":
        raise SystemExit("CURRENT_HOST evidence is forbidden on non-designated GitHub runners")

    plan_path = Path(args.plan).expanduser().resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("schema") != "fa3.stable-audio-3-current-host-plan.v1":
        raise SystemExit("invalid Stable Audio 3 current-host plan schema")
    if plan.get("upstream_immutable_reference") != UPSTREAM_PIN:
        raise SystemExit("plan upstream pin mismatch")

    source = Path(plan["source_checkout"]).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit("source checkout missing")
    head = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
    if head != UPSTREAM_PIN:
        raise SystemExit(f"source checkout is not pinned to {UPSTREAM_PIN}: {head}")

    cases = plan.get("cases", [])
    if {c.get("case_id") for c in cases} != REQUIRED_CASES:
        raise SystemExit("current-host plan must contain exactly the seven canonical Stable Audio 3 cases")

    env = os.environ.copy()
    env.update({
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
    })

    receipt_cases = []
    for case in cases:
        cid = case["case_id"]
        identity = case.get("runtime_identity", {})
        missing = IDENTITY_FIELDS - set(identity)
        if missing:
            raise SystemExit(f"{cid}: incomplete runtime identity: {sorted(missing)}")
        if identity.get("precision") == "bf16":
            raise SystemExit(f"{cid}: retired medium bf16 is forbidden")
        if identity.get("pcm_conversion_semantics") != "ROUND_TO_NEAREST":
            raise SystemExit(f"{cid}: PCM conversion identity mismatch")
        if identity.get("limiter_identity") != "SA3-SAME-OUTPUT-LIMITER-0.977-2026-08-20":
            raise SystemExit(f"{cid}: limiter identity mismatch")
        if case.get("accelerator"):
            lease = case.get("hrb_lease")
            if not lease or not Path(lease).expanduser().is_file():
                raise SystemExit(f"{cid}: accelerator case requires a real HRB lease receipt")
        argv = case.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
            raise SystemExit(f"{cid}: argv must be a non-empty string array")
        out = Path(case["output_wav"]).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
        proc = subprocess.run(argv, cwd=str(source), env=env, text=True, capture_output=True, check=False)
        if proc.returncode != 0:
            raise SystemExit(f"{cid}: command failed rc={proc.returncode}\n{proc.stderr[-4000:]}")
        if not out.is_file():
            raise SystemExit(f"{cid}: declared output WAV missing: {out}")
        facts = wav_facts(out)
        receipt_cases.append({
            "case_id": cid,
            "status": "PASS",
            "runtime_identity": identity,
            "accelerator": bool(case.get("accelerator")),
            "hrb_lease": case.get("hrb_lease"),
            "output_wav": str(out),
            "wav": facts,
            "argv_sha256": hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest(),
        })

    receipt = {
        "schema": "fa3.stable-audio-3-current-host-evidence.v1",
        "status": "CURRENT_HOST_STABLE_AUDIO_3_E2E_PASS",
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "upstream_immutable_reference": UPSTREAM_PIN,
        "collected_at": now(),
        "current_host": True,
        "production_e2e": True,
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "plan_path": str(plan_path),
        "plan_sha256": sha256_file(plan_path),
        "sample_rate_hz": 44100,
        "channels": 2,
        "limiter_ceiling": 0.977,
        "pcm_conversion_semantics": "ROUND_TO_NEAREST",
        "cases": receipt_cases,
    }
    out_path = Path(args.output).expanduser().resolve()
    write_json(out_path, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
