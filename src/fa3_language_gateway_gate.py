#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

GATE_ID = "FA3-LANGUAGE-GATEWAY-GATESET-001"
PROFILE_IDS = (
    "FA3-LANGUAGE-POLICY-001",
    "FA3-LANGUAGE-FABRIC-001",
    "FA3-LANGUAGE-ADMISSION-001",
    "FA3-LLM-GATEWAY-001",
)
ALLOWED_LANGUAGE_STATUS = {"NATIVE", "VALIDATED", "BRIDGED", "UNVERIFIED", "UNSUPPORTED"}


class LanguagePolicyDenied(ValueError):
    pass


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_locale(value: str) -> str:
    value = value.strip().replace("_", "-")
    if not value:
        raise LanguagePolicyDenied("language locale is required")
    parts = value.split("-")
    if not re.fullmatch(r"[A-Za-z]{2,3}", parts[0]):
        raise LanguagePolicyDenied(f"invalid BCP47 language tag: {value}")
    lang = parts[0].lower()
    if len(parts) == 1:
        return lang
    normalized = [lang]
    for part in parts[1:]:
        if len(part) == 2 and part.isalpha():
            normalized.append(part.upper())
        elif len(part) == 4 and part.isalpha():
            normalized.append(part.title())
        elif re.fullmatch(r"[A-Za-z0-9]{1,8}", part):
            normalized.append(part)
        else:
            raise LanguagePolicyDenied(f"invalid BCP47 language tag: {value}")
    return "-".join(normalized)


def validate_language_selection(primary: str, secondary: str, additional: list[str] | None = None) -> dict[str, Any]:
    primary_n = normalize_locale(primary)
    secondary_n = normalize_locale(secondary)
    if primary_n.lower() == secondary_n.lower():
        raise LanguagePolicyDenied("primary and secondary languages must be distinct")
    additional_n: list[str] = []
    seen = {primary_n.lower(), secondary_n.lower()}
    for value in additional or []:
        item = normalize_locale(value)
        if item.lower() in seen:
            continue
        seen.add(item.lower())
        additional_n.append(item)
    return {
        "primary_language": primary_n,
        "secondary_language": secondary_n,
        "additional_languages": additional_n,
        "required_languages": [primary_n, secondary_n],
    }


def requires_hungarian_support(selection: dict[str, Any]) -> bool:
    required = {str(v).lower() for v in selection.get("required_languages", [])}
    return bool(required & {"hu", "hu-hu"})


