#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from fa3_release_baseline import module_active_capability_count
from fa3_reuse_catalog import build_catalog

SOURCE_ID = "FA3-SOURCE-AI-ENGINEERING-FROM-SCRATCH-001"
REFERENCE_ID = "FA3-AI-ENGINEERING-UPSTREAM-REFERENCE-2026-08-30"
DECISION_ID = "FA3-DEC-AI-ENGINEERING-FROM-SCRATCH-2026-08-30"
GATE_ID = "FA3-AIENG-GATESET-001"
INTENT_ID = "FA3-AI-ENGINEERING-REFERENCE-APPLICATION-INTENT-001"
ASSESSMENT_ID = "FA3-AI-ENGINEERING-REFERENCE-REUSE-ASSESSMENT-001"
PATTERN_BUNDLE_ID = "FA3-AI-ENGINEERING-DERIVED-PATTERNS-001"
UPSTREAM_REPO = "rohitg00/ai-engineering-from-scratch"
REFERENCE_COMMIT = "8bc378c2e07777899322ae77cd0dde94cb12fab3"
CAPABILITY_COUNT = module_active_capability_count(__file__)

SOURCE_RULES = [
    "REGISTRY_PUBLICATION_NOT_PRODUCTION_ADMISSION",
    "SKILL_CONTEXT_NOT_EXECUTION_AUTHORITY",
    "AGENT_ASSERTION_NOT_COMPLETION_EVIDENCE",
    "ATTRIBUTABLE_EXECUTION_EVIDENCE_REQUIRED",
    "POSITIVE_NEGATIVE_BOUNDARY_CONFORMANCE_REQUIRED",
    "RAW_BOUNDARY_AND_ADAPTER_PROJECTION_EVIDENCE_REQUIRED",
    "INGRESS_ORIGIN_EGRESS_TRACE_REQUIRED",
    "COMPATIBILITY_DOWNGRADE_FAIL_CLOSED",
    "EVIDENCE_REDACTION_BEFORE_PERSISTENCE",
    "ROLLBACK_READINESS_REQUIRED_BEFORE_PROMOTION",
    "PROGRESSIVE_DISCLOSURE_WITHOUT_AUTHORITY_ESCALATION",
]

OVERLAY_RULES = [
    "REUSE_DISCOVERY_BINDING_REQUIRED",
    "SOFTWARE_COEXISTENCE_AND_HOST_NON_INTERFERENCE",
    "HARDWARE_AUDIT_REFERENCE_ONLY_NO_RUNTIME_PROMOTION",
]

RULES = SOURCE_RULES + OVERLAY_RULES


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra):
    return {"code": code, "severity": "P0", "message": message, **extra}


def registry_admission_valid(*, published: bool, immutable_identity: bool, integrity_verified: bool,
                             provenance_verified: bool, policy_admitted: bool) -> bool:
    return all((published, immutable_identity, integrity_verified, provenance_verified, policy_admitted))


def execution_control_valid(*, context_or_skill_active: bool, capability_exposed: bool,
                            authorized: bool, approval_required: bool, approved: bool,
                            sandboxed: bool, verification_ready: bool) -> bool:
    return all((
        context_or_skill_active,
        capability_exposed,
        authorized,
        (approved if approval_required else True),
        sandboxed,
        verification_ready,
    ))


def completion_state_valid(*, requested_state: str, deterministic_gate_pass: bool,
                           independent_of_actor_claim: bool, evidence_bound: bool) -> bool:
    controlled = {"PASS", "CONFORMANT", "ACCEPTED", "PROMOTION_ELIGIBLE", "PROMOTED"}
    if requested_state not in controlled:
        return True
    return deterministic_gate_pass and independent_of_actor_claim and evidence_bound


def execution_evidence_valid(evidence: dict) -> bool:
    required = (
        "command", "argv", "cwd", "actor_identity", "capability_or_request_id",
        "input_artifact_refs", "exit_code", "output_artifact_refs", "environment_identity",
    )
    return all(k in evidence and evidence[k] not in (None, "") for k in required)


