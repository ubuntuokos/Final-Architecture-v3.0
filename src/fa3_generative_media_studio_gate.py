#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROFILE = "canonical/profiles/FA3-GENERATIVE-MEDIA-STUDIO-001.json"
CONTRACT = "canonical/contracts/FA3-GENERATIVE-MEDIA-STUDIO-CONTRACTS-001.json"
REQUEST_SCHEMA = "canonical/contracts/FA3-GENERATIVE-MEDIA-STUDIO-REQUEST-001.schema.json"
DECISION = "canonical/decisions/FA3-DEC-GENERATIVE-MEDIA-STUDIO-2026-09-28.json"
REFERENCE = "canonical/references/FA3-AUTOM8AI-DONOR-REFERENCE-2026-09-28.json"
INTENT = "canonical/intents/FA3-GENERATIVE-MEDIA-STUDIO-APPLICATION-INTENT-001.json"
ASSESSMENT = "canonical/assessments/FA3-GENERATIVE-MEDIA-STUDIO-REUSE-ASSESSMENT-001.json"
ENFORCEMENT = "canonical/generative-media-studio-enforcement.json"
GATE_RECORD = "canonical/FA3-GATE-GENERATIVE-MEDIA-STUDIO-001.json"
GATE_REGISTRY = "canonical/FA3-GATE-REGISTRY-001.json"
POLICY = "canonical/enforcement-policy.json"
QML = "apps/fa3-generative-media-studio/qml/Main.qml"
BACKEND = "apps/fa3-generative-media-studio/src/StudioBackend.cpp"
CMAKE = "apps/fa3-generative-media-studio/CMakeLists.txt"
DESKTOP = "apps/fa3-generative-media-studio/packaging/org.fa3.GenerativeMediaStudio.desktop"
ACTION = "canonical/actions/media.generate.execute.json"

GATESET_ID = "FA3-GENERATIVE-MEDIA-STUDIO-GATESET-001"
PROFILE_ID = "FA3-GENERATIVE-MEDIA-STUDIO-001"
CONTRACT_ID = "FA3-GENERATIVE-MEDIA-STUDIO-CONTRACTS-001"


def load(root: Path, rel: str) -> dict:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {rel}")
    return value


