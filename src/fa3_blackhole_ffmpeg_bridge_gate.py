#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_blackhole_ffmpeg_bridge import run_bridge_regressions, validate_payload

GATE_ID = "FA3-BLACKHOLE-FFMPEG-BRIDGE-GATESET-001"
CONTRACT_ID = "FA3-BLACKHOLE-FFMPEG-BRIDGE-CONTRACTS-001"
RUNTIME_ID = "FA3-BLACKHOLE-FFMPEG-BRIDGE-RUNTIME-CONFORMANCE-001"
PAYLOAD_PATH = "canonical/payloads/blackhole_ffmpeg_bridge.json"
EVIDENCE_PATH = "evidence/reference/blackhole-ffmpeg-bridge-reference-2026-09-14.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def canonical_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "contract": root / "canonical/contracts/FA3-BLACKHOLE-FFMPEG-BRIDGE-CONTRACTS-001.json",
        "runtime": root / "canonical/FA3-BLACKHOLE-FFMPEG-BRIDGE-RUNTIME-CONFORMANCE-001.json",
        "enforcement": root / "canonical/blackhole-ffmpeg-bridge-enforcement.json",
        "payload": root / PAYLOAD_PATH,
        "stt": root / "canonical/profiles/FA3-STT-MEDIA-001.json",
        "neural": root / "canonical/profiles/FA3-NEURAL-MEDIA-EXECUTION-001.json",
        "hrb": root / "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json",
        "evidence": root / EVIDENCE_PATH,
    }
    for name, path in paths.items():
        if not path.is_file():
            findings.append(finding("BHBR-REF-001", "required bridge artifact missing", artifact=name, path=str(path.relative_to(root))))
    if findings:
        return {"result": "FAIL", "findings": findings}

    contract = _load(paths["contract"])
    runtime = _load(paths["runtime"])
    enforcement = _load(paths["enforcement"])
    payload = _load(paths["payload"])
    evidence = _load(paths["evidence"])

    if contract.get("id") != CONTRACT_ID or contract.get("provider_neutral") is not True:
        findings.append(finding("BHBR-REF-002", "bridge contract identity/provider-neutrality drift"))
    deps = set(contract.get("delegates_to") or [])
    for required in ("FA3-STT-MEDIA-001", "FA3-NEURAL-MEDIA-EXECUTION-001", "FA3-HOST-RESOURCE-BROKER-001"):
        if required not in deps:
            findings.append(finding("BHBR-REF-003", "required existing authority/profile delegation missing", required=required))
    zero_policy = contract.get("zero_copy_policy") or {}
    if zero_policy.get("intent_boolean_is_evidence") is not False:
        findings.append(finding("BHBR-REF-004", "zero-copy intent was promoted to evidence"))
    if zero_policy.get("end_to_end_gpu_resident_baseline_claim") is not False:
        findings.append(finding("BHBR-REF-005", "end-to-end GPU-resident baseline overclaim detected"))
    if zero_policy.get("measured_frame_to_tensor_evidence_required") is not True:
        findings.append(finding("BHBR-REF-006", "measured frame-to-tensor evidence requirement missing"))

    try:
        validate_payload(payload)
    except Exception as exc:
        findings.append(finding("BHBR-REF-007", "canonical example payload is invalid", error=str(exc)))

    if runtime.get("id") != RUNTIME_ID or runtime.get("status") != "PENDING_CURRENT_HOST":
        findings.append(finding("BHBR-REF-008", "runtime conformance must remain PENDING_CURRENT_HOST"))
    if runtime.get("reference_ci_may_promote_runtime") is not False:
        findings.append(finding("BHBR-REF-009", "reference CI incorrectly has runtime-promotion authority"))

    if enforcement.get("gate_id") != GATE_ID or enforcement.get("fail_closed") is not True:
        findings.append(finding("BHBR-REF-010", "bridge enforcement identity/fail-closed drift"))
    if enforcement.get("regression_case_count") != 16:
        findings.append(finding("BHBR-REF-011", "bridge regression case count drift"))

    if evidence.get("status") != "PASS" or evidence.get("current_host_runtime_claim") is not False:
        findings.append(finding("BHBR-REF-012", "reference evidence/runtime-claim separation drift"))
    if evidence.get("runtime_status") != "PENDING_CURRENT_HOST":
        findings.append(finding("BHBR-REF-013", "reference evidence must preserve current-host pending state"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    canonical = canonical_check(root)
    regressions = run_bridge_regressions()
    result = "PASS" if canonical["result"] == "PASS" and regressions["result"] == "PASS" else "FAIL"
    report = {
        "schema": "fa3.blackhole-ffmpeg-bridge-gate-report.v1",
        "gate_id": GATE_ID,
        "result": result,
        "canonical": canonical,
        "regressions": regressions,
        "current_host_runtime_claim": False,
        "runtime_status": "PENDING_CURRENT_HOST",
    }
    _write(root / "reports/blackhole-ffmpeg-bridge-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
