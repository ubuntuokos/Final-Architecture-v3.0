#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-AI-SEC-VALIDATION-001"
CONTRACT_ID = "FA3-AI-SECURITY-VALIDATION-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-AI-INFRA-GUARD-001"
DECISION_ID = "FA3-DEC-AI-INFRA-GUARD-2026-08-30"
REFERENCE_ID = "FA3-AI-INFRA-GUARD-UPSTREAM-REFERENCE-2026-08-31"
GATE_ID = "FA3-AI-INFRA-GUARD-GATESET-001"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "v4.6.0"
REFERENCE_COMMIT = "e8931cc68001b66ad024fd87ef07394e9e96524a"
MANDATORY_CONSTRAINT = "AI-Infra-Guard SHALL NOT become an FA3 identity, authorization, MCP/capability-gateway, model-routing, host-resource, evidence/provenance, secrets, network-egress, artifact-trust, promotion or canonical-registry authority."

P0_INVARIANTS = [
    "AISEC_DETERMINISTIC_FIRST_SECURITY_VALIDATION",
    "AISEC_LLM_OUTPUT_NOT_SECURITY_AUTHORITY",
    "AISEC_SCAN_COVERAGE_EXPLICIT",
    "AISEC_RUNTIME_REACHABLE_ARTIFACT_COMPLETENESS",
    "AISEC_SECURITY_ENGINES_INDEPENDENTLY_VERSIONED",
    "AISEC_RULESET_VERSION_AND_DIGEST_REQUIRED",
    "AISEC_TYPED_SCHEMA_VALIDATED_SECURITY_RULES",
    "AISEC_STATIC_DYNAMIC_ADVERSARIAL_EVIDENCE_SEPARATED",
    "AISEC_SECURITY_TEST_CAPABILITY_SCOPED",
    "AISEC_SCAN_TARGET_AND_EXTERNAL_RESPONSES_UNTRUSTED",
    "AISEC_SARIF_PROJECTION_NON_CANONICAL",
    "AISEC_SECURITY_VERDICT_EVIDENCE_BOUND",
    "AISEC_MUTATION_BYPASS_REGRESSION_REQUIRED",
    "AISEC_MODEL_PROVIDER_IDENTITY_VERIFICATION_REQUIRED",
    "AISEC_UNRESOLVED_CRITICAL_FINDING_BLOCKS_PROMOTION",
    "AISEC_SCANNER_CONFORMANCE_AND_NON_AUTHORITY_REQUIRED",
]

EXPECTED_BOUNDARIES = {
    "identity": "EXISTING_FA3_IDENTITY_AUTHORITY_ONLY",
    "authorization_policy": "FA3-AUTH-SECURITY-GOV-001",
    "mcp_tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
    "model_routing": "FA3-AUTH-MODEL-ROUTER-001",
    "host_resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
    "secrets": "EXISTING_FA3_SECRETS_AUTHORITY_ONLY",
    "network_egress": "EXISTING_FA3_NETWORK_EGRESS_AUTHORITY_ONLY",
    "artifact_trust": "FA3-REG-ARTIFACT-MODEL-001",
    "registry": "FA3-REGISTRY-001",
    "promotion": "EXISTING_FA3_PROMOTION_AUTHORITY_ONLY",
}

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}

def deterministic_first_valid(*, deterministic_checks_run: bool, deterministic_evidence_ids: list[str],
                              llm_analysis_present: bool, llm_is_sole_verdict_basis: bool) -> bool:
    return bool(deterministic_checks_run and deterministic_evidence_ids and not llm_is_sole_verdict_basis)

def llm_non_authority_valid(*, llm_output_treated_as_untrusted: bool,
                            llm_can_authorize: bool, llm_can_promote: bool) -> bool:
    return bool(llm_output_treated_as_untrusted and not llm_can_authorize and not llm_can_promote)

def coverage_valid(*, examined_artifacts: list[str], excluded_artifacts: list[str],
                   unsupported_artifacts: list[str], scan_depth: str,
                   analysis_modes: list[str]) -> bool:
    return bool(examined_artifacts and scan_depth and analysis_modes
                and excluded_artifacts is not None and unsupported_artifacts is not None)

def runtime_surface_complete(*, runtime_reachable_artifacts: list[str], examined_artifacts: list[str],
                             unsupported_artifacts: list[str], verdict: str) -> bool:
    reachable = set(runtime_reachable_artifacts)
    examined = set(examined_artifacts)
    unsupported = set(unsupported_artifacts)
    if verdict == "PASS":
        return bool(reachable.issubset(examined) and not (reachable & unsupported))
    return True

