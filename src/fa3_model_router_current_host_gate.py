#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from fa3_model_router_runtime import AUTHORITY_ID

GATE_ID = "FA3-MODEL-ROUTER-CURRENT-HOST-GATESET-001"
REQUIRED_ROUTES = {"fa3-pageindex-index", "fa3-pageindex-reason"}
REQUIRED_CHECKS = {
    "authority_bound",
    "provider_catalog_dynamic",
    "logical_routes_exposed",
    "physical_backend_not_canonical_pinned",
    "physical_model_not_canonical_pinned",
    "authenticated_loopback_litellm",
    "real_route_execution",
}


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    path = receipt_path or root / "evidence/receipts/model-router-current-host.json"
    if not path.is_absolute():
        path = root / path
    fs: list[dict[str, Any]] = []
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec.get("schema") != "fa3.model-router.current-host-receipt.v1" or rec.get("gate_id") != GATE_ID:
            fs.append(finding("MR-HOST-001", "receipt schema/gate binding mismatch"))
        if rec.get("authority") != AUTHORITY_ID or rec.get("result") != "PASS" or rec.get("provider_neutral") is not True:
            fs.append(finding("MR-HOST-002", "receipt does not prove provider-neutral Model Router authority PASS"))
        if rec.get("physical_backend_pinned") is not False or rec.get("physical_model_pinned") is not False:
            fs.append(finding("MR-HOST-003", "receipt claims a canonical physical provider/model pin"))
        routes = set(rec.get("logical_routes", []))
        if not REQUIRED_ROUTES.issubset(routes):
            fs.append(finding("MR-HOST-004", "required PageIndex logical routes missing", routes=sorted(routes)))
        checks = rec.get("checks", {})
        for key in REQUIRED_CHECKS:
            if checks.get(key) is not True:
                fs.append(finding("MR-HOST-005", "required current-host check missing", check=key))
        endpoint = str(rec.get("endpoint", ""))
        if not (endpoint.startswith("http://127.0.0.1:") or endpoint.startswith("http://localhost:") or endpoint.startswith("http://[::1]:")):
            fs.append(finding("MR-HOST-006", "current-host endpoint is not loopback"))
        try:
            captured = dt.datetime.fromisoformat(str(rec.get("captured_at", "")).replace("Z", "+00:00"))
            age = dt.datetime.now(dt.timezone.utc) - captured.astimezone(dt.timezone.utc)
            if age < dt.timedelta(0) or age > dt.timedelta(hours=24):
                raise ValueError("stale")
        except Exception:
            fs.append(finding("MR-HOST-007", "receipt timestamp stale/invalid"))
        try:
            head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            if rec.get("repository_head") != head:
                fs.append(finding("MR-HOST-008", "receipt is not bound to checkout HEAD"))
        except Exception:
            fs.append(finding("MR-HOST-009", "checkout HEAD could not be verified"))
        resolutions = rec.get("route_resolutions", {})
        if not isinstance(resolutions, dict) or any(not isinstance(resolutions.get(r), dict) for r in REQUIRED_ROUTES):
            fs.append(finding("MR-HOST-010", "route resolution evidence incomplete"))
    except Exception as exc:
        fs.append(finding("MR-HOST-000", "current-host receipt missing/unreadable", error=repr(exc)))

    report = {
        "schema": "fa3.model-router-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not fs else "FAIL",
        "findings": fs,
        "global_promotion_claim": False,
    }
    report_path = root / "reports/model-router-current-host-gate-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--receipt")
    args = ap.parse_args()
    report = gate(Path(args.root), Path(args.receipt) if args.receipt else None)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
