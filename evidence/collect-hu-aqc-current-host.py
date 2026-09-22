#!/usr/bin/env python3
from __future__ import annotations

import argparse
import array
import json
import re
import unicodedata
import wave
from pathlib import Path
from typing import Any

from fa3_runtime_hardening import evaluate_hungarian_aqc
from fa3_hu_aqc_input import BUNDLE_SCHEMA, validate_bundle
from fa3_runtime_hardening_current_host import (
    load_json,
    repo_head,
    sha256_file,
    utcnow,
    write_json,
)


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^0-9a-záéíóöőúüű\s]+", " ", text)
    return " ".join(text.split())


def _levenshtein(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(cur[-1] + 1, prev[j] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def _error_rates(reference: str, hypothesis: str) -> tuple[float, float]:
    ref = _normalize_text(reference)
    hyp = _normalize_text(hypothesis)
    ref_chars = list(ref.replace(" ", ""))
    hyp_chars = list(hyp.replace(" ", ""))
    ref_words = ref.split()
    hyp_words = hyp.split()
    cer = _levenshtein(ref_chars, hyp_chars) / max(1, len(ref_chars))
    wer = _levenshtein(ref_words, hyp_words) / max(1, len(ref_words))
    return cer, wer


def _signal_metrics(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.getnframes()
        if width != 2:
            raise RuntimeError("HU-AQC current-host signal recomputation currently requires PCM16 WAV")
        raw = wf.readframes(frames)
    samples = array.array("h")
    samples.frombytes(raw)
    if not samples:
        raise RuntimeError("audio contains no PCM samples")
    abs_values = [abs(int(x)) for x in samples]
    clip = sum(v >= 32760 for v in abs_values) / len(abs_values)
    silence = sum(v <= 328 for v in abs_values) / len(abs_values)
    finite = True
    return {
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_width_bytes": width,
        "sample_count": len(samples),
        "clipping_ratio": clip,
        "silence_ratio": silence,
        "finite_audio": finite,
    }


def _scorers_admitted(bundle: dict[str, Any], cloning: bool) -> tuple[bool, list[str]]:
    scorers = bundle.get("scorers", {})
    required = ["asr", "language", "grammar", "toxicity", "perceptual"]
    if cloning:
        required.append("speaker")
    reasons: list[str] = []
    for name in required:
        row = scorers.get(name, {})
        digest = str(row.get("model_sha256", ""))
        if not row.get("id") or not row.get("version"):
            reasons.append(f"{name} scorer identity/version missing")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            reasons.append(f"{name} scorer model digest invalid")
        if row.get("license_status") != "ADMITTED":
            reasons.append(f"{name} scorer license not admitted")
        if not row.get("license_evidence_ref"):
            reasons.append(f"{name} scorer license evidence missing")
        if row.get("current_host_measured") is not True:
            reasons.append(f"{name} scorer not marked current-host measured")
        source_digest = str(row.get("source_receipt_sha256", ""))
        if not re.fullmatch(r"[0-9a-fA-F]{64}", source_digest):
            reasons.append(f"{name} scorer source receipt digest invalid")
    return not reasons, reasons


def collect(root: Path, *, audio: Path, metrics_path: Path, output: Path) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "fa3.hu-aqc-current-host-receipt.v1",
        "surface": "HU_AQC",
        "repository_head": repo_head(root),
        "captured_at": utcnow(),
        "synthetic": False,
        "global_promotion_claim": False,
        "locale": "hu-HU",
    }
    try:
        if not audio.is_file():
            raise RuntimeError(f"audio missing: {audio}")
        if not metrics_path.is_file():
            raise RuntimeError(f"metrics input missing: {metrics_path}")
        bundle = load_json(metrics_path)
        if bundle.get("schema") != BUNDLE_SCHEMA:
            raise RuntimeError("HU-AQC metrics input schema mismatch")
        bundle_findings = validate_bundle(root, audio=audio, bundle=bundle)
        if bundle_findings:
            raise RuntimeError("; ".join(bundle_findings))
        reference = str(bundle.get("reference_text", ""))
        hypothesis = str(bundle.get("asr_transcript", ""))
        if not reference or not hypothesis:
            raise RuntimeError("reference text and ASR back-transcription are required")
        cer, wer = _error_rates(reference, hypothesis)
        signal = _signal_metrics(audio)
        cloning = bool(bundle.get("cloning", False))
        scorers_ok, scorer_reasons = _scorers_admitted(bundle, cloning)
        if not scorers_ok:
            raise RuntimeError("; ".join(scorer_reasons))
        metrics = {
            "language_confidence": bundle.get("language_confidence"),
            "grammar_score": bundle.get("grammar_score"),
            "register_consistent": bundle.get("register_consistent"),
            "toxicity_score": bundle.get("toxicity_score"),
            "asr_cer": cer,
            "asr_wer": wer,
            "perceptual_quality": bundle.get("perceptual_quality"),
            "speaker_similarity": bundle.get("speaker_similarity"),
            "finite_audio": signal["finite_audio"],
            "clipping_ratio": signal["clipping_ratio"],
            "silence_ratio": signal["silence_ratio"],
        }
        aqc = evaluate_hungarian_aqc(
            metrics,
            cloning=cloning,
            scorer_license_admitted=True,
        )
        receipt.update({
            "audio_path": str(audio),
            "audio_sha256": sha256_file(audio),
            "metrics_input_sha256": sha256_file(metrics_path),
            "signal_metrics_recomputed_locally": True,
            "asr_error_rates_recomputed_locally": True,
            "scorer_provenance_admitted": True,
            "signal_metrics": signal,
            "asr_metrics": {"cer": cer, "wer": wer},
            "scorers": bundle.get("scorers", {}),
            "aqc": aqc,
        })
        if not aqc["passed"]:
            raise RuntimeError("one or more mandatory HU-AQC dimensions failed")
        receipt["result"] = "PASS"
        receipt["status"] = "CURRENT_HOST_PASS"
    except Exception as exc:
        receipt["result"] = "PENDING"
        receipt["status"] = "PENDING_CURRENT_HOST"
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
    receipt["completed_at"] = utcnow()
    write_json(output, receipt)
    return receipt


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--audio", required=True)
    p.add_argument("--metrics-json", required=True)
    p.add_argument("--output", default="evidence/receipts/hu-aqc-current-host.json")
    a = p.parse_args()
    root = Path(a.root).resolve()
    output = Path(a.output)
    if not output.is_absolute():
        output = root / output
    receipt = collect(
        root,
        audio=Path(a.audio).resolve(),
        metrics_path=Path(a.metrics_json).resolve(),
        output=output,
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
