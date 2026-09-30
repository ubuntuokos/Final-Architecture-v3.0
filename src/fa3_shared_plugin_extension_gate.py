#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import active_capability_count
from fa3_shared_plugin_extension_fabric import (
    HRB,
    MODEL_ROUTER,
    SECURITY,
    ai_access_decision,
    binding_decision,
    validate_manifest,
)

PATHS = {
    "profile": "canonical/profiles/FA3-SHARED-PLUGIN-EXTENSION-FABRIC-001.json",
    "contract": "canonical/contracts/FA3-SHARED-PLUGIN-EXTENSION-CONTRACTS-001.json",
    "registry": "canonical/shared-plugin-extension-registry.json",
    "migration": "canonical/shared-plugin-extension-migration-inventory.json",
    "current_host": "canonical/FA3-SHARED-PLUGIN-EXTENSION-CURRENT-HOST-CONFORMANCE-001.json",
    "decision": "canonical/decisions/FA3-DEC-SHARED-PLUGIN-EXTENSION-AI-ACCESS-2026-09-30.json",
    "enforcement": "canonical/shared-plugin-extension-enforcement.json",
    "intent": "canonical/intents/FA3-SHARED-PLUGIN-EXTENSION-FABRIC-APPLICATION-INTENT-001.json",
    "reuse_assessment": "canonical/assessments/FA3-SHARED-PLUGIN-EXTENSION-FABRIC-REUSE-ASSESSMENT-001.json",
    "decision_assessment": "canonical/assessments/FA3-SHARED-PLUGIN-EXTENSION-FABRIC-DECISION-ASSESSMENT-2026-09-30.json",
}
GATE_ID = "FA3-GATE-SHARED-PLUGIN-EXTENSION-001"


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: object required")
    return value


def finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    missing = [rel for rel in PATHS.values() if not (root / rel).is_file()]
    if missing:
        return {
            "schema": "fa3.shared-plugin-extension-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "findings": [finding("SPE-000", f"missing {p}") for p in missing],
        }

    profile = loadj(root / PATHS["profile"])
    contract = loadj(root / PATHS["contract"])
    registry = loadj(root / PATHS["registry"])
    migration = loadj(root / PATHS["migration"])
    current_host = loadj(root / PATHS["current_host"])
    decision = loadj(root / PATHS["decision"])
    enforcement = loadj(root / PATHS["enforcement"])
    intent = loadj(root / PATHS["intent"])
    reuse_assessment = loadj(root / PATHS["reuse_assessment"])
    decision_assessment = loadj(root / PATHS["decision_assessment"])
    cap_count = active_capability_count(root)

    checks: list[tuple[str, bool, str]] = [
        ("SPE-001", cap_count == 175 and profile.get("capability_count") == 175 and contract.get("capability_count") == 175, "capability baseline must remain 175"),
        ("SPE-002", profile.get("new_capability") is False and profile.get("new_architectural_authority") is False, "shared fabric must not add capability or authority"),
        ("SPE-003", profile.get("component_scope") == "SHARED_ONLY", "plugins/extensions must be shared"),
        ("SPE-004", set(profile.get("component_kinds", [])) == {"PLUGIN", "EXTENSION"}, "both plugin and extension kinds are required"),
        ("SPE-005", profile.get("binding_policy", {}).get("capability_based") is True and profile.get("binding_policy", {}).get("single_application_hard_binding") is False, "binding must be capability based"),
        ("SPE-006", profile.get("binding_policy", {}).get("explicit_activation_required") is True and profile.get("binding_policy", {}).get("automatic_activation") is False, "activation must be explicit"),
        ("SPE-007", profile.get("ai_access", {}).get("toggle_levels") == ["GLOBAL", "APPLICATION", "MODULE", "COMPONENT", "CAPABILITY"], "AI toggle hierarchy drift"),
        ("SPE-008", profile.get("ai_access", {}).get("direct_provider_access") is False and profile.get("ai_access", {}).get("model_router_authority") == MODEL_ROUTER, "AI must route through Model Router"),
        ("SPE-009", profile.get("ai_access", {}).get("silent_fallback") is False, "silent AI fallback must remain forbidden"),
        ("SPE-010", profile.get("ai_access", {}).get("external_shared_component_default") == "DISABLED", "external shared component AI must default disabled"),
        ("SPE-011", profile.get("authority_bindings", {}).get("hardware") == HRB and profile.get("authority_bindings", {}).get("security_admission") == SECURITY, "existing authority bindings changed"),
        ("SPE-012", contract.get("manifest_schema") == "fa3.shared-plugin-extension-manifest.v1", "manifest schema drift"),
        ("SPE-013", contract.get("coexistence", {}).get("upstream_uninstall_required") is False and contract.get("coexistence", {}).get("collision_fail_closed") is True, "Software Coexistence weakened"),
        ("SPE-014", contract.get("hardware_safety", {}).get("hardware_parameter_mutation") is False and contract.get("hardware_safety", {}).get("safety_bypass") is False, "Hardware Safety Envelope weakened"),
        ("SPE-015", contract.get("retroactive_scope") == "ALL_EXISTING_PLANNED_IN_PROGRESS_AND_FUTURE_FA3_APPLICATIONS", "retroactive shared scope missing"),
        ("SPE-016", registry.get("authority") is False and registry.get("automatic_activation") is False, "registry acquired authority or automatic activation"),
        ("SPE-017", migration.get("retroactive_reconciliation_required") is True and migration.get("no_capability_loss") is True, "retroactive capability preservation missing"),
        ("SPE-018", current_host.get("status") == "PENDING_CURRENT_HOST" and current_host.get("production_promotion") is False and current_host.get("physical_proof_required") is True, "current-host state overclaims proof"),
        ("SPE-019", decision.get("approved_architecture") == "SHARED_PLUGIN_EXTENSION_FABRIC_WITH_SCOPED_AI_TOGGLES", "decision record mismatch"),
        ("SPE-020", enforcement.get("fail_closed") is True and enforcement.get("capability_count") == 175, "enforcement baseline drift"),
        ("SPE-020A", intent.get("schema") == "fa3.application-intent.v1" and intent.get("project_id") == profile.get("id") and "FA3-REUSE-DISCOVERY-001" in intent.get("integration_requirements", []), "ApplicationIntent adoption/reuse binding missing"),
        ("SPE-020B", reuse_assessment.get("schema") == "fa3.reuse-assessment.v1" and reuse_assessment.get("result") == "PASS" and profile.get("id") in reuse_assessment.get("covered_ids", []) and reuse_assessment.get("intent_path") == PATHS["intent"], "Reuse Assessment adoption coverage missing"),
        ("SPE-020C", any(isinstance(row, dict) and row.get("source_family_id") == "FA3-KHRONOS-OPEN-STANDARDS-001" and row.get("review_status") in {"MATCHED", "REVIEWED_NO_MATCH"} and row.get("authority") is False and row.get("automatic_selection") is False for row in reuse_assessment.get("mandatory_source_reviews", [])), "mandatory Khronos source-family review missing"),
        ("SPE-020D", decision_assessment.get("schema") == "fa3.decision-fabric-assessment.v1" and decision_assessment.get("assessment") == "NOT_APPLICABLE" and profile.get("id") in decision_assessment.get("covered_ids", []) and decision_assessment.get("project_radar_checked") is True, "Decision Fabric applicability assessment missing"),
        ("SPE-020E", all(decision_assessment.get("security_boundary", {}).get(field) is False for field in ("may_grant_permission", "may_expand_candidate_set", "may_create_agent", "may_admit_model", "may_admit_provider")), "Decision Fabric security boundary weakened"),
    ]

    sample = {
        "schema": "fa3.shared-plugin-extension-manifest.v1",
        "component_id": "FA3-TEST-SHARED-COMPONENT",
        "kind": "PLUGIN",
        "scope": "SHARED",
        "authority": False,
        "automatic_activation": False,
        "capabilities": {"provides": ["fa3.test.enhance"], "requires_host": ["fa3.test.host"]},
        "host_contracts": ["fa3.test.host.v1"],
        "provenance": {"source": "fixture", "immutable_revision": "1", "content_sha256": "a"*64, "license": "MIT"},
        "ai": {
            "uses_ai": True,
            "capabilities": ["fa3.test.ai"],
            "default_access": "DISABLED",
            "direct_provider_access": False,
            "silent_fallback": False,
            "route_authority": MODEL_ROUTER,
        },
        "runtime": {"hardware_authority": HRB},
        "security": {"admission_authority": SECURITY},
    }
    try:
        validate_manifest(sample)
        app = {
            "application_id": "fa3.test",
            "accepted_component_kinds": ["PLUGIN", "EXTENSION"],
            "host_capabilities": ["fa3.test.host"],
            "host_contracts": ["fa3.test.host.v1"],
            "capabilities": [],
            "denied_components": [],
        }
        binding = binding_decision(sample, app)
        denied = ai_access_decision(sample, capability="fa3.test.ai", global_policy={"state": "DISABLED", "local_allowed": True, "remote_allowed": False})
        allowed = ai_access_decision(sample, capability="fa3.test.ai", global_policy={"state": "ENABLED", "local_allowed": True, "remote_allowed": False})
        checks.extend([
            ("SPE-021", binding.eligible and binding.added_capabilities == ("fa3.test.enhance",), "capability-based binding regression"),
            ("SPE-022", not denied.allowed and denied.reason == "GLOBAL_AI_DISABLED", "global AI off switch regression"),
            ("SPE-023", allowed.allowed and allowed.route_authority == MODEL_ROUTER and not allowed.silent_fallback_allowed, "AI route/silent-fallback regression"),
        ])
    except Exception as exc:
        checks.append(("SPE-024", False, f"executable contract regression: {exc}"))

    findings = [finding(code, msg) for code, ok, msg in checks if not ok]
    report = {
        "schema": "fa3.shared-plugin-extension-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "checks": len(checks),
        "blocking_findings": len(findings),
        "findings": findings,
        "current_host_runtime_promoted": False,
        "capability_count": cap_count,
        "new_capability": False,
        "new_architectural_authority": False,
    }
    out = root / "reports/shared-plugin-extension-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    report = gate(args.root)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
