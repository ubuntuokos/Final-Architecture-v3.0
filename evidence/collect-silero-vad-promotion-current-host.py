#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_silero_vad_provider import SUPPORTED_SAMPLE_RATES, SileroVadProvider, sha256_file


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_pcm16_mono(path: Path) -> tuple[int, list[float]]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if channels != 1 or width != 2 or rate not in SUPPORTED_SAMPLE_RATES:
        raise RuntimeError(f"{path}: expected mono PCM16 WAV at 8k or 16k")
    import numpy as np
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if len(audio) == 0:
        raise RuntimeError(f"{path}: empty audio")
    return rate, audio.tolist()


def label_at(t: float, annotations: list[dict[str, Any]]) -> bool | None:
    for ann in annotations:
        if float(ann["start_s"]) <= t < float(ann["end_s"]):
            return bool(ann["speech"])
    return None


def metrics_for_case(probabilities: list[float], rate: int, threshold: float, annotations: list[dict[str, Any]]) -> dict[str, Any]:
    window = SUPPORTED_SAMPLE_RATES[rate]
    tp = fp = tn = fn = ignored = 0
    for index, probability in enumerate(probabilities):
        center = ((index * window) + (window / 2.0)) / float(rate)
        expected = label_at(center, annotations)
        if expected is None:
            ignored += 1
            continue
        predicted = probability >= threshold
        if predicted and expected:
            tp += 1
        elif predicted and not expected:
            fp += 1
        elif not predicted and expected:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn, "ignored_frames": ignored,
        "precision": precision, "recall": recall, "f1": f1,
    }


