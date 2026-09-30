#!/usr/bin/env python3
"""FA3 tutorial-reference reuse planner.

This module is deliberately non-authoritative and non-executing. It consumes
only tutorial records already represented by an ACCEPTED_REFERENCE donor entry,
matches Tutorial Feature Units (TFUs) to the existing capability/application
inventory, proposes shared placement, emits retrospective impact/manual tasks,
and records Current Host alignment requirements. It never executes tutorial
commands, installs dependencies, admits providers, changes the capability
baseline, or promotes runtime state.
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
CAPABILITY_MATRIX = "canonical/conformance-matrix.csv"
CAPABILITY_MODEL = "canonical/FA3-CAPABILITY-MODEL-175-001.json"
POLICY = "canonical/FA3-TUTORIAL-SHARED-CAPABILITY-POLICY-001.json"
SCHEMA = "canonical/schemas/FA3-TUTORIAL-REFERENCE-SCHEMA-001.json"
CURRENT_HOST_IMPACT = "canonical/FA3-TUTORIAL-SHARED-CAPABILITY-CURRENT-HOST-IMPACT-001.json"

RIGHTS_STATES = {
    "PERMISSIVE",
    "REFERENCE_ONLY",
    "UNKNOWN_REFERENCE_ONLY",
    "OWNER_AUTHORED",
}
REUSE_ALLOWANCES = {
    "FUNCTIONAL_ANALYSIS_ONLY",
    "CLEAN_FA3_REEXPRESSION",
    "LICENSE_REVIEWED_REUSE",
}
PLACEMENTS = {"AUTO", "APPLICATION_LOCAL", "SHARED"}


def load_json(path: Path) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(row, dict):
        raise ValueError(f"expected JSON object: {path}")
    return row


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
            "kind": "CURATED_EXTERNAL_APPLICATION",
            "lifecycle": "CATALOG_" + str(item.get("admission", "UNKNOWN")),
            "aliases": sorted(set([item["name"], str(item["id"])])),
        }
    for item in links.get("applications", []):
        aid = str(item["application_id"])
        apps[aid] = {
            "application_id": aid,
            "name": item["name"],
            "kind": item["kind"],
            "lifecycle": item["lifecycle"],
            "aliases": sorted(set([item["name"], aid] + item.get("aliases", []))),
        }
    return apps


def capability_inventory(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with (root / CAPABILITY_MATRIX).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            cid = str(row.get("capability_id", "")).strip()
            if not cid:
                continue
            out[cid] = {
                "capability_id": cid,
                "name": str(row.get("capability", "")).strip(),
                "layers": str(row.get("layers", "")).strip(),
                "activation": str(row.get("activation", "")).strip(),
                "design_conformance": str(row.get("design_conformance", "")).strip(),
                "runtime_conformance": str(row.get("runtime_conformance", "")).strip(),
            }
    return out


def _match_capabilities(
    hints: list[str], capabilities: dict[str, dict[str, Any]]
) -> tuple[list[str], list[str]]:
    matches: set[str] = set()
    ambiguous: list[str] = []
    by_name: dict[str, list[str]] = {}
    for cid, row in capabilities.items():
        by_name.setdefault(norm(row["name"]), []).append(cid)
    for raw in hints:
        hint = str(raw).strip()
        if hint in capabilities:
            matches.add(hint)
            continue
        candidates = by_name.get(norm(hint), [])
        if len(candidates) == 1:
            matches.add(candidates[0])
        elif len(candidates) > 1:
            ambiguous.append(hint)
    return sorted(matches), sorted(set(ambiguous))


def _match_applications(
    hints: list[str], apps: dict[str, dict[str, Any]]
) -> tuple[list[str], list[str]]:
    aliases: dict[str, set[str]] = {}
    for aid, row in apps.items():
        for alias in row["aliases"]:
            aliases.setdefault(norm(str(alias)), set()).add(aid)
    matches: set[str] = set()
    ambiguous: list[str] = []
    for raw in hints:
        hint = str(raw).strip()
        if hint in apps:
            matches.add(hint)
            continue
        candidates = aliases.get(norm(hint), set())
        if len(candidates) == 1:
            matches.update(candidates)
        elif len(candidates) > 1:
            ambiguous.append(hint)
    return sorted(matches), sorted(set(ambiguous))


def _validate_tutorial(
    tutorial: dict[str, Any], registered_donor: dict[str, Any] | None
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def add(code: str, message: str) -> None:
        findings.append({"code": code, "message": message})

    if tutorial.get("schema") != "fa3.tutorial-reference-input.v1":
        add("TUT-INPUT-001", "tutorial input schema identity mismatch")
    if tutorial.get("reference_class") != "TUTORIAL_REFERENCE":
        add("TUT-INPUT-002", "reference_class must be TUTORIAL_REFERENCE")
    if not tutorial.get("donor_id"):
        add("TUT-INPUT-003", "donor_id is required")
    if registered_donor is None:
        add(
            "TUT-REG-001",
            "tutorial donor_id is not a published ACCEPTED_REFERENCE planning source",
        )

    provenance = tutorial.get("provenance")
    if not isinstance(provenance, dict):
        add("TUT-RIGHTS-001", "provenance object is required")
    else:
        if provenance.get("rights_status") not in RIGHTS_STATES:
            add("TUT-RIGHTS-002", "rights_status is missing or unsupported")
        if provenance.get("reuse_allowance") not in REUSE_ALLOWANCES:
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
        if not str(feature.get("name", "")).strip() or not str(
            feature.get("intent", "")
        ).strip():
            add("TUT-TFU-004", f"{fid or '<missing>'}: name and intent are required")
        if feature.get("requested_placement", "AUTO") not in PLACEMENTS:
            add("TUT-PLACE-001", f"{fid or '<missing>'}: unsupported requested_placement")
        for key in ("capability_hints", "application_hints"):
            if key in feature and not isinstance(feature.get(key), list):
                add("TUT-TFU-005", f"{fid or '<missing>'}: {key} must be a list")
        if feature.get("runtime_promotion_claimed") is True:
            add(
                "TUT-RUNTIME-001",
                f"{fid or '<missing>'}: tutorial planning cannot claim runtime promotion",
            )
        if feature.get("manual_claim_available") is True:
            add(
                "TUT-MANUAL-001",
                f"{fid or '<missing>'}: planner cannot publish an availability claim",
            )
    return findings



def _impact_action(lifecycle: str, existing: bool, shared: bool) -> str:
    if not existing:
        return (
            "ADAPTER_REQUIRED_AFTER_IMPLEMENTATION"
            if shared
            else "BLOCKED_BY_PENDING_IMPLEMENTATION"
        )
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
        if row.get("status") == "ACCEPTED_REFERENCE"
        and row.get("discoverable_for_planning") is True
    }
    donor = donors.get(str(tutorial.get("donor_id")))
    findings = _validate_tutorial(tutorial, donor)
    apps = application_inventory(root)
    capabilities = capability_inventory(root)

    donor_targets = [
        str(value)
        for value in (donor or {}).get("target_hints", [])
        if isinstance(value, str)
    ]
    feature_results: list[dict[str, Any]] = []

    features = tutorial.get("feature_units", [])
    for feature in features if isinstance(features, list) else []:
        if not isinstance(feature, dict):
            continue
        fid = str(feature.get("feature_id", "<missing>"))
        capability_hints = [str(x) for x in feature.get("capability_hints", [])]
        application_hints = [str(x) for x in feature.get("application_hints", [])]
        application_hints += donor_targets
        cap_matches, cap_ambiguous = _match_capabilities(capability_hints, capabilities)
        app_matches, app_ambiguous = _match_applications(application_hints, apps)

        existing = bool(cap_matches)
        shared = len(app_matches) >= 2
        requested = feature.get("requested_placement", "AUTO")
        if cap_ambiguous:
            findings.append(
                {
                    "code": "TUT-CAP-AMBIGUOUS",
                    "message": f"{fid}: ambiguous capability hints: {', '.join(cap_ambiguous)}",
                }
            )
        if app_ambiguous:
            findings.append(
                {
                    "code": "TUT-APP-AMBIGUOUS",
                    "message": f"{fid}: ambiguous application hints: {', '.join(app_ambiguous)}",
                }
            )
        if not app_matches:
            findings.append(
                {
                    "code": "TUT-APP-001",
                    "message": f"{fid}: no deterministic FA3 application target resolved",
                }
            )
        if shared and requested == "APPLICATION_LOCAL":
            findings.append(
                {
                    "code": "TUT-SHARED-001",
                    "message": f"{fid}: two or more consumers require one shared functional core",
                }
            )
        if not existing and feature.get("requested_top_level_capability") is True:
            findings.append(
                {
                    "code": "TUT-CAP-175-GUARD",
                    "message": f"{fid}: new top-level capability requires explicit capability-model reconciliation",
                }
            )

        impact = []
        for aid in app_matches:
            lifecycle = apps[aid]["lifecycle"]
            impact.append(
                {
                    "application_id": aid,
                    "lifecycle": lifecycle,
                    "action": _impact_action(lifecycle, existing, shared),
                    "manual_update_required": True,
                    "capability_loss_allowed": False,
                }
            )

        if shared:
            placement = "SHARED_LAYER_REQUIRED"
        elif app_matches:
            placement = "APPLICATION_CONTEXT"
        else:
            placement = "TARGET_UNRESOLVED"

        current_host = {
            "structural_runtime_change": feature.get("structural_runtime_change") is True,
            "alignment": (
                "CURRENT_HOST_REQUALIFICATION_REQUIRED_AFTER_IMPLEMENTATION"
