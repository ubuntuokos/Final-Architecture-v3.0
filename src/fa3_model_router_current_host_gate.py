#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
GATE_ID = "FA3-MODEL-ROUTER-CURRENT-HOST-GATESET-001"
REQUIRED_ROUTES = {"fa3-text-primary","fa3-text-secondary","fa3-pageindex-index","fa3-pageindex-reason"}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    path = receipt_path or root / "evidence/receipts/model-router-current-host.json"
    if not path.is_absolute():
        path = root / path
    findings: list[dict[str, Any]] = []
    try:
        rec = loadj(path)
        if rec.get("schema") != "fa3.model-router-current-host-receipt.v1":
            findings.append(finding("MRH-001", "current-host receipt schema mismatch"))
        if rec.get("authority") != AUTHORITY or rec.get("gate_id") != GATE_ID:
            findings.append(finding("MRH-002", "receipt authority/gate binding mismatch"))
        if rec.get("result") != "PASS" or rec.get("provider_neutral") is not True:
            findings.append(finding("MRH-003", "router current-host result is not provider-neutral PASS"))
        endpoint = str(rec.get("endpoint", ""))
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http","https"} or (parsed.hostname or "").lower() not in {"127.0.0.1","::1","localhost"}:
            findings.append(finding("MRH-004", "router endpoint is not loopback"))
        routes = set(rec.get("logical_routes", []))
        if not REQUIRED_ROUTES.issubset(routes):
            findings.append(finding("MRH-005", "required logical routes are not evidenced", routes=sorted(routes)))
        if rec.get("physical_backend_pinned") is not False or rec.get("physical_model_pinned") is not False or rec.get("runtime_selected") is not True:
            findings.append(finding("MRH-006", "receipt does not prove runtime-selected non-pinned routing"))
        probes = rec.get("route_probes", {})
        bindings = rec.get("route_bindings", {})
        provider_evidence = rec.get("provider_admission_evidence_sha256", {})
        if not isinstance(provider_evidence, dict) or not provider_evidence:
            findings.append(finding("MRH-015", "selected-provider admission evidence binding is missing"))
            provider_evidence = {}
        for route in REQUIRED_ROUTES:
            probe = probes.get(route, {}) if isinstance(probes, dict) else {}
            binding = bindings.get(route, {}) if isinstance(bindings, dict) else {}
            if probe.get("result") != "PASS":
                findings.append(finding("MRH-007", "logical route execution did not PASS", route=route))
            if not binding.get("provider_id") or not binding.get("runtime_id") or not binding.get("model"):
                findings.append(finding("MRH-008", "logical route lacks selected provider/runtime/model provenance", route=route))
            provider_id = str(binding.get("provider_id", "")).strip()
            digest = str(provider_evidence.get(provider_id, "")).strip().lower()
            if provider_id and (len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)):
                findings.append(finding("MRH-015", "logical route provider is not bound to valid current-host admission evidence", route=route, provider_id=provider_id))
            if binding.get("selection") != "RUNTIME_DISCOVERED":
                findings.append(finding("MRH-009", "route binding was not runtime-discovered", route=route))
        try:
            captured = dt.datetime.fromisoformat(str(rec.get("captured_at","")).replace("Z","+00:00"))
            age = dt.datetime.now(dt.timezone.utc) - captured.astimezone(dt.timezone.utc)
            if age < dt.timedelta(0) or age > dt.timedelta(hours=24):
                raise ValueError("stale")
        except Exception:
            findings.append(finding("MRH-010", "router current-host receipt is stale or invalid"))
        try:
            head = subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
            if rec.get("repository_head") != head:
                findings.append(finding("MRH-011", "router current-host receipt is not bound to checkout HEAD"))
        except Exception:
            findings.append(finding("MRH-012", "unable to determine repository HEAD"))
        if rec.get("service_active") is not True or rec.get("selection_receipt_verified") is not True:
            findings.append(finding("MRH-013", "central router service/selection receipt not verified"))
        if rec.get("global_promotion_claim") is not False:
            findings.append(finding("MRH-014", "router receipt overclaims global promotion"))
    except Exception as exc:
        findings.append(finding("MRH-000", "current-host router receipt missing or unreadable", error=repr(exc)))
    return {
        "schema": "fa3.model-router-current-host-gate.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "global_promotion_claim": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--receipt")
    args = ap.parse_args()
    root=Path(args.root).resolve()
    result = gate(root, Path(args.receipt) if args.receipt else None)
    report=root/"reports/model-router-current-host-gate-report.json"
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\\n",encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
