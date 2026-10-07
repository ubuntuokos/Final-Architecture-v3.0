#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Product-family placement helpers for the existing FA3 application inventory."""
from __future__ import annotations

from typing import Any

PLATFORM_ID = "FA3-PLATFORM-001"
REGISTRY_ID = "FA3-PRODUCT-FAMILY-REGISTRY-001"
EXPECTED_FAMILIES = {
    "FA3-FAMILY-CREATIVE-MEDIA-001",
    "FA3-FAMILY-STUDIO-FILM-001",
    "FA3-FAMILY-AI-WORKSTATION-001",
    "FA3-FAMILY-BUSINESS-COLLABORATION-001",
    "FA3-FAMILY-ENTERPRISE-001",
}


def validate_product_family_registry(registry: dict[str, Any], capability_count: int) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if registry.get("id") != REGISTRY_ID or registry.get("platform_id") != PLATFORM_ID:
        findings.append({"code": "PLATFORM_REGISTRY_ID_INVALID", "detail": REGISTRY_ID})
    if registry.get("authority") is not False or registry.get("source_of_execution_truth") is not False:
        findings.append({"code": "PRODUCT_FAMILY_AUTHORITY_FORBIDDEN", "detail": REGISTRY_ID})
    if registry.get("capability_count") != capability_count:
        findings.append({"code": "PRODUCT_FAMILY_CAPABILITY_BASELINE_DRIFT", "detail": str(registry.get("capability_count"))})
    if registry.get("new_capabilities") != 0 or registry.get("new_architectural_authorities") != 0:
        findings.append({"code": "PRODUCT_FAMILY_BASELINE_OR_AUTHORITY_DELTA_FORBIDDEN", "detail": REGISTRY_ID})

    families = registry.get("product_families", [])
    family_ids = [row.get("family_id") for row in families if isinstance(row, dict)]
    if set(family_ids) != EXPECTED_FAMILIES or len(family_ids) != len(set(family_ids)):
        findings.append({"code": "PRODUCT_FAMILY_SET_INVALID", "detail": ",".join(sorted(str(x) for x in family_ids))})

    seen: set[str] = set()
    for row in registry.get("application_placements", []):
        if not isinstance(row, dict):
            findings.append({"code": "INVALID_APPLICATION_PRODUCT_FAMILY_PLACEMENT", "detail": "<non-object>"})
            continue
        aid = row.get("application_id")
        primary = row.get("primary_family")
        secondary = row.get("secondary_families", [])
        if not isinstance(aid, str) or not aid or aid in seen:
            findings.append({"code": "DUPLICATE_OR_INVALID_APPLICATION_PRODUCT_FAMILY_PLACEMENT", "detail": str(aid)})
            continue
        seen.add(aid)
        if row.get("platform_id") != PLATFORM_ID or row.get("authority") is not False:
            findings.append({"code": "APPLICATION_PLATFORM_BINDING_INVALID", "detail": aid})
        if primary not in EXPECTED_FAMILIES:
            findings.append({"code": "INVALID_PRIMARY_PRODUCT_FAMILY", "detail": aid})
        if not isinstance(secondary, list) or any(x not in EXPECTED_FAMILIES for x in secondary):
            findings.append({"code": "INVALID_SECONDARY_PRODUCT_FAMILY", "detail": aid})
            secondary = []
        if primary in secondary or len(secondary) != len(set(secondary)):
            findings.append({"code": "DUPLICATE_PRODUCT_FAMILY_BINDING", "detail": aid})
        if row.get("classification_status") != "CLASSIFIED":
            findings.append({"code": "APPLICATION_PRODUCT_FAMILY_NOT_CLASSIFIED", "detail": aid})
        if row.get("automatic_permission_grant") is not False or row.get("automatic_runtime_activation") is not False:
            findings.append({"code": "PRODUCT_FAMILY_AUTOMATIC_AUTHORIZATION_FORBIDDEN", "detail": aid})
    return findings


def placement_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row["application_id"]: row
        for row in registry.get("application_placements", [])
        if isinstance(row, dict) and isinstance(row.get("application_id"), str)
    }


def apply_product_family_placement(
    applications: dict[str, dict[str, Any]],
    registry: dict[str, Any],
    errors: list[dict[str, str]],
) -> dict[str, list[str]]:
    placements = placement_map(registry)
    by_family: dict[str, list[str]] = {family_id: [] for family_id in EXPECTED_FAMILIES}

    for aid, app in applications.items():
        placement = placements.get(aid)
        if placement is None:
            errors.append({"code": "UNCLASSIFIED_APPLICATION_PRODUCT_FAMILY", "detail": aid})
            app["platform"] = {"id": PLATFORM_ID, "classification": "UNCLASSIFIED"}
            app["product_family"] = {"primary": None, "secondary": []}
            continue
        primary = placement["primary_family"]
        secondary = sorted(set(placement.get("secondary_families", [])))
        app["platform"] = {
            "id": PLATFORM_ID,
            "layer": "APPLICATION",
            "hierarchy": ["PLATFORM", "PRODUCT_FAMILY", "APPLICATION"],
            "classification": "CLASSIFIED",
        }
        app["product_family"] = {
            "primary": primary,
            "secondary": secondary,
            "placement_kind": placement.get("placement_kind"),
            "context_only": True,
            "permission_grant": False,
            "execution_authority": False,
        }
        by_family.setdefault(primary, []).append(aid)
        for family_id in secondary:
            by_family.setdefault(family_id, []).append(aid)

    orphaned = sorted(set(placements) - set(applications))
    for aid in orphaned:
        errors.append({"code": "ORPHANED_APPLICATION_PRODUCT_FAMILY_PLACEMENT", "detail": aid})

    return {key: sorted(set(value)) for key, value in sorted(by_family.items())}
