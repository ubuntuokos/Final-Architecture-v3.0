#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import urllib.parse
from datetime import datetime, timezone
from typing import Any

CAPABILITY_COUNT = 143
PROFILE_ID = "FA3-MENTOR-CURRENT-HOST-001"
PARENT_PROFILE_ID = "FA3-MENTOR-001"
GATE_ID = "FA3-GATE-MENTOR-CURRENT-HOST-001"
EVIDENCE_LEVEL = "CURRENT_HOST_PRODUCTION_E2E"
MCP_AUTHORITY = "FA3-AUTH-MCP-GATEWAY-001"
KNOWLEDGE_AUTHORITY = "FA3-KNOWLEDGE-001"
EVIDENCE_AUTHORITY = "FA3-AUTH-OBS-EVIDENCE-001"
MENTOR_PROVIDER = "FA3-PROVIDER-MENTOR-LOCAL-001"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sanitized_endpoint(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    host = p.hostname or ""
    port = f":{p.port}" if p.port else ""
    return urllib.parse.urlunsplit((p.scheme, f"{host}{port}", p.path, "", ""))


def endpoint_is_loopback(url: str) -> bool:
    p = urllib.parse.urlsplit(url)
    host = p.hostname
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def bkt_update(p_known: float, correct: bool, *, p_learn: float = 0.15, p_guess: float = 0.20, p_slip: float = 0.10) -> float:
    p_known = min(1.0, max(0.0, float(p_known)))
    if correct:
        num = p_known * (1.0 - p_slip)
        den = num + (1.0 - p_known) * p_guess
    else:
        num = p_known * p_slip
        den = num + (1.0 - p_known) * (1.0 - p_guess)
    posterior = num / den if den else p_known
    return min(1.0, max(0.0, posterior + (1.0 - posterior) * p_learn))


def fsrs_style_schedule(*, previous_stability_days: float, difficulty: float, correct: bool, p_known: float) -> dict[str, float]:
    stability = max(0.25, float(previous_stability_days))
    difficulty = min(10.0, max(1.0, float(difficulty)))
    if correct:
        gain = 1.0 + 0.65 * p_known + (11.0 - difficulty) * 0.035
        stability = min(3650.0, stability * gain + 0.35)
        difficulty = max(1.0, difficulty - 0.18 * max(0.0, p_known - 0.5))
    else:
        stability = max(0.25, stability * 0.42)
        difficulty = min(10.0, difficulty + 0.55)
    interval = max(1.0, round(stability * (0.65 + 0.55 * p_known), 2))
    return {"stability_days": round(stability, 4), "difficulty": round(difficulty, 4), "interval_days": interval}


def mastery_evidence_valid(update: dict[str, Any]) -> bool:
    refs = update.get("evidence_refs")
    return bool(refs and isinstance(refs, list) and all(isinstance(x, str) and x for x in refs))


def _status_pass(obj: dict[str, Any]) -> bool:
    return str(obj.get("status", "")).upper() in {"PASS", "OK", "HEALTHY", "ACCEPTED", "ALLOW", "ALLOWED"}


def validate_authority_response(obj: dict[str, Any], *, expected_authority: str | None = None, forbid_mentor_authority: bool = True) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    authority = obj.get("authority_id") or obj.get("authority")
    if not _status_pass(obj):
        findings.append({"code": "MENTOR-HOST-AUTH-001", "message": "authority response is not PASS/OK/ACCEPTED", "observed_status": obj.get("status")})
    if expected_authority and authority != expected_authority:
        findings.append({"code": "MENTOR-HOST-AUTH-002", "message": "authority identity mismatch", "expected": expected_authority, "observed": authority})
    if forbid_mentor_authority and authority in {PARENT_PROFILE_ID, PROFILE_ID, MENTOR_PROVIDER}:
        findings.append({"code": "MENTOR-HOST-AUTH-003", "message": "Mentor illegally appeared as architectural authority", "observed": authority})
    return findings


def validate_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    f: list[dict[str, Any]] = []
    def add(code: str, msg: str, **extra: Any) -> None:
        f.append({"code": code, "severity": "P0", "message": msg, **extra})

    if receipt.get("schema") != "fa3.mentor-current-host-receipt.v1":
        add("MENTOR-HOST-001", "receipt schema mismatch")
    if receipt.get("profile_id") != PROFILE_ID or receipt.get("parent_profile_id") != PARENT_PROFILE_ID:
        add("MENTOR-HOST-002", "profile identity mismatch")
    if receipt.get("evidence_level") != EVIDENCE_LEVEL:
        add("MENTOR-HOST-003", "evidence level is not current-host production E2E")
    if receipt.get("fixture_semantics") in {"SYNTHETIC", "MOCK", "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST"}:
        add("MENTOR-HOST-004", "synthetic/mock fixture cannot be current-host evidence")
    if receipt.get("host_scope") != "CURRENT_HOST" or receipt.get("global_promotion_claim") is not False:
        add("MENTOR-HOST-005", "current-host scope/global promotion invariant mismatch")
    if receipt.get("capability_count_after") != CAPABILITY_COUNT or receipt.get("new_capabilities") != 0 or receipt.get("new_architectural_authorities") != 0:
        add("MENTOR-HOST-006", "capability/authority invariant mismatch")

    components = receipt.get("components", {})
    required = ["mentor_runtime", "central_mcp", "knowledge_rag", "memory", "evidence", "mastery", "bubblewrap"]
    for name in required:
        if str(components.get(name, {}).get("status", "")).upper() != "PASS":
            add("MENTOR-HOST-007", f"required component not PASS: {name}", component=name, observed=components.get(name))

    mcp = components.get("central_mcp", {})
    if (mcp.get("authority_id") or mcp.get("authority")) != MCP_AUTHORITY:
        add("MENTOR-HOST-008", "Central MCP authority mismatch")
    if mcp.get("execution_performed_by_mentor") is not False:
        add("MENTOR-HOST-009", "Mentor performed execution instead of typed escalation")

    knowledge = components.get("knowledge_rag", {})
    if (knowledge.get("authority_id") or knowledge.get("authority")) != KNOWLEDGE_AUTHORITY:
        add("MENTOR-HOST-010", "Knowledge/RAG authority mismatch")
    if not knowledge.get("provenance_refs"):
        add("MENTOR-HOST-011", "Knowledge/RAG proof lacks provenance")

    memory = components.get("memory", {})
    if memory.get("explicit_user_consent") is not True or memory.get("write_via_central_mcp") is not True:
        add("MENTOR-HOST-012", "Memory write did not prove explicit consent and Central MCP routing")
    if memory.get("authority_id") in {None, "", PARENT_PROFILE_ID, PROFILE_ID, MENTOR_PROVIDER}:
        add("MENTOR-HOST-013", "Memory authority missing or illegally owned by Mentor")
    if memory.get("marker_roundtrip") is not True:
        add("MENTOR-HOST-014", "Memory write/read marker roundtrip failed")

    evidence = components.get("evidence", {})
    if (evidence.get("authority_id") or evidence.get("authority")) != EVIDENCE_AUTHORITY or not evidence.get("evidence_id"):
        add("MENTOR-HOST-015", "canonical evidence receipt missing or authority mismatch")

    mastery = components.get("mastery", {})
    if not mastery_evidence_valid(mastery) or not (0.0 <= float(mastery.get("p_known_before", -1)) <= 1.0 and 0.0 <= float(mastery.get("p_known_after", -1)) <= 1.0):
        add("MENTOR-HOST-016", "mastery update lacks valid evidence binding/probability")
    if float(mastery.get("interval_days", 0)) <= 0:
        add("MENTOR-HOST-017", "FSRS-style interval is not positive")

    sandbox = components.get("bubblewrap", {})
    if sandbox.get("backend") != "bubblewrap":
        add("MENTOR-HOST-018", "Bubblewrap backend not proven")
    for key in ("positive_lab", "network_denied", "host_write_denied", "timeout_terminated"):
        if sandbox.get(key) is not True:
            add("MENTOR-HOST-019", f"sandbox invariant failed: {key}")
    if sandbox.get("writable_host_paths") not in ([], None):
        add("MENTOR-HOST-020", "sandbox exposed writable host paths")

    authorities = receipt.get("observed_authorities", [])
    forbidden = {PARENT_PROFILE_ID, PROFILE_ID, MENTOR_PROVIDER}
    if any(x in forbidden for x in authorities):
        add("MENTOR-HOST-021", "Mentor observed as authority in E2E chain")

    if receipt.get("status") != "PASS":
        add("MENTOR-HOST-022", "receipt status is not PASS")
    return f


def receipt_digest(receipt: dict[str, Any]) -> str:
    clone = dict(receipt)
    clone.pop("receipt_sha256", None)
    return digest_json(clone)