def conformance_evidence_valid(*, positive: bool, negative: bool, boundary: bool) -> bool:
    return positive and negative and boundary


def protocol_projection_evidence_valid(*, raw_boundary: bool, adapter_projection: bool,
                                       same_exchange_identity: bool) -> bool:
    return raw_boundary and adapter_projection and same_exchange_identity


def gateway_trace_valid(*, ingress: bool, origin: bool, egress: bool, correlation_id: str) -> bool:
    return ingress and origin and egress and bool(correlation_id)


def downgrade_allowed(*, explicit_permission: bool, bounded_scope: bool,
                      target_version: str, compatibility_evidence: bool) -> bool:
    return explicit_permission and bounded_scope and bool(target_version) and compatibility_evidence


def redaction_order_valid(stages: list[str]) -> bool:
    needed = ("REDACT", "SERIALIZE", "HASH", "STORE")
    if any(x not in stages for x in needed):
        return False
    pos = {x: stages.index(x) for x in needed}
    return pos["REDACT"] < pos["SERIALIZE"] < pos["HASH"] < pos["STORE"]


def rollback_ready(*, target_version: str, artifact_digest: str, health_evidence: bool,
                   route_restore_procedure: bool, trusted_readiness_evidence: bool) -> bool:
    return all((
        bool(target_version), bool(artifact_digest), health_evidence,
        route_restore_procedure, trusted_readiness_evidence,
    ))


def progressive_disclosure_valid(*, discovered: bool, activated: bool,
                                  branch_context_loaded: bool, grants_authority: bool) -> bool:
    if grants_authority:
        return False
    if branch_context_loaded and not activated:
        return False
    return discovered or activated or not branch_context_loaded


def reference_reuse_boundary_valid(*, reference_only: bool, automatic_fetch: bool,
                                   automatic_install: bool, automatic_activation: bool,
                                   authority: bool) -> bool:
    return (
        reference_only
        and not automatic_fetch
        and not automatic_install
        and not automatic_activation
        and not authority
    )


def coexistence_boundary_valid(*, namespaced: bool, upstream_uninstall_required: bool,
                               global_mutation: bool, default_port_hijack: bool) -> bool:
    return (
        namespaced
        and not upstream_uninstall_required
        and not global_mutation
        and not default_port_hijack
    )


def hardware_reference_valid(*, vendor_neutral: bool, cpu_only_viable: bool,
                             accelerator_cardinality: str, global_accelerator_requirement: bool,
                             current_host_runtime_promotion_claim: bool) -> bool:
    return (
        vendor_neutral
        and cpu_only_viable
        and accelerator_cardinality == "0..N"
        and not global_accelerator_requirement
        and not current_host_runtime_promotion_claim
    )