def gate(root: Path) -> dict:
    root = Path(root).resolve()
    findings: list[dict[str, str]] = []
    required = [
        PROFILE, CONTRACT, REQUEST_SCHEMA, DECISION, REFERENCE, INTENT, ASSESSMENT,
        ENFORCEMENT, GATE_RECORD, GATE_REGISTRY, POLICY, ACTION, QML, BACKEND, CMAKE, DESKTOP,
    ]
    for rel in required:
        if not (root / rel).is_file():
            findings.append({"code": "GMS-001", "message": f"missing:{rel}"})
    if findings:
        return {
            "schema": "fa3.generative-media-studio-gate-report.v1",
            "gate_id": GATESET_ID,
            "result": "FAIL",
            "findings": findings,
            "current_host_runtime_promotion_claim": False,
        }

    p = load(root, PROFILE)
    c = load(root, CONTRACT)
    s = load(root, REQUEST_SCHEMA)
    d = load(root, DECISION)
    r = load(root, REFERENCE)
    i = load(root, INTENT)
    a = load(root, ASSESSMENT)
    e = load(root, ENFORCEMENT)
    gr = load(root, GATE_RECORD)
    registry = load(root, GATE_REGISTRY)
    policy = load(root, POLICY)
    action = load(root, ACTION)
    qml = (root / QML).read_text(encoding="utf-8")
    backend = (root / BACKEND).read_text(encoding="utf-8")
    cmake = (root / CMAKE).read_text(encoding="utf-8")
    desktop = (root / DESKTOP).read_text(encoding="utf-8")

    checks = [
        (p.get("id") == PROFILE_ID, "GMS-002", "profile identity drift"),
        (p.get("capability_count") == 175 and p.get("new_capability") is False, "GMS-003", "capability baseline drift"),
        (p.get("new_architectural_authority") is False, "GMS-004", "authority delta"),
        (p.get("current_host_runtime_promotion_claim") is False, "GMS-005", "profile runtime overclaim"),
        (c.get("id") == CONTRACT_ID and c.get("provider_neutral") is True, "GMS-006", "contract identity/provider neutrality drift"),
        (c.get("request_compilation", {}).get("physical_provider_pin_allowed") is False, "GMS-007", "provider pin allowed"),
        (c.get("request_compilation", {}).get("physical_model_pin_allowed") is False, "GMS-008", "model pin allowed"),
        (c.get("authority_boundaries", {}).get("provider_routing") == "FA3-AUTH-MODEL-ROUTER-001", "GMS-009", "Model Router authority drift"),
        (c.get("authority_boundaries", {}).get("host_resources") == "FA3-AUTH-HOST-RESOURCE-BROKER-001", "GMS-010", "HRB authority drift"),
        (c.get("hardware_audit", {}).get("accelerator_cardinality") == "0..N", "GMS-011", "accelerator cardinality drift"),
        (c.get("hardware_audit", {}).get("cpu_only_architecture_supported") is True, "GMS-012", "CPU-only architecture lost"),
        (s.get("$id") == "FA3-GENERATIVE-MEDIA-STUDIO-REQUEST-001", "GMS-013", "request schema identity drift"),
        (s.get("properties", {}).get("route", {}).get("properties", {}).get("physical_provider_pin", {}).get("const") is False, "GMS-014", "request schema permits provider pin"),
        (s.get("properties", {}).get("route", {}).get("properties", {}).get("physical_model_pin", {}).get("const") is False, "GMS-015", "request schema permits model pin"),
        (d.get("new_capabilities") == 0 and d.get("new_architectural_authorities") == 0 and d.get("capability_count_after") == 175, "GMS-016", "decision baseline delta"),
        (d.get("runtime_claims", {}).get("current_host_provider_execution_pass") is False, "GMS-017", "decision runtime overclaim"),
        (r.get("policy", {}).get("autom8ai_fork_is_canonical_source") is False, "GMS-018", "Autom8AI fork incorrectly authoritative"),
        (r.get("policy", {}).get("original_upstream_is_canonical_donor_source") is True, "GMS-019", "upstream provenance missing"),
        (r.get("policy", {}).get("code_imported_by_this_change") is False, "GMS-020", "unadmitted donor code import claimed"),
        (i.get("schema") == "fa3.application-intent.v1" and i.get("project_id") == PROFILE_ID, "GMS-021", "ApplicationIntent identity drift"),
        (i.get("declared_new_capabilities") == [] and i.get("proposed_authority_roles") == [], "GMS-022", "ApplicationIntent capability/authority delta"),
        (i.get("hardware_audit", {}).get("cpu_only_viable") is True and i.get("hardware_audit", {}).get("accelerator_cardinality") == "0..N", "GMS-023", "ApplicationIntent hardware drift"),
        (i.get("namespace_claims", {}).get("requires_upstream_uninstall") is False and i.get("namespace_claims", {}).get("global_environment_mutation") is False, "GMS-024", "ApplicationIntent coexistence drift"),
        (a.get("schema") == "fa3.reuse-assessment.v1" and a.get("result") == "PASS", "GMS-025", "ReuseAssessment invalid"),
        (a.get("current_host_runtime_promotion_claim") is False and a.get("global_promotion_claim") is False, "GMS-026", "ReuseAssessment promotion overclaim"),
        (a.get("capability_count_after") == 175 and a.get("new_architectural_authorities") == 0, "GMS-027", "ReuseAssessment baseline drift"),
        (a.get("reuse_result", {}).get("existing_capability_reused") == "CAP-111" and a.get("reuse_result", {}).get("autom8ai_fork_treated_as_authority") is False, "GMS-028", "reuse boundary drift"),
        (e.get("gate_id") == GATESET_ID and e.get("fail_closed") is True, "GMS-029", "enforcement identity/fail-closed drift"),
        (gr.get("enforcement_id") == GATESET_ID and gr.get("fail_closed") is True and gr.get("static_pass_promotes_runtime") is False, "GMS-030", "gate record drift"),
        (GATESET_ID in registry.get("mandatory_reference_gates", []) and registry.get("mandatory_reference_gates") == policy.get("mandatory_reference_gates"), "GMS-030A", "global gate registry/policy binding drift"),
        (policy.get("generative_media_studio_profile_id") == PROFILE_ID and policy.get("generative_media_studio_contract_id") == CONTRACT_ID and policy.get("generative_media_studio_gate_id") == GATESET_ID and policy.get("generative_media_studio_current_host_runtime_promotion_claim") is False, "GMS-030B", "global enforcement policy Studio binding drift"),
        (action.get("id") == "media.generate.execute" and action.get("security", {}).get("authentication") == "required" and action.get("security", {}).get("authorization") == "required" and action.get("resources", {}).get("hrb_required") is True and action.get("resources", {}).get("accelerator", {}).get("cardinality") == "0..N" and action.get("evidence", {}).get("required") is True, "GMS-030C", "UAF action contract boundary drift"),
        ("from: 6" in qml and "to: 20" in qml, "GMS-031", "6..20 second Studio control missing"),
        ("FA3 Model Router" in qml, "GMS-032", "Model Router projection missing"),
        ("PENDING_ADMISSION" in backend and "media.generate.execute" in backend, "GMS-033", "request UAF handoff/state binding missing"),
        ("physical_provider_pin" in backend and "physical_model_pin" in backend, "GMS-034", "pin-denial fields missing"),
        ("Qt6::Qml" in cmake and "Qt6::Quick" in cmake, "GMS-035", "Qt6/QML build contract missing"),
        ("org.fa3.GenerativeMediaStudio.desktop" in cmake and "Exec=fa3-generative-media-studio" in desktop, "GMS-036", "desktop launcher not materialized"),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append({"code": code, "message": message})

    for token in ["QProcess", "QNetworkAccessManager", "QTcpSocket", "curl ", "wget ", "system("]:
        if token in backend:
            findings.append({"code": "GMS-037", "message": f"direct execution/network token present:{token}"})

    return {
        "schema": "fa3.generative-media-studio-gate-report.v1",
        "gate_id": GATESET_ID,
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "claims": ["STATIC_APPLICATION_CONTRACT_CONFORMANCE"] if not findings else [],
        "non_claims": ["CURRENT_HOST_BUILD_PASS", "PROVIDER_EXECUTION_PASS", "PRODUCTION_PROMOTION"],
        "current_host_runtime_promotion_claim": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
