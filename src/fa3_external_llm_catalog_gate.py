#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_external_llm_catalog import (
    REFERENCE_ID,
    normalize_markdown,
    runtime_eligible,
    transition_allowed,
    validate_runtime_catalog,
)
from fa3_release_baseline import module_active_capability_count

GATE_ID = "FA3-GATE-EXTERNAL-LLM-CATALOG-001"
GATESET_ID = "FA3-EXTERNAL-LLM-CATALOG-GATESET-001"
PROFILE_ID = "FA3-EXTERNAL-LLM-CATALOG-001"
CONTRACT_ID = "FA3-EXTERNAL-LLM-CATALOG-CONTRACTS-001"
DECISION_ID = "FA3-DEC-EXTERNAL-LLM-CATALOG-2026-09-24"
ASSESSMENT_PROJECT_ID = "FA3-EXTERNAL-LLM-CATALOG-2026-09-24"
UPSTREAM_COMMIT = "4a91e1d93a6df0753ade804f75b4e17fbad89886"
README_BLOB_SHA = "6efd805b95fe690a9276a664c632bb3a6e170e79"
CAPABILITY_COUNT = module_active_capability_count(__file__)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def _regressions(root: Path) -> dict[str, Any]:
    fixture = (root / "tests/fixtures/freellm-readme-mini.md").read_text(encoding="utf-8")
    catalog = normalize_markdown(
        fixture,
        source_commit=UPSTREAM_COMMIT,
        observed_at="2026-09-24",
    )
    providers = {row["provider_name"]: row for row in catalog["providers"]}
    base = providers["Groq"]
    admitted = json.loads(json.dumps(base))
    admitted["discovery_state"] = "ADMITTED"
    admitted["admission"] = {
        "fa3_provider_id": "FA3-PROVIDER-EXAMPLE-001",
        "admission_receipt": "evidence/receipts/example.json",
        "explicit_external_policy": True,
        "credential_handle_present": True,
        "live_capability_probe": True,
    }

    cases = [
        ("FIXTURE_THREE_PROVIDERS", len(catalog["providers"]) == 3),
        ("PARSER_DISCOVERED_ONLY", all(row["discovery_state"] == "DISCOVERED" for row in catalog["providers"])),
        ("GROQ_BASE_URL_NORMALIZED", base["base_url"] == "https://api.groq.com/openai/v1"),
        ("NO_CREDENTIAL_VALUE_FIELDS", validate_runtime_catalog(catalog) == []),
        ("DISCOVERED_TO_OBSERVED_ALLOWED", transition_allowed("DISCOVERED", "OBSERVED")),
        ("DISCOVERED_TO_ENABLED_BLOCKED", not transition_allowed("DISCOVERED", "ENABLED")),
        ("VERIFIED_TO_ADMITTED_ALLOWED", transition_allowed("VERIFIED", "ADMITTED")),
        ("VERIFIED_TO_ENABLED_BLOCKED", not transition_allowed("VERIFIED", "ENABLED")),
        (
            "DISCOVERED_NOT_RUNTIME_ELIGIBLE",
            not runtime_eligible(base, security_privacy_admitted=True, egress_policy_admitted=True, credential_required=False),
        ),
        (
            "ADMITTED_FULL_CHAIN_RUNTIME_ELIGIBLE",
            runtime_eligible(admitted, security_privacy_admitted=True, egress_policy_admitted=True, credential_required=True),
        ),
        (
            "MISSING_EGRESS_POLICY_BLOCKED",
            not runtime_eligible(admitted, security_privacy_admitted=True, egress_policy_admitted=False, credential_required=True),
        ),
        (
            "MISSING_CREDENTIAL_HANDLE_BLOCKED",
            not runtime_eligible(
                {**admitted, "admission": {**admitted["admission"], "credential_handle_present": False}},
                security_privacy_admitted=True,
                egress_policy_admitted=True,
                credential_required=True,
            ),
        ),
    ]
    rows = [{"case": name, "status": "PASS" if ok else "FAIL"} for name, ok in cases]
    passed = sum(row["status"] == "PASS" for row in rows)
    return {
        "schema": "fa3.external-llm-catalog-regression-report.v1",
        "result": "PASS" if passed == len(rows) else "FAIL",
        "passed": passed,
        "total": len(rows),
        "cases": rows,
    }


