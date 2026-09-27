#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_hu_speech_editable_video_reference import REFERENCE_ID, run_reference_e2e
from fa3_release_baseline import module_active_capability_count

GATE_ID = "FA3-HU-SPEECH-EDITABLE-VIDEO-REFERENCE-GATESET-001"
REFERENCE_PATH = "canonical/references/FA3-HU-SPEECH-EDITABLE-VIDEO-REFERENCE-001.json"
RECEIPT_PATH = "evidence/receipts/hu-speech-editable-video-current-host.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, str]] = []
    required = [
        REFERENCE_PATH,
        "src/fa3_hu_speech_editable_video_reference.py",
        "evidence/collect-hu-speech-editable-video-current-host.py",
        "src/fa3_whisper_stt_provider.py",
        "src/fa3_blackhole_kdenlive.py",
        "src/fa3_caption_subtitle.py",
        "src/fa3_caption_workflows.py",
        "canonical/profiles/FA3-STT-MEDIA-001.json",
        "canonical/profiles/FA3-CAPTION-SUBTITLE-001.json",
        "canonical/profiles/FA3-PROGRAMMABLE-VIDEO-EDITING-001.json",
        "canonical/profiles/FA3-KDENLIVE-EDITORIAL-001.json",
        "canonical/contracts/FA3-VIDEO-TIMELINE-PROVIDER-CONTRACTS-001.json",
    ]
    for rel in required:
        if not (root / rel).is_file():
            findings.append(_finding("HUSPEECH-001", f"missing materialization path: {rel}"))
    if findings:
        return {
            "schema": "fa3.hu-speech-editable-video-reference-gate-report.v1",
            "gate_id": GATE_ID,
            "reference_journey_id": REFERENCE_ID,
            "result": "FAIL",
            "findings": findings,
            "current_host_status": "PENDING_CURRENT_HOST",
            "current_host_runtime_promotion_claim": False,
        }

    ref = _load(root / REFERENCE_PATH)
    expected_count = module_active_capability_count(__file__)
    checks = [
        ("HUSPEECH-002", ref.get("id") == REFERENCE_ID, "reference journey identity drift"),
        ("HUSPEECH-003", ref.get("capability_count") == expected_count == 175, "active capability baseline drift"),
        ("HUSPEECH-004", ref.get("new_capability") is False and ref.get("new_architectural_authority") is False, "reference journey gained capability or authority"),
        ("HUSPEECH-005", ref.get("requested_locale") == "hu-HU" and ref.get("provider_language_code") == "hu", "Hungarian language contract drift"),
        ("HUSPEECH-006", set(ref.get("capability_bindings", [])) == {"CAP-017", "CAP-121", "CAP-126", "CAP-168"}, "capability bindings drift"),
        ("HUSPEECH-007", ref.get("canonical_timeline_ir") == "OpenTimelineIO" and ref.get("fa3_video_project_artifact") == "project.fa3video", "editable video project/OTIO contract drift"),
        ("HUSPEECH-008", ref.get("kdenlive", {}).get("direct_project_xml_mutation") is False and ref.get("kdenlive", {}).get("human_finishing_boundary") is True, "Kdenlive human-edit boundary drift"),
        ("HUSPEECH-009", ref.get("human_edit", {}).get("required") is True and ref.get("human_edit", {}).get("reexport_required") is True, "human edit/re-export proof requirement missing"),
        ("HUSPEECH-010", ref.get("resilience", {}).get("retry_resume_required") is True and ref.get("resilience", {}).get("failure_injection_required") is True and ref.get("resilience", {}).get("rollback_required") is True, "resilience proof contract incomplete"),
        ("HUSPEECH-011", ref.get("measurement", {}).get("wall_time_required") is True and ref.get("measurement", {}).get("cpu_required") is True and ref.get("measurement", {}).get("ram_required") is True and ref.get("measurement", {}).get("vram_required_when_accelerated") is True, "runtime/resource measurement contract incomplete"),
        ("HUSPEECH-012", ref.get("lineage", {}).get("final_project_sha256_required") is True and ref.get("lineage", {}).get("source_to_final_hash_chain_required") is True, "lineage/final project hash contract incomplete"),
        ("HUSPEECH-013", ref.get("current_host", {}).get("receipt") == RECEIPT_PATH and ref.get("current_host", {}).get("reference_ci_may_claim_pass") is False, "current-host evidence boundary drift"),
        ("HUSPEECH-014", ref.get("hardware_audit", {}).get("vendor_neutral") is True and ref.get("hardware_audit", {}).get("cpu_only") is True and ref.get("hardware_audit", {}).get("accelerator_cardinality") == "0..N", "hardware audit portability contract drift"),
        ("HUSPEECH-015", ref.get("coexistence", {}).get("requires_upstream_uninstall") is False and ref.get("coexistence", {}).get("global_environment_mutation") is False, "software coexistence boundary drift"),
        ("HUSPEECH-016", ref.get("current_host_runtime_promotion_claim") is False, "reference journey claimed current-host runtime promotion"),
    ]
    for code, ok, message in checks:
        if not ok:
            findings.append(_finding(code, message))

    try:
        reference_e2e = run_reference_e2e(root)
    except Exception as exc:
        reference_e2e = {"result": "FAIL", "error": repr(exc), "current_host_claim": False}
    if reference_e2e.get("result") != "PASS":
        findings.append(_finding("HUSPEECH-017", "deterministic reference E2E failed"))
    if reference_e2e.get("current_host_claim") is not False:
        findings.append(_finding("HUSPEECH-018", "reference E2E incorrectly claimed current-host evidence"))

    receipt_path = root / RECEIPT_PATH
    current_host_state = "PENDING_CURRENT_HOST"
    receipt_summary: dict[str, Any] = {"present": receipt_path.is_file(), "valid": False}
    if receipt_path.is_file():
        try:
            receipt = _load(receipt_path)
            receipt_valid = (
                receipt.get("schema") == "fa3.hu-speech-editable-video-current-host-evidence.v1"
                and receipt.get("status") == "CURRENT_HOST_HU_SPEECH_EDITABLE_VIDEO_E2E_PASS"
                and receipt.get("current_host") is True
                and receipt.get("ci") is False
                and receipt.get("production_promotion") is False
                and receipt.get("input", {}).get("requested_locale") == "hu-HU"
                and receipt.get("speech_recognition", {}).get("detected_language") in {"hu", "hu-HU"}
                and receipt.get("human_edit", {}).get("actor") == "HUMAN_OPERATOR"
                and receipt.get("failure_injection", {}).get("recovered") is True
                and receipt.get("rollback", {}).get("verified") is True
                and len(str(receipt.get("final_project", {}).get("sha256", ""))) == 64
                and receipt.get("runtime_metrics", {}).get("wall_seconds") is not None
                and receipt.get("runtime_metrics", {}).get("peak_rss_bytes") is not None
                and receipt.get("runtime_metrics", {}).get("vram_peak_bytes") is not None
            )
            receipt_summary = {
                "present": True,
                "valid": receipt_valid,
                "run_id": receipt.get("run_id"),
                "source_commit": receipt.get("source_commit"),
                "host_id": receipt.get("host_id"),
                "collected_at": receipt.get("collected_at"),
                "expires_at": receipt.get("expires_at"),
            }
            if receipt_valid:
                current_host_state = "CURRENT_HOST_PASS"
            else:
                findings.append(_finding("HUSPEECH-019", "present current-host receipt is invalid"))
        except Exception as exc:
            findings.append(_finding("HUSPEECH-020", f"current-host receipt parse failed: {exc}"))

    return {
        "schema": "fa3.hu-speech-editable-video-reference-gate-report.v1",
        "gate_id": GATE_ID,
        "reference_journey_id": REFERENCE_ID,
        "result": "PASS" if not findings else "FAIL",
        "reference_e2e": reference_e2e,
        "current_host_status": current_host_state,
        "current_host_receipt": receipt_summary,
        "findings": findings,
        "current_host_runtime_promotion_claim": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate FA3 Hungarian speech -> editable video project reference journey")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--report", default="reports/hu-speech-editable-video-reference-gate-report.json")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    result = gate(root)
    report = Path(args.report)
    if not report.is_absolute():
        report = root / report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
