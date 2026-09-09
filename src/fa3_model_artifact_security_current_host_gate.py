#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_model_artifact_security_gate import admission_valid

GATE_ID = "FA3-GATE-MODEL-ARTIFACT-SECURITY-CURRENT-HOST-001"
RECEIPT = "evidence/receipts/model-artifact-security-current-host.json"
SCANNERS = {"modelaudit","clamav","yara","trivy","bandit","pip-audit","modelscan","picklescan","fickling","garak","cosign"}


def loadj(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def finding(code: str, message: str, **extra: Any) -> dict[str, Any]: return {"code": code, "severity": "P0", "message": message, **extra}
def digest(v: Any) -> bool: return isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) is not None


def gate(root: Path) -> dict[str, Any]:
    path = root / RECEIPT
    fs: list[dict[str, Any]] = []
    receipt: dict[str, Any] = {}
    if not path.is_file():
        fs.append(finding("MODEL-SEC-HOST-001", "current-host model security receipt missing"))
    else:
        try: receipt = loadj(path)
        except Exception as exc: fs.append(finding("MODEL-SEC-HOST-002", "current-host receipt unreadable", error=repr(exc)))
    if receipt:
        if receipt.get("runtime_id") != "FA3-MODEL-ARTIFACT-SECURITY-RUNTIME-CONFORMANCE-001" or receipt.get("status") != "PASS" or receipt.get("evidence_level") != "CURRENT_HOST_PRODUCTION_E2E_PASS":
            fs.append(finding("MODEL-SEC-HOST-003", "runtime identity/status/evidence level mismatch"))
        if not (receipt.get("real_tool_execution") is True and receipt.get("synthetic_target") is False and receipt.get("synthetic_negative_fixture") is True and receipt.get("runtime_promotion_eligible") is True):
            fs.append(finding("MODEL-SEC-HOST-004", "real-target production semantics missing"))
        if receipt.get("scan_network_egress") is not False or receipt.get("modelaudit_telemetry") is not False or receipt.get("root_execution") is not False:
            fs.append(finding("MODEL-SEC-HOST-005", "runtime isolation/telemetry invariant drift"))
        tools = receipt.get("toolchain", {})
        if set(tools) != SCANNERS:
            fs.append(finding("MODEL-SEC-HOST-006", "toolchain inventory incomplete", present=sorted(tools)))
        for sid in SCANNERS:
            row = tools.get(sid, {})
            if not (row.get("present") is True and row.get("version") and digest(row.get("binary_or_package_digest")) and digest(row.get("ruleset_digest"))):
                fs.append(finding("MODEL-SEC-HOST-007", "scanner identity incomplete", scanner_id=sid))
        prod = receipt.get("production_admission", {})
        if not admission_valid(prod):
            fs.append(finding("MODEL-SEC-HOST-008", "real local model security admission is not valid"))
        if prod.get("promotion", {}).get("security_state") != "SECURITY_ADMITTED" or prod.get("promotion", {}).get("direct_runtime_store_download_bypass") is not False:
            fs.append(finding("MODEL-SEC-HOST-009", "Model Manager security state/bypass invariant failed"))
        neg = receipt.get("negative_pickle_regression", {})
        if neg.get("fixture_executed") is not False or neg.get("blocked") is not True:
            fs.append(finding("MODEL-SEC-HOST-010", "controlled malicious pickle was not blocked without execution"))
        expected = {"modelaudit","modelscan","picklescan","fickling"}
        if set(neg.get("blocking_scanners", [])) != expected:
            fs.append(finding("MODEL-SEC-HOST-011", "dangerous serialization scanner negative coverage incomplete", observed=neg.get("blocking_scanners")))
        hook = receipt.get("model_manager_hook", {})
        if not (hook.get("security_state") == "SECURITY_ADMITTED" and hook.get("model_manager_promotion_eligible") is True and hook.get("direct_runtime_store_download_bypass") is False):
            fs.append(finding("MODEL-SEC-HOST-012", "Model Manager security hook failed"))
        if receipt.get("new_capabilities") != 0 or receipt.get("new_architectural_authorities") != 0 or receipt.get("capability_count_after") != 143:
            fs.append(finding("MODEL-SEC-HOST-013", "capability/authority invariant drift"))
    report = {"schema":"fa3.model-artifact-security-current-host-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not fs else "FAIL","findings":fs,"promotion_effect":"MODEL_SECURITY_RUNTIME_CURRENT_HOST_PRODUCTION_E2E_ONLY_GLOBAL_PROMOTION_SEPARATE"}
    out = root / "reports/model-artifact-security-current-host-gate-report.json"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1])); args = ap.parse_args()
    report = gate(Path(args.root).resolve()); print(json.dumps(report, indent=2)); return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__": raise SystemExit(main())
