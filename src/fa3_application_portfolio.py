#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fa3_release_baseline import load_active_release_baseline

LEVELS = "canonical/FA3-OPERATING-LEVEL-MODEL-001.json"
PORTFOLIO = "canonical/FA3-APPLICATION-PORTFOLIO-001.json"
DOMAINS = "canonical/FA3-DOMAIN-PACK-REGISTRY-001.json"
DEPENDENCIES = "canonical/FA3-APPLICATION-DEPENDENCY-REGISTRY-001.json"
CATALOG = "canonical/FA3-PRODUCT-CATALOG-001.json"
ENTITLEMENT = "canonical/FA3-ENTITLEMENT-POLICY-001.json"
APP_DONOR = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
EXTERNAL_CATALOG = "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json"
PRODUCT_FAMILY = "canonical/FA3-PRODUCT-FAMILY-REGISTRY-001.json"
GUI = "canonical/FA3-GUI-SURFACE-REGISTRY-001.json"


def load(root: Path, rel: str) -> dict:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + rel)
    return value


def physical_application_ids(root: Path) -> set[str]:
    app_root = root / "apps"
    if not app_root.is_dir():
        return set()
    found: set[str] = set()
    for path in app_root.iterdir():
        if not path.is_dir() or path.name == "shared":
            continue
        if path.name.startswith("fa3-"):
            found.add("fa3." + path.name[4:])
        elif path.name == "workload-mode":
            found.add("fa3.workload-mode")
    return found


def validate(root: Path) -> list[str]:
    lv, po, dm, dp, ca, ep, ad, xc, pf, gui = [
        load(root, rel)
        for rel in (
            LEVELS, PORTFOLIO, DOMAINS, DEPENDENCIES, CATALOG, ENTITLEMENT,
            APP_DONOR, EXTERNAL_CATALOG, PRODUCT_FAMILY, GUI,
        )
    ]
    findings: list[str] = []
    baseline = load_active_release_baseline(root).capability_count
    order = lv.get("order", [])
    expected_order = ["MINIMAL", "PERSONAL", "PROFESSIONAL", "STUDIO", "BUSINESS", "ENTERPRISE"]
    if order != expected_order:
        findings.append("OPERATING_LEVEL_ORDER_INVALID")
    rank = {value: index for index, value in enumerate(order)}

    governed = {
        LEVELS: lv, PORTFOLIO: po, DOMAINS: dm, DEPENDENCIES: dp,
        CATALOG: ca, ENTITLEMENT: ep,
    }
    for rel, record in governed.items():
        if record.get("authority") is not False:
            findings.append("AUTHORITY_BYPASS:" + rel)
        if record.get("new_architectural_authority") not in (None, False):
            findings.append("NEW_ARCHITECTURAL_AUTHORITY_FORBIDDEN:" + rel)
        if record.get("new_capability") not in (None, False):
            findings.append("NEW_CAPABILITY_FORBIDDEN:" + rel)
        if "capability_count" in record and record.get("capability_count") != baseline:
            findings.append("CAPABILITY_BASELINE_DRIFT:" + rel)

    states = set(po.get("portfolio_states", []))
    classes = set(po.get("application_classes", []))
    domains = set(dm.get("domains", []))
    families = {row["family_id"] for row in pf.get("product_families", [])}
    placements = {row["application_id"]: row for row in pf.get("application_placements", [])}
    surfaces = {row.get("route_id") for row in gui.get("surfaces", []) if row.get("route_id")}
    dependency_map = dp.get("application_dependencies", {})
    components = set(dp.get("platform_components", []))

    bundle_membership: dict[str, list[str]] = {}
    for bundle in ca.get("bundles", []):
        if bundle.get("optional") is not True:
            findings.append("BUNDLE_NOT_OPTIONAL:" + str(bundle.get("id")))
        for aid in bundle.get("applications", []):
            bundle_membership.setdefault(aid, []).append(bundle["id"])

    ids: set[str] = set()
    by_id: dict[str, dict] = {}
    for app in po.get("applications", []):
        aid = app.get("application_id")
        if not isinstance(aid, str) or not aid or aid in ids:
            findings.append("DUPLICATE_OR_INVALID_APPLICATION_ID:" + str(aid))
            continue
        ids.add(aid)
        by_id[aid] = app
        if aid in surfaces:
            findings.append("GUI_SURFACE_AS_APPLICATION:" + aid)
        if app.get("portfolio_state") not in states:
            findings.append("INVALID_PORTFOLIO_STATE:" + aid)
        if app.get("application_class") not in classes:
            findings.append("INVALID_APPLICATION_CLASS:" + aid)
        minimum = app.get("minimum_operating_level")
        if minimum not in rank:
            findings.append("INVALID_OPERATING_LEVEL:" + aid)
        elif app.get("supported_operating_levels") != order[rank[minimum]:]:
            findings.append("OPERATING_LEVEL_INHERITANCE_INVALID:" + aid)
        if app.get("primary_domain") not in domains:
            findings.append("INVALID_DOMAIN:" + aid)
        if app.get("individually_entitleable") is not True:
            findings.append("INDIVIDUAL_ENTITLEMENT_REQUIRED:" + aid)

        placement = placements.get(aid)
        if not placement:
            findings.append("PRODUCT_FAMILY_PLACEMENT_MISSING:" + aid)
        elif (
            app.get("primary_product_family") != placement.get("primary_family")
            or placement.get("primary_family") not in families
        ):
            findings.append("PRODUCT_FAMILY_PLACEMENT_MISMATCH:" + aid)

        if aid not in dependency_map:
            findings.append("MISSING_DEPENDENCY_DECLARATION:" + aid)
        else:
            required = dependency_map[aid]
            if not isinstance(required, list):
                findings.append("INVALID_DEPENDENCY_DECLARATION:" + aid)
            else:
                for dep in required:
                    if dep not in components:
                        findings.append("UNKNOWN_PLATFORM_DEPENDENCY:" + aid + ":" + str(dep))
                if sorted(app.get("required_platform_dependencies", [])) != sorted(required):
                    findings.append("DEPENDENCY_PROJECTION_DRIFT:" + aid)

        expected_bundles = sorted(bundle_membership.get(aid, []))
        if sorted(app.get("available_in_bundles", [])) != expected_bundles:
            findings.append("BUNDLE_MEMBERSHIP_DRIFT:" + aid)

        app_class = app.get("application_class")
        state = app.get("portfolio_state")
        markers = app.get("implementation_markers", [])
        if app_class in {"INTERNAL_APPLICATION", "SYSTEM_APPLICATION", "COMPANION_APPLICATION"} and state == "EXISTING":
            if not markers:
                findings.append("EXISTING_IMPLEMENTATION_MARKER_REQUIRED:" + aid)
            for marker in markers:
                if not (root / marker).exists():
                    findings.append("IMPLEMENTATION_MARKER_MISSING:" + aid + ":" + marker)
        if app_class in {"INTERNAL_APPLICATION", "COMPANION_APPLICATION"} and state == "IN_PROGRESS":
            refs = app.get("active_work_refs", [])
            if not refs:
                findings.append("IN_PROGRESS_WORK_REF_REQUIRED:" + aid)

    for aid in dependency_map:
        if aid not in ids:
            findings.append("DEPENDENCY_APPLICATION_UNKNOWN:" + aid)
    for aid in bundle_membership:
        if aid not in ids:
            findings.append("BUNDLE_APPLICATION_UNKNOWN:" + aid)

    for aid in physical_application_ids(root):
        if aid not in ids:
            findings.append("ACTIVE_IMPLEMENTATION_WITHOUT_PORTFOLIO_RECORD:" + aid)
        elif by_id[aid].get("portfolio_state") != "EXISTING":
            findings.append("PORTFOLIO_STATE_DRIFT:" + aid)

    declared = {row.get("application_id"): row for row in ad.get("applications", [])}
    for app in po.get("applications", []):
        aid = app["application_id"]
        if app.get("application_class") in {"INTERNAL_APPLICATION", "COMPANION_APPLICATION"}:
            row = declared.get(aid)
            if not row:
                findings.append("APPLICATION_DONOR_DECLARATION_MISSING:" + aid)
            elif row.get("lifecycle") != app.get("portfolio_state"):
                findings.append("APPLICATION_DONOR_LIFECYCLE_DRIFT:" + aid)

    for row in xc.get("applications", []):
        aid = "studio." + str(row.get("id"))
        if aid not in ids:
            findings.append("CURATED_EXTERNAL_APPLICATION_MISSING:" + aid)
        elif by_id[aid].get("fa3_entitlement_does_not_grant_upstream_rights") is not True:
            findings.append("EXTERNAL_UPSTREAM_RIGHTS_BOUNDARY_MISSING:" + aid)

    if not ep.get("rules", {}).get("higher_operating_level_does_not_grant_apps"):
        findings.append("TIER_APP_LOCKIN_POLICY_MISSING")
    if not ep.get("rules", {}).get("product_family_is_context_not_permission"):
        findings.append("PRODUCT_FAMILY_PERMISSION_SEPARATION_MISSING")
    if not dp.get("rules", {}).get("platform_dependency_never_grants_application_entitlement"):
        findings.append("DEPENDENCY_ENTITLEMENT_SEPARATION_MISSING")
    return sorted(set(findings))


