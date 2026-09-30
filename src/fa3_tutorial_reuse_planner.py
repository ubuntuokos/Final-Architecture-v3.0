#!/usr/bin/env python3
"""Non-authoritative FA3 tutorial reuse and shared-capability planner.

The planner reads only already-published donor references and static FA3 registries.
It never executes tutorial commands, installs dependencies, admits providers,
changes the 175-capability baseline, or promotes runtime state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

DONOR_REGISTRY = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
APP_CATALOG = "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json"
APP_LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
CAP_MATRIX = "canonical/conformance-matrix.csv"
CAP_MODEL = "canonical/FA3-CAPABILITY-MODEL-175-001.json"
POLICY = "canonical/FA3-TUTORIAL-SHARED-CAPABILITY-POLICY-001.json"
SCHEMA = "canonical/schemas/FA3-TUTORIAL-REFERENCE-SCHEMA-001.json"
HOST_IMPACT = "canonical/FA3-TUTORIAL-SHARED-CAPABILITY-CURRENT-HOST-IMPACT-001.json"
RIGHTS = {"PERMISSIVE", "REFERENCE_ONLY", "UNKNOWN_REFERENCE_ONLY", "OWNER_AUTHORED"}
ALLOWANCES = {"FUNCTIONAL_ANALYSIS_ONLY", "CLEAN_FA3_REEXPRESSION", "LICENSE_REVIEWED_REUSE"}
PLACEMENTS = {"AUTO", "APPLICATION_LOCAL", "SHARED"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def application_inventory(root: Path) -> dict[str, dict[str, Any]]:
    catalog = load_json(root / APP_CATALOG)
    links = load_json(root / APP_LINKS)
    apps: dict[str, dict[str, Any]] = {}
    for item in catalog.get("applications", []):
        aid = "studio." + str(item["id"])
        apps[aid] = {
            "application_id": aid,
            "name": item["name"],
            "lifecycle": "CATALOG_" + str(item.get("admission", "UNKNOWN")),
            "aliases": [item["name"], str(item["id"]), aid],
        }
    for item in links.get("applications", []):
        aid = str(item["application_id"])
        apps[aid] = {
            "application_id": aid,
            "name": item["name"],
            "lifecycle": item["lifecycle"],
            "aliases": [item["name"], aid] + list(item.get("aliases", [])),
        }
    return apps


def capability_inventory(root: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    with (root / CAP_MATRIX).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cid = str(row.get("capability_id", "")).strip()
            if cid:
                result[cid] = {
                    "capability_id": cid,
                    "name": str(row.get("capability", "")).strip(),
                    "layers": str(row.get("layers", "")).strip(),
                }
    return result


def match_capabilities(hints: list[str], caps: dict[str, dict[str, str]]) -> tuple[list[str], list[str]]:
    by_name: dict[str, list[str]] = {}
    for cid, row in caps.items():
        by_name.setdefault(norm(row["name"]), []).append(cid)
    matches: set[str] = set()
    ambiguous: set[str] = set()
    for raw in hints:
        hint = str(raw).strip()
        if hint in caps:
            matches.add(hint)
        else:
            found = by_name.get(norm(hint), [])
            if len(found) == 1:
                matches.add(found[0])
            elif len(found) > 1:
                ambiguous.add(hint)
    return sorted(matches), sorted(ambiguous)


def match_applications(hints: list[str], apps: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    aliases: dict[str, set[str]] = {}
    for aid, row in apps.items():
        for alias in row["aliases"]:
            aliases.setdefault(norm(str(alias)), set()).add(aid)
    matches: set[str] = set()
    ambiguous: set[str] = set()
    for raw in hints:
        hint = str(raw).strip()
        if hint in apps:
            matches.add(hint)
        else:
            found = aliases.get(norm(hint), set())
            if len(found) == 1:
                matches.update(found)
            elif len(found) > 1:
                ambiguous.add(hint)
    return sorted(matches), sorted(ambiguous)


def validate_input(tutorial: dict[str, Any], donor: dict[str, Any] | None) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def add(code: str, message: str) -> None:
        findings.append({"code": code, "message": message})

    if tutorial.get("schema") != "fa3.tutorial-reference-input.v1":
        add("TUT-INPUT-001", "tutorial input schema identity mismatch")
    if tutorial.get("reference_class") != "TUTORIAL_REFERENCE":
        add("TUT-INPUT-002", "reference_class must be TUTORIAL_REFERENCE")
    if donor is None:
        add("TUT-REG-001", "tutorial donor_id is not a published ACCEPTED_REFERENCE planning source")
    provenance = tutorial.get("provenance")
    if not isinstance(provenance, dict):
        add("TUT-RIGHTS-001", "provenance object is required")
    else:
        if provenance.get("rights_status") not in RIGHTS:
            add("TUT-RIGHTS-002", "rights_status is missing or unsupported")
        if provenance.get("reuse_allowance") not in ALLOWANCES:
            add("TUT-RIGHTS-003", "reuse_allowance is missing or unsupported")
        if not str(provenance.get("source", "")).strip():
            add("TUT-RIGHTS-004", "source provenance is required")
    features = tutorial.get("feature_units")
    if not isinstance(features, list) or not features:
        add("TUT-TFU-001", "at least one Tutorial Feature Unit is required")
        return findings
    seen: set[str] = set()
    for feature in features:
        if not isinstance(feature, dict):
            add("TUT-TFU-002", "feature_units must contain objects")
            continue
        fid = str(feature.get("feature_id", "")).strip()
        if not fid or fid in seen:
            add("TUT-TFU-003", "feature_id must be non-empty and unique")
        seen.add(fid)
        if not str(feature.get("name", "")).strip() or not str(feature.get("intent", "")).strip():
            add("TUT-TFU-004", f"{fid or '<missing>'}: name and intent are required")
        if feature.get("requested_placement", "AUTO") not in PLACEMENTS:
            add("TUT-PLACE-001", f"{fid or '<missing>'}: unsupported requested_placement")
        if feature.get("runtime_promotion_claimed") is True:
            add("TUT-RUNTIME-001", f"{fid or '<missing>'}: planner cannot claim runtime promotion")
        if feature.get("manual_claim_available") is True:
            add("TUT-MANUAL-001", f"{fid or '<missing>'}: planner cannot publish an availability claim")
    return findings


def impact_action(lifecycle: str, existing: bool, shared: bool) -> str:
    if not existing:
        return "ADAPTER_REQUIRED_AFTER_IMPLEMENTATION" if shared else "BLOCKED_BY_PENDING_IMPLEMENTATION"
    if not shared:
        return "MANUAL_ONLY"
    if lifecycle == "PLANNED":
        return "ADAPTER_REQUIRED"
    if lifecycle == "REFERENCE_ONLY":
        return "REFERENCE_ONLY_NO_RUNTIME_MIGRATION"
    return "REGRESSION_REVALIDATION"


def plan_tutorial(root: Path, tutorial_path: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    tutorial_path = Path(tutorial_path).resolve()
    tutorial = load_json(tutorial_path)
    registry = load_json(root / DONOR_REGISTRY)
    donors = {
        str(row.get("donor_id")): row
        for row in registry.get("entries", [])
        if row.get("status") == "ACCEPTED_REFERENCE" and row.get("discoverable_for_planning") is True
    }
    donor = donors.get(str(tutorial.get("donor_id")))
    findings = validate_input(tutorial, donor)
    apps = application_inventory(root)
    caps = capability_inventory(root)
    donor_targets = [str(x) for x in (donor or {}).get("target_hints", []) if isinstance(x, str)]
    results: list[dict[str, Any]] = []

    features = tutorial.get("feature_units", [])
    for feature in features if isinstance(features, list) else []:
        if not isinstance(feature, dict):
            continue
        fid = str(feature.get("feature_id", "<missing>"))
        cap_ids, cap_ambiguous = match_capabilities([str(x) for x in feature.get("capability_hints", [])], caps)
        app_ids, app_ambiguous = match_applications(
            [str(x) for x in feature.get("application_hints", [])] + donor_targets, apps
        )
        existing = bool(cap_ids)
        shared = len(app_ids) >= 2
        requested = feature.get("requested_placement", "AUTO")
        if cap_ambiguous:
            findings.append({"code": "TUT-CAP-AMBIGUOUS", "message": f"{fid}: ambiguous capability hints"})
        if app_ambiguous:
            findings.append({"code": "TUT-APP-AMBIGUOUS", "message": f"{fid}: ambiguous application hints"})
        if not app_ids:
            findings.append({"code": "TUT-APP-001", "message": f"{fid}: no deterministic FA3 application target resolved"})
        if shared and requested == "APPLICATION_LOCAL":
            findings.append({"code": "TUT-SHARED-001", "message": f"{fid}: two or more consumers require one shared functional core"})
        if not existing and feature.get("requested_top_level_capability") is True:
            findings.append({"code": "TUT-CAP-175-GUARD", "message": f"{fid}: new top-level capability requires explicit capability-model reconciliation"})

        impact = [
            {
                "application_id": aid,
                "lifecycle": apps[aid]["lifecycle"],
                "action": impact_action(apps[aid]["lifecycle"], existing, shared),
                "manual_update_required": True,
                "capability_loss_allowed": False,
            }
            for aid in app_ids
        ]
        manual_tasks = [
            {
                "application_id": aid,
                "state": "DRAFT_TASK_ONLY",
                "availability_claim_allowed": False,
                "must_use_actual_fa3_ui": True,
                "required_sections": [
                    "FA3_UI_ENTRY_POINT", "APPLICATION_WORKFLOW", "PREREQUISITES_AND_PERMISSIONS",
                    "AVAILABILITY_OR_UNAVAILABLE_STATE", "UNDO_ROLLBACK_WHERE_APPLICABLE", "TUTORIAL_PROVENANCE"
                ],
            }
            for aid in app_ids
        ]
        structural = feature.get("structural_runtime_change") is True
        results.append({
            "feature_id": fid,
            "name": feature.get("name"),
            "intent": feature.get("intent"),
            "capability_match_state": "EXISTING_CAPABILITY" if existing else "REAL_GAP",
            "matched_capability_ids": cap_ids,
            "matched_application_ids": app_ids,
            "shared_core_required": shared,
            "placement": "SHARED_LAYER_REQUIRED" if shared else "APPLICATION_CONTEXT" if app_ids else "TARGET_UNRESOLVED",
            "candidate_shared_owner_layers": sorted({caps[cid]["layers"] for cid in cap_ids if caps[cid].get("layers")}),
            "requested_placement": requested,
            "impact": impact,
            "manual_tasks": manual_tasks,
            "current_host": {
                "structural_runtime_change": structural,
                "alignment": "CURRENT_HOST_REQUALIFICATION_REQUIRED_AFTER_IMPLEMENTATION" if structural else "NO_RUNTIME_DELTA_FROM_PLANNER",
                "physical_non_simulated_evidence_required_for_runtime_promotion": structural,
                "runtime_promotion_claimed": False,
            },
            "implementation_authorized_by_planner": False,
            "automatic_donor_adoption": False,
            "automatic_code_import": False,
        })

    return {
        "schema": "fa3.tutorial-reuse-plan.v1",
        "policy_id": "FA3-TUTORIAL-SHARED-CAPABILITY-POLICY-001",
        "tutorial_input_sha256": hashlib.sha256(tutorial_path.read_bytes()).hexdigest(),
        "donor_id": tutorial.get("donor_id"),
        "reference_class": tutorial.get("reference_class"),
        "result": "BLOCKED" if findings else "PASS",
        "capability_baseline": 175,
        "capability_delta": 0,
        "authority_delta": 0,
        "runtime_promotion": False,
        "executes_tutorial_commands": False,
        "features": results,
        "findings": findings,
    }


def self_check(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, str]] = []

    def require(ok: bool, code: str, message: str) -> None:
        if not ok:
            findings.append({"code": code, "message": message})

    policy = load_json(root / POLICY)
    schema = load_json(root / SCHEMA)
    host = load_json(root / HOST_IMPACT)
    links = load_json(root / APP_LINKS)
    model = load_json(root / CAP_MODEL)
    require(model.get("canonical_capability_count") == 175, "TUT-SELF-001", "canonical capability baseline must remain 175")
    require(policy.get("new_capabilities") == 0 and policy.get("new_architectural_authorities") == 0, "TUT-SELF-002", "tutorial policy must add no capability or authority")
    require(policy.get("capability_count_after") == 175, "TUT-SELF-003", "tutorial policy capability count drift")
    registry = policy.get("registry_policy", {})
    require(registry.get("tutorial_intake_bypass") is False, "TUT-SELF-004", "tutorial intake may not bypass normal donor intake")
    require(registry.get("tutorial_registry_entry_requires_normal_owner_marked_intake") is True, "TUT-SELF-005", "normal owner-marked donor intake requirement missing")
    require(schema.get("$id") == "FA3-TUTORIAL-REFERENCE-SCHEMA-001", "TUT-SELF-006", "tutorial schema identity drift")
    require(host.get("runtime_delta") == "NONE" and host.get("current_host_runtime_promotion_claim") is False, "TUT-SELF-007", "static materialization may not claim runtime promotion")
    require(host.get("structural_runtime_change_requires_requalification") is True, "TUT-SELF-008", "future structural runtime changes must require Current Host requalification")
    lp = links.get("policy", {})
    for key in (
        "tutorial_reference_processing_required", "tutorial_existing_function_manual_adaptation_required",
        "tutorial_missing_function_need_assessment_required", "multi_application_feature_shared_layer_required",
        "retrospective_shared_impact_required", "affected_application_manual_update_required",
        "structural_change_current_host_alignment_required", "capability_loss_during_shared_migration_forbidden",
    ):
        require(lp.get(key) is True, "TUT-SELF-009", f"application-link policy missing: {key}")
    return {
        "schema": "fa3.tutorial-shared-capability-self-check.v1",
        "result": "PASS" if not findings else "FAIL",
        "capability_baseline": 175,
        "runtime_delta": "NONE",
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 non-authoritative tutorial reuse planner")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--tutorial", type=Path)
    mode.add_argument("--self-check", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = self_check(args.root) if args.self_check else plan_tutorial(args.root, args.tutorial)
    if args.output:
        target = args.output if args.output.is_absolute() else args.root / args.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.check and result["result"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
