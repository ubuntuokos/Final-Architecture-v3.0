#!/usr/bin/env python3
"""Non-authoritative, dynamically derived FA3 application/donor cross-reference."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

APP = "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json"
GUI = "canonical/FA3-GUI-SURFACE-REGISTRY-001.json"
DONOR = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
AUTO = ("automatic_selection", "automatic_fetch", "automatic_install",
        "automatic_activation", "automatic_dependency", "automatic_code_import",
        "automatic_provider_admission", "automatic_model_selection")

REQUIRED_TUTORIAL_SHARED_POLICY = {
    "tutorial_reference_processing_required": True,
    "tutorial_existing_function_manual_adaptation_required": True,
    "tutorial_missing_function_need_assessment_required": True,
    "manual_publish_requires_verified_implementation": True,
    "multi_application_feature_shared_layer_required": True,
    "shared_capability_local_duplication_forbidden_without_justification": True,
    "retrospective_shared_impact_required": True,
    "affected_application_manual_update_required": True,
    "structural_change_current_host_alignment_required": True,
    "capability_loss_during_shared_migration_forbidden": True,
}


def load(path: Path) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(row, dict):
        raise ValueError("expected JSON object: " + str(path))
    return row


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def fingerprint(row: dict[str, Any]) -> str:
    keys = ("name", "source", "status", "donor_modes", "capability_hints",
            "domain_hints", "problem_hints", "target_hints", "tags", "license",
            "code_reuse_policy", "discoverable_for_planning", "selection_scope")
    return json.dumps({key: row.get(key) for key in keys}, sort_keys=True, ensure_ascii=False)


def build_index(root: Path, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    catalog, surfaces, registry, declaration = (load(root / rel) for rel in (APP, GUI, DONOR, LINKS))
    errors: list[dict[str, str]] = []
    if declaration.get("id") != "FA3-APPLICATION-DONOR-LINKS-001" or declaration.get("authority") is not False:
        errors.append({"code": "LINK_POLICY_INVALID", "detail": LINKS})
    policy = declaration.get("policy", {})
    missing_policy = [
        key for key, expected in REQUIRED_TUTORIAL_SHARED_POLICY.items()
        if policy.get(key) is not expected
    ]
    if missing_policy:
        errors.append({
            "code": "TUTORIAL_SHARED_POLICY_INVALID",
            "detail": ",".join(sorted(missing_policy)),
        })
    donors = registry.get("entries", [])
    if registry.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001" or registry.get("backfill", {}).get("entry_count") != len(donors):
        errors.append({"code": "DONOR_REGISTRY_DRIFT", "detail": DONOR})
    donor_by_source: dict[str, dict[str, Any]] = {}
    donor_ids: set[str] = set()
    for donor in donors:
        key = donor.get("source", {}).get("normalized_key")
        did = donor.get("donor_id")
        if not key or key in donor_by_source or not did or did in donor_ids:
            errors.append({"code": "DUPLICATE_DONOR_ID_OR_SOURCE", "detail": str(did)})
        if donor.get("authority") is not False or any(donor.get(flag) is not False for flag in AUTO):
            errors.append({"code": "DONOR_AUTO_ADMISSION_FORBIDDEN", "detail": str(did)})
        donor_by_source[key] = donor
        donor_ids.add(did)

    applications: dict[str, dict[str, Any]] = {}
    for item in catalog.get("applications", []):
        aid = "studio." + str(item["id"])
        if aid in applications:
            errors.append({"code": "DUPLICATE_APPLICATION", "detail": aid})
        applications[aid] = {
            "application_id": aid, "name": item["name"],
            "kind": "CURATED_EXTERNAL_APPLICATION",
            "lifecycle": "CATALOG_" + str(item.get("admission", "UNKNOWN")),
            "aliases": [item["name"]], "source_catalog": APP,
            "donor_assessment": "NOT_AUTOMATICALLY_ASSESSED",
        }
    curated_count = len(applications)
    for item in declaration.get("applications", []):
        aid = item["application_id"]
        if aid in applications or item.get("lifecycle") not in ("PLANNED", "REFERENCE_ONLY"):
            errors.append({"code": "DUPLICATE_OR_INVALID_DECLARED_APPLICATION", "detail": aid})
            continue
        applications[aid] = {
            "application_id": aid, "name": item["name"], "kind": item["kind"],
            "lifecycle": item["lifecycle"],
            "aliases": sorted(set([item["name"]] + item.get("aliases", []))),
            "source_ref": item.get("source_ref"), "source_catalog": LINKS,
            "donor_assessment": "NOT_AUTOMATICALLY_ASSESSED",
        }
    gui_surfaces = []
    seen_surfaces: set[str] = set()
    for surface in surfaces.get("surfaces", []):
        sid = surface["route_id"]
        if sid in seen_surfaces:
            errors.append({"code": "DUPLICATE_GUI_SURFACE", "detail": sid})
        seen_surfaces.add(sid)
        gui_surfaces.append({"surface_id": sid, "title": surface.get("title"),
                             "source_catalog": GUI, "is_application": False})

    for app in applications.values():
        aliases = {norm(s) for s in app["aliases"]}
        source_key = app.get("source_ref") or "project:" + app["name"].lower()
        source = donor_by_source.get(source_key)
        app["existing_source_donors"] = [source["donor_id"]] if source else []
        app["suggested_donors"] = sorted([
            {"donor_id": donor["donor_id"], "status": donor["status"],
             "matched_targets": sorted(set(h for h in donor.get("target_hints", [])
                                            if isinstance(h, str) and norm(h) in aliases)),
             "disposition": "REVIEW_SUGGESTION_ONLY", "automatic_activation": False,
             "automatic_code_import": False}
            for donor in donors
            if donor.get("status") not in ("REJECTED", "SUPERSEDED")
            and donor.get("discoverable_for_planning") is True
            and any(isinstance(h, str) and norm(h) in aliases for h in donor.get("target_hints", []))
        ], key=lambda d: d["donor_id"])
        app["authority"] = False
        app["automatic_activation"] = False
        app["automatic_code_import"] = False

    shared_capabilities = []
    seen_shared: set[str] = set()
    for item in declaration.get("shared_capabilities", []):
        sid = str(item.get("id", ""))
        consumers = sorted(set(str(x) for x in item.get("consumer_applications", []) if x))
        valid = (
            bool(sid)
            and sid not in seen_shared
            and bool(item.get("owner_layer"))
            and len(consumers) >= 2
            and all(app_id in applications for app_id in consumers)
            and item.get("authority") is False
            and item.get("local_ui_adapter_only") is True
            and item.get("retrospective_review_required") is True
            and item.get("manual_update_required") is True
            and item.get("capability_loss_allowed") is False
            and item.get("current_host_alignment_required_for_structural_change") is True
        )
        if not valid:
            errors.append({
                "code": "INVALID_SHARED_CAPABILITY",
                "detail": sid or "<missing-id>",
            })
        seen_shared.add(sid)
        shared_capabilities.append({
            "id": sid,
            "owner_layer": item.get("owner_layer"),
            "consumer_applications": consumers,
            "status": item.get("status", "PROPOSED"),
            "authority": False,
            "retrospective_review_required": True,
            "manual_update_required": True,
            "local_ui_adapter_only": True,
            "capability_loss_allowed": False,
            "current_host_alignment_required_for_structural_change": True,
        })

    edges = []
    seen_edges: set[str] = set()
    for edge in declaration.get("relationships", []):
        eid = edge["id"]
        source, target = edge["from_application"], edge["to_application"]
        if (eid in seen_edges or source not in applications or target not in applications
                or source == target or edge.get("status") != "PROPOSED"
                or edge.get("human_approval_required") is not True):
            errors.append({"code": "INVALID_CROSS_APP_EDGE", "detail": eid})
        seen_edges.add(eid)
        edges.append({
            "id": eid, "from_application": source, "to_application": target,
            "offered_artifacts": edge.get("offered_artifacts", []),
            "integration_boundary": edge.get("integration_boundary"),
            "status": "PROPOSED", "human_approval_required": True,
            "admission_required": True, "automatic_activation": False,
            "automatic_code_import": False,
        })

    reevaluation = []
    if previous is not None:
        before = {d.get("source", {}).get("normalized_key"): d for d in previous.get("entries", [])}
        after = donor_by_source
        for key in sorted(set(before) | set(after)):
            old, new = before.get(key), after.get(key)
            if old and new and fingerprint(old) == fingerprint(new):
                continue
            affected = []
            for app in applications.values():
                aliases = {norm(s) for s in app["aliases"]}
                source_key = app.get("source_ref") or "project:" + app["name"].lower()
                if any(source_key == row.get("source", {}).get("normalized_key")
                       or any(isinstance(h, str) and norm(h) in aliases
                              for h in row.get("target_hints", []))
                       for row in (old, new) if row):
                    affected.append(app["application_id"])
            reevaluation.append({
                "source_key": key,
                "change": "ADDED" if not old else "REMOVED" if not new else "UPDATED",
                "affected_applications": sorted(affected),
                "disposition": "TARGETED_HUMAN_REVIEW" if affected else "NO_EXACT_MATCH",
                "automatic_adoption": False,
            })
    return {
        "schema": "fa3.application-donor-index.v1", "derived": True,
        "authority": False, "runtime_promotion": False,
        "source_catalogs": [APP, GUI, DONOR, LINKS],
        "hardware_audit": {
            "vendor_neutral": True, "cpu_only_viable": True,
            "accelerator_cardinality": "0..N", "global_accelerator_requirement": False,
            "hardware_mutation": False,
            "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "model_route_authority": "FA3-AUTH-MODEL-ROUTER-001",
        },
        "counts": {"curated_apps": curated_count,
                   "declared_apps": len(applications) - curated_count,
                   "total_apps": len(applications),
                   "gui_surfaces_not_apps": len(gui_surfaces),
                   "donor_records": len(donors),
                   "proposed_cross_app_links": len(edges),
                   "shared_capabilities": len(shared_capabilities),
                   "changed_donor_sources": len(reevaluation)},
        "applications": [applications[k] for k in sorted(applications)],
        "gui_surfaces": sorted(gui_surfaces, key=lambda x: x["surface_id"]),
        "cross_application_links": sorted(edges, key=lambda x: x["id"]),
        "shared_capabilities": sorted(shared_capabilities, key=lambda x: x["id"]),
        "tutorial_shared_policy": {
            "registered_tutorial_only": True,
            "existing_function_routes_to_fa3_native_manual": True,
            "missing_function_requires_need_assessment": True,
            "multi_application_function_routes_to_shared_layer": True,
            "retrospective_application_impact_required": True,
            "manual_publish_requires_verified_implementation": True,
            "structural_change_requires_current_host_alignment": True,
        },
        "reevaluation": reevaluation,
        "validation": {"result": "PASS" if not errors else "FAIL", "findings": errors},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 derived application/donor index")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--previous-registry", type=Path)
    parser.add_argument("--app")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    previous = load(args.previous_registry) if args.previous_registry else None
    result = build_index(args.root, previous=previous)
    if args.app:
        matches = [a for a in result["applications"] if a["application_id"] == args.app]
        if not matches:
            parser.error("unknown application_id: " + args.app)
        result = {"application": matches[0],
                  "outgoing": [e for e in result["cross_application_links"]
                               if e["from_application"] == args.app],
                  "incoming": [e for e in result["cross_application_links"]
                               if e["to_application"] == args.app],
                  "validation": result["validation"]}
    if args.output:
        dst = args.output if args.output.is_absolute() else args.root / args.output
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    display = {"counts": result["counts"], "validation": result["validation"]} if args.summary and "counts" in result else result
    print(json.dumps(display, ensure_ascii=False, indent=2))
    return 1 if args.check and result["validation"]["result"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
