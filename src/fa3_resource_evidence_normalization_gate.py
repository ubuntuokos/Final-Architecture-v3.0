#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

HOST_ATTESTATION = Path("canonical/FA3-HOST-ATTESTATION-001.json")
COMPUTE_PROFILE = Path("canonical/FA3-COMPUTE-PROFILE-001.json")
WORKLOAD_ENVELOPE = Path("canonical/FA3-WORKLOAD-RESOURCE-ENVELOPE-001.json")
RESOURCE_CONTRACT = Path("canonical/FA3-RESOURCE-ADMISSION-CONTRACTS-001.json")
EVIDENCE_ENVELOPE = Path("canonical/FA3-EVIDENCE-ENVELOPE-001.json")
RESULT_CONTRACT = Path("canonical/FA3-ENFORCEMENT-RESULT-001.json")
REFERENCE_SCENARIO = Path("canonical/FA3-REFERENCE-SCENARIO-001.json")
GATE_RECORD = Path("canonical/FA3-GATE-RESOURCE-EVIDENCE-NORMALIZATION-001.json")
DECISION = Path("canonical/decisions/FA3-DEC-RESOURCE-EVIDENCE-NORMALIZATION-2026-09-14.json")
REFERENCE_EVIDENCE = Path("evidence/reference/resource-evidence-normalization-2026-09-14.json")
ENFORCEMENT_POLICY = Path("canonical/enforcement-policy.json")

