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
        if row.get("reuse_status") not in {"REFERENCE_ONLY","PATTERN_CANDIDATE","COMPOSITE_REFERENCE"}:
            fail("PATTERN_REUSE_STATUS_INVALID", str(pid))

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
