#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from fa3_reuse_catalog import build_catalog

AUTHORITY_ROLE_MAP = {
    "model_routing": "FA3-AUTH-MODEL-ROUTER-001",
    "host_resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    "resource_admission": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    "security": "FA3-AUTH-SECURITY-GOV-001",
    "mcp": "FA3-AUTH-MCP-GATEWAY-001",
    "capability_gateway": "FA3-AUTH-MCP-GATEWAY-001",
    "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
    "registry": "FA3-REGISTRY-001",
    "model_registry": "EXISTING_FA3_ARTIFACT_MODEL_REGISTRY_ONLY",
    "secrets": "EXISTING_FA3_SECRETS_AUTHORITY_ONLY",
    "knowledge": "FA3-KNOWLEDGE-001",
    "memory": "EXISTING_FA3_MEMORY_AUTHORITY_ONLY",
}

REQUIRED_NAMESPACE_FIELDS = (
    "package_prefix", "service_prefix", "config_root", "cache_root",
    "runtime_root", "socket_namespace", "data_root", "desktop_prefix",
)


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _terms(values: list[str]) -> set[str]:
    out: set[str] = set()
    for value in values:
        out.update(x for x in re.split(r"[^a-z0-9_.:-]+", value.lower()) if x)
        out.add(_norm(value))
    return out


def _score(intent: dict[str, Any], entry: dict[str, Any]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0
    required = set(intent.get("required_capabilities", []))
    optional = set(intent.get("optional_capabilities", []))
    caps = set(entry.get("capabilities", []))
    exact_required = sorted(required & caps)
    exact_optional = sorted(optional & caps)
    if exact_required:
        score += 100 * len(exact_required)
        reasons.append("EXACT_REQUIRED_CAPABILITY:" + ",".join(exact_required))
    if exact_optional:
        score += 40 * len(exact_optional)
        reasons.append("EXACT_OPTIONAL_CAPABILITY:" + ",".join(exact_optional))

    intent_terms = _terms(list(intent.get("problem_classes", [])) + list(intent.get("execution_classes", [])))
    candidate_terms = set(entry.get("tokens", []))
    overlap = sorted(intent_terms & candidate_terms)
    if overlap:
        score += min(30, 5 * len(overlap))
        reasons.append("TERM_MATCH:" + ",".join(overlap[:6]))
    return score, reasons


def _reuse_mode(entry: dict[str, Any]) -> str:
    cls = entry.get("candidate_class")
    dist = entry.get("distribution_class")
    status = str(entry.get("status", ""))
    if cls == "REUSABLE_PATTERN":
        return "PATTERN_REUSE"
    if cls in {"UPSTREAM_REFERENCE", "THIRD_PARTY_REFERENCE"} or dist == "REFERENCE_ONLY":
        return "REFERENCE_ONLY"
    if cls == "PROVIDER" and ("PENDING" in status or "NOT_ADMITTED" in status or "BLOCKED" in status):
        return "DESIGN_REUSE_RUNTIME_PENDING"
    return "REUSE_CANDIDATE"


def _authority_collisions(intent: dict[str, Any]) -> list[dict[str, Any]]:
    collisions = []
    for role in intent.get("proposed_authority_roles", []):
        canonical = AUTHORITY_ROLE_MAP.get(str(role))
        if canonical:
            collisions.append({
                "role": role,
                "existing_authority": canonical,
                "state": "COLLISION",
                "reason": "FA3 already has a canonical authority for this role",
            })
    return collisions


def _coexistence_findings(intent: dict[str, Any]) -> list[str]:
    ns = intent.get("namespace_claims", {})
    findings = [f"MISSING_NAMESPACE:{field}" for field in REQUIRED_NAMESPACE_FIELDS if not ns.get(field)]
    if ns.get("requires_upstream_uninstall") is not False:
        findings.append("UPSTREAM_UNINSTALL_NOT_EXPLICITLY_FORBIDDEN")
    if ns.get("global_environment_mutation") is not False:
        findings.append("GLOBAL_ENVIRONMENT_MUTATION_NOT_EXPLICITLY_FORBIDDEN")
    if ns.get("claims_default_port") is not False:
        findings.append("DEFAULT_PORT_CLAIM_NOT_EXPLICITLY_FORBIDDEN")
    return findings


def _hardware_findings(intent: dict[str, Any]) -> list[str]:
    h = intent.get("hardware_audit", {})
    findings = []
    if h.get("vendor_neutral") is not True:
        findings.append("HARDWARE_VENDOR_NEUTRAL_REQUIRED")
    if h.get("cpu_only_viable") is not True:
        findings.append("CPU_ONLY_VIABILITY_REQUIRED")
    if h.get("accelerator_cardinality") != "0..N":
        findings.append("ACCELERATOR_CARDINALITY_MUST_BE_0_TO_N")
    if h.get("global_accelerator_requirement") is not False:
        findings.append("GLOBAL_ACCELERATOR_REQUIREMENT_FORBIDDEN")
    return findings


def bounded_rank(preauthorized_ids: list[str], ranked_ids: list[str]) -> list[str]:
    allowed = set(preauthorized_ids)
    extra = [item for item in ranked_ids if item not in allowed]
    if extra:
        raise ValueError("Decision Fabric candidate expansion forbidden: " + ",".join(extra))
    return ranked_ids


def resolve(root: Path, intent: dict[str, Any]) -> dict[str, Any]:
    catalog = build_catalog(root)
    candidates = []
    for entry in catalog["entries"]:
        score, reasons = _score(intent, entry)
        if score <= 0:
            continue
        row = dict(entry)
        row["score"] = score
        row["match_reasons"] = reasons
        row["reuse_mode"] = _reuse_mode(entry)
        candidates.append(row)
    candidates.sort(key=lambda row: (-row["score"], row["candidate_class"], row["candidate_id"]))

    required = list(intent.get("required_capabilities", []))
    satisfied: dict[str, list[str]] = {cap: [] for cap in required}
    for row in candidates:
        for cap in required:
            if cap in row.get("capabilities", []):
                satisfied[cap].append(row["candidate_id"])
    gaps = [
        {"capability": cap, "state": "REAL_GAP", "reason": "NO_EXISTING_EXACT_CAPABILITY_CANDIDATE"}
        for cap, ids in satisfied.items() if not ids
    ]

    duplicate_capabilities = []
    known_caps = {entry["candidate_id"] for entry in catalog["entries"] if entry["candidate_class"] == "CAPABILITY"}
    for cap in intent.get("declared_new_capabilities", []):
        if cap in known_caps:
            duplicate_capabilities.append(cap)

    payload = json.dumps(intent, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "schema": "fa3.reuse-resolution.v1",
        "project_id": intent.get("project_id"),
        "intent_id": intent.get("id"),
        "intent_digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
        "catalog_policy_id": catalog["policy_id"],
        "catalog_entry_count": catalog["entry_count"],
        "candidates": candidates[:50],
        "required_capability_satisfaction": satisfied,
        "gaps": gaps,
        "duplicate_declared_capabilities": duplicate_capabilities,
        "authority_collisions": _authority_collisions(intent),
        "coexistence_findings": _coexistence_findings(intent),
        "hardware_findings": _hardware_findings(intent),
        "existing_authority_bindings": AUTHORITY_ROLE_MAP,
        "decision_fabric_candidate_expansion": "DENY",
        "agent_native_output": "PROPOSAL_ONLY",
    }