def resolve(root: Path, application_ids: list[str], requested_level: str | None = None) -> dict:
    lv, po, dp = [load(root, rel) for rel in (LEVELS, PORTFOLIO, DEPENDENCIES)]
    order = lv["order"]
    rank = {value: index for index, value in enumerate(order)}
    by_id = {app["application_id"]: app for app in po["applications"]}
    unknown = sorted(set(application_ids) - set(by_id))
    if unknown:
        raise ValueError("UNKNOWN_APPLICATION:" + ",".join(unknown))
    dependency_map = dp.get("application_dependencies", {})
    missing_dependencies = sorted(set(application_ids) - set(dependency_map))
    if missing_dependencies:
        raise ValueError("MISSING_DEPENDENCY_DECLARATION:" + ",".join(missing_dependencies))
    required_rank = max([rank[by_id[aid]["minimum_operating_level"]] for aid in application_ids] or [0])
    if requested_level is not None:
        if requested_level not in rank:
            raise ValueError("INVALID_OPERATING_LEVEL:" + requested_level)
        if rank[requested_level] < required_rank:
            raise ValueError("APPLICATION_BELOW_MINIMUM_OPERATING_LEVEL")
        required_rank = max(required_rank, rank[requested_level])
    components: set[str] = set()
    for aid in application_ids:
        components.update(dependency_map[aid])
    return {
        "operating_level": order[required_rank],
        "applications": application_ids,
        "platform_dependencies": sorted(components),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apps", nargs="*")
    parser.add_argument("--level")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    findings = validate(root)
    if findings:
        print(json.dumps({"result": "FAIL", "findings": findings}, indent=2))
        return 2
    if args.apps is not None:
        try:
            result = resolve(root, args.apps, args.level)
        except ValueError as exc:
            print(json.dumps({"result": "DENY", "finding": str(exc)}, indent=2))
            return 2
        print(json.dumps({"result": "PASS", **result}, indent=2))
        return 0
    print(json.dumps({"result": "PASS", "findings": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