def check_minimums(metrics: dict[str, Any], minimums: dict[str, Any], case_id: str) -> None:
    for key in ("precision", "recall", "f1"):
        if key in minimums and float(metrics[key]) < float(minimums[key]):
            raise RuntimeError(f"quality regression: {case_id} {key}={metrics[key]:.6f} < {float(minimums[key]):.6f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect FA3 Silero VAD production-promotion current-host evidence")
    ap.add_argument("--model", required=True)
    ap.add_argument("--expected-sha256", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--provider", default="CPUExecutionProvider")
    ap.add_argument("--hrb-lease")
    ap.add_argument("--concurrency-workers", type=int, default=4)
    ap.add_argument("--soak-iterations", type=int, default=100)
    ap.add_argument("--output", default="evidence/current-host/FA3-SILERO-VAD-PROMOTION-EVIDENCE-001.json")
    args = ap.parse_args()

    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and os.environ.get("FA3_CURRENT_HOST_RUNNER") != "1":
        raise SystemExit("CURRENT_HOST promotion evidence is forbidden on non-designated GitHub runners")
    if args.concurrency_workers < 2:
        raise SystemExit("concurrency-workers must be >= 2")
    if args.soak_iterations < 1:
        raise SystemExit("soak-iterations must be >= 1")

    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "fa3.silero-vad-quality-corpus.v1":
        raise SystemExit("quality manifest schema mismatch")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SystemExit("quality manifest requires non-empty cases")
    threshold = float(manifest.get("threshold", 0.5))
    reset_tolerance = float(manifest.get("reset_probability_tolerance", 1e-5))

    receipt: dict[str, Any] = {
        "schema": "fa3.silero-vad-promotion-evidence.v1",
        "id": "FA3-SILERO-VAD-PROMOTION-EVIDENCE-001",
        "provider_id": "FA3-PROVIDER-SILERO-VAD-001",
        "status": "FAIL",
        "current_host_evidence_bundle_pass": False,
        "production_promotion_eligible": False,
        "document_derived": False,
        "collected_at": now(),
        "host": {"platform": platform.platform(), "python": platform.python_version()},
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "execution_provider": args.provider,
        "threshold": threshold,
        "cases": [],
        "concurrency": {},
        "soak": {},
        "errors": [],
    }

    loaded: list[tuple[dict[str, Any], int, list[float]]] = []
    try:
        sample_rates_seen: set[int] = set()
        provider = SileroVadProvider(args.model, args.expected_sha256, args.provider, args.hrb_lease)
        receipt["execution_evidence"] = provider.execution_evidence()

        for case in cases:
            case_id = str(case.get("id", "")).strip()
            if not case_id:
                raise RuntimeError("quality case missing id")
            path = Path(str(case.get("path", ""))).expanduser().resolve()
            if not path.is_file():
                raise RuntimeError(f"quality case file missing: {case_id}")
            annotations = case.get("annotations")
            if not isinstance(annotations, list) or not annotations:
                raise RuntimeError(f"quality case annotations missing: {case_id}")
            rate, audio = read_pcm16_mono(path)
            sample_rates_seen.add(rate)
            started = time.perf_counter()
            probabilities = provider.process_audio(audio, rate)
            elapsed = time.perf_counter() - started
            metrics = metrics_for_case(probabilities, rate, threshold, annotations)
            minimums = case.get("minimum_metrics", manifest.get("minimum_metrics", {}))
            check_minimums(metrics, minimums, case_id)

            probabilities_after_reset = provider.process_audio(audio, rate)
            import numpy as np
            reset_max_abs_diff = float(np.max(np.abs(np.asarray(probabilities) - np.asarray(probabilities_after_reset))))
            if reset_max_abs_diff > reset_tolerance:
                raise RuntimeError(f"state reset regression in {case_id}: max diff {reset_max_abs_diff}")

            duration = len(audio) / float(rate)
            receipt["cases"].append({
                "id": case_id,
                "path": str(path),
                "sha256": sha256_file(path),
                "sample_rate_hz": rate,
                "duration_seconds": duration,
                "elapsed_seconds": elapsed,
                "rtf": elapsed / duration,
                "metrics": metrics,
                "minimum_metrics": minimums,
                "reset_max_abs_probability_diff": reset_max_abs_diff,
                "result": "PASS",
            })
            loaded.append((case, rate, audio))

        if sample_rates_seen != {8000, 16000}:
            raise RuntimeError("promotion corpus must exercise both 8 kHz and 16 kHz")

        concurrency_case, concurrency_rate, concurrency_audio = loaded[0]
        def run_worker(worker_id: int) -> dict[str, Any]:
            p = SileroVadProvider(args.model, args.expected_sha256, args.provider, args.hrb_lease)
            started = time.perf_counter()
            probs = p.process_audio(concurrency_audio, concurrency_rate)
            return {"worker": worker_id, "frames": len(probs), "elapsed_seconds": time.perf_counter() - started}

        with ThreadPoolExecutor(max_workers=args.concurrency_workers) as pool:
            workers = list(pool.map(run_worker, range(args.concurrency_workers)))
        receipt["concurrency"] = {
            "case_id": concurrency_case["id"],
            "workers": args.concurrency_workers,
            "results": workers,
            "state_isolation": "SEPARATE_PROVIDER_SESSION_PER_WORKER",
            "result": "PASS",
        }

        soak_started = time.perf_counter()
        total_frames = 0
        for _ in range(args.soak_iterations):
            for _, rate, audio in loaded:
                total_frames += len(provider.process_audio(audio, rate))
        receipt["soak"] = {
            "iterations": args.soak_iterations,
            "cases_per_iteration": len(loaded),
            "frames_processed": total_frames,
            "elapsed_seconds": time.perf_counter() - soak_started,
            "result": "PASS",
        }

        receipt["status"] = "PASS"
        receipt["current_host_evidence_bundle_pass"] = True
        receipt["promotion_note"] = (
            "Current-host VAD evidence bundle passed. Final production promotion remains owned by canonical FA3 "
            "artifact/model admission, policy reconciliation and evidence authorities; this collector never self-promotes."
        )
    except Exception as exc:
        receipt["errors"].append(str(exc))

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
