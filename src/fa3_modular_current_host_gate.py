#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from fa3_modular_runtime import (
    MAX_PROVIDER_ID,
    MOJO_PROVIDER_ID,
    RUNTIME_ID,
    evidence_complete,
    version_channel,
)

RECEIPT = "evidence/receipts/modular-current-host.json"
LEVEL = "CURRENT_HOST_PRODUCTION_E2E_PASS"

def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def writej(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def validate_receipt(root: Path) -> dict[str, Any]:
    path = root / RECEIPT
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str, **details: Any) -> None:
        findings.append({"code": code, "severity": "P0", "message": message, **details})

    if not path.exists():
        return {"result": "FAIL", "findings": [{"code": "MODULAR-HOST-001", "severity": "P0", "message": "Modular current-host receipt missing"}]}
    try:
        receipt = loadj(path)
    except Exception as exc:
        return {"result": "FAIL", "findings": [{"code": "MODULAR-HOST-002", "severity": "P0", "message": "receipt unreadable", "detail": repr(exc)}]}

    if receipt.get("status") != "PASS" or receipt.get("evidence_level") != LEVEL:
        fail("MODULAR-HOST-003", "production PASS/evidence level missing")
    if receipt.get("runtime_id") != RUNTIME_ID:
        fail("MODULAR-HOST-004", "runtime identity mismatch")
    if not evidence_complete(receipt):
        fail("MODULAR-HOST-005", "combined MAX/Mojo evidence incomplete")
    if receipt.get("evidence_channel") not in {"stable", "nightly"}:
        fail("MODULAR-HOST-006", "invalid evidence channel")

    for key in ("max", "mojo"):
        ev = receipt.get(key, {})
        if version_channel(str(ev.get("version", ""))) != receipt.get("evidence_channel"):
            fail("MODULAR-HOST-007", f"{key} version/evidence channel mismatch")

    maxe = receipt.get("max", {})
    if maxe.get("bind_host") not in {"127.0.0.1", "localhost"}:
        fail("MODULAR-HOST-008", "MAX E2E was not loopback-bound")
    if maxe.get("openai_endpoint") != "/v1/chat/completions" or not maxe.get("response_sha256"):
        fail("MODULAR-HOST-009", "OpenAI endpoint inference evidence missing")
    if maxe.get("model_artifact_sha256") != maxe.get("expected_model_artifact_sha256"):
        fail("MODULAR-HOST-013", "MAX model artifact digest does not match canonical allowlist")

    if str(maxe.get("devices", "")).startswith("gpu:"):
        hrb = maxe.get("hrb") or {}
        guard = maxe.get("resource_guard") or {}
        if hrb.get("broker_validation") != "VALID" or not hrb.get("lease_id") or not str(hrb.get("accelerator_uuid", "")).startswith("GPU-"):
            fail("MODULAR-HOST-010", "GPU MAX execution lacks validated HRB lease")
        if guard.get("mechanism") != "max --device-memory-utilization" or not (0.0 < float(guard.get("fraction", 0.0)) <= 0.95):
            fail("MODULAR-HOST-014", "GPU MAX execution lacks lease-derived bounded memory guard")

    for key in ("server_log", "response_file", "mojo_source", "mojo_binary"):
        ref = receipt.get("artifacts", {}).get(key, {})
        artifact_path = Path(ref.get("path", ""))
        if not artifact_path.is_file():
            fail("MODULAR-HOST-011", f"artifact missing: {key}")
        elif ref.get("sha256") != sha256(artifact_path):
            fail("MODULAR-HOST-012", f"artifact digest mismatch: {key}")

    return {"result": "PASS" if not findings else "FAIL", "findings": findings, "receipt": receipt}

def gate(root: Path) -> dict[str, Any]:
    checked = validate_receipt(root)
    report = {
        "schema": "fa3.modular-current-host-gate-report.v1",
        "runtime_id": RUNTIME_ID,
        "provider_ids": [MAX_PROVIDER_ID, MOJO_PROVIDER_ID],
        "result": checked["result"],
        "evidence_level": checked.get("receipt", {}).get("evidence_level"),
        "findings": checked["findings"],
        "promotion_effect": "PROVIDER_SPECIFIC_PRODUCTION_E2E_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED",
    }
    writej(root / "reports/modular-current-host-gate-report.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
