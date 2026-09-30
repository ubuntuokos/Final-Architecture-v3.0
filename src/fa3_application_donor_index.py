#!/usr/bin/env python3
"""Non-authoritative, dynamically derived FA3 application/donor cross-reference."""
from __future__ import annotations
import argparse
import json
import re
from datetime import date
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
    # Owner policy: every donor-record change must be processed.  Do not
    # silently discard timestamp, provenance, pin, archival or other metadata
    # changes from the impact stream.
    return json.dumps(row, sort_keys=True, ensure_ascii=False)


def changed_fields(old: dict[str, Any] | None, new: dict[str, Any] | None) -> list[str]:
    if old is None or new is None:
        return ["__record__"]
    return sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))



def canonical_capability_bindings(root: Path) -> dict[str, list[str]]:
    """Read only explicit canonical capability_bindings; never infer IDs from names."""
    bindings: dict[str, list[str]] = {}
    for path in (root / "canonical").rglob("*.json"):
        try:
            row = load(path)
        except Exception:
            continue
        record_id = row.get("id")
        values = row.get("capability_bindings")
        if (
            isinstance(record_id, str)
            and isinstance(values, list)
            and all(isinstance(value, str) and value.startswith("CAP-") for value in values)
        ):
            bindings[record_id] = sorted(set(values))
    return bindings


