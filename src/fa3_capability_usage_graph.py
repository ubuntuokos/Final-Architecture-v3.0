#!/usr/bin/env python3
"""Derived Donor ↔ Capability ↔ Consumer graph for FA3.

This module creates projections only. Donor identity, capability identity,
application identity, routing, resources, secrets, policy and evidence remain
owned by their existing canonical authorities.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_application_donor_index import DONOR, LINKS, build_index, load

CAPABILITY_MODEL = "canonical/FA3-CAPABILITY-MODEL-175-001.json"
BINDING_ROOTS = ("canonical/profiles", "canonical/contracts")
ALLOWED_CONSUMER_KINDS = {
    "APPLICATION", "SHARED_MODULE", "PROFILE", "AUTHORITY",
    "GUI_SURFACE", "TEST_HARNESS", "CURRENT_HOST_PATH",
}
ALLOWED_RELATIONSHIPS = {
    "DIRECT", "INDIRECT_SHARED", "OPTIONAL", "GUI_PROJECTION",
    "TEST_ONLY", "ENFORCEMENT_OWNER",
}
ALLOWED_USAGE = {
    "CAPABILITY_PATTERN", "ALGORITHM_PATTERN", "WORKFLOW_PATTERN",
    "ARCHITECTURE_PATTERN", "UI_UX_PATTERN", "CODE_REUSE",
    "RUNTIME_DEPENDENCY", "REFERENCE_BINDING",
}
ALLOWED_STATUS = {"ACTIVE", "PINNED_STABLE", "REPLACEMENT_PENDING", "REMOVED"}
ALLOWED_CURRENT_HOST_IMPACT = {
    "NO_RUNTIME_IMPACT", "STRUCTURAL_REASSESSMENT_REQUIRED",
    "RUNTIME_REQUALIFICATION_REQUIRED",
}
CAP_RE = re.compile(r"^CAP-(\d{3})$")


def _binding_records(root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for rel in BINDING_ROOTS:
        directory = root / rel
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.json")):
            try:
                row = load(path)
            except Exception:
                continue
            record_id = row.get("id")
            if not isinstance(record_id, str) or not record_id:
                continue
            raw = row.get("capability_bindings", [])
            caps = sorted(set(x for x in raw if isinstance(x, str))) if isinstance(raw, list) else []
            records[record_id] = {
                "record_id": record_id,
                "path": str(path.relative_to(root)),
                "capability_ids": caps,
            }
    return records


def _valid_capability_id(value: str, maximum: int) -> bool:
    match = CAP_RE.fullmatch(value)
    return bool(match and 1 <= int(match.group(1)) <= maximum)


def _normalize_consumers(
    usage: dict[str, Any],
    *,
    applications: set[str],
    gui_surfaces: set[str],
    binding_records: dict[str, dict[str, Any]],
    errors: list[dict[str, str]],
) -> list[dict[str, str]]:
    raw = usage.get("consumers", [])
    consumers: list[dict[str, str]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                errors.append({"code": "INVALID_USAGE_CONSUMER", "detail": str(usage.get("id"))})
                continue
            kind = item.get("kind")
            cid = item.get("id")
            relationship = item.get("relationship", "DIRECT")
            if kind not in ALLOWED_CONSUMER_KINDS or not isinstance(cid, str) or not cid:
                errors.append({"code": "INVALID_USAGE_CONSUMER", "detail": str(usage.get("id"))})
                continue
            if relationship not in ALLOWED_RELATIONSHIPS:
                errors.append({"code": "INVALID_USAGE_RELATIONSHIP", "detail": str(usage.get("id"))})
                continue
            if kind == "APPLICATION" and cid not in applications:
                errors.append({"code": "UNKNOWN_APPLICATION_CONSUMER", "detail": cid})
                continue
            if kind == "GUI_SURFACE" and cid not in gui_surfaces:
                errors.append({"code": "UNKNOWN_GUI_CONSUMER", "detail": cid})
                continue
            if kind == "PROFILE" and cid not in binding_records:
                errors.append({"code": "UNKNOWN_PROFILE_CONSUMER", "detail": cid})
                continue
            consumers.append({"kind": kind, "id": cid, "relationship": relationship})

    legacy_app = usage.get("application_id")
    if isinstance(legacy_app, str) and legacy_app:
        if legacy_app not in applications:
            errors.append({"code": "UNKNOWN_APPLICATION_CONSUMER", "detail": legacy_app})
        else:
            consumers.append({
                "kind": "APPLICATION",
                "id": legacy_app,
                "relationship": "DIRECT",
            })

    dedup: dict[str, dict[str, str]] = {}
    for item in consumers:
        key = f'{item["kind"]}:{item["id"]}'
        if key in dedup and dedup[key] != item:
            errors.append({"code": "DUPLICATE_USAGE_CONSUMER", "detail": key})
        dedup[key] = item
    return [dedup[key] for key in sorted(dedup)]


def build_capability_usage_graph(
    root: Path,
    previous_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    declaration = load(root / LINKS)
    registry = load(root / DONOR)
    capability_model = load(root / CAPABILITY_MODEL)
    app_index = build_index(root, previous=previous_registry)
    errors: list[dict[str, str]] = list(app_index["validation"]["findings"])

    capability_count = int(capability_model.get("canonical_capability_count", 0))
    if capability_count != 175:
        errors.append({"code": "CAPABILITY_BASELINE_DRIFT", "detail": str(capability_count)})

    donor_ids = {
        row.get("donor_id")
        for row in registry.get("entries", [])
        if isinstance(row, dict) and isinstance(row.get("donor_id"), str)
    }
    applications = {row["application_id"] for row in app_index.get("applications", [])}
    gui_surfaces = {row["surface_id"] for row in app_index.get("gui_surfaces", [])}
    bindings = _binding_records(root)

    contract = declaration.get("donor_usage_contract", {})
    if contract.get("schema") != "fa3.donor-capability-consumer-usage.v2":
        errors.append({"code": "CAPABILITY_USAGE_CONTRACT_DRIFT", "detail": LINKS})
    if contract.get("manual_capability_ids_field") != "FORBIDDEN":
        errors.append({"code": "MANUAL_CAPABILITY_ID_POLICY_DRIFT", "detail": LINKS})

    usage_records = declaration.get("donor_usage_records", [])
    if not isinstance(usage_records, list):
        errors.append({"code": "INVALID_DONOR_USAGE_RECORDS", "detail": LINKS})
        usage_records = []

    seen: set[str] = set()
    edges: list[dict[str, Any]] = []
    by_donor: dict[str, dict[str, Any]] = {}
    by_capability: dict[str, dict[str, Any]] = {}
    by_consumer: dict[str, dict[str, Any]] = {}

    for usage in usage_records:
        uid = usage.get("id") if isinstance(usage, dict) else None
        if not isinstance(usage, dict) or not isinstance(uid, str) or not uid or uid in seen:
            errors.append({"code": "INVALID_OR_DUPLICATE_USAGE_EDGE", "detail": str(uid)})
            continue
        seen.add(uid)

        donor_id = usage.get("donor_id")
        donor_capability_key = usage.get("donor_capability_key")
        usage_kind = usage.get("usage_kind")
        status = usage.get("status")
        if donor_id not in donor_ids:
            errors.append({"code": "UNKNOWN_USAGE_DONOR", "detail": uid})
        if not isinstance(donor_capability_key, str) or not donor_capability_key.strip():
            errors.append({"code": "DONOR_CAPABILITY_KEY_REQUIRED", "detail": uid})
        if usage_kind not in ALLOWED_USAGE:
            errors.append({"code": "INVALID_USAGE_KIND", "detail": uid})
        if status not in ALLOWED_STATUS:
            errors.append({"code": "INVALID_USAGE_STATUS", "detail": uid})
        if "capability_ids" in usage:
            errors.append({"code": "MANUAL_CAPABILITY_IDS_FORBIDDEN", "detail": uid})

        refs = usage.get("fa3_binding_refs", [])
        if not isinstance(refs, list) or any(not isinstance(x, str) for x in refs):
            errors.append({"code": "INVALID_BINDING_REFS", "detail": uid})
            refs = []

        resolved_records: list[dict[str, Any]] = []
        capability_ids: set[str] = set()
        for ref in refs:
            row = bindings.get(ref)
            if row is None:
                errors.append({"code": "UNKNOWN_CANONICAL_BINDING_REF", "detail": f"{uid}:{ref}"})
                continue
            resolved_records.append(row)
            for cap in row["capability_ids"]:
                if not _valid_capability_id(cap, capability_count):
                    errors.append({"code": "INVALID_CANONICAL_CAPABILITY_BINDING", "detail": f"{ref}:{cap}"})
                else:
                    capability_ids.add(cap)

        binding_status = "RESOLVED" if capability_ids else "UNRESOLVED_CAPABILITY_BINDING"
        if status in {"ACTIVE", "PINNED_STABLE", "REPLACEMENT_PENDING"} and usage_kind != "REFERENCE_BINDING" and binding_status != "RESOLVED":
            errors.append({"code": "ACTIVE_USAGE_REQUIRES_RESOLVED_CAPABILITY_BINDING", "detail": uid})

        consumers = _normalize_consumers(
            usage,
            applications=applications,
            gui_surfaces=gui_surfaces,
            binding_records=bindings,
            errors=errors,
        )
        if status != "REMOVED" and not consumers:
            errors.append({"code": "ACTIVE_USAGE_REQUIRES_CONSUMER", "detail": uid})

        current_host_impact = usage.get("current_host_impact")
        if current_host_impact not in ALLOWED_CURRENT_HOST_IMPACT:
            errors.append({"code": "CURRENT_HOST_IMPACT_REQUIRED", "detail": uid})
            current_host_impact = "STRUCTURAL_REASSESSMENT_REQUIRED"

        edge = {
            "id": uid,
            "donor_id": donor_id,
            "donor_capability_key": donor_capability_key,
            "usage_kind": usage_kind,
            "status": status,
            "fa3_binding_refs": sorted(set(refs)),
            "resolved_binding_records": sorted(
                ({"record_id": row["record_id"], "path": row["path"]} for row in resolved_records),
                key=lambda row: row["record_id"],
            ),
            "capability_ids": sorted(capability_ids),
            "binding_status": binding_status,
            "consumers": consumers,
            "current_host_impact": current_host_impact,
            "provenance": usage.get("provenance", {}),
            "authority": False,
            "runtime_promotion": False,
        }
        edges.append(edge)

        donor_view = by_donor.setdefault(str(donor_id), {
            "donor_id": donor_id, "edge_ids": [], "capabilities": [], "consumers": [],
        })
        donor_view["edge_ids"].append(uid)
        donor_view["capabilities"].extend(edge["capability_ids"])
        donor_view["consumers"].extend(f'{x["kind"]}:{x["id"]}' for x in consumers)

        for cap in edge["capability_ids"]:
            cap_view = by_capability.setdefault(cap, {
                "capability_id": cap, "edge_ids": [], "donors": [], "consumers": [],
            })
            cap_view["edge_ids"].append(uid)
            cap_view["donors"].append(str(donor_id))
            cap_view["consumers"].extend(f'{x["kind"]}:{x["id"]}' for x in consumers)

        for consumer in consumers:
            key = f'{consumer["kind"]}:{consumer["id"]}'
            consumer_view = by_consumer.setdefault(key, {
                "consumer": key, "edge_ids": [], "donors": [], "capabilities": [],
            })
            consumer_view["edge_ids"].append(uid)
            consumer_view["donors"].append(str(donor_id))
            consumer_view["capabilities"].extend(edge["capability_ids"])

    for table in (by_donor, by_capability, by_consumer):
        for row in table.values():
            for key, value in list(row.items()):
                if isinstance(value, list):
                    row[key] = sorted(set(value))

    impact: list[dict[str, Any]] = []
    if previous_registry is not None:
        edges_by_donor: dict[str, list[dict[str, Any]]] = {}
        for edge in edges:
            edges_by_donor.setdefault(str(edge["donor_id"]), []).append(edge)
        for change in app_index.get("reevaluation", []):
            related = [
                edge for donor_id in change.get("donor_ids", [])
                for edge in edges_by_donor.get(str(donor_id), [])
                if edge.get("status") != "REMOVED"
            ]
            affected_consumers = sorted({
                f'{consumer["kind"]}:{consumer["id"]}'
                for edge in related for consumer in edge["consumers"]
            })
            affected_caps = sorted({
                cap for edge in related for cap in edge["capability_ids"]
            })
            impacts = {edge["current_host_impact"] for edge in related}
            current_host_required = bool(
                impacts & {"STRUCTURAL_REASSESSMENT_REQUIRED", "RUNTIME_REQUALIFICATION_REQUIRED"}
            )
            required_actions = list(change.get("required_actions", []))
            if related:
                required_actions += [
                    "DONOR_TO_CAPABILITY_TO_CONSUMER_REVERSE_IMPACT_LOOKUP",
                    "CAPABILITY_BINDING_REVALIDATION",
                ]
            impact.append({
                **change,
                "affected_capabilities": affected_caps,
                "affected_consumers": affected_consumers,
                "current_host_reconciliation_required": current_host_required,
                "required_actions": sorted(set(required_actions)),
            })

    result = {
        "schema": "fa3.capability-usage-graph.v1",
        "id": "FA3-CAPABILITY-USAGE-GRAPH-DERIVED",
        "derived": True,
        "authority": False,
        "runtime_promotion": False,
        "capability_count": capability_count,
        "new_capability": False,
        "new_architectural_authority": False,
        "source_of_truth": LINKS,
        "binding_sources": list(BINDING_ROOTS),
        "manual_capability_id_inference": False,
        "counts": {
            "usage_edges": len(edges),
            "donors_with_usage": len(by_donor),
            "capabilities_with_usage": len(by_capability),
            "consumers_with_usage": len(by_consumer),
            "canonical_binding_records": len(bindings),
            "changed_donor_sources": len(impact),
        },
        "edges": sorted(edges, key=lambda row: row["id"]),
        "views": {
            "by_donor": dict(sorted(by_donor.items())),
            "by_capability": dict(sorted(by_capability.items())),
            "by_consumer": dict(sorted(by_consumer.items())),
        },
        "update_impact": impact,
        "validation": {"result": "PASS" if not errors else "FAIL", "findings": errors},
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Donor ↔ Capability ↔ Consumer map")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--previous-registry", type=Path)
    parser.add_argument("--donor")
    parser.add_argument("--capability")
    parser.add_argument("--consumer")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    previous = load(args.previous_registry) if args.previous_registry else None
    graph = build_capability_usage_graph(args.root, previous_registry=previous)

    display: Any = graph
    if args.donor:
        display = graph["views"]["by_donor"].get(args.donor)
    elif args.capability:
        display = graph["views"]["by_capability"].get(args.capability)
    elif args.consumer:
        display = graph["views"]["by_consumer"].get(args.consumer)
    elif args.summary:
        display = {"counts": graph["counts"], "validation": graph["validation"]}

    if args.output:
        target = args.output if args.output.is_absolute() else args.root / args.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(display, ensure_ascii=False, indent=2))
    return 1 if args.check and graph["validation"]["result"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
