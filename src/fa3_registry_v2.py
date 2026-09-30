#!/usr/bin/env python3
"""FA3 Donor & Capability Registry v2 shadow migration and volume planning."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any

from fa3_application_donor_index import build_index

LEGACY_REGISTRY = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
APP_LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
CAP_MODEL = "canonical/FA3-CAPABILITY-MODEL-175-001.json"
POLICY = "canonical/FA3-DONOR-REGISTRY-V2-POLICY-001.json"

TARGET_FILL = 0.70
MIN_FREE_RESERVE = 0.30
ROLLOVER = 0.90
REBALANCE = 0.95
REBALANCE_TARGET = 0.70

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "agents": ("agent", "agentic", "multi-agent"),
    "ai-generation": ("generation", "generative", "diffusion", "text-to", "image generation", "video generation"),
    "audio": ("audio", "music", "voice", "speech", "daw", "midi"),
    "business": ("crm", "erp", "business", "sales", "finance", "accounting"),
    "communication": ("mail", "email", "chat", "messaging", "contact", "meeting", "conference"),
    "creative": ("creative", "design", "media production", "studio"),
    "data": ("database", "data", "sql", "vector", "storage"),
    "gateway-proxy": ("gateway", "proxy", "reverse proxy", "api gateway"),
    "graphics-2d": ("2d", "vector", "svg", "illustration"),
    "graphics-3d": ("3d", "dcc", "mesh", "scene", "usd", "gltf"),
    "model-runtime": ("model", "inference", "gguf", "onnx", "runtime", "llm"),
    "orchestration": ("orchestration", "orchestrator", "workflow", "temporal", "scheduler"),
    "photo": ("photo", "raw", "image editor", "photography"),
    "security": ("security", "auth", "identity", "zero trust", "secret"),
    "story-writing": ("story", "screenplay", "writing", "script", "novel"),
    "system": ("linux", "system", "kernel", "packaging", "desktop", "hardware"),
    "video": ("video", "editor", "broadcast", "streaming", "codec", "vfx"),
    "shared": ("shared", "plugin", "extension", "common service"),
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("EXPECTED_JSON_OBJECT:" + str(path))
    return value


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _json_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "unnamed"


def validate_policy(policy: dict[str, Any]) -> None:
    storage = policy.get("storage", {})
    expected = {
        "initial_target_fill_percent": 70,
        "minimum_free_growth_reserve_percent": 30,
        "rollover_percent": 90,
        "rebalance_percent": 95,
        "rebalance_target_fill_percent": 70,
    }
    for key, value in expected.items():
        if storage.get(key) != value:
            raise ValueError("REGISTRY_V2_CAPACITY_POLICY_DRIFT:" + key)
    if policy.get("capability_baseline") != 175:
        raise ValueError("REGISTRY_V2_CAPABILITY_BASELINE_NOT_175")


def capacity_for_used(used_bytes: int) -> int:
    if used_bytes < 0:
        raise ValueError("NEGATIVE_USED_BYTES")
    if used_bytes == 0:
        return 0
    # Integer arithmetic avoids binary-float drift (e.g. 700 / 0.70 -> 1000 exactly).
    return (used_bytes * 100 + 69) // 70


def fill_ratio(used_bytes: int, capacity_bytes: int) -> float:
    if used_bytes < 0 or capacity_bytes <= 0:
        raise ValueError("INVALID_CAPACITY")
    return used_bytes / capacity_bytes


def volume_state(used_bytes: int, capacity_bytes: int) -> str:
    ratio = fill_ratio(used_bytes, capacity_bytes)
    if ratio >= REBALANCE:
        return "REBALANCE_REQUIRED"
    if ratio >= ROLLOVER:
        return "ROLLOVER"
    return "OPEN"


def rebalance_bytes_required(used_bytes: int, capacity_bytes: int) -> int:
    if volume_state(used_bytes, capacity_bytes) != "REBALANCE_REQUIRED":
        return 0
    target = math.floor(capacity_bytes * REBALANCE_TARGET)
    return max(0, used_bytes - target)


def derive_growth_profile(observation: dict[str, Any] | None) -> dict[str, Any]:
    if not observation:
        return {
            "upstream_activity": "UNKNOWN",
            "registry_growth_impact": "UNKNOWN",
            "storage_class": "SHARED_VOLUME",
            "basis": "NO_ACTIVITY_OBSERVATION",
        }
    commits = int(observation.get("commits_90d", 0) or 0)
    releases = int(observation.get("releases_12m", 0) or 0)
    registry_changes = int(observation.get("registry_changes_90d", 0) or 0)
    if observation.get("bursty") is True:
        upstream = "BURSTY"
    elif commits >= 90 or releases >= 12:
        upstream = "HIGH"
    elif commits >= 12 or releases >= 4:
        upstream = "NORMAL"
    elif commits or releases:
        upstream = "LOW"
    else:
        upstream = "STATIC"
    if observation.get("registry_bursty") is True:
        impact = "BURSTY"
    elif registry_changes >= 9:
        impact = "HIGH"
    elif registry_changes >= 3:
        impact = "NORMAL"
    elif registry_changes:
        impact = "LOW"
    else:
        impact = "STATIC"
    dedicated = upstream in {"HIGH", "BURSTY"} or impact in {"HIGH", "BURSTY"}
    return {
        "upstream_activity": upstream,
        "registry_growth_impact": impact,
        "storage_class": "DEDICATED_SERIES" if dedicated else "SHARED_VOLUME",
        "basis": "OBSERVED_HISTORY",
        "observation": observation,
    }


def _hint_strings(donor: dict[str, Any]) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for priority, key in enumerate(
        ("domain_hints", "target_hints", "tags", "capability_hints", "problem_hints"),
        start=5,
    ):
        values = donor.get(key, [])
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str):
                    rows.append((10 - priority, value.casefold()))
    return rows


def classify_categories(donor: dict[str, Any]) -> dict[str, Any]:
    scores: dict[str, int] = {}
    for weight, text in _hint_strings(donor):
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                scores[category] = scores.get(category, 0) + weight
    if not scores:
        return {
            "primary_category": "cross-domain",
            "categories": ["cross-domain"],
            "classification": "REVIEW_REQUIRED",
        }
    ordered = sorted(scores, key=lambda key: (-scores[key], key))
    return {
        "primary_category": ordered[0],
        "categories": ordered,
        "classification": "DERIVED_FROM_EXISTING_HINTS",
    }


def _validate_legacy(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    registry = _load(root / LEGACY_REGISTRY)
    links = _load(root / APP_LINKS)
    cap_model = _load(root / CAP_MODEL)
    if registry.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
        raise ValueError("UNEXPECTED_LEGACY_REGISTRY")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        raise ValueError("LEGACY_ENTRIES_NOT_LIST")
    if registry.get("backfill", {}).get("entry_count") != len(entries):
        raise ValueError("LEGACY_REGISTRY_COUNT_DRIFT")
    if cap_model.get("id") != "FA3-CAPABILITY-MODEL-175-001":
        raise ValueError("UNEXPECTED_CAPABILITY_MODEL")
    if cap_model.get("canonical_capability_count") != 175:
        raise ValueError("CAPABILITY_BASELINE_NOT_175")
    ids: set[str] = set()
    keys: set[str] = set()
    for index, donor in enumerate(entries):
        did = donor.get("donor_id")
        key = donor.get("source", {}).get("normalized_key")
        if not isinstance(did, str) or not did or did in ids:
            raise ValueError("DUPLICATE_OR_INVALID_DONOR_ID:" + str(index))
        if not isinstance(key, str) or not key or key in keys:
            raise ValueError("DUPLICATE_OR_INVALID_SOURCE_KEY:" + str(index))
        ids.add(did)
        keys.add(key)
    return registry, links, cap_model


def _activity_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("observations", []) if isinstance(raw, dict) else []
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("donor_id"), str):
            raise ValueError("INVALID_ACTIVITY_OBSERVATION")
        if not isinstance(row.get("source_refs"), list) or not row["source_refs"]:
            raise ValueError("ACTIVITY_OBSERVATION_REQUIRES_SOURCE_REFS")
        result[row["donor_id"]] = row
    return result


def _record_plan(donor: dict[str, Any], observation: dict[str, Any] | None, handling_limit_bytes: int) -> dict[str, Any]:
    category = classify_categories(donor)
    growth = derive_growth_profile(observation)
    size = _json_bytes(donor)
    target_bytes = math.floor(handling_limit_bytes * TARGET_FILL)
    storage_class = growth["storage_class"]
    if size > target_bytes:
        storage_class = "DEDICATED_SERIES"
        growth = {**growth, "storage_class": storage_class, "large_record": True}
    return {
        "donor_id": donor["donor_id"],
        "source_key": donor["source"]["normalized_key"],
        "primary_category": category["primary_category"],
        "categories": category["categories"],
        "category_classification": category["classification"],
        "growth_profile": growth,
        "storage_class": storage_class,
        "serialized_record_bytes": size,
    }


def build_plan(root: Path, *, handling_limit_bytes: int, activity_observations: Path | None = None) -> dict[str, Any]:
    if handling_limit_bytes <= 0:
        raise ValueError("HANDLING_LIMIT_MUST_BE_POSITIVE")
    root = root.resolve()
    policy = _load(root / POLICY)
    validate_policy(policy)
    registry, _links, cap_model = _validate_legacy(root)
    observations = _activity_map(activity_observations)
    records = [
        _record_plan(donor, observations.get(donor["donor_id"]), handling_limit_bytes)
        for donor in registry["entries"]
    ]
    app_index = build_index(root)
    if app_index.get("validation", {}).get("result") != "PASS":
        raise ValueError("APPLICATION_DONOR_INDEX_NOT_PASS")
    return {
        "schema": "fa3.donor-registry-v2-shadow-plan.v1",
        "authority": False,
        "canonical_cutover": False,
        "legacy_registry_sha256": _file_sha256(root / LEGACY_REGISTRY),
        "legacy_registry_count": len(registry["entries"]),
        "capability_model_id": cap_model["id"],
        "capability_count": 175,
        "handling_limit_bytes": handling_limit_bytes,
        "capacity_policy": {
            "target_fill_percent": 70,
            "reserve_percent": 30,
            "rollover_percent": 90,
            "rebalance_percent": 95,
            "rebalance_target_fill_percent": 70
        },
        "records": records,
        "capability_consumer_map": app_index["capability_consumer_map"],
    }


def _volume_wrapper(dataset: str, volume_id: str, limit: int, entries: list[dict[str, Any]]) -> dict[str, Any]:
    wrapper = {
        "schema": "fa3.donor-registry-volume.v1",
        "dataset": dataset,
        "volume_id": volume_id,
        "state": "OPEN",
        "capacity": {
            "handling_limit_bytes": limit,
            "target_fill_percent": 70,
            "reserve_percent": 30,
            "rollover_percent": 90,
            "rebalance_percent": 95,
            "rebalance_target_fill_percent": 70
        },
        "entries": entries,
    }
    used = _json_bytes(wrapper)
    wrapper["capacity"]["used_bytes"] = used
    wrapper["capacity"]["fill_percent"] = round(100.0 * used / limit, 4)
    wrapper["capacity"]["free_percent"] = round(100.0 - wrapper["capacity"]["fill_percent"], 4)
    wrapper["state"] = volume_state(used, limit) if used <= limit else "REBALANCE_REQUIRED"
    return wrapper


def _pack_shared(category: str, records: list[tuple[dict[str, Any], dict[str, Any]]], handling_limit_bytes: int) -> list[tuple[str, dict[str, Any], list[dict[str, Any]]]]:
    result: list[tuple[str, dict[str, Any], list[dict[str, Any]]]] = []
    current: list[dict[str, Any]] = []
    current_plans: list[dict[str, Any]] = []
    target = math.floor(handling_limit_bytes * TARGET_FILL)
    sequence = 1
    for donor, plan in records:
        candidate = current + [donor]
        wrapper = _volume_wrapper("donors." + category, f"{category}.{sequence:03d}", handling_limit_bytes, candidate)
        if current and _json_bytes(wrapper) > target:
            final = _volume_wrapper("donors." + category, f"{category}.{sequence:03d}", handling_limit_bytes, current)
            result.append((f"donors/{category}/{category}.{sequence:03d}.json", final, current_plans))
            sequence += 1
            current = [donor]
            current_plans = [plan]
        else:
            current = candidate
            current_plans.append(plan)
    if current:
        final = _volume_wrapper("donors." + category, f"{category}.{sequence:03d}", handling_limit_bytes, current)
        if _json_bytes(final) > target:
            raise ValueError("SHARED_VOLUME_TARGET_EXCEEDED:" + category)
        result.append((f"donors/{category}/{category}.{sequence:03d}.json", final, current_plans))
    return result


def shadow_migrate(root: Path, output: Path, *, handling_limit_bytes: int, activity_observations: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    output = output.resolve()
    plan = build_plan(root, handling_limit_bytes=handling_limit_bytes, activity_observations=activity_observations)
    registry, links, _cap_model = _validate_legacy(root)
    donors_by_id = {row["donor_id"]: row for row in registry["entries"]}
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    shared: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    dedicated: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for record_plan in plan["records"]:
        donor = donors_by_id[record_plan["donor_id"]]
        if record_plan["storage_class"] == "DEDICATED_SERIES":
            dedicated.append((donor, record_plan))
        else:
            shared.setdefault(record_plan["primary_category"], []).append((donor, record_plan))

    locations: dict[str, dict[str, Any]] = {}
    source_index: dict[str, str] = {}
    category_index: dict[str, list[str]] = {}
    receipts: list[dict[str, Any]] = []
    volume_manifests: list[dict[str, Any]] = []

    for category in sorted(shared):
        rows = sorted(shared[category], key=lambda item: item[0]["donor_id"])
        for relpath, wrapper, record_plans in _pack_shared(category, rows, handling_limit_bytes):
            _write(output / relpath, wrapper)
            volume_manifests.append({"path": relpath, "dataset": wrapper["dataset"], "volume_id": wrapper["volume_id"], "capacity": wrapper["capacity"]})
            for donor, record_plan in zip(wrapper["entries"], record_plans):
                did = donor["donor_id"]
                locations[did] = {"path": relpath, "storage_class": "SHARED_VOLUME"}
                source_index[donor["source"]["normalized_key"]] = did
                for cat in record_plan["categories"]:
                    category_index.setdefault(cat, []).append(did)
                receipts.append({
                    "donor_id": did,
                    "target_path": relpath,
                    "storage_class": "SHARED_VOLUME",
                    "primary_category": record_plan["primary_category"],
                    "migration_status": "MIGRATED_UNCHANGED",
                    "refresh_status": "NOT_RUN" if record_plan["growth_profile"]["basis"] == "NO_ACTIVITY_OBSERVATION" else "ACTIVITY_PROFILE_APPLIED"
                })

    for donor, record_plan in sorted(dedicated, key=lambda item: item[0]["donor_id"]):
        did = donor["donor_id"]
        relpath = f"donor-series/{_slug(did)}/record.001.json"
        wrapper = _volume_wrapper("donor-series." + did, "record.001", handling_limit_bytes, [donor])
        if _json_bytes(wrapper) > math.floor(handling_limit_bytes * TARGET_FILL):
            raise ValueError("OVERSIZED_DONOR_REQUIRES_ANNEX_NORMALIZATION:" + did)
        _write(output / relpath, wrapper)
        volume_manifests.append({"path": relpath, "dataset": wrapper["dataset"], "volume_id": wrapper["volume_id"], "capacity": wrapper["capacity"]})
        locations[did] = {"path": relpath, "storage_class": "DEDICATED_SERIES"}
        source_index[donor["source"]["normalized_key"]] = did
        for cat in record_plan["categories"]:
            category_index.setdefault(cat, []).append(did)
        receipts.append({
            "donor_id": did,
            "target_path": relpath,
            "storage_class": "DEDICATED_SERIES",
            "primary_category": record_plan["primary_category"],
            "migration_status": "MIGRATED_UNCHANGED",
            "refresh_status": "ACTIVITY_PROFILE_APPLIED" if record_plan["growth_profile"]["basis"] == "OBSERVED_HISTORY" else "NOT_RUN"
        })

    for key in category_index:
        category_index[key] = sorted(set(category_index[key]))

    _write(output / "indexes/donor-location-index.json", {"schema": "fa3.donor-location-index.v1", "derived": True, "locations": locations})
    _write(output / "indexes/source-key-index.json", {"schema": "fa3.donor-source-key-index.v1", "derived": True, "sources": source_index})
    _write(output / "indexes/category-index.json", {"schema": "fa3.donor-category-index.v1", "derived": True, "categories": category_index})
    _write(output / "indexes/capability-consumer-map.json", plan["capability_consumer_map"])
    _write(output / "usage/source-declarations.json", {
        "schema": "fa3.registry-v2-usage-source-projection.v1",
        "derived": True,
        "authority": False,
        "source": APP_LINKS,
        "donor_usage_records": links.get("donor_usage_records", [])
    })
    _write(output / "migration/migration-receipts.json", {
        "schema": "fa3.registry-v2-migration-receipts.v1",
        "legacy_registry_sha256": plan["legacy_registry_sha256"],
        "receipts": sorted(receipts, key=lambda item: item["donor_id"])
    })
    manifest = {
        "schema": "fa3.donor-registry-v2-manifest.v1",
        "authority": False,
        "canonical_cutover": False,
        "legacy_registry": LEGACY_REGISTRY,
        "legacy_registry_sha256": plan["legacy_registry_sha256"],
        "legacy_registry_count": plan["legacy_registry_count"],
        "capability_count": 175,
        "handling_limit_bytes": handling_limit_bytes,
        "capacity_policy": plan["capacity_policy"],
        "volumes": volume_manifests,
        "indexes": [
            "indexes/donor-location-index.json",
            "indexes/source-key-index.json",
            "indexes/category-index.json",
            "indexes/capability-consumer-map.json"
        ]
    }
    _write(output / "registry-manifest.json", manifest)
    verification = verify_shadow(root, output)
    _write(output / "migration/verification.json", verification)
    return {"manifest": manifest, "verification": verification}


def verify_shadow(root: Path, shadow: Path) -> dict[str, Any]:
    root = root.resolve()
    shadow = shadow.resolve()
    registry, _links, cap_model = _validate_legacy(root)
    manifest = _load(shadow / "registry-manifest.json")
    locations = _load(shadow / "indexes/donor-location-index.json").get("locations", {})
    source_index = _load(shadow / "indexes/source-key-index.json").get("sources", {})
    legacy_ids = {row["donor_id"] for row in registry["entries"]}
    legacy_keys = {row["source"]["normalized_key"] for row in registry["entries"]}
    findings: list[str] = []
    if set(locations) != legacy_ids:
        findings.append("DONOR_ID_PARITY_FAIL")
    if set(source_index) != legacy_keys:
        findings.append("SOURCE_KEY_PARITY_FAIL")
    if manifest.get("legacy_registry_count") != len(legacy_ids):
        findings.append("COUNT_PARITY_FAIL")
    if manifest.get("legacy_registry_sha256") != _file_sha256(root / LEGACY_REGISTRY):
        findings.append("LEGACY_SHA_MISMATCH")
    if cap_model.get("canonical_capability_count") != 175 or manifest.get("capability_count") != 175:
        findings.append("CAPABILITY_175_FAIL")
    for volume in manifest.get("volumes", []):
        capacity = volume.get("capacity", {})
        used = int(capacity.get("used_bytes", -1))
        limit = int(capacity.get("handling_limit_bytes", 0))
        if used < 0 or limit <= 0:
            findings.append("INVALID_VOLUME_CAPACITY:" + str(volume.get("path")))
            continue
        if used > math.floor(limit * TARGET_FILL):
            findings.append("INITIAL_30_PERCENT_RESERVE_NOT_PRESERVED:" + str(volume.get("path")))
    return {
        "schema": "fa3.donor-registry-v2-verification.v1",
        "result": "PASS" if not findings else "FAIL",
        "legacy_count": len(legacy_ids),
        "shadow_count": len(locations),
        "capability_count": 175,
        "zero_manual_reentry": True,
        "findings": findings
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Donor Registry v2 shadow tooling")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("--handling-limit-bytes", type=int, required=True)
    plan_parser.add_argument("--activity-observations", type=Path)
    migrate = sub.add_parser("shadow-migrate")
    migrate.add_argument("--output", type=Path, required=True)
    migrate.add_argument("--handling-limit-bytes", type=int, required=True)
    migrate.add_argument("--activity-observations", type=Path)
    verify = sub.add_parser("verify-shadow")
    verify.add_argument("--shadow", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        result = build_plan(args.root, handling_limit_bytes=args.handling_limit_bytes, activity_observations=args.activity_observations)
    elif args.command == "shadow-migrate":
        result = shadow_migrate(args.root, args.output, handling_limit_bytes=args.handling_limit_bytes, activity_observations=args.activity_observations)
    else:
        result = verify_shadow(args.root, args.shadow)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    terminal_result = result.get("result", result.get("verification", {}).get("result", "PASS"))
    return 0 if terminal_result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
