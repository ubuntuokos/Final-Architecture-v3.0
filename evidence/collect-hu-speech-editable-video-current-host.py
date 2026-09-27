#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_blackhole_kdenlive import PreparationRequest, run_pipeline, sha256_file
from fa3_hu_speech_editable_video_reference import complete_from_stt


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def gpu_inventory() -> str | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,uuid,name,driver_version,memory.total", "--format=csv,noheader"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect real FA3 hu-HU speech -> editable video project current-host evidence")
    ap.add_argument("--media", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--model-cache", required=True)
    ap.add_argument("--model", default="turbo")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--hrb-lease")
    ap.add_argument("--human-edit-text", required=True)
    ap.add_argument("--receipt", default=str(ROOT / "evidence/receipts/hu-speech-editable-video-current-host.json"))
    args = ap.parse_args()

    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        raise SystemExit("Physical current-host reference evidence is not accepted from GitHub Actions")

    media = Path(args.media).expanduser().resolve()
    model_cache = Path(args.model_cache).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if not media.is_file():
        raise SystemExit("input media missing")
    if not model_cache.exists():
        raise SystemExit("offline Whisper model cache missing")
    if args.device.startswith("cuda") and not args.hrb_lease:
        raise SystemExit("CUDA current-host run requires an explicit HRB lease")
    if not args.human_edit_text.strip():
        raise SystemExit("explicit human edit is required")

    output_dir.mkdir(parents=True, exist_ok=True)
    provider_dir = output_dir / "provider-pipeline"
    provider_command = [
        sys.executable,
        str(ROOT / "src/fa3_whisper_stt_provider.py"),
        "--root", str(ROOT),
        "transcribe",
        "--request", "{request}",
        "--result", "{result}",
        "--model", args.model,
        "--device", args.device,
        "--model-cache", str(model_cache),
        "--word-timestamps",
    ]
    if args.hrb_lease:
        provider_command += ["--hrb-lease", str(Path(args.hrb_lease).expanduser().resolve())]

    request = PreparationRequest(
        input_media=str(media),
        output_dir=str(provider_dir),
        language="hu",
        stt_command=tuple(provider_command),
    )

    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    wall_start = time.perf_counter()
    vram_peak_bytes: int | None = 0 if args.device == "cpu" else None
    torch_mod = None
    if args.device.startswith("cuda"):
        try:
            import torch as torch_mod
            torch_mod.cuda.reset_peak_memory_stats()
        except Exception as exc:
            raise SystemExit(f"CUDA metrics unavailable: {exc}")

    pipeline = run_pipeline(ROOT, request)
    if pipeline.get("status") != "PASS":
        raise SystemExit("FFmpeg -> Whisper -> subtitle projection did not PASS")
    handoff = json.loads(Path(pipeline["handoff_path"]).read_text(encoding="utf-8"))
    stt_result = json.loads(Path(pipeline["stt_result_path"]).read_text(encoding="utf-8"))
    if str(stt_result.get("language", "")).lower() not in {"hu", "hu-hu"}:
        raise SystemExit(f"hu-HU recognition proof failed: detected {stt_result.get('language')}")

    journey = complete_from_stt(
        handoff,
        stt_result,
        output_dir / "editable-project",
        human_edit_text=args.human_edit_text,
        inject_failure_once=True,
    )
    if journey.get("result") != "PASS":
        raise SystemExit("editable-video reference journey failed")
    if journey["failure_injection"].get("recovered") is not True:
        raise SystemExit("failure injection did not recover")
    if journey["rollback"].get("verified") is not True:
        raise SystemExit("rollback verification failed")

    if torch_mod is not None:
        vram_peak_bytes = int(torch_mod.cuda.max_memory_allocated())

    wall_seconds = time.perf_counter() - wall_start
    usage_after = resource.getrusage(resource.RUSAGE_SELF)
    collected = utc_now()
    run_id = f"HU-SPEECH-{uuid.uuid4()}"
    final_project = Path(journey["editorial_handoff"]["fa3_video_project"])
    final_hash = journey["lineage"]["final_project_sha256"]
    if not final_project.is_file() or sha256_file(final_project) != final_hash:
        raise SystemExit("final project artifact hash verification failed")

    receipt = {
        "schema": "fa3.hu-speech-editable-video-current-host-evidence.v1",
        "id": run_id,
        "status": "CURRENT_HOST_HU_SPEECH_EDITABLE_VIDEO_E2E_PASS",
        "reference_journey_id": "FA3-HU-SPEECH-EDITABLE-VIDEO-REFERENCE-001",
        "collected_at": iso(collected),
        "expires_at": iso(collected + timedelta(days=30)),
        "source_commit": git_head(),
        "run_id": run_id,
        "host_id": socket.gethostname(),
        "current_host": True,
        "ci": False,
        "production_promotion": False,
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "gpu_inventory": gpu_inventory(),
        },
        "hardware_audit": {
            "vendor_neutral_contract": True,
            "cpu_only_supported": True,
            "accelerator_cardinality": "0..N",
            "selected_device": args.device,
            "accelerator_execution_requires_hrb_lease": args.device.startswith("cuda"),
            "hrb_lease_supplied": bool(args.hrb_lease),
        },
        "input": {
            "media_path": str(media),
            "media_sha256": sha256_file(media),
            "model": args.model,
            "model_cache": str(model_cache),
            "network_model_fetch": False,
            "requested_locale": "hu-HU",
            "provider_language_code": "hu",
        },
        "runtime_metrics": {
            "wall_seconds": round(wall_seconds, 6),
            "cpu_user_seconds": round(usage_after.ru_utime - usage_before.ru_utime, 6),
            "cpu_system_seconds": round(usage_after.ru_stime - usage_before.ru_stime, 6),
            "peak_rss_bytes": int(usage_after.ru_maxrss) * 1024,
            "vram_peak_bytes": vram_peak_bytes,
            "vram_metric_scope": "CUDA_PROCESS_ALLOCATED" if args.device.startswith("cuda") else "CPU_ROUTE_ZERO",
        },
        "speech_recognition": {
            "detected_language": stt_result.get("language"),
            "provider_id": stt_result.get("provider_id"),
            "provider_result_sha256": sha256_file(Path(pipeline["stt_result_path"])),
            "segment_count": len(stt_result.get("segments", [])),
            "word_timestamps_present": all(bool(x.get("words")) for x in stt_result.get("segments", [])),
        },
        "human_edit": {
            "required": True,
            "actor": journey["captions"]["human_edit_actor"],
            "edited_revision": journey["captions"]["edited_revision"],
        },
        "retry_resume": journey["retry_resume"],
        "failure_injection": journey["failure_injection"],
        "rollback": journey["rollback"],
        "lineage": journey["lineage"],
        "interchange": journey["editorial_handoff"],
        "final_project": {
            "path": str(final_project),
            "sha256": final_hash,
            "format": "project.fa3video",
            "editable": True,
        },
    }
    receipt_path = Path(args.receipt).expanduser().resolve()
    write_json(receipt_path, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
