#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fa3_minimax_h3_provider_adapter import (
    PROVIDER_ID,
    H3AdmissionError,
    H3ProviderError,
    MiniMaxH3Adapter,
    adapter_conformance,
    config_from_env,
)

RECEIPT_REL = "evidence/receipts/minimax-h3-current-host.json"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git_sha(root: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return os.environ.get("GITHUB_SHA")


def ffprobe_qc(video: Path) -> dict[str, Any]:
    try:
        raw = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        data = json.loads(raw)
    except Exception as exc:
        return {"result": "FAIL", "error": repr(exc), "video_stream": False, "audio_stream": False}
    streams = data.get("streams", []) if isinstance(data, dict) else []
    video_stream = any(isinstance(s, dict) and s.get("codec_type") == "video" for s in streams)
    audio_stream = any(isinstance(s, dict) and s.get("codec_type") == "audio" for s in streams)
    try:
        duration = float((data.get("format") or {}).get("duration") or 0)
    except Exception:
        duration = 0.0
    return {
        "result": "PASS" if video_stream and audio_stream and duration > 0 else "FAIL",
        "video_stream": video_stream,
        "audio_stream": audio_stream,
        "duration_seconds": duration,
        "stream_count": len(streams),
        "ffprobe_sha256": canonical_hash(data),
    }


def pending_receipt(root: Path, state: str, message: str, credential_class: str | None = None) -> dict[str, Any]:
    receipt = {
        "schema": "fa3.minimax-h3-current-host-receipt.v1",
        "status": state,
        "provider_id": PROVIDER_ID,
        "evidence_level": "PENDING_EXTERNAL_ADMISSION",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "credential_class": credential_class,
        "message": message,
        "secret_persisted": False,
        "runtime_promotion_claim": False,
    }
    write_json(root / RECEIPT_REL, receipt)
    return receipt


def collect(root: Path, prompt: str, duration: int, ratio: str, resolution: str) -> dict[str, Any]:
    credential_class = os.environ.get("FA3_MINIMAX_H3_CREDENTIAL_CLASS") or None
    if not os.environ.get("MINIMAX_H3_API_KEY"):
        return pending_receipt(root, "PENDING_EXTERNAL_ADMISSION", "MINIMAX_H3_API_KEY is not available on the current-host runner", credential_class)
    if os.environ.get("FA3_MINIMAX_H3_SERVICE_TERMS_ADMITTED") != "1":
        return pending_receipt(root, "PENDING_EXTERNAL_ADMISSION", "Hosted service terms have not been explicitly admitted", credential_class)
    if not credential_class:
        return pending_receipt(root, "PENDING_EXTERNAL_ADMISSION", "FA3_MINIMAX_H3_CREDENTIAL_CLASS is not explicit", None)

    ir = {
        "schema": "fa3.VideoGenerationIR/current-host-e2e.v1",
        "prompt": prompt,
        "duration": duration,
        "ratio": ratio,
        "resolution": resolution,
        "purpose": "PROVIDER_RUNTIME_CONFORMANCE",
    }
    request_sha = canonical_hash(ir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_dir = root / "evidence/runtime/minimax-h3-current-host" / stamp
    output = runtime_dir / "minimax-h3-e2e.mp4"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    conf = adapter_conformance()
    if conf.get("result") != "PASS":
        receipt = pending_receipt(root, "FAIL", "Adapter conformance failed before provider execution", credential_class)
        receipt["adapter_conformance"] = conf
        write_json(root / RECEIPT_REL, receipt)
        return receipt

    try:
        config = config_from_env()
        adapter = MiniMaxH3Adapter(config)
        provider = adapter.run_hosted_video(ir, output)
    except H3AdmissionError as exc:
        return pending_receipt(root, "PENDING_EXTERNAL_ADMISSION", str(exc), credential_class)
    except H3ProviderError as exc:
        message = str(exc)
        external = any(marker in message for marker in ("HTTP 401", "HTTP 402", "HTTP 403", "HTTP 429"))
        return pending_receipt(
            root,
            "PENDING_EXTERNAL_ADMISSION" if external else "FAIL",
            message,
            credential_class,
        )

    qc = ffprobe_qc(output)
    if qc.get("result") != "PASS":
        status = "FAIL"
        evidence_level = "CURRENT_HOST_REMOTE_E2E_FAILED"
    else:
        status = "PASS"
        evidence_level = "CURRENT_HOST_REMOTE_E2E_PASS"

    artifact = dict(provider["artifact"])
    artifact["path"] = str(output.resolve())
    provenance = {
        "provider_id": PROVIDER_ID,
        "provider_task_id": provider["task_id"],
        "canonical_request_schema": ir["schema"],
        "request_sha256": request_sha,
        "repository_commit": git_sha(root),
        "artifact_sha256": artifact["sha256"],
        "execution_topology": "HOSTED_REMOTE_FROM_CURRENT_HOST",
        "provider_api_base": config.api_base,
        "provider_endpoint": "/v2/video_generation",
        "provider_model": "MiniMax-H3",
        "static_price_used": False,
    }
    promotion = {
        "service_terms": "PASS",
        "credential_class": "PASS",
        "entitlement_discovery": provider["entitlement_discovery"]["result"],
        "adapter_conformance": conf["result"],
        "real_video_e2e": "PASS" if provider.get("status") == "PASS" else "FAIL",
        "qc": qc["result"],
        "provenance": "PASS" if provenance["provider_task_id"] and provenance["request_sha256"] else "FAIL",
    }
    if any(value != "PASS" for value in promotion.values()):
        status = "FAIL"
        evidence_level = "CURRENT_HOST_REMOTE_E2E_FAILED"

    receipt = {
        "schema": "fa3.minimax-h3-current-host-receipt.v1",
        "status": status,
        "provider_id": PROVIDER_ID,
        "model": "MiniMax-H3",
        "evidence_level": evidence_level,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "runner": {
            "hostname": socket.gethostname(),
            "runner_name": os.environ.get("RUNNER_NAME"),
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
        },
        "execution_topology": "HOSTED_REMOTE_FROM_CURRENT_HOST",
        "credential_class": provider["credential_class"],
        "billing_mode": provider["billing_mode"],
        "task_id": provider["task_id"],
        "provider_terminal_status": provider["provider_terminal_status"],
        "entitlement_discovery": provider["entitlement_discovery"],
        "provider_usage": provider["provider_usage"],
        "cost_evidence": provider["cost_evidence"],
        "latency": provider["latency"],
        "artifact": artifact,
        "quality_evidence": qc,
        "adapter_conformance": conf,
        "provenance": provenance,
        "promotion_criteria": promotion,
        "secret_persisted": False,
        "local_h3_execution_claimed": False,
        "local_h3_license_admission": "NOT_APPLICABLE_TO_HOSTED_REMOTE_E2E",
        "runtime_promotion_claim": status == "PASS",
    }
    write_json(root / RECEIPT_REL, receipt)
    write_json(runtime_dir / "execution-evidence.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real MiniMax H3 hosted current-host evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--prompt", default="A four-second cinematic shot of soft morning light moving across a quiet geometric sculpture, with subtle ambient room sound.")
    parser.add_argument("--duration", type=int, default=4)
    parser.add_argument("--ratio", default="16:9")
    parser.add_argument("--resolution", default="768P")
    args = parser.parse_args()
    receipt = collect(Path(args.root).resolve(), args.prompt, args.duration, args.ratio, args.resolution)
    print(json.dumps({k: v for k, v in receipt.items() if k not in {"provider_usage"}}, indent=2))
    return 0 if receipt.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
