#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

GATESET_ID = "FA3-STTIF-GATESET-001"
PROFILE_ID = "FA3-STTIF-001"
CONTRACT_ID = "FA3-STTIF-CONTRACTS-001"
DECISION_ID = "FA3-DEC-STTIF-LTX-TILED-FUSION-2026-10-01"
DONORS = {
    "FA3-DONOR-LTX2-001",
    "FA3-DONOR-COMFYUI-LTXVIDEO-001",
    "FA3-DONOR-LTX-TILED-FUSION-DOC-001",
}
AUTO_FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def validate(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-STTIF-001.json",
        "contract": root / "canonical/contracts/FA3-STTIF-CONTRACTS-001.json",
        "intent": root / "canonical/intents/FA3-STTIF-APPLICATION-INTENT-001.json",
        "assessment": root / "canonical/assessments/FA3-STTIF-REUSE-ASSESSMENT-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-STTIF-LTX-TILED-FUSION-2026-10-01.json",
        "gate": root / "canonical/FA3-GATE-STTIF-001.json",
        "enforcement": root / "canonical/sttif-enforcement.json",
        "reference": root / "canonical/references/FA3-LTX25-TILED-FUSION-UPSTREAM-REFERENCE-2026-10-01.json",
        "impact": root / "canonical/current-host-impact/FA3-CH-IMPACT-STTIF-20261001.json",
        "links": root / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
        "registry": root / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
        "ltx_rights": root / "canonical/license-rights/descriptors/FA3-DONOR-LTX2-UPSTREAM-001.json",
        "comfy_rights": root / "canonical/license-rights/descriptors/FA3-DONOR-COMFYUI-LTXVIDEO-UPSTREAM-001.json",
        "gate_registry": root / "canonical/FA3-GATE-REGISTRY-001.json",
        "policy": root / "canonical/enforcement-policy.json",
        "engine": root / "src/fa3_sttif.py",
    }
    for name, path in paths.items():
        if not path.is_file():
            findings.append(_finding("STTIF-001", "required file missing", name=name, path=path.as_posix()))
    if findings:
        return findings

    profile = _load(paths["profile"])
    contract = _load(paths["contract"])
    intent = _load(paths["intent"])
    assessment = _load(paths["assessment"])
    decision = _load(paths["decision"])
    gate = _load(paths["gate"])
    enforcement = _load(paths["enforcement"])
    reference = _load(paths["reference"])
    impact = _load(paths["impact"])
    links = _load(paths["links"])
    registry = _load(paths["registry"])
    ltx_rights = _load(paths["ltx_rights"])
    comfy_rights = _load(paths["comfy_rights"])
    gate_registry = _load(paths["gate_registry"])
    policy = _load(paths["policy"])

    checks = [
        (profile.get("id") == PROFILE_ID and profile.get("capability_count") == 175, "STTIF-002", "profile baseline mismatch"),
        (profile.get("new_capability") is False and profile.get("new_architectural_authority") is False, "STTIF-003", "profile changes capability or authority baseline"),
        (set(profile.get("capability_bindings", [])) == {"CAP-159", "CAP-160", "CAP-161", "CAP-163"}, "STTIF-004", "profile capability bindings drift"),
        (contract.get("id") == CONTRACT_ID and contract.get("profile") == PROFILE_ID and contract.get("capability_count") == 175, "STTIF-005", "contract identity/baseline mismatch"),
        (contract.get("donor_separation", {}).get("copied_external_source_code") is False and contract.get("donor_separation", {}).get("copied_external_model_artifacts") is False, "STTIF-006", "external reuse boundary weakened"),
        (intent.get("project_id") == PROFILE_ID and intent.get("declared_new_capabilities") == [] and intent.get("proposed_authority_roles") == [], "STTIF-007", "ApplicationIntent authority/capability delta invalid"),
        (assessment.get("result") == "PASS" and assessment.get("capability_count_after") == 175 and assessment.get("current_host_runtime_promotion_claim") is False, "STTIF-008", "ReuseAssessment invalid"),
        (decision.get("id") == DECISION_ID and decision.get("compatibility", {}).get("capability_delta") == 0 and decision.get("compatibility", {}).get("authority_delta") == 0, "STTIF-009", "decision baseline delta invalid"),
        (gate.get("gateset_id") == GATESET_ID and gate.get("static_pass_promotes_provider_runtime") is False, "STTIF-010", "gate runtime boundary invalid"),
        (enforcement.get("gate_id") == GATESET_ID and enforcement.get("capability_count") == 175 and enforcement.get("current_host_runtime_promotion_claim") is False, "STTIF-011", "enforcement baseline/runtime semantics invalid"),
        (impact.get("status") == "NO_RUNTIME_IMPACT" and impact.get("physical_requalification_required") is False and impact.get("global_promotion_claim") is False, "STTIF-012", "Current Host impact must stay non-promoting"),
        (reference.get("status") == "REFERENCE_ONLY" and reference.get("fa3_interpretation", {}).get("copied_source_code") is False and reference.get("fa3_interpretation", {}).get("runtime_admission") is False, "STTIF-013", "upstream reference boundary invalid"),
        (ltx_rights.get("disposition") == "REFERENCE_ONLY" and comfy_rights.get("disposition") == "REFERENCE_ONLY", "STTIF-014", "upstream License & Rights boundary invalid"),
        (GATESET_ID in gate_registry.get("mandatory_reference_gates", []), "STTIF-015", "STTIF missing from canonical gate registry"),
        (gate_registry.get("mandatory_reference_gates") == policy.get("mandatory_reference_gates"), "STTIF-016", "gate registry and enforcement-policy mirrors differ"),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append(_finding(code, message))

    by_id = {entry.get("donor_id"): entry for entry in registry.get("entries", [])}
    for donor_id in sorted(DONORS):
        row = by_id.get(donor_id)
        if not row:
            findings.append(_finding("STTIF-017", "required donor reference missing", donor_id=donor_id))
            continue
        if row.get("status") != "ACCEPTED_REFERENCE":
            findings.append(_finding("STTIF-018", "donor is not reference-only accepted intake", donor_id=donor_id))
        if any(row.get(flag) is not False for flag in AUTO_FLAGS):
            findings.append(_finding("STTIF-019", "donor automatic action or authority flag enabled", donor_id=donor_id))

    shared = next((x for x in links.get("shared_capabilities", []) if x.get("id") == "FA3-SHARED-STTIF-001"), None)
    if not shared:
        findings.append(_finding("STTIF-020", "shared capability consumer binding missing"))
    elif shared.get("authority") is not False or shared.get("current_host_impact", {}).get("classification") != "NO_RUNTIME_IMPACT":
        findings.append(_finding("STTIF-021", "shared capability authority/current-host boundary invalid"))

    usage_donors = {x.get("donor_id") for x in links.get("donor_usage_records", []) if x.get("status") == "ACTIVE"}
    if not DONORS.issubset(usage_donors):
        findings.append(_finding("STTIF-022", "active donor usage traceability incomplete", missing=sorted(DONORS - usage_donors)))

    engine_text = paths["engine"].read_text(encoding="utf-8").lower()
    if "import ltx" in engine_text or "import comfy" in engine_text:
        findings.append(_finding("STTIF-023", "FA3-native engine has upstream runtime import"))

    return findings


def gate(root: Path) -> dict[str, Any]:
    findings = validate(root)
    return {
        "schema": "fa3.sttif-gate-report.v1",
        "gate_id": GATESET_ID,
        "result": "FAIL" if findings else "PASS",
        "findings": findings,
        "capability_count": 175,
        "capability_delta": 0,
        "authority_delta": 0,
        "current_host_runtime_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="reports/sttif-gate-report.json")
    args = parser.parse_args()
    report = gate(Path(args.root))
    output = Path(args.root) / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
