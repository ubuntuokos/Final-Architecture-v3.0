#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

REGISTRY = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
POLICY = "canonical/universal-capability-access-policy.json"
AUDIT = "canonical/universal-capability-access-audit-status.json"
GATE = "canonical/FA3-GATE-UNIVERSAL-CAPABILITY-ACCESS-001.json"
CAPABILITY_COUNT = module_active_capability_count(__file__)

INDEX_KINDS = {
    "GITHUB_TOPIC", "GITHUB_ORGANIZATION", "GITHUB_ORG", "GITHUB_PROFILE",
    "DISCOVERY_INDEX", "GITHUB_CATALOG",
}
REASON_PATTERNS = (
    ("NONCOMMERCIAL", re.compile(r"NONCOMMERCIAL|NON-COMMERCIAL|CC-BY-NC|BY-NC-ND|BY-NC-SA|RESEARCH[-_ ]?ONLY|ACADEMIC[-_ ]?ONLY", re.I)),
    ("PROPRIETARY", re.compile(r"PROPRIETARY|COMMERCIAL APPLICATION", re.I)),
    ("CUSTOM_RESTRICTED_LICENSE", re.compile(r"COMMUNITY LICENSE|CUSTOM_LICENSE_RESTRICTIONS|NOKIA-HEIF|AUDERING|ADOBE RESEARCH LICENSE", re.I)),
    ("GEOGRAPHIC_OR_FIELD_RESTRICTION", re.compile(r"GEO_RESTRICT|TERRITOR|GEOGRAPH|REGION[-_ ]?RESTRICT|FIELD[-_ ]?OF[-_ ]?USE|EUROPEAN UNION|UNITED KINGDOM|SOUTH KOREA", re.I)),
    ("SERVICE_OR_PAID_CONDITION", re.compile(r"PAID DEPENDENCY|COMMERCIAL API|SERVICE TERMS|REQUIRES ACCOUNT|ACCOUNT REQUIRED|API KEY|CLOUD[-_ ]?ONLY|ENTITLEMENT REQUIRED", re.I)),
    ("VENDOR_OR_HARDWARE_LOCK", re.compile(r"NVIDIA[-_ ]?ONLY|CUDA[-_ ]?ONLY|GPU[-_ ]?ONLY|WINDOWS[-_ ]?ONLY|MACOS[-_ ]?ONLY|APPLE[-_ ]?ONLY", re.I)),
)
REVIEW_PATTERN = re.compile(
    r"UNKNOWN|UNVERIFIED|PENDING|REVIEW_REQUIRED|NOASSERTION|NO_ROOT_LICENSE|CONFLICT|MIXED_REVIEW_REQUIRED|EXACT_LICENSE_REVIEW",
    re.I,
)
MATERIAL_USAGE_KINDS = {"CODE_REUSE", "RUNTIME_DEPENDENCY"}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def classify_donor(row: dict[str, Any]) -> dict[str, Any]:
    source = row.get("source") or {}
    license_row = row.get("license") or {}
    kind = str(source.get("kind", "")).upper()
    status = str(license_row.get("status", "")).upper()
    declared = str(license_row.get("declared", "")).upper()
    policy = str(row.get("code_reuse_policy", "")).upper()
    modes = [str(x).upper() for x in row.get("donor_modes", [])]
    tags = [str(x).upper() for x in row.get("tags", [])]
    notes = [str(x).upper() for x in row.get("notes", [])]

    if (
        kind in INDEX_KINDS
        or "DISCOVERY_INDEX" in modes
        or re.search(
            r"COLLECTION_INDEX|ORGANIZATION_INDEX|PROFILE_OR_ORGANIZATION_INDEX|NOT_APPLICABLE_INDEX|INDEX_NOT_CODE|NOT_APPLICABLE_TO_ORGANIZATION_INDEX",
            status,
        )
    ):
        return {"classification": "INDEX_OR_DISCOVERY_ONLY", "reasons": []}

    full = " ".join([status, declared, policy, *tags, *notes])
    reasons = [name for name, pattern in REASON_PATTERNS if pattern.search(full)]
    if reasons:
        return {"classification": "KNOWN_ACCESS_BARRIER_SIGNAL", "reasons": sorted(set(reasons))}

    if REVIEW_PATTERN.search(" ".join([status, declared, policy])):
        return {"classification": "ACCESS_RIGHTS_REVIEW_REQUIRED", "reasons": []}

    return {"classification": "NO_KNOWN_ACCESS_BARRIER_SIGNAL", "reasons": []}


def is_material_usage(usage: dict[str, Any]) -> bool:
    if usage.get("usage_kind") in MATERIAL_USAGE_KINDS:
        return True
    if usage.get("material_adoption") is True:
        return True
    for key in ("code_imported", "runtime_dependency", "provider_admission", "model_admission", "dataset_admission", "asset_admission"):
        if usage.get(key) is True:
            return True
    return False


