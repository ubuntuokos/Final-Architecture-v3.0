#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from fa3_demucs_provider import HRB_LEASE_SCHEMA, HRB_PROFILE_ID, PROVIDER_ID, PROVIDER_VERSION

RECEIPT = "evidence/receipts/demucs-current-host.json"
PRODUCTION_LEVEL = "CURRENT_HOST_PRODUCTION_E2E_PASS"
SMOKE_LEVEL = "CURRENT_HOST_SYNTHETIC_E2E_PASS"

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()

def validate_receipt(root: Path, require_production: bool = True) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    receipt_path = root / RECEIPT
    if not receipt_path.exists():
        return {
            "result": "FAIL",
            "findings": [{"code":"DEMUCS-HOST-001","severity":"P0","message":"Demucs current-host receipt is missing"}],
        }
    try:
        receipt = _load(receipt_path)
    except Exception as exc:
        return {
            "result":"FAIL",
            "findings":[{"code":"DEMUCS-HOST-002","severity":"P0","message":"Demucs current-host receipt is unreadable","detail":repr(exc)}],
        }

    def fail(code: str, message: str, **details: Any) -> None:
        findings.append({"code":code,"severity":"P0","message":message,**details})

    if receipt.get("status") != "PASS":
        fail("DEMUCS-HOST-003", "Demucs current-host receipt status is not PASS")
    if receipt.get("provider_id") != PROVIDER_ID or receipt.get("provider_version") != PROVIDER_VERSION:
        fail("DEMUCS-HOST-004", "Demucs provider identity/version mismatch")
    level = receipt.get("evidence_level")
    allowed = {PRODUCTION_LEVEL} if require_production else {PRODUCTION_LEVEL, SMOKE_LEVEL}
    if level not in allowed:
        fail("DEMUCS-HOST-005", "Demucs current-host evidence level is insufficient", level=level, require_production=require_production)
    if require_production and receipt.get("synthetic_input") is not False:
        fail("DEMUCS-HOST-006", "Production current-host PASS cannot use synthetic input")
    conf = receipt.get("executable_conformance", {})
    if conf.get("result") != "PASS" or conf.get("passed") != conf.get("total") or int(conf.get("total", 0)) < 13:
        fail("DEMUCS-HOST-007", "Executable provider/security conformance is not complete PASS")
    if receipt.get("hrb_enforced") is not True:
        fail("DEMUCS-HOST-008", "Host Resource Broker enforcement is not proven")
    if receipt.get("model_trust_enforced") is not True:
        fail("DEMUCS-HOST-009", "Model trust/class allowlist enforcement is not proven")

    execution_ref = receipt.get("execution_evidence", {})
    execution_path_value = execution_ref.get("path")
    if not execution_path_value:
        fail("DEMUCS-HOST-010", "Execution evidence path missing")
    else:
        execution_path = Path(execution_path_value)
        if not execution_path.is_file():
            fail("DEMUCS-HOST-011", "Execution evidence file missing on collecting host")
        else:
            actual = _sha256(execution_path)
            if actual != execution_ref.get("sha256"):
                fail("DEMUCS-HOST-012", "Execution evidence digest mismatch")
            try:
                execution = _load(execution_path)
            except Exception as exc:
                fail("DEMUCS-HOST-013", "Execution evidence unreadable", detail=repr(exc))
            else:
                if execution.get("status") != "PASS" or execution.get("provider_id") != PROVIDER_ID:
                    fail("DEMUCS-HOST-014", "Execution evidence provider/status mismatch")
                trust = execution.get("model_trust", {})
                if trust.get("container") != "SAFETENSORS" or trust.get("class_allowlisted") is not True or trust.get("legacy_pickle_used") is not False:
                    fail("DEMUCS-HOST-015", "Execution evidence does not prove safe allowlisted model loading")
                device = str(execution.get("provider_runtime", {}).get("device", ""))
                if device.startswith("cuda:"):
                    if not execution.get("device_lease"):
                        fail("DEMUCS-HOST-016", "CUDA execution evidence lacks HRB lease")
                    hrb = execution.get("hrb", {})
                    if (
                        hrb.get("schema") != HRB_LEASE_SCHEMA
                        or hrb.get("issuer") != HRB_PROFILE_ID
                        or hrb.get("broker_validation") != "VALID"
                        or not str(hrb.get("accelerator_uuid", "")).startswith("GPU-")
                    ):
                        fail("DEMUCS-HOST-018", "CUDA execution evidence lacks canonical HRB lease/broker validation")
                    guard = execution.get("resource_guard", {})
                    if (
                        guard.get("mechanism") != "torch.cuda.set_per_process_memory_fraction"
                        or int(guard.get("memory_max_bytes", 0)) <= 0
                    ):
                        fail("DEMUCS-HOST-019", "CUDA execution evidence lacks lease-derived PyTorch allocator guard")
                if not execution.get("output_hashes") or not execution.get("quality_evidence"):
                    fail("DEMUCS-HOST-017", "Stem output/quality evidence missing")

    return {"result":"PASS" if not findings else "FAIL","findings":findings,"receipt":receipt}

def gate(root: Path, require_production: bool = True) -> dict[str, Any]:
    checked = validate_receipt(root, require_production=require_production)
    report = {
        "schema":"fa3.demucs-current-host-gate-report.v1",
        "provider_id":PROVIDER_ID,
        "provider_version":PROVIDER_VERSION,
        "require_production":require_production,
        "result":checked["result"],
        "findings":checked["findings"],
        "evidence_level":checked.get("receipt", {}).get("evidence_level"),
        "promotion_effect":"PROVIDER_SPECIFIC_E2E_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED",
    }
    _write(root / "reports/demucs-current-host-gate-report.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser(description="Validate FA3 Demucs current-host E2E evidence")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--allow-synthetic", action="store_true")
    args = ap.parse_args()
    report = gate(Path(args.root).resolve(), require_production=not args.allow_synthetic)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