def capability_refresh_status(registry: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    policy = registry.get("planning_policy", {})
    period_days = int(policy.get("monthly_capability_refresh_days", 31))
    effective = policy.get("monthly_capability_refresh_policy_effective_date")
    due: list[dict[str, Any]] = []
    active = 0
    for donor in registry.get("entries", []):
        if donor.get("status") == "SUPERSEDED":
            continue
        active += 1
        stamp = donor.get("capability_reviewed_at")
        clock_source = "capability_reviewed_at"
        if not stamp:
            stamp = effective
            clock_source = "policy_effective_date_initial_grace"
        try:
            reviewed = date.fromisoformat(str(stamp))
            age_days = (today - reviewed).days
        except (TypeError, ValueError):
            age_days = period_days
        if age_days >= period_days:
            due.append({
                "donor_id": donor.get("donor_id"),
                "source_key": donor.get("source", {}).get("normalized_key"),
                "review_clock": stamp,
                "review_clock_source": clock_source,
                "age_days": age_days,
                "required_action": "REFRESH_DONOR_CAPABILITY_LIST_AND_PROPAGATE_ALL_CHANGES",
            })
    return {
        "period_days": period_days,
        "active_donors": active,
        "due_count": len(due),
        "due": due,
        "policy": "MONTHLY_DONOR_CAPABILITY_REFRESH_REQUIRED",
    }


def build_index(root: Path, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    catalog, surfaces, registry, declaration = (load(root / rel) for rel in (APP, GUI, DONOR, LINKS))
    errors: list[dict[str, str]] = []
    if declaration.get("id") != "FA3-APPLICATION-DONOR-LINKS-001" or declaration.get("authority") is not False:
        errors.append({"code": "LINK_POLICY_INVALID", "detail": LINKS})
    required_policy = {
        "all_applications_in_scope_even_without_declared_dependency": True,
        "declared_and_implicit_dependencies_must_be_reconciled": True,
        "every_donor_change_must_be_processed": True,
        "donor_change_requires_application_impact_lookup": True,
        "donor_usage_reverse_traceability_required": True,
        "donor_usage_record_required_before_adoption": True,
        "donor_security_change_immediate": True,
        "unsafe_donor_active_registry_forbidden": True,
        "donor_change_capability_non_regression": True,
        "capability_loss_only_for_verified_fa3_risk": True,
        "current_host_alignment_required_for_structural_or_runtime_change": True,
    }
    for key, expected in required_policy.items():
        if declaration.get("policy", {}).get(key) is not expected:
            errors.append({"code": "MANDATORY_APPLICATION_DONOR_POLICY_MISSING",
                           "detail": key})
    policy = declaration.get("policy", {})
    missing_tutorial_policy = [
        key for key, expected in REQUIRED_TUTORIAL_SHARED_POLICY.items()
        if policy.get(key) is not expected
    ]
    if missing_tutorial_policy:
        errors.append({"code": "TUTORIAL_SHARED_POLICY_INVALID",
                       "detail": ",".join(sorted(missing_tutorial_policy))})
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
        if donor.get("status") == "REJECTED":
            errors.append({"code": "REJECTED_DONOR_ACTIVE_REGISTRY_FORBIDDEN", "detail": str(did)})
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

    usage_records = declaration.get("donor_usage_records", [])
    if not isinstance(usage_records, list):
        errors.append({"code": "INVALID_DONOR_USAGE_RECORDS", "detail": LINKS})
        usage_records = []
    usage_by_donor: dict[str, list[dict[str, Any]]] = {}
    usage_by_app: dict[str, list[dict[str, Any]]] = {}
    seen_usage: set[str] = set()
    allowed_usage = {"CAPABILITY_PATTERN", "ALGORITHM_PATTERN", "WORKFLOW_PATTERN",
                     "ARCHITECTURE_PATTERN", "UI_UX_PATTERN", "CODE_REUSE",
                     "RUNTIME_DEPENDENCY", "REFERENCE_BINDING"}
    allowed_usage_status = {"ACTIVE", "PINNED_STABLE", "REPLACEMENT_PENDING", "REMOVED"}
    for usage in usage_records:
        uid = usage.get("id") if isinstance(usage, dict) else None
        aid = usage.get("application_id") if isinstance(usage, dict) else None
        did = usage.get("donor_id") if isinstance(usage, dict) else None
        if (not uid or uid in seen_usage or aid not in applications or did not in donor_ids
                or usage.get("usage_kind") not in allowed_usage
                or usage.get("status") not in allowed_usage_status):
            errors.append({"code": "INVALID_DONOR_USAGE_RECORD", "detail": str(uid)})
            continue
        seen_usage.add(uid)
        usage_by_donor.setdefault(did, []).append(usage)
        usage_by_app.setdefault(aid, []).append(usage)

    capability_bindings = canonical_capability_bindings(root)
    allowed_consumer_kinds = {
        "APPLICATION", "SHARED_MODULE", "PROFILE", "AUTHORITY",
        "GUI_SURFACE", "TEST_HARNESS", "CURRENT_HOST_PATH",
    }
    allowed_current_host_impact = {
        "NO_RUNTIME_IMPACT", "STRUCTURAL_REASSESSMENT_REQUIRED",
        "RUNTIME_REQUALIFICATION_REQUIRED",
    }
    capability_usage_edges: list[dict[str, Any]] = []
    by_usage_donor: dict[str, list[str]] = {}
    by_usage_capability: dict[str, list[str]] = {}
    by_usage_consumer: dict[str, list[str]] = {}
    gui_surface_ids = {row["surface_id"] for row in gui_surfaces}

    for usage in usage_records:
        uid = usage.get("id") if isinstance(usage, dict) else None
        if not uid or uid not in seen_usage:
            continue
        aid = usage["application_id"]
        did = usage["donor_id"]
        fa3_bindings = usage.get("fa3_bindings") or {}
        if not isinstance(fa3_bindings, dict):
            errors.append({"code": "INVALID_FA3_BINDINGS", "detail": uid})
            fa3_bindings = {}
        if fa3_bindings.get("capability_ids"):
            errors.append({"code": "MANUAL_CAPABILITY_BINDING_FORBIDDEN", "detail": uid})

        binding_refs: list[str] = []
        normalized_refs: dict[str, list[str]] = {}
        for key in ("profile_ids", "contract_ids", "authority_ids", "shared_module_ids"):
            values = fa3_bindings.get(key, [])
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                errors.append({"code": "INVALID_BINDING_REFERENCE", "detail": uid + ":" + key})
                values = []
            normalized_refs[key] = sorted(set(values))
            if key in ("profile_ids", "contract_ids"):
                binding_refs.extend(values)

        derived_capabilities = sorted({
            capability
            for record_id in binding_refs
            for capability in capability_bindings.get(record_id, [])
        })
        unresolved_refs = sorted({
            record_id for record_id in binding_refs if record_id not in capability_bindings
        })
        if (
            declaration.get("schema") == "fa3.application-donor-links.v3"
            and usage.get("usage_kind") == "CAPABILITY_PATTERN"
            and not derived_capabilities
        ):
            errors.append({"code": "UNRESOLVED_CAPABILITY_BINDING", "detail": uid})

        consumers = [{"kind": "APPLICATION", "id": aid, "relationship": "PRIMARY_APPLICATION"}]
        extra_consumers = usage.get("consumers", [])
        if not isinstance(extra_consumers, list):
            errors.append({"code": "INVALID_CONSUMERS", "detail": uid})
            extra_consumers = []
        for consumer in extra_consumers:
            if (
                not isinstance(consumer, dict)
                or consumer.get("kind") not in allowed_consumer_kinds
                or not isinstance(consumer.get("id"), str)
                or not consumer["id"]
            ):
                errors.append({"code": "INVALID_CONSUMER", "detail": uid})
                continue
            if consumer["kind"] == "APPLICATION" and consumer["id"] not in applications:
                errors.append({"code": "UNKNOWN_APPLICATION_CONSUMER", "detail": uid + ":" + consumer["id"]})
                continue
            if consumer["kind"] == "GUI_SURFACE" and consumer["id"] not in gui_surface_ids:
                errors.append({"code": "UNKNOWN_GUI_CONSUMER", "detail": uid + ":" + consumer["id"]})
                continue
            consumers.append({
                "kind": consumer["kind"],
                "id": consumer["id"],
                "relationship": consumer.get("relationship", "INDIRECT_SHARED"),
            })
        unique_consumers = {
            (consumer["kind"], consumer["id"], consumer["relationship"]): consumer
            for consumer in consumers
        }

        current_host_impact = (usage.get("current_host_impact") or {}).get(
            "classification", "NO_RUNTIME_IMPACT"
        )
        if current_host_impact not in allowed_current_host_impact:
            errors.append({"code": "INVALID_CURRENT_HOST_IMPACT", "detail": uid})
            current_host_impact = "STRUCTURAL_REASSESSMENT_REQUIRED"

        edge = {
            "id": uid,
            "donor_id": did,
            "donor_capability_key": usage.get("donor_capability_key"),
            "usage_kind": usage.get("usage_kind"),
            "status": usage.get("status"),
            "fa3_bindings": {
                **normalized_refs,
                "capability_ids": derived_capabilities,
                "unresolved_binding_ids": unresolved_refs,
                "resolution": (
                    "RESOLVED"
                    if binding_refs and not unresolved_refs and derived_capabilities
                    else "UNRESOLVED_CAPABILITY_BINDING"
                    if unresolved_refs or (
                        declaration.get("schema") == "fa3.application-donor-links.v3"
                        and usage.get("usage_kind") == "CAPABILITY_PATTERN"
                        and not derived_capabilities
                    )
                    else "NOT_REQUIRED"
                ),
            },
            "consumers": sorted(
                unique_consumers.values(),
                key=lambda value: (value["kind"], value["id"], value["relationship"]),
            ),
            "current_host_impact": {"classification": current_host_impact},
            "provenance": usage.get("provenance", {}),
        }
        capability_usage_edges.append(edge)
        by_usage_donor.setdefault(did, []).append(uid)
        for capability in derived_capabilities:
            by_usage_capability.setdefault(capability, []).append(uid)
        for consumer in edge["consumers"]:
            key = consumer["kind"] + ":" + consumer["id"]
            by_usage_consumer.setdefault(key, []).append(uid)

    capability_consumer_map = {
        "schema": "fa3.capability-consumer-map.v1",
        "derived": True,
        "authority": False,
        "edges": sorted(capability_usage_edges, key=lambda edge: edge["id"]),
        "views": {
            "by_donor": {key: sorted(value) for key, value in sorted(by_usage_donor.items())},
            "by_capability": {
                key: sorted(value) for key, value in sorted(by_usage_capability.items())
            },
            "by_consumer": {
                key: sorted(value) for key, value in sorted(by_usage_consumer.items())
            },
        },
    }

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
        app["declared_donor_usage"] = sorted(
            [{"usage_id": u["id"], "donor_id": u["donor_id"],
              "usage_kind": u["usage_kind"], "status": u["status"]}
             for u in usage_by_app.get(app["application_id"], [])],
            key=lambda u: u["usage_id"])
        app["fa3_compliance"] = {
            "applies_without_declared_dependency": True,
            "declared_and_implicit_dependency_reconciliation_required": True,
            "every_donor_change_processed": True,
            "donor_usage_traceability_required": True,
            "capability_non_regression_on_donor_change": True,
            "capability_loss_only_for_verified_fa3_risk": True,
            "current_host_alignment_for_structural_or_runtime_change": True,
        }
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
            donor_ids_for_change = {row.get("donor_id") for row in (old, new)
                                    if isinstance(row, dict) and row.get("donor_id")}
            explicitly_used_by = {
                u["application_id"]
                for did in donor_ids_for_change for u in usage_by_donor.get(did, [])
                if u.get("status") != "REMOVED"
            }
            for app in applications.values():
                aliases = {norm(s) for s in app["aliases"]}
                source_key = app.get("source_ref") or "project:" + app["name"].lower()
                if (app["application_id"] in explicitly_used_by or
                        any(source_key == row.get("source", {}).get("normalized_key")
                            or any(isinstance(h, str) and norm(h) in aliases
                                   for h in row.get("target_hints", []))
                            for row in (old, new) if row)):
                    affected.append(app["application_id"])
            fields = changed_fields(old, new)
            security_fields = {"status", "license", "code_reuse_policy", "rejection_reasons",
                               "source_pin_status", "upstream_snapshot",
                               "upstream_observation", "upstream_archived",
                               "security_review", "security_status"}
            capability_fields = {"donor_modes", "capability_hints", "domain_hints",
                                 "problem_hints", "target_hints", "tags"}
            security_sensitive = bool(security_fields.intersection(fields))
            capability_sensitive = bool(capability_fields.intersection(fields))
            required_actions = ["DONOR_DIFF_CLASSIFICATION",
                                "DONOR_TO_APPLICATION_REVERSE_IMPACT_LOOKUP"]
            if affected:
                required_actions += [
                    "CAPABILITY_PARITY_NON_REGRESSION",
                    "LAYER_AND_DEPENDENCY_RECONCILIATION",
                    "CURRENT_HOST_ALIGNMENT_IF_STRUCTURAL_OR_RUNTIME_AFFECTED",
                    "TEST_GATE_EVIDENCE_RECONCILIATION",
                    "RELEASE_PROJECTION_RECONCILIATION",
                ]
            if security_sensitive:
                required_actions.append("IMMEDIATE_SECURITY_AND_TRUST_REEVALUATION")
            if not new and explicitly_used_by:
                required_actions += ["LOCK_LAST_VERIFIED_STABLE_IF_AVAILABLE",
                                     "REPLACE_DONOR_OR_FA3_NATIVE_REMATERIALIZE_BEFORE_RELEASE"]
            reevaluation.append({
                "source_key": key,
                "donor_ids": sorted(donor_ids_for_change),
                "change": "ADDED" if not old else "REMOVED" if not new else "UPDATED",
                "changed_fields": fields,
                "security_sensitive": security_sensitive,
                "capability_sensitive": capability_sensitive,
                "affected_applications": sorted(set(affected)),
                "explicitly_used_by": sorted(explicitly_used_by),
                "affected_capability_usage_edges": sorted({
                    edge["id"] for edge in capability_usage_edges
                    if edge["donor_id"] in donor_ids_for_change and edge["status"] != "REMOVED"
                }),
                "affected_capabilities": sorted({
                    capability
                    for edge in capability_usage_edges
                    if edge["donor_id"] in donor_ids_for_change and edge["status"] != "REMOVED"
                    for capability in edge["fa3_bindings"]["capability_ids"]
                }),
                "affected_consumers": sorted({
                    consumer["kind"] + ":" + consumer["id"]
                    for edge in capability_usage_edges
                    if edge["donor_id"] in donor_ids_for_change and edge["status"] != "REMOVED"
                    for consumer in edge["consumers"]
                }),
                "required_actions": required_actions,
                "disposition": ("IMMEDIATE_SECURITY_RECONCILIATION" if security_sensitive and affected
                                else "MANDATORY_APPLICATION_RECONCILIATION" if affected
                                else "MANDATORY_DONOR_RECONCILIATION"),
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
        "tutorial_shared_policy": {"registered_tutorial_only": True, "existing_function_routes_to_fa3_native_manual": True, "missing_function_requires_need_assessment": True, "multi_application_function_routes_to_shared_layer": True, "retrospective_application_impact_required": True, "manual_publish_requires_verified_implementation": True, "structural_change_requires_current_host_alignment": True},
        "capability_consumer_map": capability_consumer_map,
        "reevaluation": reevaluation,
        "validation": {"result": "PASS" if not errors else "FAIL", "findings": errors},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 derived application/donor index")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--previous-registry", type=Path)
    parser.add_argument("--app")
    parser.add_argument("--donor")
    parser.add_argument("--capability")
    parser.add_argument("--consumer")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--monthly-refresh-check", action="store_true")
    args = parser.parse_args()
    previous = load(args.previous_registry) if args.previous_registry else None
    result = build_index(args.root, previous=previous)
    if args.monthly_refresh_check:
        registry = load(args.root.resolve() / DONOR)
        result["monthly_capability_refresh"] = capability_refresh_status(registry)
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
    if args.donor or args.capability or args.consumer:
        views = result["capability_consumer_map"]["views"]
        selected_ids: set[str] | None = None
        for view_name, value in (
            ("by_donor", args.donor),
            ("by_capability", args.capability),
            ("by_consumer", args.consumer),
        ):
            if value:
                ids = set(views[view_name].get(value, []))
                selected_ids = ids if selected_ids is None else selected_ids & ids
        selected_ids = selected_ids or set()
        result = {
            "capability_consumer_map": {
                **result["capability_consumer_map"],
                "edges": [
                    edge for edge in result["capability_consumer_map"]["edges"]
                    if edge["id"] in selected_ids
                ],
            },
            "validation": result["validation"],
        }
    if args.output:
        dst = args.output if args.output.is_absolute() else args.root / args.output
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    display = {"counts": result["counts"], "validation": result["validation"]} if args.summary and "counts" in result else result
    print(json.dumps(display, ensure_ascii=False, indent=2))
    failed = args.check and result["validation"]["result"] != "PASS"
    if args.monthly_refresh_check and result.get("monthly_capability_refresh", {}).get("due_count", 0):
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
