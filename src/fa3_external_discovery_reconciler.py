#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from fa3_api_mega_list_adapter import sanitize_locator
from fa3_application_donor_index import build_index
from fa3_external_discovery_store import validate_candidate_store
from fa3_reuse_catalog import build_catalog

POLICY_ID = "FA3-EXTERNAL-DISCOVERY-RECONCILIATION-001"
PROJECTION_SCHEMA = "fa3.external-discovery-reconciliation-projection.v1"
CAP_RE = re.compile(r"^CAP-(\d{3})$")
STOP_TERMS = {
    "api", "apis", "tool", "tools", "service", "services", "app", "apps",
    "server", "servers", "online", "free", "best", "official", "featured",
    "actor", "actors", "the", "and", "for", "with", "from",
}


def _stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten_strings(item)


def _terms(values: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for value in values:
        lower = str(value).casefold()
        out.update(re.findall(r"[a-z0-9][a-z0-9_.:+-]{1,63}", lower))
        out.update(re.findall(r"[a-z0-9]{3,}", lower))
    return {term for term in out if term not in STOP_TERMS}


def _candidate_terms(candidate: dict[str, Any]) -> set[str]:
    values: list[str] = []
    values.extend(str(x) for x in candidate.get("listing_names", []) if x)
    values.extend(str(x) for x in candidate.get("discovery_terms", []) if x)
    for key in ("provider_identity", "service_identity", "canonical_locator"):
        if candidate.get(key):
            values.append(str(candidate[key]))
    return _terms(values)


def _canonical_capability(value: str) -> bool:
    match = CAP_RE.fullmatch(str(value))
    return bool(match and 1 <= int(match.group(1)) <= 175)


def _normalize_locator(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.startswith(("http://", "https://")):
        return None
    try:
        return str(sanitize_locator(value)["canonical_locator"])
    except (ValueError, UnicodeError):
        return None


def _source_identity(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    normalized = _normalize_locator(raw)
    if normalized:
        parsed = urlsplit(normalized)
        if parsed.hostname in {"github.com", "www.github.com"}:
            return normalized.casefold()
        return normalized
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", raw):
        return ("https://github.com/" + raw.strip("/")).casefold()
    if raw.casefold().startswith("github:"):
        slug = raw.split(":", 1)[1].strip("/")
        if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", slug):
            return ("https://github.com/" + slug).casefold()
    return None


def _provider_source_values(obj: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("repository", "source_repository", "homepage", "source_url", "source_locator"):
        value = obj.get(key)
        if isinstance(value, str):
            values.append(value)
    upstream = obj.get("upstream")
    if isinstance(upstream, dict):
        for key in ("repository", "homepage", "url", "source_url", "locator"):
            value = upstream.get(key)
            if isinstance(value, str):
                values.append(value)
    source = obj.get("source")
    if isinstance(source, dict):
        for key in ("repository", "homepage", "url", "locator", "normalized_key"):
            value = source.get(key)
            if isinstance(value, str):
                values.append(value)
    elif isinstance(source, str):
        values.append(source)
    return values


def _provider_capabilities(obj: dict[str, Any]) -> list[str]:
    found: set[str] = set()
    for key in ("capability_projection", "capabilities", "capability_bindings"):
        value = obj.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str) and _canonical_capability(item):
                found.add(item)
            elif isinstance(item, dict):
                cap = item.get("capability_id") or item.get("id")
                if isinstance(cap, str) and _canonical_capability(cap):
                    found.add(cap)
    return sorted(found)


def _provider_index(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base = root / "canonical/providers"
    if not base.is_dir():
        return rows
    for path in sorted(base.glob("*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        provider_id = obj.get("id")
        if not isinstance(provider_id, str) or not provider_id:
            continue
        source_values = _provider_source_values(obj)
        locators = sorted({
            identity
            for value in source_values
            for identity in [_source_identity(value)]
            if identity
        })
        token_values = [
            str(obj.get("id", "")),
            str(obj.get("name", "")),
            str(obj.get("provider_role", "")),
            *[str(x) for x in obj.get("classification", []) if isinstance(x, str)],
            *source_values,
        ]
        rows.append({
            "provider_id": provider_id,
            "status": obj.get("status"),
            "source_path": path.relative_to(root).as_posix(),
            "locators": locators,
            "tokens": sorted(_terms(token_values)),
            "capabilities": _provider_capabilities(obj),
        })
    return rows


def _score_terms(candidate_terms: set[str], entry_terms: Iterable[str]) -> tuple[int, list[str]]:
    overlap = sorted(candidate_terms & set(str(x).casefold() for x in entry_terms))
    return len(overlap), overlap


def _donor_matches(candidate: dict[str, Any], catalog_entries: list[dict[str, Any]]) -> dict[str, Any]:
    locator = _source_identity(candidate.get("canonical_locator"))
    terms = _candidate_terms(candidate)
    exact: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for entry in catalog_entries:
        if entry.get("candidate_class") != "DONOR_REFERENCE":
            continue
        source_locator = _source_identity(entry.get("source_locator"))
        source_key = _source_identity(entry.get("source_normalized_key"))
        if locator and locator in {source_locator, source_key}:
            exact.append({
                "donor_id": entry["candidate_id"],
                "basis": "EXACT_SOURCE_LOCATOR",
                "capabilities": [cap for cap in entry.get("capabilities", []) if _canonical_capability(cap)],
            })
            continue
        score, overlap = _score_terms(terms, entry.get("tokens", []))
        if score >= 3:
            review.append({
                "donor_id": entry["candidate_id"],
                "basis": "TOKEN_REVIEW_ONLY",
                "score": score,
                "matched_terms": overlap[:8],
                "capabilities": [cap for cap in entry.get("capabilities", []) if _canonical_capability(cap)],
            })
    review.sort(key=lambda row: (-row["score"], row["donor_id"]))
    return {
        "status": "EXISTING_DONOR" if exact else "POSSIBLE_EXISTING_DONOR_REVIEW" if review else "NO_EXISTING_DONOR_MATCH",
        "exact_matches": exact,
        "review_matches": review[:10],
        "donor_intake_allowed": False,
        "explicit_owner_marker_required_for_new_donor": True,
        "automatic_usage_edge_creation": False,
    }


def _provider_matches(candidate: dict[str, Any], providers: list[dict[str, Any]]) -> dict[str, Any]:
    locator = _source_identity(candidate.get("canonical_locator"))
    terms = _candidate_terms(candidate)
    exact: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for provider in providers:
        if locator in provider["locators"]:
            exact.append({
                "provider_id": provider["provider_id"],
                "basis": "EXACT_SOURCE_LOCATOR",
                "capabilities": provider["capabilities"],
                "status": provider.get("status"),
            })
            continue
        score, overlap = _score_terms(terms, provider["tokens"])
        if score >= 3:
            review.append({
                "provider_id": provider["provider_id"],
                "basis": "TOKEN_REVIEW_ONLY",
                "score": score,
                "matched_terms": overlap[:8],
                "capabilities": provider["capabilities"],
                "status": provider.get("status"),
            })
    review.sort(key=lambda row: (-row["score"], row["provider_id"]))
    return {
        "status": (
            "EXISTING_PROVIDER"
            if exact
            else "POSSIBLE_EXISTING_PROVIDER_REVIEW"
            if review
            else "NEW_PROVIDER_CANDIDATE_REQUIRES_ADMISSION"
        ),
        "exact_matches": exact,
        "review_matches": review[:10],
        "automatic_provider_registration": False,
        "automatic_mcp_registration": False,
        "automatic_runtime_activation": False,
    }


def _reuse_matches(candidate: dict[str, Any], catalog_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    terms = _candidate_terms(candidate)
    matched: list[dict[str, Any]] = []
    for entry in catalog_entries:
        if entry.get("candidate_class") in {"DONOR_REFERENCE", "PROVIDER"}:
            continue
        score, overlap = _score_terms(terms, entry.get("tokens", []))
        if score < 2:
            continue
        matched.append({
            "candidate_id": entry.get("candidate_id"),
            "candidate_class": entry.get("candidate_class"),
            "score": score,
            "matched_terms": overlap[:8],
            "capabilities": [cap for cap in entry.get("capabilities", []) if _canonical_capability(cap)],
            "source_path": entry.get("source_path"),
            "shared_module_ids": list(entry.get("shared_module_ids", [])) if isinstance(entry.get("shared_module_ids"), list) else [],
            "automatic_selection": False,
        })
    matched.sort(key=lambda row: (-row["score"], str(row["candidate_class"]), str(row["candidate_id"])))
    return matched[:20]


def _capability_projection(
    donor: dict[str, Any],
    provider: dict[str, Any],
    reuse_matches: list[dict[str, Any]],
) -> dict[str, Any]:
    confirmed = sorted({
        cap
        for section in (donor, provider)
        for row in section.get("exact_matches", [])
        for cap in row.get("capabilities", [])
        if _canonical_capability(cap)
    })
    suggestions: dict[str, int] = {}
    for row in reuse_matches:
        for cap in row.get("capabilities", []):
            if _canonical_capability(cap):
                suggestions[cap] = max(suggestions.get(cap, 0), int(row.get("score", 0)))
    for section in (donor, provider):
        for row in section.get("review_matches", []):
            for cap in row.get("capabilities", []):
                if _canonical_capability(cap):
                    suggestions[cap] = max(suggestions.get(cap, 0), int(row.get("score", 0)))
    suggested = [
        {"capability_id": cap, "score": score, "basis": "DETERMINISTIC_REVIEW_ONLY"}
        for cap, score in sorted(suggestions.items(), key=lambda item: (-item[1], item[0]))
        if cap not in confirmed
    ][:16]
    status = (
        "EXACT_EXISTING_CAPABILITY"
        if confirmed
        else "EXISTING_CAPABILITY_SUBFUNCTION_REVIEW"
        if suggested
        else "UNMAPPED_FUNCTIONAL_GAP_REVIEW"
    )
    return {
        "status": status,
        "confirmed_capability_ids": confirmed,
        "suggested_capabilities": suggested,
        "new_capability_id_creation_allowed": False,
        "capability_baseline": 175,
    }


def _application_impact(
    candidate: dict[str, Any],
    capability: dict[str, Any],
    app_index: dict[str, Any],
) -> dict[str, Any]:
    terms = _candidate_terms(candidate)
    capability_ids = list(capability.get("confirmed_capability_ids", []))
    capability_ids.extend(row["capability_id"] for row in capability.get("suggested_capabilities", []))

    capability_edges = {
        edge["id"]: edge for edge in app_index.get("capability_consumer_map", {}).get("edges", [])
        if isinstance(edge, dict) and edge.get("id")
    }
    shared_edges = {
        edge["id"]: edge for edge in app_index.get("shared_capability_consumer_map", {}).get("edges", [])
        if isinstance(edge, dict) and edge.get("id")
    }
    cap_views = app_index.get("capability_consumer_map", {}).get("views", {}).get("by_capability", {})
    shared_views = app_index.get("shared_capability_consumer_map", {}).get("views", {}).get("by_capability", {})

    affected: dict[str, set[str]] = {}
    existing_shared_ids: set[str] = set()
    for cap in capability_ids:
        for edge_id in cap_views.get(cap, []):
            edge = capability_edges.get(edge_id, {})
            for consumer in edge.get("consumers", []):
                if consumer.get("kind") == "APPLICATION":
                    affected.setdefault(str(consumer["id"]), set()).add("CAPABILITY_CONSUMER:" + cap)
        for edge_id in shared_views.get(cap, []):
            edge = shared_edges.get(edge_id, {})
            sid = edge.get("shared_capability_id")
            if sid:
                existing_shared_ids.add(str(sid))
            for consumer in edge.get("consumers", []):
                if consumer.get("kind") == "APPLICATION":
                    affected.setdefault(str(consumer["id"]), set()).add("SHARED_CAPABILITY_CONSUMER:" + cap)

    applications = app_index.get("applications", [])
    for app in applications:
        app_id = str(app.get("application_id", ""))
        values = [str(app.get("name", ""))]
        values.extend(str(x) for x in app.get("aliases", []) if x)
        score, overlap = _score_terms(terms, _terms(values))
        if score >= 2 and app_id:
            affected.setdefault(app_id, set()).add("APPLICATION_TERM_REVIEW:" + ",".join(overlap[:4]))

    affected_rows = [
        {"application_id": app_id, "basis": sorted(basis)}
        for app_id, basis in sorted(affected.items())
    ]
    return {
        "all_registered_applications_scanned": len(applications),
        "retrospective_scope": "ALL_REGISTERED_APPLICATIONS",
        "affected_applications": affected_rows,
        "affected_application_count": len(affected_rows),
        "existing_shared_capability_ids": sorted(existing_shared_ids),
        "manual_review_required": True,
        "automatic_application_mutation": False,
    }


def _shared_projection(
    candidate: dict[str, Any],
    reuse_matches: list[dict[str, Any]],
    impact: dict[str, Any],
) -> dict[str, Any]:
    shared_pattern_matches = [
        row for row in reuse_matches if row.get("candidate_class") == "SHARED_MODULE_PATTERN"
    ]
    existing_shared = list(impact.get("existing_shared_capability_ids", []))
    existing_shared.extend(
        shared_id
        for row in shared_pattern_matches
        for shared_id in row.get("shared_module_ids", [])
        if shared_id
    )
    existing_shared = sorted(set(existing_shared))
    app_count = int(impact.get("affected_application_count", 0))
    if existing_shared:
        status = "EXISTING_SHARED_MATCH"
    elif app_count >= 2:
        status = "SHARED_REUSE_CANDIDATE"
    elif app_count == 1:
        status = "APPLICATION_REUSE_CANDIDATE"
    else:
        status = "REVIEW_REQUIRED"
    return {
        "status": status,
        "existing_shared_ids": existing_shared,
        "shared_pattern_matches": shared_pattern_matches[:10],
        "minimum_application_consumers_for_new_shared": 2,
        "automatic_shared_materialization": False,
        "capability_loss_allowed": False,
    }


def reconcile_candidate(
    candidate: dict[str, Any],
    *,
    catalog_entries: list[dict[str, Any]],
    provider_index: list[dict[str, Any]],
    app_index: dict[str, Any],
) -> dict[str, Any]:
    donor = _donor_matches(candidate, catalog_entries)
    provider = _provider_matches(candidate, provider_index)
    reuse_matches = _reuse_matches(candidate, catalog_entries)
    capability = _capability_projection(donor, provider, reuse_matches)
    impact = _application_impact(candidate, capability, app_index)
    shared = _shared_projection(candidate, reuse_matches, impact)
    return {
        "candidate_id": candidate["candidate_id"],
        "source_categories": list(candidate.get("source_categories", [])),
        "provider_identity": candidate.get("provider_identity"),
        "service_identity": candidate.get("service_identity"),
        "canonical_locator": candidate.get("canonical_locator"),
        "donor_reconciliation": donor,
        "provider_reconciliation": provider,
        "reuse_catalog_matches": reuse_matches,
        "capability_reconciliation": capability,
        "shared_reconciliation": shared,
        "application_impact": impact,
        "authority": False,
        "automatic_adoption": False,
        "automatic_code_import": False,
        "automatic_install": False,
        "automatic_activation": False,
        "runtime_promotion": False,
    }


def build_reconciliation(root: Path, candidate_store: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    store_findings = validate_candidate_store(candidate_store)
    if store_findings:
        raise ValueError(json.dumps(store_findings, ensure_ascii=False, sort_keys=True))

    catalog = build_catalog(root)
    app_index = build_index(root)
    if app_index.get("validation", {}).get("result") != "PASS":
        raise ValueError("application/donor inventory validation failed")
    providers = _provider_index(root)
    results = [
        reconcile_candidate(
            candidate,
            catalog_entries=catalog["entries"],
            provider_index=providers,
            app_index=app_index,
        )
        for candidate in candidate_store.get("candidates", [])
    ]

    summary: dict[str, int] = {}
    for row in results:
        for section, key in (
            ("donor_reconciliation", "status"),
            ("provider_reconciliation", "status"),
            ("capability_reconciliation", "status"),
            ("shared_reconciliation", "status"),
        ):
            value = str(row[section][key])
            summary[value] = summary.get(value, 0) + 1

    projection = {
        "schema": PROJECTION_SCHEMA,
        "policy_id": POLICY_ID,
        "authority": False,
        "canonical_source_of_truth": False,
        "derived": True,
        "rebuildable": True,
        "input_store_digest": candidate_store.get("store_digest"),
        "input_candidate_count": candidate_store.get("candidate_count"),
        "reuse_catalog_policy_id": catalog.get("policy_id"),
        "reuse_catalog_entry_count": catalog.get("entry_count"),
        "provider_record_count": len(providers),
        "registered_application_count": app_index.get("counts", {}).get("total_apps"),
        "result_count": len(results),
        "summary": dict(sorted(summary.items())),
        "results": results,
        "explicit_donor_marker_required_before_new_donor_intake": True,
        "automatic_donor_creation": False,
        "automatic_provider_admission": False,
        "automatic_mcp_registration": False,
        "automatic_shared_materialization": False,
        "automatic_application_mutation": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count": 175,
        "current_host_impact": "STRUCTURAL_REASSESSMENT_REQUIRED",
        "current_host_obligation_delta": 0,
    }
    projection["projection_digest"] = _stable_digest(
        {key: value for key, value in projection.items() if key != "projection_digest"}
    )
    return projection


def validate_reconciliation(projection: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if projection.get("schema") != PROJECTION_SCHEMA or projection.get("policy_id") != POLICY_ID:
        findings.append({"code": "EXTREC-SCHEMA", "message": "reconciliation schema/policy drift"})
    for flag in (
        "authority",
        "canonical_source_of_truth",
        "automatic_donor_creation",
        "automatic_provider_admission",
        "automatic_mcp_registration",
        "automatic_shared_materialization",
        "automatic_application_mutation",
    ):
        if projection.get(flag) is not False:
            findings.append({"code": "EXTREC-AUTHORITY", "message": f"{flag} must be false"})
    if projection.get("derived") is not True or projection.get("rebuildable") is not True:
        findings.append({"code": "EXTREC-DERIVED", "message": "projection must be derived and rebuildable"})
    if projection.get("capability_count") != 175 or projection.get("new_capabilities") != 0:
        findings.append({"code": "EXTREC-CAPABILITY", "message": "capability baseline/delta invalid"})
    if projection.get("new_architectural_authorities") != 0:
        findings.append({"code": "EXTREC-AUTHORITY-DELTA", "message": "architectural authority delta forbidden"})
    results = projection.get("results")
    if not isinstance(results, list) or projection.get("result_count") != len(results):
        findings.append({"code": "EXTREC-COUNT", "message": "reconciliation result count mismatch"})
        results = []
    seen: set[str] = set()
    for row in results:
        candidate_id = row.get("candidate_id") if isinstance(row, dict) else None
        if not candidate_id or candidate_id in seen:
            findings.append({"code": "EXTREC-CANDIDATE", "message": "missing/duplicate candidate id"})
            continue
        seen.add(candidate_id)
        caps = list(row.get("capability_reconciliation", {}).get("confirmed_capability_ids", []))
        caps.extend(
            x.get("capability_id")
            for x in row.get("capability_reconciliation", {}).get("suggested_capabilities", [])
            if isinstance(x, dict)
        )
        if any(not _canonical_capability(str(cap)) for cap in caps):
            findings.append({"code": "EXTREC-CAPABILITY-ID", "message": f"out-of-baseline capability: {candidate_id}"})
        if row.get("donor_reconciliation", {}).get("donor_intake_allowed") is not False:
            findings.append({"code": "EXTREC-DONOR-PROMOTION", "message": f"donor promotion allowed: {candidate_id}"})
        if row.get("provider_reconciliation", {}).get("automatic_provider_registration") is not False:
            findings.append({"code": "EXTREC-PROVIDER-PROMOTION", "message": f"provider promotion allowed: {candidate_id}"})
        if row.get("shared_reconciliation", {}).get("automatic_shared_materialization") is not False:
            findings.append({"code": "EXTREC-SHARED-PROMOTION", "message": f"shared promotion allowed: {candidate_id}"})
    expected = _stable_digest({key: value for key, value in projection.items() if key != "projection_digest"})
    if projection.get("projection_digest") != expected:
        findings.append({"code": "EXTREC-DIGEST", "message": "projection digest drift"})
    return findings
