#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_license_rights import evaluate_descriptor, evaluate_release_receipt
from fa3_release_baseline import module_active_capability_count

CAPABILITY_COUNT = module_active_capability_count(__file__)


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def regressions(policy: dict[str, Any]) -> dict[str, Any]:
    base = {
        "schema": "fa3.license-rights-descriptor.v1",
        "subject": {"id": "fixture", "type": "CODE"},
        "source": {"locator": "example/repo", "revision": "a" * 40},
        "license": {
            "declared": "MIT",
            "detected": ["MIT"],
            "concluded": "MIT",
            "effective": "MIT",
        },
        "rights": {
            "modification_allowed": True,
            "redistribution_allowed": True,
            "commercial_use_allowed": True,
        },
        "obligations": {
            "attribution_required": True,
            "source_offer_required": False,
            "entitlement_required": False,
            "unresolved": [],
        },
        "disposition": "ALLOW_WITH_OBLIGATIONS",
        "evidence": ["fixture"],
    }
    positive = evaluate_descriptor(base, policy)

    unknown = json.loads(json.dumps(base))
    unknown["license"]["effective"] = "UNKNOWN"
    unknown_result = evaluate_descriptor(unknown, policy)

    entitlement = json.loads(json.dumps(base))
    entitlement["obligations"]["entitlement_required"] = True
    entitlement_result = evaluate_descriptor(entitlement, policy)

    pending_release = {
        "schema": "fa3.release-license-compliance-receipt.v1",
        "release": {"id": "fixture"},
        "repository_audit": {"status": "PENDING"},
        "sbom": {"spdx_status": "GENERATED", "cyclonedx_status": "GENERATED"},
        "notices": {"third_party_notice_status": "GENERATED"},
        "obligations": {
            "attribution_resolved": True,
            "source_offer_resolved": True,
            "entitlements_resolved": True,
        },
        "counts": {"unknown_license_count": 0, "unresolved_conflict_count": 0},
    }
    pending_result = evaluate_release_receipt(pending_release, policy)

    release_ok = json.loads(json.dumps(pending_release))
    release_ok["repository_audit"]["status"] = "PASS"
    release_result = evaluate_release_receipt(release_ok, policy)

    cases = {
        "descriptor_positive": positive["result"] == "PASS" and positive["admitted_for_release"] is True,
        "unknown_license_refused": unknown_result["result"] == "FAIL",
        "missing_entitlement_ref_refused": entitlement_result["result"] == "FAIL",
        "pending_retroactive_audit_blocks_release": pending_result["result"] == "FAIL",
        "complete_release_receipt_positive": release_result["result"] == "PASS",
    }
    return {
        "result": "PASS" if all(cases.values()) else "FAIL",
        "cases": [{"case_id": k, "status": "PASS" if v else "FAIL"} for k, v in cases.items()],
    }


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    paths = {
        "policy": "canonical/license-rights-policy.json",
        "audit": "canonical/license-rights-audit-status.json",
        "profile": "canonical/profiles/FA3-LICENSE-RIGHTS-001.json",
        "contracts": "canonical/contracts/FA3-LICENSE-RIGHTS-CONTRACTS-001.json",
        "decision": "canonical/decisions/FA3-DEC-LICENSE-RIGHTS-AUTHORITY-2026-09-30.json",
        "decision_assessment": "canonical/assessments/FA3-LICENSE-RIGHTS-DECISION-ASSESSMENT-2026-09-30.json",
        "application_intent": "canonical/intents/FA3-LICENSE-RIGHTS-APPLICATION-INTENT-001.json",
        "reuse_assessment": "canonical/assessments/FA3-LICENSE-RIGHTS-REUSE-ASSESSMENT-001.json",
        "gate": "canonical/FA3-GATE-LICENSE-RIGHTS-001.json",
        "descriptor_schema": "canonical/schemas/license-rights-descriptor.v1.json",
        "release_schema": "canonical/schemas/release-license-compliance-receipt.v1.json",
        "automated_code_policy": "canonical/supply-chain-license-policy.json",
    }
    data: dict[str, dict[str, Any]] = {}
    for key, rel in paths.items():
        try:
            data[key] = loadj(root / rel)
        except Exception as exc:
            findings.append(finding("LR-000", "required license-rights materialization unreadable", path=rel, error=repr(exc)))

    for rel in ("LICENSE", "NOTICE", "TRADEMARKS.md", "COMMERCIAL-LICENSING.md", "REUSE.toml", "LICENSES/Apache-2.0.txt"):
        if not (root / rel).is_file():
            findings.append(finding("LR-001", "required repository licensing file missing", path=rel))

    if not findings:
        policy = data["policy"]
        profile = data["profile"]
        contracts = data["contracts"]
        audit = data["audit"]
        gate_record = data["gate"]

        if policy.get("id") != "FA3-LICENSE-RIGHTS-POLICY-001" or policy.get("status") != "CANONICAL_FAIL_CLOSED":
            findings.append(finding("LR-010", "license-rights policy identity or fail-closed status drift"))
        if policy.get("third_party_relicense_forbidden") is not True:
            findings.append(finding("LR-011", "third-party no-relicense invariant missing"))
        if policy.get("code_model_dataset_asset_service_rights_are_distinct") is not True:
            findings.append(finding("LR-012", "rights-domain separation invariant missing"))
        if policy.get("fa3_original_default_license") != "Apache-2.0":
            findings.append(finding("LR-013", "FA3 original default license drift"))
        fail_closed = policy.get("fail_closed", {})
        required_fail_closed = (
            "unknown_license",
            "unknown_right",
            "unknown_redistribution_right",
            "unknown_commercial_use_right",
            "unresolved_license_conflict",
            "missing_entitlement_when_required",
        )
        if not all(fail_closed.get(x) is True for x in required_fail_closed):
            findings.append(finding("LR-014", "required fail-closed policy flags missing"))

        if profile.get("id") != "FA3-LICENSE-RIGHTS-001" or profile.get("capability_count") != CAPABILITY_COUNT:
            findings.append(finding("LR-020", "license-rights profile capability reconciliation drift"))
        if profile.get("new_capability") is not False or profile.get("new_architectural_authority") is not False:
            findings.append(finding("LR-021", "license-rights profile illegally expands architecture baseline"))
        if contracts.get("capability_count") != CAPABILITY_COUNT:
            findings.append(finding("LR-022", "license-rights contracts capability count drift"))

        if data["descriptor_schema"].get("$id") != "fa3.license-rights-descriptor.v1":
            findings.append(finding("LR-030", "rights descriptor schema identity drift"))
        if data["release_schema"].get("$id") != "fa3.release-license-compliance-receipt.v1":
            findings.append(finding("LR-031", "release receipt schema identity drift"))

        if data["automated_code_policy"].get("id") != "FA3-SCS-LICENSE-POLICY-001":
            findings.append(finding("LR-040", "automated code-license policy binding drift"))

        if gate_record.get("gateset_id") != "FA3-SUPPLY-RUNTIME-HARDENING-GATESET-001" or gate_record.get("fail_closed") is not True:
            findings.append(finding("LR-050", "license-rights subgate binding drift"))

        assessment = data["decision_assessment"]
        if assessment.get("schema") != "fa3.decision-fabric-assessment.v1" or "FA3-LICENSE-RIGHTS-001" not in assessment.get("covered_ids", []):
            findings.append(finding("LR-051", "Decision Fabric applicability assessment binding missing"))
        if assessment.get("assessment") != "NOT_APPLICABLE":
            findings.append(finding("LR-052", "license/right admission must not be delegated to Decision Fabric"))

        intent = data["application_intent"]
        reuse = data["reuse_assessment"]
        if intent.get("schema") != "fa3.application-intent.v1" or intent.get("project_id") != "FA3-LICENSE-RIGHTS-001":
            findings.append(finding("LR-053", "License & Rights ApplicationIntent binding drift"))
        if reuse.get("schema") != "fa3.reuse-assessment.v1" or reuse.get("result") != "PASS" or "FA3-LICENSE-RIGHTS-001" not in reuse.get("covered_ids", []):
            findings.append(finding("LR-054", "License & Rights reuse assessment missing or not PASS"))

        # Pending historical audit is an acceptable materialization state only while
        # release eligibility remains fail-closed.
        if audit.get("status") == "PENDING_RETROACTIVE_AUDIT":
            if audit.get("release_eligible") is not False or audit.get("global_runtime_promotion_claim") is not False:
                findings.append(finding("LR-060", "pending retroactive audit must block release/promotion"))
        elif audit.get("status") == "PASS":
            if audit.get("release_eligible") is not True:
                findings.append(finding("LR-061", "completed rights audit does not enable release eligibility"))
        else:
            findings.append(finding("LR-062", "unknown rights audit state"))

    reg = regressions(data.get("policy", {})) if "policy" in data else {"result": "FAIL", "cases": []}
    if reg["result"] != "PASS":
        findings.append(finding("LR-070", "license-rights fail-closed regression matrix failed"))

    report = {
        "schema": "fa3.license-rights-gate-report.v1",
        "gate_id": "FA3-GATE-LICENSE-RIGHTS-001",
        "gateset_id": "FA3-SUPPLY-RUNTIME-HARDENING-GATESET-001",
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "regressions": reg,
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "release_eligible": data.get("audit", {}).get("release_eligible", False),
        "retroactive_audit_status": data.get("audit", {}).get("status", "UNREADABLE"),
    }
    out = root / "reports/license-rights-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
