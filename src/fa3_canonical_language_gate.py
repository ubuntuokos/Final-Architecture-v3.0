#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-CANONICAL-LANGUAGE-GATESET-001"
POLICY_PATH = "canonical/profiles/FA3-LANGUAGE-POLICY-001.json"
ENFORCEMENT_PATH = "canonical/language-gateway-enforcement.json"

REQUIRED_CANONICAL_SURFACE = {
    "capability_id",
    "command_id",
    "gui_action_id",
    "tool_name",
    "function_name",
    "schema_key",
    "protocol_field",
    "event_type",
    "policy_rule",
    "error_code",
    "audit_security_record_field",
    "metric_name",
    "model_capability_descriptor_field",
    "application_manifest_field",
    "executable_gate_identifier",
    "test_identifier",
    "evidence_record_field",
    "provenance_field",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_conformance(root: Path) -> dict[str, Any]:
    root = root.resolve()
    policy_path = root / POLICY_PATH
    enforcement_path = root / ENFORCEMENT_PATH
    missing = [str(path.relative_to(root)) for path in (policy_path, enforcement_path) if not path.is_file()]
    if missing:
        return {
            "schema": "fa3.canonical-language-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "passed": 0,
            "total": 1,
            "cases": [],
            "findings": [{"code": "CANLANG-ARTIFACTS", "severity": "P0", "message": "canonical language artifacts missing", "missing": missing}],
            "current_host_production_claim": False,
        }

    policy = loadj(policy_path)
    enforcement = loadj(enforcement_path)
    plane = policy.get("language_planes", {}).get("canonical_platform_language", {})
    surface = policy.get("canonical_english_surface", {})
    rules = set(enforcement.get("rules", []))
    checks: list[dict[str, Any]] = []

    def check(case_id: str, condition: bool, detail: str) -> None:
        checks.append({"id": case_id, "result": "PASS" if condition else "FAIL", "detail": detail})

    check(
        "CANLANG-001",
        plane.get("language") == "en" and plane.get("mutable_by_user_locale_selection") is False,
        "canonical machine language is immutable English",
    )
    check(
        "CANLANG-002",
        plane.get("translated_projection_allowed") is True and plane.get("translated_projection_authoritative") is False,
        "localized projections are allowed but non-authoritative",
    )
    check(
        "CANLANG-003",
        plane.get("machine_readable_identifiers_remain_english") is True,
        "machine-readable identifiers remain English",
    )
    check(
        "CANLANG-004",
        set(surface.get("must_remain_english", [])) == REQUIRED_CANONICAL_SURFACE,
        "canonical English surface is complete and exact",
    )
    check(
        "CANLANG-005",
        surface.get("display_labels_may_be_localized") is True
        and surface.get("human_readable_descriptions_may_be_localized") is True
        and surface.get("localized_label_may_replace_machine_identifier") is False
        and surface.get("localized_projection_may_mutate_canonical_payload") is False,
        "human-visible localization cannot replace or mutate canonical machine fields",
    )
    neutrality = policy.get("language_neutrality", {})
    check(
        "CANLANG-006",
        neutrality.get("globally_required_specific_user_language") is None
        and neutrality.get("canonical_machine_language_is_not_user_language_requirement") is True,
        "English canonical machine language does not become a mandatory user language",
    )
    model_plane = policy.get("language_planes", {}).get("model_application_admission_language", {})
    check(
        "CANLANG-007",
        model_plane.get("source") == "FA3-LANGUAGE-ADMISSION-001 validated capability evidence"
        and model_plane.get("native_language_match_required") is False
        and model_plane.get("validated_or_bridged_operability_may_satisfy") is True,
        "model/application admission language remains independent from canonical machine language",
    )
    check(
        "CANLANG-008",
        {"CANONICAL_PLATFORM_MACHINE_LANGUAGE_ENGLISH", "LOCALIZED_PROJECTION_CANNOT_REPLACE_CANONICAL_MACHINE_IDENTIFIERS"}.issubset(rules),
        "canonical machine-language invariants are bound into language enforcement",
    )

    passed = sum(item["result"] == "PASS" for item in checks)
    return {
        "schema": "fa3.canonical-language-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if passed == len(checks) else "FAIL",
        "passed": passed,
        "total": len(checks),
        "cases": checks,
        "findings": [
            {"code": item["id"], "severity": "P0", "message": item["detail"]}
            for item in checks
            if item["result"] != "PASS"
        ],
        "reference_conformance_only": True,
        "current_host_production_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = run_conformance(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
