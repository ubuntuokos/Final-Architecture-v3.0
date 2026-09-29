"""Validate staged, non-authorizing SKILL.md reference data at a provider boundary.

This is a byte/expiry check, never a substitute for the upstream issuer-signed
admission, task selection and language claim verifier.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fa3_skill_materialization import _read_regular_nofollow, SkillSnapshotDenied

SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_CONTEXT_BYTES = 256 * 1024
MAX_PROMPT_INSTRUCTION_BYTES = 8192


class WorkerSkillContextDenied(ValueError):
    pass


def inspect_skill_context(
    context_path: Path, *,
    task_id: str, agent_id: str, required_skill_ids: list[str],
    allow_reference_fixture: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Require exact task binding, data integrity, expiry and signed evidence scope."""
    path = Path(context_path)
    if path.is_symlink() or path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise WorkerSkillContextDenied("staged context must be a private regular file")
    try:
        raw = _read_regular_nofollow(path.parent, path.name)
    except (OSError, SkillSnapshotDenied) as exc:
        raise WorkerSkillContextDenied("skill context asset cannot be read safely") from exc
    if not raw or len(raw) > MAX_CONTEXT_BYTES:
        raise WorkerSkillContextDenied("skill context exceeds bounded budget")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise WorkerSkillContextDenied("invalid UTF-8 skill context") from exc
    if not isinstance(value, dict):
        raise WorkerSkillContextDenied("skill context must be an object")
    scope = value.get("evidence_scope")
    permitted = {"PKI_AND_SECURITY_GOVERNANCE_SIGNED"}
    if allow_reference_fixture is True:
        permitted.add("CI_REFERENCE_ONLY")
    if (value.get("schema") != "fa3.developer-task-skill-projection.v1"
            or value.get("task_id") != task_id or value.get("agent_id") != agent_id
            or value.get("task_scope") != "developer"
            or value.get("grants_execution_authority") is not False
            or value.get("remote_fetch") is not False
            or scope not in permitted):
        raise WorkerSkillContextDenied("untrusted or out-of-scope skill context")
    if (not isinstance(required_skill_ids, list) or not required_skill_ids
            or len(set(required_skill_ids)) != len(required_skill_ids)):
        raise WorkerSkillContextDenied("invalid requested skill IDs")
    rows = value.get("skills")
    if not isinstance(rows, list) or len(rows) != len(required_skill_ids):
        raise WorkerSkillContextDenied("missing or extra skill")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise WorkerSkillContextDenied("timezone-aware clock required")
    seen_leases: set[str] = set()
    for wanted, row in zip(required_skill_ids, rows):
        if not isinstance(row, dict) or row.get("skill_id") != wanted:
            raise WorkerSkillContextDenied("skill identity differs from explicit request")
        if row.get("bound_task_id") != task_id:
            raise WorkerSkillContextDenied("skill lease belongs to a different task")
        lease_id = row.get("activation_lease_id")
        if (not isinstance(lease_id, str) or not lease_id.startswith("skill-lease:")
                or lease_id in seen_leases):
            raise WorkerSkillContextDenied("missing or duplicate lease ID")
        seen_leases.add(lease_id)
        try:
            expiry = datetime.fromisoformat(row["lease_expires_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkerSkillContextDenied("malformed lease expiration") from exc
        if expiry.tzinfo is None or current >= expiry:
            raise WorkerSkillContextDenied("expired worker skill lease")
        text = row.get("instructions")
        if not isinstance(text, str):
            raise WorkerSkillContextDenied("missing UTF-8 skill instructions")
        encoded = text.encode("utf-8")
        if not encoded or len(encoded) > MAX_PROMPT_INSTRUCTION_BYTES:
            raise WorkerSkillContextDenied("skill instructions exceed prompt budget")
        if (not SHA256.fullmatch(str(row.get("content_sha256", "")))
                or hashlib.sha256(encoded).hexdigest() != row["content_sha256"]
                or not SHA256.fullmatch(str(row.get("manifest_sha256", "")))
                or not row.get("selection_receipt_ref")
                or not row.get("admission_receipt_ref")):
            raise WorkerSkillContextDenied("skill payload digest or receipt reference invalid")
    return {
        "context_sha256": hashlib.sha256(raw).hexdigest(),
        "verified_skill_ids": [x["skill_id"] for x in rows],
        "skills": [{"skill_id": row["skill_id"], "instructions": row["instructions"],
                    "content_sha256": row["content_sha256"]} for row in rows],
        "evidence_scope": scope,
        "language_context": value.get("languages"),
    }
