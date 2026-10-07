#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

POLICY_AUTHORITY = "SECURITY_GOVERNANCE_POLICY_PLANE"
POLICY_PROVIDER_ID = "FA3-PROVIDER-LOCAL-SECURITY-POLICY-001"
MEMORY_CAPABILITY = "fa3.memory.retrieve"
AGENT_ACTOR_PREFIX = "FA3-AGENT-"
AGENT_CLIENT_ID = "fa3-agent-runtime"
REQUIRED_CGROUP_MARKER = "fa3-agent.slice"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _deny(capability_id: str, reason: str) -> dict[str, Any]:
    return {
        "authority": POLICY_AUTHORITY,
        "provider_id": POLICY_PROVIDER_ID,
        "status": "DENY",
        "capability_id": capability_id,
        "decision_id": "FA3-POLICY-DENY-" + _canonical_sha({"capability": capability_id, "reason": reason})[:24],
        "reason_code": reason,
    }


def resolve_policy(
    request: dict[str, Any],
    capability: dict[str, Any],
    binding: dict[str, Any],
    peer_context: dict[str, Any],
) -> dict[str, Any]:
    capability_id = str(capability.get("capability_id", ""))
    if capability_id != MEMORY_CAPABILITY:
        return _deny(capability_id, "UNSUPPORTED_LOCAL_POLICY_CAPABILITY")

    if peer_context.get("transport") != "unix":
        return _deny(capability_id, "UNTRUSTED_TRANSPORT")
    try:
        peer_uid = int(peer_context.get("uid", -1))
    except (TypeError, ValueError):
        return _deny(capability_id, "INVALID_PEER_UID")
    if peer_uid != os.getuid():
        return _deny(capability_id, "PEER_UID_MISMATCH")

    cgroup = str(peer_context.get("cgroup", ""))
    if REQUIRED_CGROUP_MARKER not in cgroup:
        return _deny(capability_id, "AGENT_CGROUP_REQUIRED")

    actor = str(request.get("actor_id", ""))
    client = str(request.get("client_id", ""))
    session = str(request.get("session_id", ""))
    if not actor.startswith(AGENT_ACTOR_PREFIX):
        return _deny(capability_id, "AGENT_ACTOR_SCOPE_MISMATCH")
    if client != AGENT_CLIENT_ID:
        return _deny(capability_id, "AGENT_CLIENT_SCOPE_MISMATCH")
    if not session:
        return _deny(capability_id, "AGENT_SESSION_REQUIRED")

    policy_request = request.get("policy_request")
    if not isinstance(policy_request, dict):
        return _deny(capability_id, "POLICY_REQUEST_REQUIRED")
    purpose = str(policy_request.get("purpose", "")).strip()
    if not purpose:
        return _deny(capability_id, "POLICY_PURPOSE_REQUIRED")

    arguments = request.get("arguments")
    if not isinstance(arguments, dict):
        return _deny(capability_id, "INVALID_ARGUMENT_SCOPE")
    project_id = str(arguments.get("project_id", "")).strip()
    workstream_id = str(arguments.get("workstream_id", "")).strip()
    if not project_id and not workstream_id:
        return _deny(capability_id, "SCOPED_RETRIEVAL_REQUIRED")

    identity_scope = binding.get("identity_scope")
    if not isinstance(identity_scope, dict):
        return _deny(capability_id, "BINDING_IDENTITY_SCOPE_MISSING")
    actor_prefixes = tuple(str(x) for x in identity_scope.get("actor_prefixes", []))
    client_ids = {str(x) for x in identity_scope.get("client_ids", [])}
    if not actor_prefixes or not any(actor.startswith(prefix) for prefix in actor_prefixes):
        return _deny(capability_id, "BINDING_ACTOR_SCOPE_MISMATCH")
    if not client_ids or client not in client_ids:
        return _deny(capability_id, "BINDING_CLIENT_SCOPE_MISMATCH")

    scope = {
        "project_ids": [project_id] if project_id else [],
        "workstream_ids": [workstream_id] if workstream_id else [],
    }
    decision_material = {
        "actor_id": actor,
        "client_id": client,
        "session_id": session,
        "capability_id": capability_id,
        "purpose": purpose,
        "scope": scope,
        "peer_pid": peer_context.get("pid"),
        "peer_uid": peer_uid,
        "peer_cgroup": cgroup,
    }
    return {
        "authority": POLICY_AUTHORITY,
        "provider_id": POLICY_PROVIDER_ID,
        "status": "ALLOW",
        "capability_id": capability_id,
        "decision_id": "FA3-POLICY-" + _canonical_sha(decision_material)[:32],
        "purpose": purpose,
        "scope": scope,
        "peer_attestation": {
            "transport": "unix",
            "uid": peer_uid,
            "pid": peer_context.get("pid"),
            "cgroup_sha256": _canonical_sha(cgroup),
            "required_cgroup_marker": REQUIRED_CGROUP_MARKER,
        },
    }
