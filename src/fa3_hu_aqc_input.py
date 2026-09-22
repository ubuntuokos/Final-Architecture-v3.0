#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fa3_host_attestation import load_artifact
from fa3_runtime_hardening_current_host import fresh_timestamp, repo_head, sha256_file, utcnow


SCORER_SCHEMA = "fa3.hu-aqc-scorer-receipt.v1"
BUNDLE_SCHEMA = "fa3.hu-aqc-current-host-input.v2"
BASE_SCORERS = ("asr", "language", "grammar", "toxicity", "perceptual")
ALL_SCORERS = BASE_SCORERS + ("speaker",)
HEX64 = re.compile(r"^(?:sha256:)?([0-9a-f]{64})$")


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{label} unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _score(value: Any, label: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")
    return score


def validate_scorer_receipt(
    receipt: Any,
    *,
    scorer: str,
    repository_head: str,
    host_attestation_ref: str,
    audio_sha256: str,
    reference_text_sha256: str,
) -> list[str]:
    if not isinstance(receipt, dict):
        return [f"{scorer} scorer receipt must be an object"]
    findings: list[str] = []
    if receipt.get("schema") != SCORER_SCHEMA:
        findings.append(f"{scorer} scorer schema mismatch")
    if receipt.get("scorer") != scorer:
        findings.append(f"{scorer} scorer identity mismatch")
    if receipt.get("repository_head") != repository_head:
        findings.append(f"{scorer} scorer repository HEAD mismatch")
    if not fresh_timestamp(receipt.get("captured_at")):
        findings.append(f"{scorer} scorer timestamp is stale or invalid")
    if receipt.get("current_host_measured") is not True or receipt.get("synthetic") is not False:
        findings.append(f"{scorer} scorer is not real current-host evidence")
    if receipt.get("host_attestation_ref") != host_attestation_ref:
        findings.append(f"{scorer} scorer host-attestation binding mismatch")
    subject = receipt.get("subject", {})
    if not isinstance(subject, dict):
        findings.append(f"{scorer} scorer subject missing")
    else:
        if subject.get("audio_sha256") != audio_sha256:
            findings.append(f"{scorer} scorer audio binding mismatch")
        if subject.get("reference_text_sha256") != reference_text_sha256:
            findings.append(f"{scorer} scorer reference-text binding mismatch")
    model = receipt.get("model", {})
    digest_match = HEX64.fullmatch(str(model.get("sha256") or "")) if isinstance(model, dict) else None
    if not isinstance(model, dict) or not str(model.get("id") or "").strip() or not str(model.get("version") or "").strip():
        findings.append(f"{scorer} scorer model identity/version missing")
    if not digest_match:
        findings.append(f"{scorer} scorer model digest invalid")
    if not isinstance(model, dict) or model.get("license_status") != "ADMITTED":
        findings.append(f"{scorer} scorer license not admitted")
    if not isinstance(model, dict) or not str(model.get("license_evidence_ref") or "").strip():
        findings.append(f"{scorer} scorer license evidence missing")
    if not str(receipt.get("measurement_id") or "").strip():
        findings.append(f"{scorer} scorer measurement identity missing")

    measurements = receipt.get("measurements", {})
    if not isinstance(measurements, dict):
        findings.append(f"{scorer} scorer measurements missing")
        return findings
    try:
        if scorer == "asr" and not str(measurements.get("transcript") or "").strip():
            findings.append("asr scorer transcript missing")
        elif scorer == "language":
            _score(measurements.get("language_confidence"), "language_confidence")
        elif scorer == "grammar":
            _score(measurements.get("grammar_score"), "grammar_score")
            if not isinstance(measurements.get("register_consistent"), bool):
                findings.append("grammar scorer register_consistent must be boolean")
        elif scorer == "toxicity":
            _score(measurements.get("toxicity_score"), "toxicity_score")
        elif scorer == "perceptual":
            _score(measurements.get("perceptual_quality"), "perceptual_quality")
        elif scorer == "speaker":
            _score(measurements.get("speaker_similarity"), "speaker_similarity")
    except ValueError as exc:
        findings.append(f"{scorer} scorer measurement invalid: {exc}")
    return findings


def _scorer_projection(receipt: dict[str, Any], receipt_path: Path) -> dict[str, Any]:
    model = receipt["model"]
    digest = HEX64.fullmatch(str(model["sha256"])).group(1)  # validated by caller
    return {
        "id": model["id"],
        "version": model["version"],
        "model_sha256": digest,
        "license_status": model["license_status"],
        "license_evidence_ref": model["license_evidence_ref"],
        "current_host_measured": True,
        "measurement_id": receipt["measurement_id"],
        "source_receipt_sha256": sha256_file(receipt_path),
    }


def produce_bundle(
    root: Path,
    *,
    audio: Path,
    reference_text_file: Path,
    host_attestation: Path,
    scorer_receipts: dict[str, Path],
    cloning: bool,
) -> dict[str, Any]:
    root = root.resolve()
    audio = audio.resolve()
    reference_text_file = reference_text_file.resolve()
    if not audio.is_file() or audio.stat().st_size <= 0:
        raise ValueError("HU-AQC audio missing or empty")
    if not reference_text_file.is_file():
        raise ValueError("HU-AQC reference-text file missing")
    reference_text = reference_text_file.read_text(encoding="utf-8").strip()
    if not reference_text:
        raise ValueError("HU-AQC reference text is empty")
    host_findings, host_ref, _, _ = load_artifact(host_attestation.resolve())
    if host_findings:
        raise ValueError("; ".join(host_findings))

    required = list(BASE_SCORERS) + (["speaker"] if cloning else [])
    missing = [name for name in required if name not in scorer_receipts]
    if missing:
        raise ValueError("required HU-AQC scorer receipts missing: " + ", ".join(missing))
    if not cloning and "speaker" in scorer_receipts:
        raise ValueError("speaker scorer receipt supplied for non-cloning HU-AQC run")

    head = repo_head(root)
    audio_sha = sha256_file(audio)
    reference_sha = sha256_file(reference_text_file)
    loaded: dict[str, dict[str, Any]] = {}
    source_receipts: dict[str, dict[str, str]] = {}
    findings: list[str] = []
    for scorer in required:
        path = scorer_receipts[scorer].resolve()
        if not path.is_file():
            findings.append(f"{scorer} scorer receipt missing")
            continue
        receipt = _load_object(path, f"{scorer} scorer receipt")
        findings.extend(validate_scorer_receipt(
            receipt,
            scorer=scorer,
            repository_head=head,
            host_attestation_ref=host_ref,
            audio_sha256=audio_sha,
            reference_text_sha256=reference_sha,
        ))
        loaded[scorer] = receipt
        source_receipts[scorer] = {"path": str(path), "sha256": sha256_file(path)}
    if findings:
        raise ValueError("; ".join(sorted(set(findings))))

    asr = loaded["asr"]["measurements"]
    language = loaded["language"]["measurements"]
    grammar = loaded["grammar"]["measurements"]
    toxicity = loaded["toxicity"]["measurements"]
    perceptual = loaded["perceptual"]["measurements"]
    bundle: dict[str, Any] = {
        "schema": BUNDLE_SCHEMA,
        "locale": "hu-HU",
        "repository_head": head,
        "captured_at": utcnow(),
        "current_host_measured": True,
        "synthetic": False,
        "host_attestation_ref": host_ref,
        "host_attestation_path": str(host_attestation.resolve()),
        "audio_sha256": audio_sha,
        "reference_text": reference_text,
        "reference_text_path": str(reference_text_file),
        "reference_text_sha256": reference_sha,
        "asr_transcript": str(asr["transcript"]),
        "language_confidence": _score(language["language_confidence"], "language_confidence"),
        "grammar_score": _score(grammar["grammar_score"], "grammar_score"),
        "register_consistent": grammar["register_consistent"],
        "toxicity_score": _score(toxicity["toxicity_score"], "toxicity_score"),
        "perceptual_quality": _score(perceptual["perceptual_quality"], "perceptual_quality"),
        "speaker_similarity": None,
        "cloning": cloning,
        "scorers": {name: _scorer_projection(loaded[name], scorer_receipts[name].resolve()) for name in required},
        "source_receipts": source_receipts,
        "producer": {
            "id": "FA3-HU-AQC-CURRENT-HOST-INPUT-PRODUCER-001",
            "version": "1.0.0",
            "default_scores_used": False,
            "single_judge_authority": False,
        },
    }
    if cloning:
        bundle["speaker_similarity"] = _score(
            loaded["speaker"]["measurements"]["speaker_similarity"],
            "speaker_similarity",
        )
    return bundle


def validate_bundle(
    root: Path,
    *,
    audio: Path,
    bundle: Any,
    verify_source_receipts: bool = True,
) -> list[str]:
    if not isinstance(bundle, dict):
        return ["HU-AQC input bundle must be an object"]
    findings: list[str] = []
    if bundle.get("schema") != BUNDLE_SCHEMA:
        findings.append("HU-AQC input bundle schema mismatch")
    if bundle.get("locale") != "hu-HU":
        findings.append("HU-AQC input bundle locale mismatch")
    if bundle.get("repository_head") != repo_head(root):
        findings.append("HU-AQC input bundle repository HEAD mismatch")
    if not fresh_timestamp(bundle.get("captured_at")):
        findings.append("HU-AQC input bundle timestamp is stale or invalid")
    if bundle.get("current_host_measured") is not True or bundle.get("synthetic") is not False:
        findings.append("HU-AQC input bundle is not real current-host evidence")
    host_ref = str(bundle.get("host_attestation_ref") or "")
    host_path = Path(str(bundle.get("host_attestation_path") or "")).expanduser()
    host_findings, expected_host_ref, _, _ = load_artifact(host_path) if str(host_path) not in ("", ".") else (["host attestation path missing"], "", {}, {})
    findings.extend(host_findings)
    if host_ref != expected_host_ref:
        findings.append("HU-AQC host-attestation digest binding mismatch")
    if not audio.is_file() or bundle.get("audio_sha256") != sha256_file(audio):
        findings.append("HU-AQC audio digest binding mismatch")
    reference_text = str(bundle.get("reference_text") or "")
    if not reference_text:
        findings.append("HU-AQC reference text missing")
    reference_path = Path(str(bundle.get("reference_text_path") or "")).expanduser()
    if not reference_path.is_file():
        findings.append("HU-AQC reference-text source file missing")
    else:
        if bundle.get("reference_text_sha256") != sha256_file(reference_path):
            findings.append("HU-AQC reference-text digest binding mismatch")
        if reference_path.read_text(encoding="utf-8").strip() != reference_text:
            findings.append("HU-AQC reference text differs from its bound source file")
    cloning = bool(bundle.get("cloning", False))
    required = list(BASE_SCORERS) + (["speaker"] if cloning else [])
    scorers = bundle.get("scorers", {})
    sources = bundle.get("source_receipts", {})
    if not isinstance(scorers, dict) or not isinstance(sources, dict):
        findings.append("HU-AQC scorer provenance missing")
        return findings
    if verify_source_receipts:
        for scorer in required:
            source = sources.get(scorer, {})
            path = Path(str(source.get("path") or "")).expanduser()
            if not path.is_file():
                findings.append(f"{scorer} source receipt missing")
                continue
            if source.get("sha256") != sha256_file(path):
                findings.append(f"{scorer} source receipt digest mismatch")
                continue
            try:
                receipt = _load_object(path, f"{scorer} source receipt")
            except ValueError as exc:
                findings.append(str(exc))
                continue
            findings.extend(validate_scorer_receipt(
                receipt,
                scorer=scorer,
                repository_head=repo_head(root),
                host_attestation_ref=host_ref,
                audio_sha256=str(bundle.get("audio_sha256") or ""),
                reference_text_sha256=str(bundle.get("reference_text_sha256") or ""),
            ))
            projection = scorers.get(scorer, {})
            if not isinstance(projection, dict) or projection.get("source_receipt_sha256") != sha256_file(path):
                findings.append(f"{scorer} scorer projection/source receipt mismatch")
            measurements = receipt.get("measurements", {})
            expected_fields = {
                "asr": ("asr_transcript", "transcript"),
                "language": ("language_confidence", "language_confidence"),
                "grammar": ("grammar_score", "grammar_score"),
                "toxicity": ("toxicity_score", "toxicity_score"),
                "perceptual": ("perceptual_quality", "perceptual_quality"),
                "speaker": ("speaker_similarity", "speaker_similarity"),
            }
            bundle_field, receipt_field = expected_fields[scorer]
            if bundle.get(bundle_field) != measurements.get(receipt_field):
                findings.append(f"{scorer} scorer measurement differs from the producer bundle")
            if scorer == "grammar" and bundle.get("register_consistent") != measurements.get("register_consistent"):
                findings.append("grammar register measurement differs from the producer bundle")
    if not cloning and ("speaker" in scorers or "speaker" in sources or bundle.get("speaker_similarity") is not None):
        findings.append("non-cloning HU-AQC bundle carries speaker measurement")
    return sorted(set(findings))
