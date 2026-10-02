#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

STORE_SCHEMA = "fa3.external-discovery-candidate-store.v1"
STORE_POLICY_ID = "FA3-EXTERNAL-DISCOVERY-CANDIDATE-STORE-001"
FORBIDDEN_PERSISTED_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "credential",
    "credentials",
    "password",
    "secret",
    "secret_value",
    "token",
}


def _stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _candidate_key(row: dict[str, Any]) -> str:
    return "|".join(
        (
            str(row.get("provider_identity", "")).casefold(),
            str(row.get("service_identity", "")).casefold(),
            str(row.get("canonical_locator", "")),
        )
    )


def _candidate_id(key: str) -> str:
    return "EXTDISC-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24].upper()


def _observation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": row["source_id"],
        "source_repository": row["source_repository"],
        "source_commit": row.get("source_commit"),
        "source_path": row["source_path"],
        "source_line": row["source_line"],
        "source_category": row["source_category"],
        "source_listing_digest": row["source_listing_digest"],
    }


def _prepare_source_snapshots(
    *,
    source_snapshot: dict[str, Any] | None,
    source_snapshots: Iterable[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if source_snapshot is not None and source_snapshots is not None:
        raise ValueError("provide source_snapshot or source_snapshots, not both")
    if source_snapshots is None:
        snapshots = [source_snapshot] if source_snapshot is not None else []
    else:
        snapshots = [dict(row) for row in source_snapshots]
    if not snapshots:
        raise ValueError("at least one source snapshot is required")
    return sorted(
        snapshots,
        key=lambda row: (
            str(row.get("source_id", "")),
            str(row.get("source_repository", "")),
            str(row.get("source_commit", "")),
            str(row.get("manifest_digest", "")),
        ),
    )


def build_candidate_store(
    *,
    observations: Iterable[dict[str, Any]],
    source_snapshot: dict[str, Any] | None = None,
    source_snapshots: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    snapshots = _prepare_source_snapshots(
        source_snapshot=source_snapshot,
        source_snapshots=source_snapshots,
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in observations:
        key = _candidate_key(row)
        if not key.strip("|"):
            continue
        grouped.setdefault(key, []).append(row)

    candidates: list[dict[str, Any]] = []
    for key in sorted(grouped):
        rows = grouped[key]
        first = sorted(
            rows,
            key=lambda r: (
                str(r.get("source_id", "")),
                str(r.get("source_path", "")),
                int(r.get("source_line", 0)),
                str(r.get("source_listing_digest", "")),
            ),
        )[0]
        observations_out = sorted(
            {_stable_digest(_observation(row)): _observation(row) for row in rows}.values(),
            key=lambda item: (
                str(item.get("source_id", "")),
                str(item.get("source_path", "")),
                int(item.get("source_line", 0)),
                str(item.get("source_listing_digest", "")),
            ),
        )
        terms = sorted({term for row in rows for term in row.get("discovery_terms", [])})
        categories = sorted({str(row.get("source_category", "")) for row in rows if row.get("source_category")})
        listing_names = sorted({str(row.get("listing_name", "")) for row in rows if row.get("listing_name")})
        listing_descriptions = sorted(
            {str(row.get("listing_description", "")) for row in rows if row.get("listing_description")}
        )
        actor_identities = sorted(
            {str(row.get("apify_actor_identity", "")) for row in rows if row.get("apify_actor_identity")}
        )
        candidate = {
            "candidate_id": _candidate_id(key),
            "candidate_class": "EXTERNAL_DISCOVERY_CANDIDATE",
            "provider_identity": first["provider_identity"],
            "service_identity": first["service_identity"],
            "canonical_locator": first["canonical_locator"],
            "listing_names": listing_names[:16],
            "listing_descriptions": listing_descriptions[:16],
            "source_categories": categories,
            "discovery_terms": terms[:128],
            "observations": observations_out,
            "mcp_hint_observed": any(bool(row.get("mcp_hint")) for row in rows),
            "skill_hint_observed": any(bool(row.get("skill_hint")) for row in rows),
            "webhook_hint_observed": any(bool(row.get("webhook_hint")) for row in rows),
            "apify_actor_identities": actor_identities[:16],
            "affiliate_or_tracking_observed": any(bool(row.get("affiliate_or_tracking_present")) for row in rows),
            "sponsorship_or_featured_observed": any(bool(row.get("sponsorship_or_featured_present")) for row in rows),
            "secret_parameter_observed": any(bool(row.get("secret_parameter_present")) for row in rows),
            "ranking_signal_allowed": False,
            "authorization_signal_allowed": False,
            "authority": False,
            "runtime_provider": False,
            "automatic_donor_creation": False,
            "automatic_provider_admission": False,
            "automatic_mcp_registration": False,
            "automatic_activation": False,
        }
        candidate["candidate_digest"] = _stable_digest(candidate)
        candidates.append(candidate)

    source_summary = (
        snapshots[0]
        if len(snapshots) == 1
        else {
            "source_id": "MULTI_SOURCE_RECONCILIATION",
            "source_count": len(snapshots),
            "source_snapshots_digest": _stable_digest(snapshots),
            "immutable": True,
            "network_fetch_performed": False,
        }
    )
    payload = {
        "schema": STORE_SCHEMA,
        "policy_id": STORE_POLICY_ID,
        "authority": False,
        "canonical_source_of_truth": False,
        "derived_state": True,
        "rebuildable": True,
        "runtime_provider": False,
        "automatic_donor_creation": False,
        "automatic_provider_admission": False,
        "automatic_mcp_registration": False,
        "automatic_activation": False,
        "source_snapshot": source_summary,
        "source_snapshots": snapshots,
        "candidate_count": len(candidates),
        "observation_count": sum(len(candidate["observations"]) for candidate in candidates),
        "candidates": candidates,
    }
    payload["store_digest"] = _stable_digest({k: v for k, v in payload.items() if k != "store_digest"})
    return payload

def _walk_forbidden(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            lower = str(key).casefold()
            next_path = f"{path}.{key}" if path else str(key)
            if lower in FORBIDDEN_PERSISTED_KEYS:
                findings.append(next_path)
            findings.extend(_walk_forbidden(item, next_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_walk_forbidden(item, f"{path}[{index}]"))
    return findings


def validate_candidate_store(store: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if store.get("schema") != STORE_SCHEMA or store.get("policy_id") != STORE_POLICY_ID:
        findings.append({"code": "EXTDISC-STORE-SCHEMA", "message": "candidate store schema/policy drift"})
    for flag in (
        "authority",
        "canonical_source_of_truth",
        "runtime_provider",
        "automatic_donor_creation",
        "automatic_provider_admission",
        "automatic_mcp_registration",
        "automatic_activation",
    ):
        if store.get(flag) is not False:
            findings.append({"code": "EXTDISC-STORE-AUTHORITY", "message": f"{flag} must be false"})
    if store.get("derived_state") is not True or store.get("rebuildable") is not True:
        findings.append({"code": "EXTDISC-STORE-DERIVED", "message": "candidate store must be derived and rebuildable"})
    snapshots = store.get("source_snapshots")
    if snapshots is None and isinstance(store.get("source_snapshot"), dict):
        snapshots = [store["source_snapshot"]]
    if not isinstance(snapshots, list) or not snapshots:
        findings.append({"code": "EXTDISC-STORE-SOURCES", "message": "at least one source snapshot is required"})
    else:
        identities = [
            (
                row.get("source_id"),
                row.get("source_repository"),
                row.get("source_commit"),
                row.get("manifest_digest"),
            )
            for row in snapshots
            if isinstance(row, dict)
        ]
        if len(identities) != len(snapshots) or len(identities) != len(set(identities)):
            findings.append({"code": "EXTDISC-STORE-SOURCES", "message": "source snapshots must be unique objects"})
    candidates = store.get("candidates")
    if not isinstance(candidates, list) or store.get("candidate_count") != len(candidates):
        findings.append({"code": "EXTDISC-STORE-COUNT", "message": "candidate count mismatch"})
        candidates = []
    ids = [row.get("candidate_id") for row in candidates if isinstance(row, dict)]
    if len(ids) != len(set(ids)):
        findings.append({"code": "EXTDISC-STORE-DUPLICATE", "message": "duplicate candidate id"})
    forbidden = _walk_forbidden(store)
    if forbidden:
        findings.append({"code": "EXTDISC-STORE-SECRET", "message": "forbidden secret-bearing keys persisted", "paths": forbidden[:20]})
    expected_digest = _stable_digest({k: v for k, v in store.items() if k != "store_digest"})
    if store.get("store_digest") != expected_digest:
        findings.append({"code": "EXTDISC-STORE-DIGEST", "message": "candidate store digest drift"})
    return findings


def volume_action(*, current_records: int, planned_capacity: int) -> dict[str, Any]:
    if planned_capacity <= 0 or current_records < 0:
        raise ValueError("invalid candidate-store capacity")
    utilization = current_records / planned_capacity
    if utilization >= 0.95:
        action = "REBALANCE_TO_70_PERCENT_AND_USE_CONTINUATION_VOLUME"
    elif utilization >= 0.90:
        action = "OPEN_NEXT_CONTINUATION_VOLUME"
    else:
        action = "NO_CAPACITY_ACTION"
    return {
        "utilization": utilization,
        "action": action,
        "growth_headroom_fraction": 0.30,
        "open_next_volume_at_utilization": 0.90,
        "rebalance_at_utilization": 0.95,
        "rebalance_target_utilization": 0.70,
    }
