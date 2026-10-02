#!/usr/bin/env python3
"""Validate and inspect the non-authoritative FA3 shared-module pattern catalogue."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CATALOGUE = "canonical/FA3-SHARED-MODULE-PATTERN-CATALOGUE-001.json"
DONORS = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
APPS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

REQUIRED_POLICY = {
    "donor_registry_remains_only_donor_identity_authority": True,
    "pattern_catalogue_is_non_authoritative": True,
    "pattern_registration_does_not_admit_code": True,
    "pattern_registration_does_not_admit_runtime": True,
    "pattern_registration_does_not_admit_provider_or_model": True,
    "analysis_only_source_cannot_receive_donor_id": True,
    "new_canonical_donor_requires_explicit_owner_donornak_marker": True,
    "shared_first_for_multi_application_patterns": True,
    "retroactive_application_impact_required": True,
    "capability_non_regression_required": True,
    "current_host_alignment_required_after_structural_or_runtime_materialization": True,
    "model_router_authority_preserved": True,
    "hrb_authority_preserved": True,
    "orchestrator_authority_preserved": True,
    "secret_broker_authority_preserved": True,
    "layer_guard_and_ai_disable_policy_preserved": True,
    "materialized_component_capability_bindings_canonical_only": True,
    "materialized_component_manual_capability_ids_forbidden": True,
    "materialized_component_runtime_activation_separately_gated": True,
}

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value

def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    catalogue = load(root / CATALOGUE)
    donors = load(root / DONORS)
    apps = load(root / APPS)
    findings: list[dict[str, str]] = []

    def fail(code: str, detail: str) -> None:
        findings.append({"code": code, "detail": detail})

    if catalogue.get("id") != "FA3-SHARED-MODULE-PATTERN-CATALOGUE-001":
        fail("CATALOGUE_ID_INVALID", str(catalogue.get("id")))
    if catalogue.get("authority") is not False:
        fail("CATALOGUE_AUTHORITY_FORBIDDEN", "authority must be false")
    if catalogue.get("capability_baseline") != 175 or catalogue.get("new_capability") is not False:
        fail("CAPABILITY_BASELINE_DRIFT", str(catalogue.get("capability_baseline")))
    if catalogue.get("new_architectural_authority") is not False:
        fail("ARCHITECTURAL_AUTHORITY_DELTA_FORBIDDEN", "new authority declared")
    for key, expected in REQUIRED_POLICY.items():
        if catalogue.get("policy", {}).get(key) is not expected:
            fail("MANDATORY_PATTERN_POLICY_MISSING", key)

    donor_rows = donors.get("entries", [])
    donor_by_id = {
        row.get("donor_id"): row
        for row in donor_rows
        if isinstance(row, dict) and isinstance(row.get("donor_id"), str)
    }
    if donors.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
        fail("DONOR_REGISTRY_INVALID", DONORS)
    if donors.get("backfill", {}).get("entry_count") != len(donor_rows):
        fail("DONOR_REGISTRY_COUNT_DRIFT", DONORS)

    app_ids = {
        row.get("application_id")
        for row in apps.get("applications", [])
        if isinstance(row, dict) and isinstance(row.get("application_id"), str)
    }

    classes = catalogue.get("pattern_classes", [])
    if not isinstance(classes, list) or len(classes) != len(set(classes)):
        fail("PATTERN_CLASS_SET_INVALID", "pattern_classes")
    class_set = set(classes)

    analysis_rows = catalogue.get("analysis_only_sources", [])
    analysis_ids: set[str] = set()
    locators: set[str] = set()
    for row in analysis_rows:
        if not isinstance(row, dict):
            fail("ANALYSIS_SOURCE_INVALID", repr(row))
            continue
        sid = row.get("id")
        locator = row.get("locator")
        if not isinstance(sid, str) or not sid.startswith("ANALYSIS-") or sid in analysis_ids:
            fail("ANALYSIS_SOURCE_ID_INVALID", str(sid))
        else:
            analysis_ids.add(sid)
        if not isinstance(locator, str) or not locator.startswith("https://") or locator in locators:
            fail("ANALYSIS_SOURCE_LOCATOR_INVALID", str(locator))
        else:
            locators.add(locator)
        if row.get("registration_status") != "OWNER_MARKER_REQUIRED":
            fail("ANALYSIS_SOURCE_PRETENDS_DONOR", str(sid))
        if "donor_id" in row:
            fail("ANALYSIS_SOURCE_DONOR_ID_FORBIDDEN", str(sid))

    modules = catalogue.get("shared_module_targets", [])
    module_ids: set[str] = set()
    for row in modules:
        if not isinstance(row, dict):
            fail("SHARED_MODULE_INVALID", repr(row))
            continue
        mid = row.get("id")
        consumers = row.get("consumer_application_ids")
        if not isinstance(mid, str) or not mid.startswith("FA3-SHARED-") or mid in module_ids:
            fail("SHARED_MODULE_ID_INVALID", str(mid))
        else:
            module_ids.add(mid)
        if not isinstance(consumers, list) or len(set(consumers)) < 2:
            fail("SHARED_MODULE_REQUIRES_MULTIPLE_CONSUMERS", str(mid))
        else:
            for aid in consumers:
                if aid not in app_ids:
                    fail("UNKNOWN_CONSUMER_APPLICATION", f"{mid}:{aid}")

    pattern_ids: set[str] = set()
    referenced_donors: set[str] = set()
    referenced_analysis: set[str] = set()
    for row in catalogue.get("patterns", []):
        if not isinstance(row, dict):
            fail("PATTERN_INVALID", repr(row))
            continue
        pid = row.get("id")
        if not isinstance(pid, str) or not pid.startswith("FA3-") or pid in pattern_ids:
            fail("PATTERN_ID_INVALID", str(pid))
        else:
            pattern_ids.add(pid)
        if row.get("class") not in class_set:
            fail("PATTERN_CLASS_UNKNOWN", f"{pid}:{row.get('class')}")
        for donor_id in row.get("canonical_donor_ids", []):
            referenced_donors.add(donor_id)
            donor = donor_by_id.get(donor_id)
            if donor is None:
                fail("UNKNOWN_CANONICAL_DONOR", f"{pid}:{donor_id}")
            elif donor.get("status") == "SUPERSEDED":
                fail("SUPERSEDED_DONOR_PATTERN_REFERENCE", f"{pid}:{donor_id}")
            elif donor.get("authority") is not False:
                fail("DONOR_AUTHORITY_FORBIDDEN", f"{pid}:{donor_id}")
        for sid in row.get("analysis_source_ids", []):
            referenced_analysis.add(sid)
            if sid not in analysis_ids:
                fail("UNKNOWN_ANALYSIS_SOURCE", f"{pid}:{sid}")
        targets = row.get("shared_module_ids", [])
        if not isinstance(targets, list) or not targets:
            fail("PATTERN_WITHOUT_SHARED_TARGET", str(pid))
        else:
            for mid in targets:
                if mid not in module_ids:
                    fail("UNKNOWN_SHARED_MODULE_TARGET", f"{pid}:{mid}")
        if row.get("reuse_status") not in {"REFERENCE_ONLY","PATTERN_CANDIDATE","COMPOSITE_REFERENCE","ADOPTED_PATTERN"}:
            fail("PATTERN_REUSE_STATUS_INVALID", str(pid))

    expected_components = {
        "FA3-SHARED-AI-INTERACTION-001",
        "FA3-SHARED-KNOWLEDGE-RETRIEVAL-001",
        "FA3-SHARED-MULTIMODAL-SOURCE-001",
        "FA3-SHARED-CONVERSATION-SESSION-001",
        "FA3-SHARED-TOOL-ACTION-MEDIATION-001",
        "FA3-SHARED-EXECUTION-SECURITY-001",
    }
    materialized_rows = catalogue.get("materialized_shared_components", [])
    materialized_ids: set[str] = set()
    app_shared_by_id = {
        row.get("id"): row
        for row in apps.get("shared_capabilities", [])
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    allowed_pattern_refs = module_ids | pattern_ids
    for row in materialized_rows:
        if not isinstance(row, dict):
            fail("MATERIALIZED_COMPONENT_INVALID", repr(row))
            continue
        cid = row.get("id")
        profile_id = row.get("profile_id")
        contract_id = row.get("contract_id")
        if not isinstance(cid, str) or cid in materialized_ids:
            fail("MATERIALIZED_COMPONENT_ID_INVALID", str(cid))
            continue
        materialized_ids.add(cid)
        if row.get("binding_semantics") != "DERIVED_FROM_CANONICAL_PROFILE_CONTRACT_ONLY":
            fail("MATERIALIZED_COMPONENT_BINDING_SEMANTICS_INVALID", cid)
        impact_state = row.get("current_host_impact")
        if cid == "FA3-SHARED-EXECUTION-SECURITY-001":
            if impact_state != "RUNTIME_REQUALIFICATION_REQUIRED":
                fail("MATERIALIZED_COMPONENT_RUNTIME_IMPACT_INVALID", cid)
        elif impact_state != "NO_RUNTIME_IMPACT":
            fail("MATERIALIZED_COMPONENT_RUNTIME_IMPACT_INVALID", cid)
        for ref in row.get("pattern_references", []):
            if ref not in allowed_pattern_refs:
                fail("MATERIALIZED_COMPONENT_PATTERN_REFERENCE_UNKNOWN", f"{cid}:{ref}")

        profile_path = root / "canonical/profiles" / f"{profile_id}.json"
        contract_path = root / "canonical/contracts" / f"{contract_id}.json"
        try:
            profile = load(profile_path)
        except Exception:
            fail("MATERIALIZED_COMPONENT_PROFILE_MISSING", f"{cid}:{profile_id}")
            continue
        try:
            contract = load(contract_path)
        except Exception:
            fail("MATERIALIZED_COMPONENT_CONTRACT_MISSING", f"{cid}:{contract_id}")
            continue

        if profile.get("id") != profile_id or contract.get("id") != contract_id:
            fail("MATERIALIZED_COMPONENT_RECORD_ID_MISMATCH", cid)
        for source_name, source in (("profile", profile), ("contract", contract)):
            if source.get("capability_count") != 175:
                fail("MATERIALIZED_COMPONENT_CAPABILITY_COUNT_DRIFT", f"{cid}:{source_name}")
            if source.get("new_capability") is not False:
                fail("MATERIALIZED_COMPONENT_NEW_CAPABILITY_FORBIDDEN", f"{cid}:{source_name}")
            if source.get("new_architectural_authority") is not False:
                fail("MATERIALIZED_COMPONENT_NEW_AUTHORITY_FORBIDDEN", f"{cid}:{source_name}")
            if source.get("provider_neutral") is not True:
                fail("MATERIALIZED_COMPONENT_PROVIDER_NEUTRAL_REQUIRED", f"{cid}:{source_name}")

        profile_caps = profile.get("capability_bindings", [])
        contract_caps = contract.get("capability_bindings", [])
        if (
            not isinstance(profile_caps, list)
            or not profile_caps
            or not isinstance(contract_caps, list)
            or sorted(set(profile_caps)) != sorted(set(contract_caps))
        ):
            fail("MATERIALIZED_COMPONENT_BINDING_PARITY_INVALID", cid)
        for cap in set(profile_caps if isinstance(profile_caps, list) else []):
            if not isinstance(cap, str) or not cap.startswith("CAP-"):
                fail("MATERIALIZED_COMPONENT_CAPABILITY_ID_INVALID", f"{cid}:{cap}")
                continue
            try:
                number = int(cap.split("-", 1)[1])
            except (ValueError, IndexError):
                number = 0
            if number < 1 or number > 175:
                fail("MATERIALIZED_COMPONENT_CAPABILITY_ID_OUT_OF_BASELINE", f"{cid}:{cap}")

        runtime = profile.get("runtime_materialization", {})
        for key in (
            "new_service", "new_daemon", "new_port", "new_socket",
            "new_package_dependency", "provider_activation", "model_selection",
            "hardware_mutation",
        ):
            if runtime.get(key) is not False:
                fail("MATERIALIZED_COMPONENT_RUNTIME_ACTIVATION_FORBIDDEN", f"{cid}:{key}")

        app_row = app_shared_by_id.get(cid)
        if app_row is None:
            fail("MATERIALIZED_COMPONENT_APPLICATION_BINDING_MISSING", cid)
        else:
            app_bindings = app_row.get("fa3_bindings", {})
            if app_bindings.get("capability_ids"):
                fail("MATERIALIZED_COMPONENT_MANUAL_CAPABILITY_BINDING_FORBIDDEN", cid)
            if profile_id not in app_bindings.get("profile_ids", []):
                fail("MATERIALIZED_COMPONENT_PROFILE_LINK_MISSING", cid)
            if contract_id not in app_bindings.get("contract_ids", []):
                fail("MATERIALIZED_COMPONENT_CONTRACT_LINK_MISSING", cid)
            app_impact = (app_row.get("current_host_impact") or {}).get("classification")
            if cid == "FA3-SHARED-EXECUTION-SECURITY-001":
                if app_impact != "RUNTIME_REQUALIFICATION_REQUIRED":
                    fail("MATERIALIZED_COMPONENT_APPLICATION_RUNTIME_IMPACT_INVALID", cid)
            elif app_impact != "NO_RUNTIME_IMPACT":
                fail("MATERIALIZED_COMPONENT_APPLICATION_RUNTIME_IMPACT_INVALID", cid)

    if materialized_ids != expected_components:
        fail(
            "MATERIALIZED_COMPONENT_SET_INVALID",
            ",".join(sorted(materialized_ids ^ expected_components)),
        )

    impact = catalogue.get("current_host_impact", {})
    if impact.get("classification") != "NO_RUNTIME_IMPACT":
        fail("STATIC_CATALOGUE_RUNTIME_IMPACT_INVALID", str(impact.get("classification")))

    return {
        "schema": "fa3.shared-module-pattern-catalogue-validation.v1",
        "catalogue_id": catalogue.get("id"),
        "capability_baseline": catalogue.get("capability_baseline"),
        "summary": {
            "patterns": len(pattern_ids),
            "shared_module_targets": len(module_ids),
            "analysis_only_sources": len(analysis_ids),
            "resolved_canonical_donors": len(referenced_donors),
            "referenced_analysis_sources": len(referenced_analysis),
            "materialized_shared_components": len(materialized_ids),
        },
        "validation": {
            "result": "PASS" if not findings else "FAIL",
            "findings": findings,
        },
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = validate(Path(args.root))
    print(json.dumps(report if not args.summary else {
        "catalogue_id": report["catalogue_id"],
        "capability_baseline": report["capability_baseline"],
        **report["summary"],
        "result": report["validation"]["result"],
        "findings": report["validation"]["findings"],
    }, indent=2, ensure_ascii=False))
    if args.check and report["validation"]["result"] != "PASS":
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
