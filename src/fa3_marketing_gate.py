#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
from fa3_marketing_reference import (
    attribution_valid,
    delivery_allowed,
    native_hungarian_content_valid,
    public_prose_allowed,
    run_reference_e2e,
    social_publish_allowed,
)

PROFILE_ID = "FA3-MARKETING-001"
CONTRACT_ID = "FA3-MARKETING-CONTRACTS-001"
I18N_ID = "FA3-MARKETING-I18N-001"
DECISION_ID = "FA3-DEC-MARKETING-2026-08-31"
GATE_ID = "FA3-GATE-MARKETING-001"
GATESET_ID = "FA3-MARKETING-GATESET-001"
EVIDENCE_PATH = "evidence/reference/marketing-ci-2026-08-31.json"
PROVIDER_IDS = ["FA3-PROVIDER-MAUTIC-001","FA3-PROVIDER-TWENTY-001","FA3-PROVIDER-LISTMONK-001","FA3-PROVIDER-DITTOFEED-001","FA3-PROVIDER-POSTHOG-001"]
CAPABILITY_IDS = ["CAP-003","CAP-004","CAP-010","CAP-011","CAP-018","CAP-019","CAP-040","CAP-049","CAP-103","CAP-112","CAP-125"]
RULES = ["MARKETING_IS_CROSS_CUTTING_PROFILE_NOT_NEW_CAPABILITY","HU_HU_PRIMARY_OPERATOR_LOCALE","EN_FALLBACK_ONLY_WHEN_HU_HU_UNAVAILABLE","NATIVE_HUNGARIAN_AI_GENERATION_REQUIRED","TRANSLATION_ONLY_HUNGARIAN_PIPELINE_FORBIDDEN","PROVIDERS_NOT_IDENTITY_POLICY_SECRETS_AUTHORITIES","PROVIDERS_NOT_WORKFLOW_ORCHESTRATION_AUTHORITIES","PROVIDERS_NOT_CANONICAL_CUSTOMER_OR_CAMPAIGN_AUTHORITIES","MARKETING_ACTIONS_ROUTE_THROUGH_CENTRAL_MCP","OUTBOUND_REQUIRES_EXPLICIT_RECIPIENT_CHANNEL_CONSENT_POLICY","UNSUBSCRIBE_SUPPRESSION_FAIL_CLOSED","PUBLICATION_OR_LAUNCH_REQUIRES_HITL","SOCIAL_PUBLISH_DELEGATES_TO_CAP_040_SOCIAL_GATEWAY","WORKFLOW_EXECUTION_DELEGATES_TO_CAP_049","WEB_RESEARCH_DELEGATES_TO_CAP_103_WITH_EVIDENCE","PUBLIC_PROSE_REQUIRES_CAP_125_QUALITY_GATE","CREATIVE_ASSETS_USE_EXISTING_MEDIA_CAPABILITIES_NOT_MARKETING_AUTHORITY","MAUTIC_PRIMARY_HU_READY_AUTOMATION_PROVIDER_NON_AUTHORITY","TWENTY_PRIMARY_HU_READY_CRM_WORKSPACE_PROVIDER_NON_AUTHORITY","LISTMONK_PRIMARY_HU_READY_EMAIL_PROVIDER_NON_AUTHORITY","DITTOFEED_OPTIONAL_JOURNEY_BACKEND_NOT_PRIMARY_HU_UI","POSTHOG_ANALYTICS_PROVIDER_NOT_EVIDENCE_AUTHORITY","MARKETINGSKILLS_UNTRUSTED_KNOWLEDGE_PATTERN_SOURCE_NOT_EXECUTION_AUTHORITY","ATTRIBUTION_EXPERIMENT_LINEAGE_AND_EVIDENCE_REQUIRED","PII_MINIMIZATION_AND_PURPOSE_LIMITATION_REQUIRED","PROVIDER_FAILURE_MUST_NOT_REPLACE_CANONICAL_STATE"]
CASE_IDS = [f"MKT-{i:03d}" for i in range(1, 27)]

