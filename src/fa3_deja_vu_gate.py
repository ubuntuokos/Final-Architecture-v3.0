#!/usr/bin/env python3
"""Static non-promotion gate for the optional deja-vu memory provider."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_SHA = "73ad34e5fdc2b0c245a0fb69b65a17f3cbb123c8"
PROVIDER_ID = "FA3-PROVIDER-DEJA-VU-001"
GATE_ID = "FA3-DEJA-RECALL-GATESET-001"


def inspect(root: Path) -> list[str]:
    def read(path: str) -> dict:
        return json.loads((root / path).read_text(encoding="utf-8"))

    findings: list[str] = []
    provider = read("canonical/providers/FA3-PROVIDER-DEJA-VU-001.json")
    policy = read("canonical/deja-vu-recall-enforcement.json")
    registry = read("canonical/mcp-capability-registry.json")
    donors = read("canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json")

    if provider.get("id") != PROVIDER_ID or provider.get("upstream", {}).get("immutable_commit") != EXPECTED_SHA:
        findings.append("DEJA-001: pinned upstream identity mismatch")
    if provider.get("new_capability") is not False or provider.get("new_architectural_authority") is not False:
        findings.append("DEJA-002: provider claims new authority/capability")
    admission = provider.get("admission", {})
    if admission.get("production_admitted") is not False or admission.get("status") != "PENDING_CURRENT_HOST":
        findings.append("DEJA-003: unsupported production admission claim")
    if policy.get("id") != GATE_ID or policy.get("production_runtime_status") != "PENDING_CURRENT_HOST":
        findings.append("DEJA-004: gate/promotion drift")
    if policy.get("authority_delta") != 0 or policy.get("capability_delta") != 0:
        findings.append("DEJA-005: authority/capability drift")
    if policy.get("fail_closed") is not True:
        findings.append("DEJA-006: gate must fail closed")
    rows = [c for c in registry.get("capabilities", []) if c.get("capability_id") == "fa3.memory.retrieve"]
    if len(rows) != 1:
        findings.append("DEJA-007: existing memory capability missing/duplicated")
    else:
        bindings = [p for p in rows[0].get("providers", []) if p.get("provider_id") == PROVIDER_ID]
        if len(bindings) != 1:
            findings.append("DEJA-008: provider binding missing/duplicated")
        else:
            p = bindings[0]
            if (p.get("state") != "PENDING_CURRENT_HOST"
                or p.get("adapter_id") != "fa3.adapter.deja-vu.retrieve"
                or p.get("gate_id") != GATE_ID
                or p.get("policy_mode") != "external_resolver"
                or p.get("policy_scope_arguments") != ["project_id"]
                or p.get("require_scoped_arguments") is not True
                or p.get("receipt_audit_required") is not True
                or p.get("require_policy_purpose") is not True
                or p.get("evidence_ref") is not None):
                findings.append("DEJA-009: unsafe or prematurely admitted binding")
    matches = [
        x for x in donors.get("entries", [])
        if x.get("source", {}).get("normalized_key") == "github:vshulcz/deja-vu"
    ]
    if len(matches) != 1 or matches[0].get("automatic_activation") is not False:
        findings.append("DEJA-010: donor missing/duplicate or auto-activation drift")
    if registry.get("capability_delta") != 0 or registry.get("authority_delta") != 0:
        findings.append("DEJA-011: gateway delta mismatch")
    return findings


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    a = p.parse_args()
    findings = inspect(a.root)
    print(json.dumps({
        "gate_id": GATE_ID,
        "static_result": "PASS" if not findings else "FAIL",
        "production_admission": "PENDING_CURRENT_HOST",
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "findings": findings,
    }, indent=2))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