RESULT_EXIT_CODES = {
    "PASS": 0,
    "NOT_APPLICABLE": 0,
    "BLOCKED": 2,
    "PENDING": 2,
    "ERROR": 3,
}
EVIDENCE_STATUSES = {"PASS", "BLOCKED", "PENDING", "NOT_APPLICABLE", "ERROR"}
CURRENT_HOST_CLASSES = {"CURRENT_HOST_RUNTIME", "CURRENT_HOST_ADMISSION"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_payload_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def validate_evidence_envelope(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_id",
        "schema_version",
        "evidence_id",
        "evidence_class",
        "subject",
        "canonical_context",
        "provenance",
        "integrity",
        "result",
        "payload_schema_id",
        "payload",
    }
    missing = sorted(required - set(envelope))
    if missing:
        errors.append("missing:" + ",".join(missing))
        return errors

    if envelope.get("schema_id") != "FA3-EVIDENCE-ENVELOPE-001":
        errors.append("schema_id")
    if envelope.get("evidence_class") in CURRENT_HOST_CLASSES:
        execution = envelope.get("execution_context")
        if not isinstance(execution, dict) or not execution.get("host_attestation_ref"):
            errors.append("current_host_requires_host_attestation_ref")

    canonical = envelope.get("canonical_context", {})
    for key in ("architecture_release", "release_baseline_id", "release_manifest_digest"):
        if not canonical.get(key):
            errors.append(f"canonical_context.{key}")

    provenance = envelope.get("provenance", {})
    for key in ("collector_id", "collector_revision", "generated_at"):
        if not provenance.get(key):
            errors.append(f"provenance.{key}")
    if not isinstance(provenance.get("artifact_digests", []), list):
        errors.append("provenance.artifact_digests")

    result = envelope.get("result", {})
    if result.get("status") not in EVIDENCE_STATUSES:
        errors.append("result.status")
    claims = result.get("claims")
    non_claims = result.get("non_claims")
    if not isinstance(claims, list) or not isinstance(non_claims, list):
        errors.append("result.claims_non_claims")
    elif set(claims) & set(non_claims):
        errors.append("claim_non_claim_overlap")

    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        errors.append("payload_not_object")
    else:
        expected = envelope.get("integrity", {}).get("payload_sha256")
        actual = _canonical_payload_hash(payload)
        if expected != actual:
            errors.append("payload_sha256_mismatch")

    if envelope.get("promotion_authority") is True:
        errors.append("envelope_cannot_be_promotion_authority")
    return errors


def evaluate_resource_admission(
    measured_metrics: dict[str, Any],
    requirements: list[dict[str, Any]],
    hrb_authorization: dict[str, Any] | None,
) -> dict[str, Any]:
    authorization_id = (
        hrb_authorization.get("authorization_id") or hrb_authorization.get("lease_id")
        if isinstance(hrb_authorization, dict) else None
    )
    if not isinstance(hrb_authorization, dict) or hrb_authorization.get("status") != "VALID" or not authorization_id:
        return normalized_result(
            gate_id="FA3-RESOURCE-ADMISSION-CONTRACTS-001",
            mode="ADMISSION",
            result="BLOCKED",
            reason_code="HRB_AUTHORIZATION_INVALID",
            findings=[{"severity": "P0", "status": "FAIL", "message": "A valid HRB admission authorization is required."}],
        )

    failed: list[dict[str, Any]] = []
    for req in requirements:
        metric = req.get("metric")
        op = req.get("operator")
        expected = req.get("value")
        if metric not in measured_metrics:
            failed.append({"metric": metric, "reason": "MISSING_REQUIRED_METRIC"})
            continue
        actual = measured_metrics[metric]
        try:
            if op == ">=":
                passed = actual >= expected
            elif op == "<=":
                passed = actual <= expected
            elif op == "==":
                passed = actual == expected
            elif op == "contains":
                passed = expected in actual
            else:
                passed = False
        except TypeError:
            passed = False
        if passed is not True:
            failed.append({"metric": metric, "reason": "REQUIREMENT_UNMET", "operator": op, "expected": expected, "actual": actual})

    if failed:
        return normalized_result(
            gate_id="FA3-RESOURCE-ADMISSION-CONTRACTS-001",
            mode="ADMISSION",
            result="BLOCKED",
            reason_code="RESOURCE_REQUIREMENT_UNMET",
            findings=[{"severity": "P0", "status": "FAIL", "message": json.dumps(item, sort_keys=True)} for item in failed],
        )
    return normalized_result(
        gate_id="FA3-RESOURCE-ADMISSION-CONTRACTS-001",
        mode="ADMISSION",
        result="PASS",
        reason_code="RESOURCE_ENVELOPE_AND_HRB_PASS",
        findings=[],
    )


def normalized_result(
    *,
    gate_id: str,
    mode: str,
    result: str,
    reason_code: str,
    findings: list[dict[str, Any]] | None = None,
    evidence_refs: list[str] | None = None,
    promotion_effect: str = "NO_GLOBAL_PROMOTION_CLAIM",
) -> dict[str, Any]:
    if result not in RESULT_EXIT_CODES:
        raise ValueError(f"unsupported result: {result}")
    return {
        "schema_id": "FA3-ENFORCEMENT-RESULT-001",
        "schema_version": "1.0.0",
        "gate": {"id": gate_id, "mode": mode},
        "result": result,
        "decision": {
            "reason_code": reason_code,
            "promotion_effect": promotion_effect,
            "exit_code": RESULT_EXIT_CODES[result],
        },
        "findings": findings or [],
        "evidence_refs": evidence_refs or [],
    }


def _reference_envelope(*, current_host: bool = False, tampered: bool = False) -> dict[str, Any]:
    payload = (
        {"fixture": "current-host-component", "resource_admission": "PASS", "component": "FA3-REFERENCE-SCENARIO-001"}
        if current_host
        else {"fixture": "reference", "checks": ["schema", "claims", "non_claims"], "passed": True}
    )
    envelope: dict[str, Any] = {
        "schema_id": "FA3-EVIDENCE-ENVELOPE-001",
        "schema_version": "1.0.0",
        "evidence_id": "FA3-REF-EVIDENCE-CURRENT-HOST-001" if current_host else "FA3-REF-EVIDENCE-001",
        "evidence_class": "CURRENT_HOST_RUNTIME" if current_host else "REFERENCE_CONFORMANCE",
        "subject": {
            "profile_id": "FA3-REFERENCE-SCENARIO-001",
            "provider_id": None,
            "gate_id": "FA3-RESOURCE-EVIDENCE-NORMALIZATION-GATESET-001",
        },
        "canonical_context": {
            "architecture_release": "2026-08-23/v3.0.11",
            "release_baseline_id": "FA3-RELEASE-CAPABILITY-BASELINE-001",
            "release_manifest_digest": "sha256:reference-fixture-not-production",
        },
        "provenance": {
            "collector_id": "FA3-REFERENCE-SCENARIO-001",
            "collector_revision": "1.0.0",
            "generated_at": "2026-09-14T00:00:00Z",
            "artifact_digests": [],
        },
        "integrity": {"payload_sha256": _canonical_payload_hash(payload)},
        "result": {
            "status": "PASS",
            "scope": "COMPONENT" if current_host else "REFERENCE",
            "claims": ["CURRENT_HOST_COMPONENT_PASS"] if current_host else ["REFERENCE_CONFORMANCE_PASS"],
            "non_claims": ["GLOBAL_FA3_PROMOTION", "END_TO_END_ZERO_COPY"],
        },
        "payload_schema_id": "fa3.reference-scenario.payload.v1",
        "payload": payload,
    }
    if current_host:
        envelope["execution_context"] = {
            "host_attestation_ref": "FA3-HOST-ATTESTATION-REF-001",
            "compute_profile_ref": "FA3-COMPUTE-PROFILE-REF-001",
            "workload_resource_envelope_ref": "FA3-WORKLOAD-RESOURCE-ENVELOPE-REF-001",
            "hrb_lease_ref": "FA3-HRB-LEASE-REF-001",
            "diagnostics": {"cu": 12, "tu": 4},
        }
    if tampered:
        envelope["payload"] = dict(payload)
        envelope["payload"]["tampered"] = True
    return envelope


def run_reference_scenarios() -> dict[str, Any]:
    valid_reference_errors = validate_evidence_envelope(_reference_envelope())
    tampered_errors = validate_evidence_envelope(_reference_envelope(tampered=True))
    current = _reference_envelope(current_host=True)
    current_errors = validate_evidence_envelope(current)
    admission = evaluate_resource_admission(
        measured_metrics={"gpu.vram_gib": 24, "pcie.h2d_gbps": 24, "numa.remote_latency_p95_ns": 180},
        requirements=[
            {"metric": "gpu.vram_gib", "operator": ">=", "value": 24},
            {"metric": "pcie.h2d_gbps", "operator": ">=", "value": 20},
            {"metric": "numa.remote_latency_p95_ns", "operator": "<=", "value": 250},
        ],
        hrb_authorization={"status": "VALID", "authorization_id": "FA3-HRB-AUTH-REF-001"},
    )
    missing_current_host = normalized_result(
        gate_id="FA3-REFERENCE-SCENARIO-001",
        mode="CURRENT_HOST",
        result="PENDING",
        reason_code="CURRENT_HOST_EVIDENCE_MISSING",
        promotion_effect="BLOCK_GLOBAL_PROMOTION",
    )
    cases = [
        {
            "id": "REFERENCE_VALID",
            "result": "PASS" if not valid_reference_errors else "FAIL",
            "detail": valid_reference_errors,
        },
        {
            "id": "CURRENT_HOST_MISSING",
            "result": "PASS" if missing_current_host["result"] == "PENDING" and missing_current_host["decision"]["exit_code"] == 2 else "FAIL",
            "detail": missing_current_host,
        },
        {
            "id": "TAMPERED_EVIDENCE",
            "result": "PASS" if "payload_sha256_mismatch" in tampered_errors else "FAIL",
            "detail": tampered_errors,
        },
        {
            "id": "SCOPED_CURRENT_HOST",
            "result": "PASS"
            if not current_errors
            and admission["result"] == "PASS"
            and "GLOBAL_FA3_PROMOTION" in current["result"]["non_claims"]
            else "FAIL",
            "detail": {"envelope_errors": current_errors, "admission": admission, "non_claims": current["result"]["non_claims"]},
        },
    ]
    return {
        "schema": "fa3.reference-scenario-report.v1",
        "result": "PASS" if all(case["result"] == "PASS" for case in cases) else "FAIL",
        "cases": cases,
    }


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, str]] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: str) -> None:
        checks.append({"name": name, "result": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            findings.append({"check": name, "message": detail})

    host = _load(root / HOST_ATTESTATION)
    compute = _load(root / COMPUTE_PROFILE)
    workload = _load(root / WORKLOAD_ENVELOPE)
    resource = _load(root / RESOURCE_CONTRACT)
    evidence = _load(root / EVIDENCE_ENVELOPE)
    result_contract = _load(root / RESULT_CONTRACT)
    scenario_contract = _load(root / REFERENCE_SCENARIO)
    gate_record = _load(root / GATE_RECORD)
    decision = _load(root / DECISION)
    ref_evidence = _load(root / REFERENCE_EVIDENCE)
    enforcement = _load(root / ENFORCEMENT_POLICY)

    check("host_attestation_non_authority", host.get("authority_delta") == 0 and host.get("admission_role") == "EVIDENCE_PROVENANCE_NOT_HARDWARE_MODEL_ALLOWLIST", "Host attestation must prove identity/provenance without becoming a hardware allowlist authority.")
    check("compute_profile_multidimensional", compute.get("profile_semantics", {}).get("multidimensional") is True and compute.get("aggregate_scores", {}).get("single_scalar_admission_authority_forbidden") is True, "Compute Profile must remain multidimensional and forbid scalar admission authority.")
    check("cu_tu_diagnostic_only", compute.get("aggregate_scores", {}).get("cu_tu_allowed_for_diagnostics_or_gui") is True and compute.get("aggregate_scores", {}).get("cu_tu_allowed_for_production_admission") is False, "CU/TU may be diagnostic only and must not authorize production admission.")
    check("resource_all_dimensions_fail_closed", workload.get("evaluation", {}).get("all_requirements_must_pass") is True and workload.get("evaluation", {}).get("missing_metric") == "FAIL" and workload.get("evaluation", {}).get("cross_metric_compensation") is False, "Workload Resource Envelope must fail closed per required dimension.")
    check("hrb_exclusive_authority", resource.get("authoritative_admission_authority") == "FA3-AUTH-HOST-RESOURCE-BROKER-001" and resource.get("provider_self_admission_forbidden") is True, "HRB must remain the exclusive resource admission/placement/lease authority.")
    check("resource_chain_complete", resource.get("required_inputs") == ["FA3-HOST-ATTESTATION-001", "FA3-COMPUTE-PROFILE-001", "FA3-WORKLOAD-RESOURCE-ENVELOPE-001", "HRB_ADMISSION_AUTHORIZATION"], "Resource admission must bind attestation, measured compute, workload requirements and current scope-bound HRB authorization.")
    check("evidence_envelope_non_authority", evidence.get("authority_delta") == 0 and evidence.get("envelope_is_registry_authority") is False and evidence.get("envelope_is_promotion_authority") is False, "Evidence Envelope must normalize typed receipts without replacing Registry/Evidence/Promotion authority.")
    check("evidence_claims_non_claims_required", evidence.get("required_result_fields") == ["status", "scope", "claims", "non_claims"], "Evidence results must explicitly state claims and non-claims.")
    check("enforcement_result_states", result_contract.get("result_states") == ["PASS", "BLOCKED", "PENDING", "NOT_APPLICABLE", "ERROR"], "Enforcement Result must use the normalized five-state contract.")
    check("exit_code_contract", result_contract.get("exit_codes") == {"PASS": 0, "NOT_APPLICABLE": 0, "BLOCKED": 2, "PENDING": 2, "ERROR": 3}, "CLI exit codes must remain flow-control stable.")
    check("warn_not_promotion_state", result_contract.get("warn_semantics") == "FINDING_SEVERITY_ONLY_NOT_GATE_RESULT", "WARN must not be a promotion state.")
    check("reference_scenario_four_cases", scenario_contract.get("required_cases") == ["REFERENCE_VALID", "CURRENT_HOST_MISSING", "TAMPERED_EVIDENCE", "SCOPED_CURRENT_HOST"], "Canonical reference scenario must cover positive, pending, tamper and scoped current-host cases.")
    check("existing_hrb_gate_remains_mandatory", "FA3-HRB-DETERMINISTIC-LOCALITY-GATESET-001" in enforcement.get("mandatory_reference_gates", []), "Existing HRB authority gate must remain mandatory.")
    check("gate_is_p0_fail_closed", gate_record.get("priority") == "P0" and gate_record.get("fail_closed") is True, "Normalization gate must be P0 and fail closed.")
    check("zero_capability_authority_delta", decision.get("new_capabilities") == 0 and decision.get("capability_count_change") == 0 and decision.get("new_architectural_authorities") == 0, "Materialization must add no capability or authority.")
    check("reference_evidence_truth_boundary", ref_evidence.get("repository_conformance") == "PASS" and ref_evidence.get("current_host_production_claim") is False and ref_evidence.get("global_promotion_claim") is False, "Repository reference evidence must not manufacture current-host or global promotion claims.")

    scenario = run_reference_scenarios()
    check("reference_scenarios_executable", scenario.get("result") == "PASS", "All four canonical reference scenarios must pass their expected positive/negative semantics.")

    report = normalized_result(
        gate_id="FA3-RESOURCE-EVIDENCE-NORMALIZATION-GATESET-001",
        mode="CANONICAL_REFERENCE",
        result="PASS" if not findings else "BLOCKED",
        reason_code="RESOURCE_EVIDENCE_NORMALIZATION_PASS" if not findings else "RESOURCE_EVIDENCE_NORMALIZATION_BLOCKED",
        findings=[{"severity": "P0", "status": "FAIL", **item} for item in findings],
        evidence_refs=[str(REFERENCE_EVIDENCE)],
    )
    report.update(
        {
            "checks": checks,
            "passed": sum(item["result"] == "PASS" for item in checks),
            "total": len(checks),
            "reference_scenarios": scenario,
            "capability_delta": 0,
            "architectural_authority_delta": 0,
        }
    )
    out = root / "reports/resource-evidence-normalization-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 resource/evidence/result normalization gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--reference-scenarios-only", action="store_true")
    args = parser.parse_args()
    if args.reference_scenarios_only:
        report = run_reference_scenarios()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "PASS" else 2
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["decision"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