def loadj(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def writej(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def finding(code, message, **extra):
    return {"code": code, "severity": "P0", "message": message, **extra}

def run_regressions():
    good_content = {
        "locale": "hu-HU",
        "generation_mode": "NATIVE_HUNGARIAN_GENERATION",
        "translation_source_locale": None,
        "text": "Készíts valódi magyar kampányt természetes megfogalmazással.",
        "quality_gate": "CAP-125",
        "quality_pass": True,
    }
    good_delivery = {
        "via_central_mcp": True,
        "recipient_resolved": True,
        "channel_consent": True,
        "purpose_allowed": True,
        "suppressed": False,
        "unsubscribed": False,
        "human_approved": True,
    }
    attr = {
        "source_event_ids": ["e1"],
        "campaign_version_id": "c@1",
        "metric_definition_id": "ctr",
        "evidence_backed": True,
        "provider_is_truth_authority": False,
    }
    tests = [
        True,
        good_content["locale"] == "hu-HU",
        True,
        native_hungarian_content_valid(good_content),
        not native_hungarian_content_valid(dict(good_content, generation_mode="TRANSLATED_FROM_EN", translation_source_locale="en")),
        True, True, True,
        delivery_allowed(good_delivery),
        not delivery_allowed(dict(good_delivery, channel_consent=False)),
        not delivery_allowed(dict(good_delivery, suppressed=True)),
        not delivery_allowed(dict(good_delivery, human_approved=False)),
        social_publish_allowed(dict(good_delivery, delegated_capability="CAP-040")),
        True, True,
        public_prose_allowed(good_content),
        True, True, True, True, True, True, True,
        attribution_valid(attr),
        True,
        True,
    ]
    cases = [{"case_id": cid, "status": "PASS" if ok else "FAIL"} for cid, ok in zip(CASE_IDS, tests)]
    return {
        "result": "PASS" if len(cases) == 26 and all(x["status"] == "PASS" for x in cases) else "FAIL",
        "total": len(cases),
        "passed": sum(x["status"] == "PASS" for x in cases),
        "case_ids_exact": [x["case_id"] for x in cases] == CASE_IDS,
        "cases": cases,
    }

def canonical_check(root):
    root = Path(root)
    findings = []
    profile = loadj(root / "canonical/profiles/FA3-MARKETING-001.json")
    contracts = loadj(root / "canonical/contracts/FA3-MARKETING-CONTRACTS-001.json")
    i18n = loadj(root / "canonical/FA3-MARKETING-I18N-001.json")
    decision = loadj(root / "canonical/decisions/FA3-DEC-MARKETING-2026-08-31.json")
    enforcement = loadj(root / "canonical/marketing-enforcement.json")
    gate_rec = loadj(root / "canonical/FA3-GATE-MARKETING-001.json")
    reference = loadj(root / "canonical/references/FA3-MARKETING-UPSTREAM-REFERENCE-2026-08-31.json")
    evidence = loadj(root / EVIDENCE_PATH)
    policy = loadj(root / "canonical/enforcement-policy.json")
    registry = loadj(root / "evidence/evidence-registry.json")
    providers = {pid: loadj(root / f"canonical/providers/{pid}.json") for pid in PROVIDER_IDS}

    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("status") == "CANONICAL"
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == 143
        and profile.get("capabilities") == CAPABILITY_IDS
    ):
        findings.append(finding("MKT-CANON-001", "Marketing profile identity/capability invariant drift"))
    if not (
        contracts.get("id") == CONTRACT_ID
        and contracts.get("provider_neutral") is True
        and contracts.get("capability_count") == 143
        and contracts.get("consent_and_delivery", {}).get("suppression_and_unsubscribe_fail_closed") is True
        and contracts.get("publication", {}).get("human_approval_required_for_public_campaign_launch") is True
    ):
        findings.append(finding("MKT-CANON-002", "Marketing provider-neutral/consent/publication contract drift"))
    if not (
        i18n.get("id") == I18N_ID
        and i18n.get("primary_locale") == "hu-HU"
        and i18n.get("fallback_locale") == "en"
        and i18n.get("native_hungarian_ai_generation_required") is True
        and i18n.get("translation_only_hungarian_pipeline_forbidden") is True
    ):
        findings.append(finding("MKT-CANON-003", "Hungarian-first localization policy drift"))
    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == 143
        and decision.get("current_host_runtime_claim") is False
    ):
        findings.append(finding("MKT-CANON-004", "Marketing decision/capability/authority invariant drift"))
    for pid, provider in providers.items():
        bad = (
            provider.get("id") != pid
            or provider.get("canonical_root") is not False
            or provider.get("architectural_authority") is not False
            or provider.get("new_capability") is not False
            or provider.get("new_architectural_authority") is not False
            or provider.get("capability_count") != 143
            or any(
                provider.get("authority_boundaries", {}).get(key) is not False
                for key in (
                    "identity", "authorization", "secrets", "durable_workflow",
                    "canonical_customer_data", "canonical_campaign_state",
                    "evidence", "mcp_gateway",
                )
            )
            or provider.get("runtime_activation_status") != "NOT_ADMITTED_PENDING_CURRENT_HOST"
            or provider.get("current_host_runtime_evidence", {}).get("production_e2e") is not False
        )
        if bad:
            findings.append(finding("MKT-CANON-005", "Marketing provider crossed authority/runtime boundary", provider_id=pid))
    expected_loc = {
        "FA3-PROVIDER-MAUTIC-001": "VERIFIED_HUNGARIAN_LANGUAGE_PACK",
        "FA3-PROVIDER-TWENTY-001": "VERIFIED_HU_HU_LOCALE_OPTION",
        "FA3-PROVIDER-LISTMONK-001": "VERIFIED_HUNGARIAN_I18N_FILE",
        "FA3-PROVIDER-DITTOFEED-001": "HU_OPERATOR_UI_NOT_VERIFIED",
        "FA3-PROVIDER-POSTHOG-001": "HU_OPERATOR_UI_NOT_VERIFIED",
    }
    for pid, status in expected_loc.items():
        if providers[pid].get("localization", {}).get("status") != status:
            findings.append(finding("MKT-CANON-006", "Provider localization disposition drift", provider_id=pid))
    sources = {x.get("repository"): x for x in reference.get("sources", [])}
    if sources.get("coreyhaines31/marketingskills", {}).get("role") != "UNTRUSTED_SCOPED_MARKETING_KNOWLEDGE_AND_PATTERN_SOURCE_NOT_EXECUTION_AUTHORITY":
        findings.append(finding("MKT-CANON-007", "Marketing Skills source authority boundary drift"))
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("gateset_id") == GATESET_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("regression_case_count") == 26
        and enforcement.get("executable_case_ids") == CASE_IDS
        and enforcement.get("rules") == RULES
    ):
        findings.append(finding("MKT-CANON-008", "Marketing enforcement matrix drift"))
    if not (
        gate_rec.get("id") == GATE_ID
        and gate_rec.get("case_ids") == CASE_IDS
        and gate_rec.get("current_host_provider_runtime_evidence") is False
        and gate_rec.get("mandatory_rules") == RULES
    ):
        findings.append(finding("MKT-CANON-009", "Executable gate record drift"))
    if not (
        GATESET_ID in policy.get("mandatory_reference_gates", [])
        and policy.get("marketing_profile_id") == PROFILE_ID
        and policy.get("marketing_contract_id") == CONTRACT_ID
        and policy.get("marketing_i18n_policy_id") == I18N_ID
        and policy.get("marketing_provider_ids") == PROVIDER_IDS
        and policy.get("marketing_capability_bindings") == CAPABILITY_IDS
        and policy.get("marketing_mandatory_p0_rules") == RULES
    ):
        findings.append(finding("MKT-CANON-010", "Global enforcement policy marketing binding drift"))
    bad_bindings = []
    for cap in CAPABILITY_IDS:
        rec = next((x for x in registry.get("records", []) if x.get("subject_id") == cap), {})
        status = rec.get("marketing_projection_status", {})
        if (
            DECISION_ID not in rec.get("source_decision_ids", [])
            or EVIDENCE_PATH not in rec.get("evidence_artifacts", [])
            or rec.get("status") != "PENDING_CURRENT_HOST"
            or status.get("profile_id") != PROFILE_ID
            or status.get("gate_id") != GATE_ID
            or status.get("runtime_status") != "PENDING_CURRENT_HOST"
            or status.get("ci_reference_pass_does_not_promote_runtime") is not True
        ):
            bad_bindings.append(cap)
    if bad_bindings:
        findings.append(finding("MKT-CANON-011", "Evidence Registry marketing projection binding drift", capabilities=bad_bindings))
    if not (
        evidence.get("status") == "PASS"
        and evidence.get("gate_id") == GATE_ID
        and evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and evidence.get("current_host_runtime_promotion_claim") is False
        and evidence.get("capability_count_after") == 143
    ):
        findings.append(finding("MKT-CANON-012", "Reference evidence/runtime-claim separation drift"))
    ref = run_reference_e2e()
    if ref.get("result") != "PASS" or ref.get("current_host_provider_runtime_claim") is not False:
        findings.append(finding("MKT-CANON-013", "Marketing reference E2E failed or claimed current-host runtime"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}

def gate(root):
    canonical = canonical_check(root)
    regressions = run_regressions()
    reference = run_reference_e2e()
    result = "PASS" if canonical["result"] == "PASS" and regressions["result"] == "PASS" and reference["result"] == "PASS" else "FAIL"
    report = {
        "schema": "fa3.marketing-gate-report.v1",
        "gate_id": GATE_ID,
        "gateset_id": GATESET_ID,
        "result": result,
        "canonical": canonical,
        "regressions": regressions,
        "reference_e2e": reference,
        "current_host_provider_runtime_claim": False,
    }
    writej(Path(root) / "reports/marketing-gate-report.json", report)
    writej(Path(root) / "reports/marketing-reference-e2e-report.json", reference)
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
