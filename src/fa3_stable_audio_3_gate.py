#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-STABLE-AUDIO-3-GATESET-001"
PROVIDER_ID = "FA3-PROVIDER-STABLE-AUDIO-3-001"
PROFILE_ID = "FA3-MUSIC-001"
CAPABILITY_COUNT = 143
UPSTREAM_PIN = "779434a908193105335fd8d833418603625b2859"
CURRENT_HOST_CASES = {
    "SA3-CH-001-small-sfx-cpu-text-to-audio",
    "SA3-CH-002-small-music-cpu-text-to-audio",
    "SA3-CH-003-medium-pytorch-cuda-hrb",
    "SA3-CH-004-medium-tensorrt-live-sm-pinned-engine",
    "SA3-CH-005-audio-to-audio",
    "SA3-CH-006-inpainting-and-continuation",
    "SA3-CH-007-wav-44k1-stereo-limiter-metadata",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    provider_path = root / "canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json"
    profile_path = root / "canonical/profiles/FA3-MUSIC-001.json"
    if not provider_path.is_file() or not profile_path.is_file():
        return {"gate_id": GATE_ID, "result": "FAIL", "findings": [finding("SA3-FREE-001", "required Stable Audio artifact missing")]}
    provider = loadj(provider_path)
    profile = loadj(profile_path)
    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("immutable_reference") == UPSTREAM_PIN
    ):
        findings.append(finding("SA3-FREE-002", "Stable Audio provider identity/authority drift"))
    if PROVIDER_ID not in profile.get("providers", []):
        findings.append(finding("SA3-FREE-003", "Stable Audio provider lost Music profile binding"))
    routes = provider.get("routes", {})
    if routes.get("small_music") != "CPU_LOCAL_CANDIDATE" or routes.get("small_sfx") != "CPU_LOCAL_CANDIDATE":
        findings.append(finding("SA3-FREE-004", "Stable Audio local Small routes drift"))
    if routes.get("medium") != "CUDA_LOCAL_CANDIDATE_SUBJECT_TO_HRB_E2E":
        findings.append(finding("SA3-FREE-005", "Stable Audio Medium local HRB route drift"))
    if routes.get("large") != "REMOVED_PAID_ROUTE":
        findings.append(finding("SA3-FREE-006", "Stable Audio paid Large/API route returned"))
    large = provider.get("model_family", {}).get("large", {})
    if large.get("status") != "REMOVED_FROM_FA3_PAID_ONLY" or large.get("route") != "REMOVED_PAID_ROUTE":
        findings.append(finding("SA3-FREE-007", "Stable Audio Large model is not fail-closed as removed paid route"))
    if not (
        provider.get("economics_policy") == "FA3-FREE-SELF-HOSTED-ONLY-001"
        and provider.get("paid_routes_allowed") is False
        and provider.get("remote_paid_fallback") is False
    ):
        findings.append(finding("SA3-FREE-008", "Stable Audio economics policy weakened"))
    serialized = json.dumps(provider.get("routes", {}))
    if "REMOTE_API_OR_ENTERPRISE_SELF_HOST" in serialized:
        findings.append(finding("SA3-FREE-009", "legacy paid Stable Audio route remains active"))
    audio = provider.get("audio_output_semantics", {})
    if audio.get("canonical_sample_rate_hz") != 44100 or audio.get("canonical_channels") != 2 or audio.get("canonical_master") != "lossless":
        findings.append(finding("SA3-FREE-010", "local Stable Audio output semantics drift"))
    report = {
        "schema": "fa3.stable-audio-3-gate-report.v2",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "profile_id": PROFILE_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "capability_count": CAPABILITY_COUNT,
        "paid_routes_allowed": False,
        "current_host_runtime_evidence": False,
    }
    out = root / "reports/stable-audio-3-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def current_host_gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    receipt_path = root / "evidence/receipts/stable-audio-3-current-host.json"
    if not receipt_path.is_file():
        findings.append(finding("SA3-CH-EVID-001", "real current-host Stable Audio 3 receipt missing"))
    else:
        receipt = loadj(receipt_path)
        if receipt.get("status") != "CURRENT_HOST_STABLE_AUDIO_3_E2E_PASS" or receipt.get("current_host") is not True or receipt.get("production_e2e") is not True:
            findings.append(finding("SA3-CH-EVID-002", "receipt does not prove current-host local production E2E"))
        ids = {c.get("case_id") for c in receipt.get("cases", []) if c.get("status") == "PASS"}
        if ids != CURRENT_HOST_CASES:
            findings.append(finding("SA3-CH-EVID-003", "required local current-host case set incomplete", passed=sorted(ids)))
        if receipt.get("upstream_immutable_reference") != UPSTREAM_PIN:
            findings.append(finding("SA3-CH-EVID-004", "current-host upstream pin mismatch"))
        if receipt.get("paid_remote_route_used") is True:
            findings.append(finding("SA3-CH-EVID-005", "current-host receipt used forbidden paid remote route"))
    report = {
        "schema": "fa3.stable-audio-3-current-host-gate-report.v2",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "current_host_runtime_evidence": not findings,
        "production_promotion_claim": not findings,
        "free_local_only": True,
        "findings": findings,
    }
    out = root / "reports/stable-audio-3-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