def language_capability_is_operable(status: str) -> bool:
    if status not in ALLOWED_LANGUAGE_STATUS:
        raise LanguagePolicyDenied(f"unknown language capability status: {status}")
    return status in {"NATIVE", "VALIDATED", "BRIDGED"}


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def run_conformance(root: Path) -> dict[str, Any]:
    root = root.resolve()
    paths = {
        "policy": root / "canonical/profiles/FA3-LANGUAGE-POLICY-001.json",
        "fabric": root / "canonical/profiles/FA3-LANGUAGE-FABRIC-001.json",
        "admission": root / "canonical/profiles/FA3-LANGUAGE-ADMISSION-001.json",
        "gateway": root / "canonical/profiles/FA3-LLM-GATEWAY-001.json",
        "enforcement": root / "canonical/language-gateway-enforcement.json",
        "litellm": root / "deployment/litellm/config.yaml",
        "gui": root / "apps/fa3-control-center/qml/LanguageControlPage.qml",
    }
    missing = [str(p.relative_to(root)) for p in paths.values() if not p.is_file()]
    if missing:
        return {
            "schema": "fa3.language-gateway-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "passed": 0,
            "total": 1,
            "cases": [],
            "findings": [_finding("LANG-GW-ARTIFACTS", "required language/gateway artifacts missing", missing=missing)],
            "current_host_production_claim": False,
        }

    policy = loadj(paths["policy"])
    fabric = loadj(paths["fabric"])
    admission = loadj(paths["admission"])
    gateway = loadj(paths["gateway"])
    enforcement = loadj(paths["enforcement"])
    litellm = paths["litellm"].read_text(encoding="utf-8")
    gui = paths["gui"].read_text(encoding="utf-8")
    profiles = [policy, fabric, admission, gateway]
    rules = set(enforcement.get("rules", []))
    checks: list[dict[str, Any]] = []

    def check(case_id: str, condition: bool, detail: str) -> None:
        checks.append({"id": case_id, "result": "PASS" if condition else "FAIL", "detail": detail})

    install = policy.get("installation_contract", {})
    check("LANG-GW-001", all(p.get("status") == "CANONICAL" and p.get("priority") == "P0" and p.get("requirement") == "MUST" for p in profiles), "all four profiles are canonical P0/MUST")
    check("LANG-GW-002", install.get("primary_language", {}).get("cardinality") == 1 and install.get("primary_language", {}).get("required") is True, "exactly one primary language required")
    check("LANG-GW-003", install.get("secondary_language", {}).get("cardinality") == 1 and install.get("secondary_language", {}).get("required") is True and install.get("primary_secondary_must_differ") is True, "exactly one distinct secondary language required")
    check("LANG-GW-004", install.get("additional_languages", {}).get("cardinality") == "0..N", "additional languages are optional")
    check("LANG-GW-005", policy.get("language_neutrality", {}).get("globally_required_specific_language") is None and policy.get("language_neutrality", {}).get("hungarian_is_global_default") is False, "no globally hardcoded language")
    check("LANG-GW-006", policy.get("language_neutrality", {}).get("hungarian_specific_assets_required_when") == "hu-HU is primary_language OR secondary_language", "Hungarian assets are conditional on system-language selection")
    check("LANG-GW-007", set(admission.get("capability_status_enum", [])) == ALLOWED_LANGUAGE_STATUS, "language capability status taxonomy is fixed")
    check("LANG-GW-008", admission.get("selected_system_language_obligation", {}).get("validated_language_capability_required") is True and admission.get("selected_system_language_obligation", {}).get("native_model_required") is False, "validated operability is required without forcing a language-specific LLM")
    check("LANG-GW-009", fabric.get("routing_contract", {}).get("translation_is_derived_projection") is True and fabric.get("routing_contract", {}).get("original_source_remains_authoritative") is True, "translation remains a derived projection")
    check("LANG-GW-010", fabric.get("language_context", {}).get("required") == ["user_language", "work_language", "output_language"], "user/work/output language context is explicit")
    check("LANG-GW-011", fabric.get("routing_contract", {}).get("language_need_may_override_privacy_policy") is False and fabric.get("routing_contract", {}).get("language_need_may_override_provider_policy") is False, "language requirements cannot override privacy/provider policy")
    check("LANG-GW-012", fabric.get("routing_contract", {}).get("external_translation_for_secret_data") == "DENY", "SECRET external translation denied")
    check("LANG-GW-013", set(fabric.get("fallback_domains_must_remain_distinct", [])) == {"language", "model", "provider", "infrastructure"}, "fallback domains remain separate")
    check("LANG-GW-014", gateway.get("reference_implementation") == "LiteLLM Proxy" and gateway.get("language_boundary", {}).get("gateway_is_language_neutral") is True, "LiteLLM is provider/language-neutral gateway")
    nonresp = set(gateway.get("non_responsibilities", []))
    check("LANG-GW-015", {"model weight storage or installation", "hardware scheduling or accelerator leasing", "secret source of truth", "language translation or locale governance"}.issubset(nonresp), "LiteLLM cannot absorb registry/HRB/Vault/Language Fabric responsibilities")
    check("LANG-GW-016", gateway.get("blackhole_boundary", {}).get("blackhole_is_one_gateway_client") is True and gateway.get("blackhole_boundary", {}).get("all_fa3_llm_clients_must_route_through_blackhole") is False, "Blackhole is a client, not the universal front door")
    route = gateway.get("routing_policy", {})
    check("LANG-GW-017", route.get("default") == "LOCAL_FIRST" and route.get("external_paid_providers_default_enabled") is False, "local-first and external providers disabled by default")
    check("LANG-GW-018", route.get("local_failure_may_silently_fallback_to_cloud") is False and route.get("fallback_must_remain_in_policy_equivalent_domain") is True, "no silent local-to-cloud fallback")
    check("LANG-GW-019", gateway.get("security", {}).get("plaintext_secrets_in_config") == "FORBIDDEN" and "os.environ/FA3_LITELLM_MASTER_KEY" in litellm, "secrets are runtime injected")
    check("LANG-GW-020", not re.search(r"(?im)^\s*(master_key|api_key):\s*[\"']?(?!os\.environ/)(?!\$\{)[^#\n]+", litellm), "LiteLLM config contains no committed plaintext key")
    check("LANG-GW-021", "hungarian-only" not in litellm.lower() and "blacklist:" not in litellm.lower(), "no global language blacklist in LiteLLM")
    check("LANG-GW-022", "pass_through_headers: true" not in litellm.lower() and "forward_client_headers_to_llm_api: true" not in litellm.lower(), "client-header forwarding is not enabled")
    check("LANG-GW-023", not re.search(r"api_base:\s*[\"']?http://localhost", litellm, re.I), "container backend endpoints are not hardcoded to LiteLLM localhost")
    check("LANG-GW-024", gateway.get("authority_bindings", {}).get("host_resource_admission") == "FA3-AUTH-HOST-RESOURCE-BROKER-001" and gateway.get("authority_bindings", {}).get("artifact_model_registry") == "FA3-REG-ARTIFACT-MODEL-001", "HRB and model-registry authority boundaries retained")
    check("LANG-GW-025", all(p.get("capability_count_delta") == 0 and p.get("authority_delta") == 0 for p in profiles), "no capability or authority count increase")
    check("LANG-GW-026", all(rule in rules for rule in ["EXACTLY_ONE_PRIMARY_LANGUAGE_REQUIRED", "EXACTLY_ONE_DISTINCT_SECONDARY_LANGUAGE_REQUIRED", "NO_SILENT_LOCAL_TO_CLOUD_FALLBACK", "PLAINTEXT_LITELLM_SECRETS_FORBIDDEN"]), "mandatory P0 rule set contains critical invariants")
    check("LANG-GW-027", "primaryLanguage" in gui and "secondaryLanguage" in gui and "primaryLanguage === secondaryLanguage" in gui, "GUI projects mandatory distinct primary/secondary language policy")

    # Executable policy cases: positive and negative branches.
    try:
        sel_hu = validate_language_selection("hu-HU", "en-US", ["de-DE"])
        positive = sel_hu["primary_language"] == "hu-HU" and sel_hu["secondary_language"] == "en-US" and requires_hungarian_support(sel_hu)
    except LanguagePolicyDenied:
        positive = False
    check("LANG-GW-028", positive, "hu-HU primary + en-US secondary is accepted and activates Hungarian support")

    try:
        sel_intl = validate_language_selection("en-US", "de-DE")
        international = not requires_hungarian_support(sel_intl)
    except LanguagePolicyDenied:
        international = False
    check("LANG-GW-029", international, "non-Hungarian international installation does not activate Hungarian-specific dependency")

    duplicate_denied = False
    try:
        validate_language_selection("en-US", "en-US")
    except LanguagePolicyDenied:
        duplicate_denied = True
    check("LANG-GW-030", duplicate_denied, "identical primary/secondary language fails closed")
    check("LANG-GW-031", language_capability_is_operable("NATIVE") and language_capability_is_operable("VALIDATED") and language_capability_is_operable("BRIDGED") and not language_capability_is_operable("UNVERIFIED") and not language_capability_is_operable("UNSUPPORTED"), "language admission status semantics are executable")

    passed = sum(case["result"] == "PASS" for case in checks)
    findings = [_finding(case["id"], case["detail"]) for case in checks if case["result"] != "PASS"]
    return {
        "schema": "fa3.language-gateway-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if passed == len(checks) else "FAIL",
        "passed": passed,
        "total": len(checks),
        "cases": checks,
        "findings": findings,
        "reference_conformance_only": True,
        "current_host_status": "PENDING_CURRENT_HOST",
        "current_host_production_claim": False,
    }


def gate(root: Path) -> dict[str, Any]:
    report = run_conformance(root)
    writej(root.resolve() / "reports/language-gateway-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