def validate_material_usage(usage: dict[str, Any], donor_class: dict[str, Any]) -> list[str]:
    if not is_material_usage(usage):
        return []
    findings: list[str] = []
    access = usage.get("universal_access")
    if not isinstance(access, dict):
        return ["UCA-201:MATERIAL_USAGE_UNIVERSAL_ACCESS_EVIDENCE_REQUIRED"]
    if access.get("restriction_circumvention") is True:
        findings.append("UCA-202:RESTRICTION_CIRCUMVENTION_FORBIDDEN")

    classification = donor_class["classification"]
    if classification == "ACCESS_RIGHTS_REVIEW_REQUIRED":
        findings.append("UCA-203:UNKNOWN_ACCESS_RIGHTS_BLOCK_MATERIAL_ADOPTION")
    elif classification == "KNOWN_ACCESS_BARRIER_SIGNAL":
        if access.get("classification") != "OPTIONAL_RESTRICTED_WITH_GLOBAL_SUBSTITUTE":
            findings.append("UCA-204:RESTRICTED_DONOR_MUST_BE_OPTIONAL_WITH_GLOBAL_SUBSTITUTE")
        refs = access.get("global_substitute_refs")
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or not x for x in refs):
            findings.append("UCA-205:GLOBAL_SUBSTITUTE_EVIDENCE_REQUIRED")
    elif classification == "INDEX_OR_DISCOVERY_ONLY":
        findings.append("UCA-206:DISCOVERY_INDEX_CANNOT_BE_MATERIAL_DEPENDENCY")
    else:
        if access.get("classification") not in {"GLOBAL_BASELINE", "OPTIONAL_WITH_GLOBAL_EQUIVALENT"}:
            findings.append("UCA-207:MATERIAL_USAGE_ACCESS_CLASSIFICATION_REQUIRED")
    return findings


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    registry_raw = (root / REGISTRY).read_bytes()
    registry = json.loads(registry_raw)
    links = loadj(root / LINKS)
    policy = loadj(root / POLICY)
    audit = loadj(root / AUDIT)
    gate_row = loadj(root / GATE)

    if policy.get("id") != "FA3-UNIVERSAL-CAPABILITY-ACCESS-POLICY-001" or policy.get("status") != "CANONICAL_FAIL_CLOSED":
        findings.append({"code": "UCA-001", "message": "policy identity/status drift"})
    if policy.get("capability_count") != CAPABILITY_COUNT or policy.get("new_architectural_authority") is not False:
        findings.append({"code": "UCA-002", "message": "capability/authority invariant drift"})
    if gate_row.get("fail_closed") is not True or gate_row.get("gateset_id") != "FA3-SUPPLY-RUNTIME-HARDENING-GATESET-001":
        findings.append({"code": "UCA-003", "message": "gate binding drift"})

    entries = registry.get("entries", [])
    by_id = {row.get("donor_id"): row for row in entries if isinstance(row, dict)}
    counts = {
        "INDEX_OR_DISCOVERY_ONLY": 0,
        "KNOWN_ACCESS_BARRIER_SIGNAL": 0,
        "ACCESS_RIGHTS_REVIEW_REQUIRED": 0,
        "NO_KNOWN_ACCESS_BARRIER_SIGNAL": 0,
    }
    reason_counts = {name: 0 for name, _ in REASON_PATTERNS}
    classes: dict[str, dict[str, Any]] = {}
    for row in entries:
        c = classify_donor(row)
        classes[row["donor_id"]] = c
        counts[c["classification"]] += 1
        for reason in c["reasons"]:
            reason_counts[reason] += 1

    current_blob = git_blob_sha(registry_raw)
    if audit.get("registry_git_blob_sha") != current_blob:
        findings.append({"code": "UCA-010", "message": "audit snapshot registry blob mismatch", "actual": current_blob})
    if audit.get("registry_entry_count") != len(entries):
        findings.append({"code": "UCA-011", "message": "audit registry count mismatch"})
    if audit.get("classification_counts") != counts:
        findings.append({"code": "UCA-012", "message": "audit classification count drift", "actual": counts})
    if audit.get("known_access_barrier_reason_counts") != reason_counts:
        findings.append({"code": "UCA-013", "message": "audit barrier-reason count drift", "actual": reason_counts})

    usage = [row for row in links.get("donor_usage_records", []) if row.get("status") in {"ACTIVE", "PINNED_STABLE", "REPLACEMENT_PENDING"}]
    material = []
    for row in usage:
        did = row.get("donor_id")
        if did not in by_id:
            findings.append({"code": "UCA-100", "message": "usage references unknown donor", "usage_id": row.get("id"), "donor_id": did})
            continue
        if is_material_usage(row):
            material.append(row)
            for item in validate_material_usage(row, classes[did]):
                code, message = item.split(":", 1)
                findings.append({"code": code, "message": message, "usage_id": row.get("id"), "donor_id": did})

    if audit.get("active_usage_edge_count") != len(usage):
        findings.append({"code": "UCA-020", "message": "active usage edge count drift", "actual": len(usage)})
    if audit.get("active_material_usage_edge_count") != len(material):
        findings.append({"code": "UCA-021", "message": "material usage edge count drift", "actual": len(material)})

    registry_policy = registry.get("planning_policy", {})
    required_registry_flags = (
        "universal_capability_access_required",
        "restricted_donor_may_not_be_sole_capability_implementation",
        "global_substitute_or_fa3_native_required_for_restricted_material_adoption",
        "unknown_access_rights_fail_closed_for_material_adoption",
    )
    if not all(registry_policy.get(key) is True for key in required_registry_flags):
        findings.append({"code": "UCA-030", "message": "registry universal-access policy binding missing"})

    report = {
        "schema": "fa3.universal-capability-access-gate-report.v1",
        "gate_id": "FA3-GATE-UNIVERSAL-CAPABILITY-ACCESS-001",
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "registry_git_blob_sha": current_blob,
        "registry_entry_count": len(entries),
        "classification_counts": counts,
        "known_access_barrier_reason_counts": reason_counts,
        "active_usage_edge_count": len(usage),
        "active_material_usage_edge_count": len(material),
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "rights_clearance_complete": audit.get("rights_clearance_complete", False),
    }
    out = root / "reports/universal-capability-access-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    result = gate(Path(args.root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