def reference_check(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-EXTERNAL-LLM-CATALOG-001.json",
        "contract": root / "canonical/contracts/FA3-EXTERNAL-LLM-CATALOG-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-EXTERNAL-LLM-CATALOG-2026-09-24.json",
        "assessment": root / "canonical/assessments/FA3-EXTERNAL-LLM-CATALOG-DECISION-ASSESSMENT-2026-09-24.json",
        "reference": root / "canonical/references/FA3-FREELLM-UPSTREAM-REFERENCE-2026-09-24.json",
        "enforcement": root / "canonical/external-llm-catalog-enforcement.json",
        "executable_gate": root / "canonical/FA3-GATE-EXTERNAL-LLM-CATALOG-001.json",
        "policy": root / "canonical/enforcement-policy.json",
        "evidence": root / "evidence/reference/external-llm-catalog-ci-2026-09-24.json",
        "model_router_enforcement": root / "canonical/model-router-enforcement.json",
        "surface_registry": root / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
        "explorer_qml": root / "apps/fa3-control-center/qml/ProviderExplorerView.qml",
        "models_qml": root / "apps/fa3-control-center/qml/ModelsProvidersPage.qml",
        "catalog_header": root / "apps/fa3-control-center/src/ExternalLlmCatalogModel.h",
        "catalog_impl": root / "apps/fa3-control-center/src/ExternalLlmCatalogModel.cpp",
        "main_cpp": root / "apps/fa3-control-center/src/main.cpp",
        "cmake": root / "apps/fa3-control-center/CMakeLists.txt",
        "fixture": root / "tests/fixtures/freellm-readme-mini.md",
    }
    for key, path in paths.items():
        if not path.is_file():
            findings.append(_finding("ELLC-001", "required materialization artifact missing", artifact=key, path=str(path.relative_to(root))))
    if findings:
        return {"schema": "fa3.external-llm-catalog-gate.v1", "gate_id": GATE_ID, "result": "FAIL", "findings": findings}

    profile = _load(paths["profile"])
    contract = _load(paths["contract"])
    decision = _load(paths["decision"])
    assessment = _load(paths["assessment"])
    reference = _load(paths["reference"])
    enforcement = _load(paths["enforcement"])
    executable_gate = _load(paths["executable_gate"])
    policy = _load(paths["policy"])
    evidence = _load(paths["evidence"])
    model_router = _load(paths["model_router_enforcement"])
    surface_registry = _load(paths["surface_registry"])

    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("status") == "CANONICAL"
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("gate_id") == GATESET_ID
        and profile.get("authority_bindings", {}).get("model_routing") == "FA3-AUTH-MODEL-ROUTER-001"
        and profile.get("runtime_policy", {}).get("silent_local_to_cloud_fallback") is False
        and profile.get("runtime_policy", {}).get("baseline_local_routes_remain_local_only") is True
    ):
        findings.append(_finding("ELLC-010", "profile identity, capability or Model Router boundary drift"))

    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("capability_count") == CAPABILITY_COUNT
        and contract.get("state_machine", {}).get("parser_initial_state") == "DISCOVERED"
        and contract.get("state_machine", {}).get("state_skip") == "DENY"
        and contract.get("credential_boundary", {}).get("api_key_value") == "FORBIDDEN"
        and contract.get("admission_boundary", {}).get("catalog_discovery_is_provider_admission") is False
        and contract.get("admission_boundary", {}).get("free_tier_is_provider_admission") is False
        and contract.get("admission_boundary", {}).get("runtime_routing_authority") == "FA3-AUTH-MODEL-ROUTER-001"
        and contract.get("admission_boundary", {}).get("silent_local_to_cloud_fallback") == "DENY"
    ):
        findings.append(_finding("ELLC-011", "normalization, credential or admission contract drift"))

    facts = reference.get("observed_repository_facts", {})
    interpretation = reference.get("fa3_interpretation", {})
    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("repository") == "open-free-llm-api/awesome-freellm-apis"
        and reference.get("commit") == UPSTREAM_COMMIT
        and reference.get("readme_blob_sha") == README_BLOB_SHA
        and reference.get("license") == "MIT"
        and facts.get("default_branch_protected") is False
        and facts.get("observed_commit_verified_signature") is False
        and interpretation.get("trust_anchor") is False
        and interpretation.get("runtime_provider") is False
        and interpretation.get("free_tier_claim_is_admission_evidence") is False
    ):
        findings.append(_finding("ELLC-012", "upstream provenance/trust interpretation drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and isinstance(decision.get("capability_count_after"), int)
        and decision.get("capability_count_after") <= CAPABILITY_COUNT
        and decision.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(_finding("ELLC-013", "decision record capability or promotion semantics drift"))

    security = assessment.get("security_boundary", {})
    if not (
        assessment.get("project_id") == ASSESSMENT_PROJECT_ID
        and assessment.get("assessment") == "RECOMMENDED"
        and assessment.get("capability_delta") == 0
        and assessment.get("authority_delta") == 0
        and security.get("may_expand_candidate_set") is False
        and security.get("may_admit_provider") is False
        and security.get("may_admit_model") is False
    ):
        findings.append(_finding("ELLC-014", "Decision Fabric advisory boundary drift"))

    required_rules = {
        "EXTERNAL_LLM_SOURCE_IS_DISCOVERY_ONLY_NOT_TRUST_AUTHORITY",
        "NORMALIZER_INITIAL_STATE_DISCOVERED_ONLY",
        "CATALOG_CANNOT_CONTAIN_SECRET_VALUES",
        "FREE_TIER_CLAIM_IS_NOT_PROVIDER_ADMISSION",
        "MODEL_ROUTER_REMAINS_SINGLE_ROUTING_AUTHORITY",
        "NO_SILENT_LOCAL_TO_CLOUD_FALLBACK",
        "DECISION_FABRIC_CANNOT_EXPAND_OR_ADMIT_PROVIDER_SET",
        "GUI_PROVIDER_EXPLORER_IS_READ_ONLY_PLUS_DRAFT_INTENT",
    }
    if (
        enforcement.get("gate_id") != GATE_ID
        or enforcement.get("gateset_id") != GATESET_ID
        or not required_rules.issubset(set(enforcement.get("mandatory_rules", [])))
    ):
        findings.append(_finding("ELLC-015", "mandatory enforcement rules incomplete"))

    if not (
        executable_gate.get("id") == GATE_ID
        and executable_gate.get("gateset_id") == GATESET_ID
        and executable_gate.get("status") == "CANONICAL_EXECUTABLE"
        and executable_gate.get("profile_id") == PROFILE_ID
        and executable_gate.get("contract_id") == CONTRACT_ID
        and executable_gate.get("decision_id") == DECISION_ID
        and executable_gate.get("reference_id") == REFERENCE_ID
        and executable_gate.get("capability_count") == CAPABILITY_COUNT
        and executable_gate.get("regression_case_count") == 12
        and executable_gate.get("global_command") == "./bin/fa3-enforce external-llm-catalog"
        and executable_gate.get("current_host_provider_runtime_evidence") is False
    ):
        findings.append(_finding("ELLC-015A", "canonical executable gate record drift"))

    if not (
        GATESET_ID in set(policy.get("mandatory_reference_gates", []))
        and policy.get("external_llm_catalog_profile_id") == PROFILE_ID
        and policy.get("external_llm_catalog_contract_id") == CONTRACT_ID
        and policy.get("external_llm_catalog_gate_id") == GATESET_ID
        and policy.get("external_llm_catalog_reference_id") == REFERENCE_ID
        and policy.get("external_llm_catalog_silent_local_to_cloud_fallback") is False
        and policy.get("external_llm_catalog_upstream_distribution_class") == "REFERENCE_ONLY"
    ):
        findings.append(_finding("ELLC-015B", "global enforcement policy binding drift"))

    if "NO_SILENT_LOCAL_TO_CLOUD_FALLBACK" not in set(model_router.get("rules", [])):
        findings.append(_finding("ELLC-016", "existing Model Router no-silent-cloud-fallback invariant missing"))

    if not (
        evidence.get("status") == "PASS"
        and evidence.get("evidence_class") == "REFERENCE_STATIC_CONFORMANCE"
        and evidence.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(_finding("ELLC-017", "reference evidence semantics drift"))

    model_surface = next((row for row in surface_registry.get("surfaces", []) if row.get("route_id") == "models.providers"), {})
    children = model_surface.get("children", [])
    explorer = next((row for row in children if row.get("surface_id") == "models.provider-explorer"), {})
    if not (
        explorer.get("projection") == "EXTERNAL_LLM_PROVIDER_DISCOVERY"
        and explorer.get("mode") == "READ_ONLY_DISCOVERY_AND_DRAFT_ADMISSION_INTENT"
        and explorer.get("direct_provider_execution") is False
        and explorer.get("authority") is False
    ):
        findings.append(_finding("ELLC-018", "Provider Explorer GUI surface boundary missing or drifted"))

    explorer_qml = paths["explorer_qml"].read_text(encoding="utf-8")
    models_qml = paths["models_qml"].read_text(encoding="utf-8")
    main_cpp = paths["main_cpp"].read_text(encoding="utf-8")
    cmake = paths["cmake"].read_text(encoding="utf-8")
    impl = paths["catalog_impl"].read_text(encoding="utf-8")
    for token in [
        "Provider Explorer",
        "DISCOVERY ≠ ADMISSION",
        "NO SILENT LOCAL → CLOUD FALLBACK",
        "Admission draft",
        "fa3ExternalLlmCatalog.providers",
    ]:
        if token not in explorer_qml:
            findings.append(_finding("ELLC-019", "Provider Explorer QML contract token missing", token=token))
    for token in ["ProviderExplorerView", "MODEL_PROVIDER_ADMISSION", "propose.external-llm-provider-admission"]:
        if token not in models_qml:
            findings.append(_finding("ELLC-020", "Models & Providers child integration missing", token=token))
    if 'setContextProperty("fa3ExternalLlmCatalog"' not in main_cpp:
        findings.append(_finding("ELLC-021", "GUI runtime catalog context property missing"))
    for token in ["ExternalLlmCatalogModel.cpp", "ExternalLlmCatalogModel.h", "qml/ProviderExplorerView.qml"]:
        if token not in cmake:
            findings.append(_finding("ELLC-022", "Control Center build integration missing", token=token))
    for forbidden in ["apiKey", "secretValue", "bearerToken", "password"]:
        if forbidden in impl:
            findings.append(_finding("ELLC-023", "GUI runtime catalog model contains forbidden secret field", token=forbidden))

    regressions = _regressions(root)
    if regressions.get("result") != "PASS":
        findings.append(_finding("ELLC-030", "parser/admission regression suite failed", regressions=regressions))

    return {
        "schema": "fa3.external-llm-catalog-gate.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "regressions": regressions,
        "capability_delta": 0,
        "authority_delta": 0,
        "current_host_runtime_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = reference_check(root)
    out = root / "reports/external-llm-catalog-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