def scan_source_authority_assignments(root: Path):
    findings = []
    canonical = root / "canonical"
    for path in canonical.rglob("*.json"):
        try:
            obj = loadj(path)
        except Exception:
            continue

        def walk(node, key_path=""):
            if isinstance(node, dict):
                for key, value in node.items():
                    kp = f"{key_path}.{key}" if key_path else key
                    lk = key.lower()
                    if isinstance(value, str) and value == SOURCE_ID:
                        if lk == "provider_id" or lk == "authority" or lk.endswith("_authority"):
                            findings.append(finding(
                                "AIENG-AUTH-001",
                                "Reference source was assigned provider/authority role",
                                path=str(path.relative_to(root)),
                                key_path=kp,
                            ))
                    walk(value, kp)
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    walk(value, f"{key_path}[{i}]")

        walk(obj)
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def reference_check(root: Path):
    findings = []
    ref_path = root / "canonical/references/FA3-AI-ENGINEERING-UPSTREAM-REFERENCE-2026-08-30.json"
    dec_path = root / "canonical/decisions/FA3-DEC-AI-ENGINEERING-FROM-SCRATCH-2026-08-30.json"
    enf_path = root / "canonical/ai-engineering-from-scratch-enforcement.json"
    pol_path = root / "canonical/enforcement-policy.json"

    for code, path in (
        ("AIENG-REF-001", ref_path),
        ("AIENG-REF-002", dec_path),
        ("AIENG-REF-003", enf_path),
        ("AIENG-REF-004", pol_path),
    ):
        if not path.exists():
            findings.append(finding(code, "Required canonical file missing", path=str(path.relative_to(root))))

    if findings:
        return {"result": "FAIL", "findings": findings}

    ref = loadj(ref_path)
    dec = loadj(dec_path)
    enf = loadj(enf_path)
    pol = loadj(pol_path)
    disp = ref.get("fa3_disposition", {})

    if not (
        ref.get("id") == REFERENCE_ID
        and ref.get("source_id") == SOURCE_ID
        and ref.get("repository") == UPSTREAM_REPO
        and ref.get("immutable_reference_commit") == REFERENCE_COMMIT
        and ref.get("observed_default_branch_head") == REFERENCE_COMMIT
        and ref.get("default_branch") == "main"
        and ref.get("reference_kind") == "PINNED_COMMIT"
        and ref.get("last_revalidated_at") == "2026-09-26"
    ):
        findings.append(finding("AIENG-REF-005", "Immutable upstream reference identity drift"))

    if not (
        disp.get("accepted") is True
        and disp.get("runtime_provider") is False
        and disp.get("canonical_root") is False
        and disp.get("architectural_authority") is False
        and disp.get("new_capability") is False
        and disp.get("new_architectural_authority") is False
        and disp.get("canonical_capability_count") == CAPABILITY_COUNT
        and disp.get("floating_main_allowed_as_promotion_evidence") is False
        and disp.get("registry_publication_is_local_admission") is False
        and disp.get("source_record_is_current_host_runtime_evidence") is False
    ):
        findings.append(finding("AIENG-REF-006", "Reference source classification/authority/capability invariant drift"))

    if not (
        dec.get("id") == DECISION_ID
        and dec.get("status") == "CANONICAL_CLOSED"
        and dec.get("decision") == "ACCEPT"
        and dec.get("source_id") == SOURCE_ID
        and dec.get("gate_id") == GATE_ID
        and dec.get("new_capabilities") == 0
        and dec.get("new_architectural_authorities") == 0
        and dec.get("new_runtime_providers") == 0
        and dec.get("capability_count_after") == CAPABILITY_COUNT
        and dec.get("canonical_rules_absorbed") == SOURCE_RULES
        and dec.get("fa3_overlay_rules") == OVERLAY_RULES
        and dec.get("application_intent_id") == INTENT_ID
        and dec.get("reuse_assessment_id") == ASSESSMENT_ID
        and dec.get("pattern_bundle_id") == PATTERN_BUNDLE_ID
        and dec.get("current_host_runtime_evidence_required") is False
    ):
        findings.append(finding("AIENG-REF-007", "Canonical decision drift"))

    if not (
        enf.get("gate_id") == GATE_ID
        and enf.get("source_id") == SOURCE_ID
        and enf.get("reference_id") == REFERENCE_ID
        and enf.get("reference_commit") == REFERENCE_COMMIT
        and enf.get("fail_closed") is True
        and enf.get("runtime_source_required_for_global_promotion") is False
        and enf.get("floating_main_allowed_as_promotion_evidence") is False
        and enf.get("mandatory_rule_count") == len(RULES)
        and enf.get("p0_invariants") == RULES
        and len(enf.get("rules", [])) == len(RULES)
        and enf.get("global_static_integration") is True
        and enf.get("regression_case_count") == len(RULES)
        and enf.get("application_intent_id") == INTENT_ID
        and enf.get("reuse_assessment_id") == ASSESSMENT_ID
        and enf.get("pattern_bundle_id") == PATTERN_BUNDLE_ID
        and enf.get("reuse_discovery_required") is True
        and enf.get("software_coexistence_required") is True
        and enf.get("hardware_audit_required") is True
        and enf.get("current_host_runtime_evidence_required") is False
    ):
        findings.append(finding("AIENG-REF-008", "Enforcement record drift"))

    if GATE_ID not in pol.get("mandatory_reference_gates", []):
        findings.append(finding("AIENG-REF-009", "Gate is not bound into global enforcement policy"))
    if pol.get("ai_engineering_source_id") != SOURCE_ID:
        findings.append(finding("AIENG-REF-010", "Global policy source binding drift"))
    if pol.get("ai_engineering_mandatory_p0_rules") != RULES:
        findings.append(finding("AIENG-REF-011", "Global policy mandatory rule set drift"))
    if pol.get("ai_engineering_application_intent_id") != INTENT_ID:
        findings.append(finding("AIENG-REF-012", "Global policy ApplicationIntent binding drift"))
    if pol.get("ai_engineering_reuse_assessment_id") != ASSESSMENT_ID:
        findings.append(finding("AIENG-REF-013", "Global policy ReuseAssessment binding drift"))
    if pol.get("ai_engineering_pattern_bundle_id") != PATTERN_BUNDLE_ID:
        findings.append(finding("AIENG-REF-014", "Global policy derived-pattern binding drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def reuse_governance_check(root: Path):
    findings = []
    intent_path = root / "canonical/intents/FA3-AI-ENGINEERING-REFERENCE-APPLICATION-INTENT-001.json"
    assessment_path = root / "canonical/assessments/FA3-AI-ENGINEERING-REFERENCE-REUSE-ASSESSMENT-001.json"
    pattern_path = root / "canonical/patterns/FA3-AI-ENGINEERING-DERIVED-PATTERNS-001.json"
    ref_path = root / "canonical/references/FA3-AI-ENGINEERING-UPSTREAM-REFERENCE-2026-08-30.json"

    for code, path in (
        ("AIENG-REUSE-001", intent_path),
        ("AIENG-REUSE-002", assessment_path),
        ("AIENG-REUSE-003", pattern_path),
    ):
        if not path.exists():
            findings.append(finding(code, "Required reuse-governance artifact missing", path=str(path.relative_to(root))))

    if findings:
        return {"result": "FAIL", "findings": findings}

    intent = loadj(intent_path)
    assessment = loadj(assessment_path)
    patterns = loadj(pattern_path)
    ref = loadj(ref_path)
    ns = intent.get("namespace_claims", {})
    ihw = intent.get("hardware_audit", {})
    ahw = assessment.get("hardware_audit", {})
    coexist = assessment.get("coexistence", {})
    binding = ref.get("reuse_discovery_binding", {})

    if not (
        intent.get("schema") == "fa3.application-intent.v1"
        and intent.get("id") == INTENT_ID
        and intent.get("project_id") == SOURCE_ID
        and intent.get("project_type") == "REFERENCE_SOURCE"
        and intent.get("proposed_authority_roles") == []
        and intent.get("declared_new_capabilities") == []
        and intent.get("runtime_materialization") is False
        and "FA3-REUSE-DISCOVERY-001" in intent.get("integration_requirements", [])
    ):
        findings.append(finding("AIENG-REUSE-004", "ApplicationIntent boundary drift"))

    if not hardware_reference_valid(
        vendor_neutral=ihw.get("vendor_neutral") is True,
        cpu_only_viable=ihw.get("cpu_only_viable") is True,
        accelerator_cardinality=str(ihw.get("accelerator_cardinality", "")),
        global_accelerator_requirement=ihw.get("global_accelerator_requirement") is True,
        current_host_runtime_promotion_claim=ihw.get("current_host_execution_required") is True,
    ):
        findings.append(finding("AIENG-REUSE-005", "ApplicationIntent hardware audit drift"))

    if not coexistence_boundary_valid(
        namespaced=all(bool(ns.get(k)) for k in (
            "package_prefix", "service_prefix", "config_root", "cache_root",
            "runtime_root", "socket_namespace", "data_root", "desktop_prefix"
        )),
        upstream_uninstall_required=ns.get("requires_upstream_uninstall") is True,
        global_mutation=ns.get("global_environment_mutation") is True,
        default_port_hijack=ns.get("claims_default_port") is True,
    ):
        findings.append(finding("AIENG-REUSE-006", "ApplicationIntent coexistence namespace drift"))

    if not (
        assessment.get("schema") == "fa3.reuse-assessment.v1"
        and assessment.get("id") == ASSESSMENT_ID
        and assessment.get("project_id") == SOURCE_ID
        and assessment.get("intent_id") == INTENT_ID
        and assessment.get("result") == "PASS"
        and assessment.get("new_capabilities") == 0
        and assessment.get("new_architectural_authorities") == 0
        and assessment.get("new_runtime_providers") == 0
        and assessment.get("capability_count_after") == CAPABILITY_COUNT
        and assessment.get("current_host_runtime_promotion_claim") is False
        and assessment.get("global_promotion_claim") is False
    ):
        findings.append(finding("AIENG-REUSE-007", "ReuseAssessment baseline or promotion boundary drift"))

    if not coexistence_boundary_valid(
        namespaced=coexist.get("namespaced") is True,
        upstream_uninstall_required=coexist.get("upstream_uninstall_required") is True,
        global_mutation=coexist.get("global_mutation") is True,
        default_port_hijack=coexist.get("default_port_hijack") is True,
    ):
        findings.append(finding("AIENG-REUSE-008", "ReuseAssessment coexistence boundary drift"))

    if not hardware_reference_valid(
        vendor_neutral=ahw.get("vendor_neutral") is True,
        cpu_only_viable=ahw.get("cpu_only_viable") is True,
        accelerator_cardinality=str(ahw.get("accelerator_cardinality", "")),
        global_accelerator_requirement=ahw.get("global_accelerator_requirement") is True,
        current_host_runtime_promotion_claim=assessment.get("current_host_runtime_promotion_claim") is True,
    ):
        findings.append(finding("AIENG-REUSE-009", "ReuseAssessment hardware boundary drift"))

    if not (
        patterns.get("schema") == "fa3.pattern-bundle.v1"
        and patterns.get("id") == PATTERN_BUNDLE_ID
        and patterns.get("source_id") == SOURCE_ID
        and patterns.get("upstream_reference_id") == REFERENCE_ID
        and patterns.get("upstream_commit") == REFERENCE_COMMIT
        and patterns.get("authority") is False
        and patterns.get("architectural_authority") is False
        and patterns.get("runtime_dependency_implied") is False
        and patterns.get("current_host_claim") is False
        and patterns.get("new_capability") is False
        and patterns.get("new_architectural_authority") is False
        and patterns.get("capability_count") == CAPABILITY_COUNT
        and patterns.get("invariants") == SOURCE_RULES
        and len(patterns.get("patterns", [])) == len(SOURCE_RULES)
    ):
        findings.append(finding("AIENG-REUSE-010", "Derived pattern bundle drift"))

    if not (
        binding.get("profile_id") == "FA3-REUSE-DISCOVERY-001"
        and binding.get("catalog_id") == "FA3-REUSE-CATALOG-001"
        and binding.get("intent_id") == INTENT_ID
        and binding.get("assessment_id") == ASSESSMENT_ID
        and binding.get("pattern_bundle_id") == PATTERN_BUNDLE_ID
        and binding.get("role") == "REFERENCE_AND_PATTERN_SOURCE_ONLY"
        and binding.get("automatic_fetch") is False
        and binding.get("automatic_install") is False
        and binding.get("automatic_activation") is False
    ):
        findings.append(finding("AIENG-REUSE-011", "Upstream reference reuse-discovery binding drift"))

    catalog = build_catalog(root)
    by_id = {}
    for row in catalog.get("entries", []):
        by_id.setdefault(row.get("candidate_id"), []).append(row)
    ref_rows = by_id.get(REFERENCE_ID, [])
    pattern_rows = by_id.get(PATTERN_BUNDLE_ID, [])

    if not any(row.get("candidate_class") == "UPSTREAM_REFERENCE" and row.get("authority") is False for row in ref_rows):
        findings.append(finding("AIENG-REUSE-012", "Reuse Catalog does not expose upstream reference as non-authoritative candidate"))
    if not any(row.get("candidate_class") == "REUSABLE_PATTERN" and row.get("authority") is False for row in pattern_rows):
        findings.append(finding("AIENG-REUSE-013", "Reuse Catalog does not expose derived pattern bundle as non-authoritative candidate"))

    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "catalog_entry_count": catalog.get("entry_count"),
    }


def run_regressions():
    cases = []

    def add(name: str, allowed: bool):
        cases.append({"name": name, "result": "PASS" if not allowed else "FAIL"})

    add("registry publication alone denied", registry_admission_valid(
        published=True, immutable_identity=False, integrity_verified=False,
        provenance_verified=False, policy_admitted=False))
    add("skill activation alone denied", execution_control_valid(
        context_or_skill_active=True, capability_exposed=True, authorized=False,
        approval_required=True, approved=False, sandboxed=False, verification_ready=False))
    add("agent self completion claim denied", completion_state_valid(
        requested_state="PROMOTED", deterministic_gate_pass=False,
        independent_of_actor_claim=False, evidence_bound=False))
    add("incomplete execution evidence denied", execution_evidence_valid({
        "command": "tool", "argv": ["tool"], "cwd": "/workspace",
        "actor_identity": "agent", "capability_or_request_id": "REQ-1",
        "input_artifact_refs": [], "exit_code": 0, "output_artifact_refs": []
    }))
    add("happy path only conformance denied", conformance_evidence_valid(
        positive=True, negative=False, boundary=False))
    add("adapter only protocol evidence denied", protocol_projection_evidence_valid(
        raw_boundary=False, adapter_projection=True, same_exchange_identity=True))
    add("gateway egress-only trace denied", gateway_trace_valid(
        ingress=False, origin=False, egress=True, correlation_id="corr-1"))
    add("automatic compatibility downgrade denied", downgrade_allowed(
        explicit_permission=False, bounded_scope=False,
        target_version="legacy", compatibility_evidence=False))
    add("redaction after serialization denied", redaction_order_valid(
        ["SERIALIZE", "REDACT", "HASH", "STORE"]))
    add("promotion without rollback readiness denied", rollback_ready(
        target_version="", artifact_digest="", health_evidence=False,
        route_restore_procedure=False, trusted_readiness_evidence=False))
    add("pre-activation branch context authority escalation denied", progressive_disclosure_valid(
        discovered=True, activated=False, branch_context_loaded=True, grants_authority=True))
    add("reference source automatic installation denied", reference_reuse_boundary_valid(
        reference_only=True, automatic_fetch=False, automatic_install=True,
        automatic_activation=False, authority=False))
    add("host interference and port hijack denied", coexistence_boundary_valid(
        namespaced=True, upstream_uninstall_required=False,
        global_mutation=True, default_port_hijack=True))
    add("hardware/runtime overclaim denied", hardware_reference_valid(
        vendor_neutral=True, cpu_only_viable=True, accelerator_cardinality="1",
        global_accelerator_requirement=True, current_host_runtime_promotion_claim=True))

    passed = sum(c["result"] == "PASS" for c in cases)
    return {
        "result": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "cases": cases,
    }


def gate(root: Path):
    reference = reference_check(root)
    reuse = reuse_governance_check(root)
    authority = scan_source_authority_assignments(root)
    regressions = run_regressions()
    ok = all(x["result"] == "PASS" for x in (reference, reuse, authority, regressions))
    report = {
        "schema": "fa3.ai-engineering-gate-report.v1",
        "gate_id": GATE_ID,
        "source_id": SOURCE_ID,
        "reference_commit": REFERENCE_COMMIT,
        "capability_count": CAPABILITY_COUNT,
        "runtime_provider_required": False,
        "current_host_runtime_evidence_required": False,
        "result": "PASS" if ok else "FAIL",
        "reference": reference,
        "reuse_governance": reuse,
        "authority_scan": authority,
        "regressions": regressions,
    }
    report_path = root / "reports/ai-engineering-gate-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