def engines_versioned(*, engines: dict[str, str], required_modes: list[str]) -> bool:
    return bool(required_modes and all(mode in engines and engines[mode] for mode in required_modes))

def ruleset_identity_valid(*, ruleset_id: str, version: str, digest: str) -> bool:
    return bool(ruleset_id and version and digest.startswith("sha256:") and len(digest) == 71)

def rule_schema_valid(*, rule_id: str, severity: str, schema_validated: bool) -> bool:
    return bool(rule_id and severity in {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"} and schema_validated)

def evidence_modes_valid(*, static_ids: list[str], dynamic_ids: list[str], adversarial_ids: list[str],
                         required_modes: list[str]) -> bool:
    mode_map = {"STATIC": static_ids, "DYNAMIC": dynamic_ids, "ADVERSARIAL": adversarial_ids}
    return bool(required_modes and all(mode_map.get(mode) for mode in required_modes))

def capability_scope_valid(*, caller_identity: str, capability_scope: list[str], policy_authority: str,
                           policy_decision: str, arbitrary_shell: bool, unrestricted_egress: bool) -> bool:
    return bool(caller_identity and capability_scope and policy_authority == "FA3-AUTH-SECURITY-GOV-001"
                and policy_decision == "ALLOW" and not arbitrary_shell and not unrestricted_egress)

def untrusted_input_valid(*, scan_target_untrusted: bool, remote_response_untrusted: bool,
                          llm_response_untrusted: bool) -> bool:
    return bool(scan_target_untrusted and remote_response_untrusted and llm_response_untrusted)

def sarif_projection_valid(*, canonical_internal_schema: str, sarif_is_projection: bool,
                           sarif_is_canonical_authority: bool) -> bool:
    return bool(canonical_internal_schema == "FA3_SECURITY_EVIDENCE"
                and sarif_is_projection and not sarif_is_canonical_authority)

def verdict_evidence_bound(*, scanner_id: str, scanner_version: str, ruleset_digest: str,
                           target_digest: str, coverage_id: str, evidence_ids: list[str],
                           verdict: str) -> bool:
    return bool(scanner_id and scanner_version and ruleset_digest.startswith("sha256:")
                and target_digest.startswith("sha256:") and coverage_id and evidence_ids
                and verdict in {"PASS", "FAIL", "INCONCLUSIVE"})

def mutation_regression_valid(*, known_positive_count: int, known_negative_count: int,
                              bypass_case_count: int, mutation_case_count: int, replayable: bool) -> bool:
    return bool(known_positive_count > 0 and known_negative_count > 0 and bypass_case_count > 0
                and mutation_case_count > 0 and replayable)

def model_provider_identity_valid(*, requested_identity: str, observed_identity: str,
                                  attestation_valid: bool, mismatch_allowed: bool) -> bool:
    return bool(requested_identity and observed_identity and attestation_valid
                and requested_identity == observed_identity and not mismatch_allowed)

def promotion_guard_valid(*, unresolved_critical_findings: int, scanner_ui_override: bool,
                          canonical_policy_decision: str) -> bool:
    return bool(unresolved_critical_findings == 0 and not scanner_ui_override
                and canonical_policy_decision == "ALLOW")

def scanner_conformance_valid(*, regression_status: str, coverage_status: str,
                              scanner_is_architectural_authority: bool,
                              scanner_is_promotion_authority: bool,
                              capability_count: int) -> bool:
    return bool(regression_status == "PASS" and coverage_status == "PASS"
                and not scanner_is_architectural_authority and not scanner_is_promotion_authority
                and capability_count == CAPABILITY_COUNT)

def provider_shape_valid(provider: dict[str, Any]) -> bool:
    required_classes = {
        "OPTIONAL_PROVIDER", "OPTIONAL_SECURITY_VALIDATION_PROVIDER", "AI_RED_TEAM_PROVIDER",
        "MCP_SECURITY_SCANNER", "AGENT_SECURITY_SCANNER", "SKILL_SECURITY_SCANNER",
        "AI_INFRA_VULNERABILITY_SCANNER", "PROMPT_SECURITY_EVALUATOR",
        "PROVIDER_API_INTEGRITY_SCANNER", "ARCHITECTURAL_PATTERN_SOURCE",
    }
    return bool(
        provider.get("id") == PROVIDER_ID
        and provider.get("parent_profile") == PROFILE_ID
        and provider.get("status") == "ACCEPTED_REFERENCE"
        and required_classes.issubset(set(provider.get("classification", [])))
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT"
        and provider.get("global_runtime_promotion_required_when_disabled") is False
        and provider.get("authority_boundaries") == EXPECTED_BOUNDARIES
        and provider.get("normative_constraint") == MANDATORY_CONSTRAINT
    )

def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-AI-SEC-VALIDATION-001.json",
        "contracts": root / "canonical/contracts/FA3-AI-SECURITY-VALIDATION-CONTRACTS-001.json",
        "provider": root / "canonical/providers/FA3-PROVIDER-AI-INFRA-GUARD-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-AI-INFRA-GUARD-2026-08-30.json",
        "reference": root / "canonical/references/FA3-AI-INFRA-GUARD-UPSTREAM-REFERENCE-2026-08-31.json",
        "enforcement": root / "canonical/ai-infra-guard-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding("AISEC-REF-001", f"Missing required AI security artifact: {name}",
                                     path=str(path.relative_to(root))))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile = _load(paths["profile"])
    contracts = _load(paths["contracts"])
    provider = _load(paths["provider"])
    decision = _load(paths["decision"])
    reference = _load(paths["reference"])
    enforcement = _load(paths["enforcement"])
    policy = _load(paths["policy"])

    if not provider_shape_valid(provider):
        findings.append(_finding("AISEC-REF-002", "AI-Infra-Guard provider boundary/classification drift"))
    if not (
        profile.get("id") == PROFILE_ID and profile.get("status") == "CANONICAL"
        and profile.get("priority") == "P0" and profile.get("parent_profile") == "FA3-SCS-001"
        and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("invariants") == P0_INVARIANTS
        and CONTRACT_ID in profile.get("contracts", [])
    ):
        findings.append(_finding("AISEC-REF-003", "AI security profile invariant drift"))
    if not (
        contracts.get("id") == CONTRACT_ID and contracts.get("profile_id") == PROFILE_ID
        and contracts.get("provider_neutral") is True
        and contracts.get("new_capability") is False
        and contracts.get("new_architectural_authority") is False
        and contracts.get("capability_count") == CAPABILITY_COUNT
        and "SecurityScanCoverage" in contracts.get("contracts", [])
        and "ProviderAPIIntegrityAssessment" in contracts.get("contracts", [])
        and "SecurityRegressionEvidence" in contracts.get("contracts", [])
    ):
        findings.append(_finding("AISEC-REF-004", "AI security contract-family invariant drift"))
    if not (
        decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID and decision.get("profile_id") == PROFILE_ID
        and decision.get("contract_id") == CONTRACT_ID and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("mandatory_canonical_rules") == P0_INVARIANTS
        and decision.get("mandatory_constraint") == MANDATORY_CONSTRAINT
    ):
        findings.append(_finding("AISEC-REF-005", "AI security canonical decision drift"))
    stable = reference.get("stable_reference", {})
    disp = reference.get("fa3_disposition", {})
    if not (
        reference.get("id") == REFERENCE_ID and reference.get("provider_id") == PROVIDER_ID
        and reference.get("repository") == "Tencent/AI-Infra-Guard"
        and stable.get("release") == REFERENCE_RELEASE and stable.get("commit_sha") == REFERENCE_COMMIT
        and disp.get("floating_main_allowed_as_promotion_evidence") is False
        and disp.get("scanner_finding_is_authorization") is False
        and disp.get("scanner_output_is_canonical_evidence_without_attestation") is False
        and disp.get("llm_only_security_pass_allowed") is False
        and disp.get("unauthenticated_public_webui_allowed") is False
        and disp.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(_finding("AISEC-REF-006", "AI-Infra-Guard immutable upstream/security disposition drift"))
    if not (
        enforcement.get("gate_id") == GATE_ID and enforcement.get("profile_id") == PROFILE_ID
        and enforcement.get("contract_id") == CONTRACT_ID and enforcement.get("provider_id") == PROVIDER_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("runtime_provider_required_for_global_promotion") is False
        and enforcement.get("floating_main_allowed_as_promotion_evidence") is False
        and enforcement.get("mandatory_rule_count") == len(P0_INVARIANTS)
        and enforcement.get("p0_invariants") == P0_INVARIANTS
        and enforcement.get("regression_case_count") == len(P0_INVARIANTS)
    ):
        findings.append(_finding("AISEC-REF-007", "AI security enforcement record drift"))
    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("AISEC-REF-008", "AI security gate is not globally mandatory"))
    if policy.get("ai_security_validation_profile_id") != PROFILE_ID:
        findings.append(_finding("AISEC-REF-009", "Global AI security profile identity drift"))
    if policy.get("ai_infra_guard_provider_id") != PROVIDER_ID:
        findings.append(_finding("AISEC-REF-010", "Global AI-Infra-Guard provider identity drift"))
    if policy.get("ai_security_validation_mandatory_p0_rules") != P0_INVARIANTS:
        findings.append(_finding("AISEC-REF-011", "Global AI security P0 invariant drift"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}

def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    def walk(obj: Any, path: str, source: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                here = f"{path}.{key}" if path else key
                if isinstance(value, str) and value == PROVIDER_ID and (
                    key == "authority" or key.endswith("_authority")
                ):
                    findings.append(_finding("AISEC-AUTH-001",
                        "AI-Infra-Guard assigned prohibited canonical authority",
                        source=source, field=here))
                walk(value, here, source)
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                walk(value, f"{path}[{idx}]", source)
    for path in sorted((root / "canonical").rglob("*.json")):
        scanned += 1
        try:
            walk(_load(path), "", str(path.relative_to(root)))
        except Exception as exc:
            findings.append(_finding("AISEC-AUTH-002", "Unreadable canonical JSON",
                                     source=str(path.relative_to(root)), error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL",
            "scanned_canonical_json_files": scanned, "findings": findings}

def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    def add(rule_id: str, name: str, positive: bool, negative: bool) -> None:
        cases.append({"rule_id": rule_id, "name": name,
                      "status": "PASS" if positive and negative else "FAIL",
                      "positive_case": positive, "negative_case": negative})

    add("FA3-AISEC-P0-001", "deterministic-first",
        deterministic_first_valid(deterministic_checks_run=True, deterministic_evidence_ids=["det:1"],
                                  llm_analysis_present=True, llm_is_sole_verdict_basis=False),
        not deterministic_first_valid(deterministic_checks_run=False, deterministic_evidence_ids=[],
                                      llm_analysis_present=True, llm_is_sole_verdict_basis=True))
    add("FA3-AISEC-P0-002", "LLM non-authority",
        llm_non_authority_valid(llm_output_treated_as_untrusted=True, llm_can_authorize=False, llm_can_promote=False),
        not llm_non_authority_valid(llm_output_treated_as_untrusted=False, llm_can_authorize=True, llm_can_promote=True))
    add("FA3-AISEC-P0-003", "explicit coverage",
        coverage_valid(examined_artifacts=["a.py"], excluded_artifacts=[], unsupported_artifacts=[],
                       scan_depth="RECURSIVE", analysis_modes=["STATIC"]),
        not coverage_valid(examined_artifacts=[], excluded_artifacts=[], unsupported_artifacts=[],
                           scan_depth="", analysis_modes=[]))
    add("FA3-AISEC-P0-004", "runtime-reachable completeness",
        runtime_surface_complete(runtime_reachable_artifacts=["a.py","b.pyc"], examined_artifacts=["a.py","b.pyc"],
                                 unsupported_artifacts=[], verdict="PASS"),
        not runtime_surface_complete(runtime_reachable_artifacts=["a.py","b.pyc"], examined_artifacts=["a.py"],
                                     unsupported_artifacts=["b.pyc"], verdict="PASS"))
    add("FA3-AISEC-P0-005", "independently versioned engines",
        engines_versioned(engines={"STATIC":"1.0","MCP":"2.0"}, required_modes=["STATIC","MCP"]),
        not engines_versioned(engines={"STATIC":"1.0"}, required_modes=["STATIC","MCP"]))
    add("FA3-AISEC-P0-006", "ruleset identity",
        ruleset_identity_valid(ruleset_id="aig:rules", version="2026-08-14",
                               digest="sha256:" + "a"*64),
        not ruleset_identity_valid(ruleset_id="aig:rules", version="", digest="latest"))
    add("FA3-AISEC-P0-007", "rule schema validation",
        rule_schema_valid(rule_id="AIG-1", severity="CRITICAL", schema_validated=True),
        not rule_schema_valid(rule_id="", severity="", schema_validated=False))
    add("FA3-AISEC-P0-008", "static/dynamic/adversarial separation",
        evidence_modes_valid(static_ids=["s1"], dynamic_ids=["d1"], adversarial_ids=["a1"],
                             required_modes=["STATIC","DYNAMIC","ADVERSARIAL"]),
        not evidence_modes_valid(static_ids=["s1"], dynamic_ids=[], adversarial_ids=[],
                                 required_modes=["STATIC","DYNAMIC","ADVERSARIAL"]))
    add("FA3-AISEC-P0-009", "capability-scoped scanner execution",
        capability_scope_valid(caller_identity="scanner:1", capability_scope=["security.scan.mcp"],
                               policy_authority="FA3-AUTH-SECURITY-GOV-001", policy_decision="ALLOW",
                               arbitrary_shell=False, unrestricted_egress=False),
        not capability_scope_valid(caller_identity="scanner:1", capability_scope=["*"],
                                   policy_authority=PROVIDER_ID, policy_decision="ALLOW",
                                   arbitrary_shell=True, unrestricted_egress=True))
    add("FA3-AISEC-P0-010", "untrusted scan inputs",
        untrusted_input_valid(scan_target_untrusted=True, remote_response_untrusted=True, llm_response_untrusted=True),
        not untrusted_input_valid(scan_target_untrusted=False, remote_response_untrusted=True, llm_response_untrusted=False))
    add("FA3-AISEC-P0-011", "SARIF projection boundary",
        sarif_projection_valid(canonical_internal_schema="FA3_SECURITY_EVIDENCE",
                               sarif_is_projection=True, sarif_is_canonical_authority=False),
        not sarif_projection_valid(canonical_internal_schema="SARIF",
                                   sarif_is_projection=False, sarif_is_canonical_authority=True))
    add("FA3-AISEC-P0-012", "evidence-bound verdict",
        verdict_evidence_bound(scanner_id=PROVIDER_ID, scanner_version=REFERENCE_RELEASE,
                               ruleset_digest="sha256:"+"b"*64, target_digest="sha256:"+"c"*64,
                               coverage_id="coverage:1", evidence_ids=["e1"], verdict="PASS"),
        not verdict_evidence_bound(scanner_id="", scanner_version="", ruleset_digest="latest",
                                   target_digest="", coverage_id="", evidence_ids=[], verdict="PASS"))
    add("FA3-AISEC-P0-013", "mutation/bypass regression",
        mutation_regression_valid(known_positive_count=2, known_negative_count=2, bypass_case_count=1,
                                  mutation_case_count=2, replayable=True),
        not mutation_regression_valid(known_positive_count=0, known_negative_count=1, bypass_case_count=0,
                                      mutation_case_count=0, replayable=False))
    add("FA3-AISEC-P0-014", "model/provider identity verification",
        model_provider_identity_valid(requested_identity="provider:model:v1", observed_identity="provider:model:v1",
                                      attestation_valid=True, mismatch_allowed=False),
        not model_provider_identity_valid(requested_identity="provider:model:v1", observed_identity="other:model:v1",
                                          attestation_valid=False, mismatch_allowed=True))
    add("FA3-AISEC-P0-015", "critical finding promotion block",
        promotion_guard_valid(unresolved_critical_findings=0, scanner_ui_override=False,
                              canonical_policy_decision="ALLOW"),
        not promotion_guard_valid(unresolved_critical_findings=1, scanner_ui_override=True,
                                  canonical_policy_decision="ALLOW"))
    add("FA3-AISEC-P0-016", "scanner conformance/non-authority",
        scanner_conformance_valid(regression_status="PASS", coverage_status="PASS",
                                  scanner_is_architectural_authority=False, scanner_is_promotion_authority=False,
                                  capability_count=CAPABILITY_COUNT),
        not scanner_conformance_valid(regression_status="PASS", coverage_status="UNKNOWN",
                                      scanner_is_architectural_authority=True, scanner_is_promotion_authority=True,
                                      capability_count=CAPABILITY_COUNT+1))
    return {"result": "PASS" if all(c["status"] == "PASS" for c in cases) else "FAIL",
            "passed": sum(c["status"] == "PASS" for c in cases), "total": len(cases), "cases": cases}

def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    ref = reference_check(root)
    regressions = run_regressions()
    auth = scan_canonical_authority_assignments(root)
    findings = list(ref.get("findings", [])) + list(auth.get("findings", []))
    if regressions["result"] != "PASS":
        findings.append(_finding("AISEC-REG-001", "AI security executable regression failed",
                                 passed=regressions["passed"], total=regressions["total"]))
    result = "PASS" if not findings else "FAIL"
    report = {
        "schema": "fa3.ai-security-validation-gate-report.v1",
        "profile_id": PROFILE_ID, "contract_id": CONTRACT_ID, "provider_id": PROVIDER_ID,
        "gate_id": GATE_ID, "result": result, "blocking_findings": len(findings),
        "reference_status": ref["result"], "authority_scan_status": auth["result"],
        "scanned_canonical_json_files": auth["scanned_canonical_json_files"],
        "regressions": regressions, "findings": findings,
        "new_capabilities": 0, "new_architectural_authorities": 0,
        "capability_count_after": CAPABILITY_COUNT,
        "current_host_runtime_promotion_claim": False,
    }
    _write(root / "reports/ai-infra-guard-gate-report.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
