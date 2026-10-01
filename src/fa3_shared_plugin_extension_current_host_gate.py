#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CONFORMANCE = "canonical/FA3-SHARED-PLUGIN-EXTENSION-CURRENT-HOST-CONFORMANCE-001.json"
DEFAULT_RECEIPT = "evidence/receipts/shared-plugin-extension-current-host.json"
EXPECTED_SCHEMA = "fa3.shared-plugin-extension-current-host-receipt.v1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    conf = _load(root / CONFORMANCE)
    receipt_file = receipt_path or (root / DEFAULT_RECEIPT)
    if not receipt_file.is_file():
        return {
            "schema": "fa3.shared-plugin-extension-current-host-gate-report.v1",
            "result": "BLOCKED",
            "reason": "PHYSICAL_CURRENT_HOST_RECEIPT_MISSING",
            "production_promotion": False,
        }
    r = _load(receipt_file)
    checks = {
        "schema": r.get("schema") == EXPECTED_SCHEMA,
        "physical_host": r.get("physical_host") is True,
        "same_component_two_apps": r.get("same_component_two_apps") is True,
        "app_toggle": r.get("ai_toggle_proof", {}).get("application") is True,
        "module_toggle": r.get("ai_toggle_proof", {}).get("module") is True,
        "component_toggle": r.get("ai_toggle_proof", {}).get("component") is True,
        "capability_toggle": r.get("ai_toggle_proof", {}).get("capability") is True,
        "global_toggle": r.get("ai_toggle_proof", {}).get("global") is True,
        "direct_provider_negative": r.get("negative_proof", {}).get("direct_provider_rejected") is True,
        "silent_fallback_negative": r.get("negative_proof", {}).get("silent_fallback_rejected") is True,
        "automatic_activation_negative": r.get("negative_proof", {}).get("automatic_activation_rejected") is True,
        "coexistence": r.get("software_coexistence_pass") is True,
        "hardware_safety": r.get("hardware_safety_envelope_pass") is True,
        "rollback": r.get("rollback_pass") is True,
        "result": r.get("result") == "PASS",
        "conformance_requires_physical": conf.get("physical_proof_required") is True,
    }
    failed = [k for k, ok in checks.items() if not ok]
    return {
        "schema": "fa3.shared-plugin-extension-current-host-gate-report.v1",
        "result": "PASS" if not failed else "FAIL",
        "failed": failed,
        "checks": checks,
        "production_promotion": not failed,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--receipt", type=Path)
    a = p.parse_args()
    r = gate(a.root, a.receipt)
    print(json.dumps(r, indent=2))
    return 0 if r["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
