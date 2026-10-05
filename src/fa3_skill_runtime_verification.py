#!/usr/bin/env python3
"""CFA3 shared Skill Fabric runtime verification.

This module reconciles the surviving runtime-verification delta from the historical
Skill Fabric PR stack into the current Skill Fabric v1.4 architecture. It is not an
admission, authorization, execution, evidence, model-routing, or resource authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from uuid import uuid4

from fa3_skill_fabric_gate import package_admission_allowed, skill_use_allowed

SCHEMA = "cfa3.skill-runtime-verification.v1"
CONTEXT_SCHEMA = "cfa3.verified-skill-worker-context.v1"
MAX_SKILL_FILE_BYTES = 4 * 1024 * 1024
MAX_PACKAGE_BYTES = 16 * 1024 * 1024
MAX_CONTEXT_BYTES = 256 * 1024


class SkillRuntimeDenied(ValueError):
    pass


@dataclass(frozen=True)
class SkillRuntimeBinding:
    root: Path
    package: dict[str, Any]
    registry_entry: dict[str, Any]
    admission: dict[str, Any]
    selection: dict[str, Any]
    lease: dict[str, Any]
    intent: dict[str, Any]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _relative_parts(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or "\\" in value:
        raise SkillRuntimeDenied("invalid relative skill path")
    path = PurePosixPath(value)
    parts = tuple(value.split("/"))
    if path.is_absolute() or parts != path.parts or any(x in ("", ".", "..") for x in parts):
        raise SkillRuntimeDenied("noncanonical or escaping skill path")
    return parts


def read_regular_nofollow(root: Path, relative: str) -> bytes:
    """Read a bounded regular file while refusing symlinks at every path component."""
    parts = _relative_parts(relative)
    root = Path(root).resolve()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    dfd = os.open(root, flags | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, flags | os.O_DIRECTORY, dir_fd=dfd)
            os.close(dfd)
            dfd = next_fd
        fd = os.open(parts[-1], flags | getattr(os, "O_NONBLOCK", 0), dir_fd=dfd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SKILL_FILE_BYTES:
                raise SkillRuntimeDenied("skill asset is not a bounded regular file")
            with os.fdopen(fd, "rb", closefd=False) as handle:
                data = handle.read(MAX_SKILL_FILE_BYTES + 1)
            if len(data) > MAX_SKILL_FILE_BYTES:
                raise SkillRuntimeDenied("skill asset exceeds byte budget")
            return data
        finally:
            os.close(fd)
    except OSError as exc:
        raise SkillRuntimeDenied("skill asset inaccessible or unsafe") from exc
    finally:
        os.close(dfd)


def snapshot_digests(root: Path, paths: list[str]) -> dict[str, Any]:
    if not isinstance(paths, list) or not paths or len(paths) > 128:
        raise SkillRuntimeDenied("invalid skill asset list")
    if len(paths) != len(set(paths)):
        raise SkillRuntimeDenied("duplicate skill asset path")
    entries: list[dict[str, str]] = []
    total = 0
    for relative in sorted(paths):
        data = read_regular_nofollow(root, relative)
        total += len(data)
        if total > MAX_PACKAGE_BYTES:
            raise SkillRuntimeDenied("skill package exceeds byte budget")
        entries.append({"path": relative, "sha256": _sha(data)})
    manifest = {"scheme": "cfa3.skill-snapshot-manifest.v1", "files": entries}
    return {
        "scheme": manifest["scheme"],
        "files": entries,
        "manifest_sha256": _sha(_canonical_bytes(manifest)),
    }


def task_activation_lease(
    *,
    task_id: str,
    skill_id: str,
    package_id: str,
    content_sha256: str,
    manifest_sha256: str,
    selection_receipt_ref: str,
    admission_receipt_ref: str,
    ttl_seconds: int = 300,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not task_id or not skill_id or not package_id:
        raise SkillRuntimeDenied("task, skill and package identities are required")
    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or not 1 <= ttl_seconds <= 3600:
        raise SkillRuntimeDenied("invalid activation TTL")
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise SkillRuntimeDenied("timezone-aware timestamp required")
    return {
        "schema": "cfa3.skill-activation-lease.v2",
        "lease_id": "skill-lease:" + str(uuid4()),
        "task_id": task_id,
        "skill_id": skill_id,
        "package_id": package_id,
        "content_sha256": content_sha256,
        "manifest_sha256": manifest_sha256,
        "selection_receipt_ref": selection_receipt_ref,
        "admission_receipt_ref": admission_receipt_ref,
        "issued_at": timestamp.isoformat(),
        "expires_at": (timestamp + timedelta(seconds=ttl_seconds)).isoformat(),
        "grants_execution_authority": False,
    }


def _parse_expiry(lease: Mapping[str, Any], now: datetime) -> datetime:
    try:
        expiry = datetime.fromisoformat(str(lease["expires_at"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise SkillRuntimeDenied("invalid activation expiry") from exc
    if expiry.tzinfo is None or now >= expiry:
        raise SkillRuntimeDenied("expired activation lease")
    return expiry


def verify_binding(
    binding: SkillRuntimeBinding,
    *,
    task_id: str,
    skill_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise SkillRuntimeDenied("timezone-aware timestamp required")
    package = binding.package
    registry = binding.registry_entry
    admission = binding.admission
    selection = binding.selection
    lease = binding.lease

    if not package_admission_allowed(package):
        raise SkillRuntimeDenied("current Skill Fabric admission contract denied package")
    if registry.get("skill_id") != skill_id or registry.get("admission_status") != "ADMITTED":
        raise SkillRuntimeDenied("skill registry identity or admission mismatch")
    package_id = package.get("package_id")
    if not package_id or registry.get("package_id") != package_id:
        raise SkillRuntimeDenied("package identity mismatch")
    entrypoints = package.get("entrypoints")
    if not isinstance(entrypoints, list) or len(entrypoints) != 1:
        raise SkillRuntimeDenied("exactly one selected skill entrypoint required")
    entrypoint = entrypoints[0]
    entry_path = entrypoint.get("path")
    if registry.get("entrypoint") != entry_path or registry.get("version") != entrypoint.get("version"):
        raise SkillRuntimeDenied("registry entrypoint/version mismatch")

    expected_content = package.get("digests", {}).get("content_sha256")
    expected_manifest = package.get("digests", {}).get("manifest_sha256")
    expected_dependency = package.get("dependencies", {}).get("digest_sha256")
    if (
        admission.get("result") != "PASS"
        or not admission.get("receipt_ref")
        or admission.get("package_id") != package_id
        or admission.get("content_sha256") != expected_content
        or admission.get("manifest_sha256") != expected_manifest
        or admission.get("dependency_digest_sha256") != expected_dependency
    ):
        raise SkillRuntimeDenied("admission receipt does not bind exact snapshot")

    if (
        not selection.get("receipt_ref")
        or selection.get("task_id") != task_id
        or selection.get("skill_id") != skill_id
        or selection.get("package_id") != package_id
        or skill_id not in selection.get("eligible_skill_ids", [])
    ):
        raise SkillRuntimeDenied("selection receipt is not task-bound")
    task_scope = str(selection.get("task_scope") or "")
    if not task_scope:
        raise SkillRuntimeDenied("selection task scope missing")

    _parse_expiry(lease, timestamp)
    required_lease = {
        "task_id": task_id,
        "skill_id": skill_id,
        "package_id": package_id,
        "content_sha256": expected_content,
        "manifest_sha256": expected_manifest,
        "selection_receipt_ref": selection["receipt_ref"],
        "admission_receipt_ref": admission["receipt_ref"],
    }
    if not lease.get("lease_id") or lease.get("grants_execution_authority") is not False:
        raise SkillRuntimeDenied("activation lease authority boundary invalid")
    if any(lease.get(key) != value for key, value in required_lease.items()):
        raise SkillRuntimeDenied("activation lease does not bind task and snapshot")

    files = package.get("files", [])
    if package.get("symlinks"):
        raise SkillRuntimeDenied("verified runtime snapshot forbids symlinks")
    observed = snapshot_digests(binding.root, files)
    observed_entry = next((x for x in observed["files"] if x["path"] == entry_path), None)
    if not observed_entry:
        raise SkillRuntimeDenied("selected SKILL.md entrypoint missing from snapshot")
    if observed_entry["sha256"] != expected_content or observed["manifest_sha256"] != expected_manifest:
        raise SkillRuntimeDenied("actual skill bytes differ from admitted digest")

    use_receipt = {
        "package_admission_status": "PASS",
        "materialization_state": "ACTIVE_FOR_TASK",
        "selection_receipt_ref": selection["receipt_ref"],
        "admission_receipt_ref": admission["receipt_ref"],
        "skill_name": entrypoint.get("name"),
        "skill_version": entrypoint.get("version"),
        "content_sha256": observed_entry["sha256"],
        "dependency_digest_sha256": expected_dependency,
        "task_scope": task_scope,
        "unsandboxed_execution": False,
        "candidate_expanded_after_eligibility": False,
        "tool_intent": binding.intent.get("tool_intent", {}),
        "model_intent": binding.intent.get("model_intent", {}),
        "resource_intent": binding.intent.get("resource_intent", {}),
        "secret_intent": binding.intent.get("secret_intent", {}),
    }
    if not skill_use_allowed(use_receipt):
        raise SkillRuntimeDenied("current Skill Fabric use gate denied verified context")

    instructions_bytes = read_regular_nofollow(binding.root, entry_path)
    if len(instructions_bytes) > MAX_CONTEXT_BYTES:
        raise SkillRuntimeDenied("skill instructions exceed worker context budget")
    try:
        instructions = instructions_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SkillRuntimeDenied("SKILL.md must be valid UTF-8") from exc

    return {
        "skill_id": skill_id,
        "package_id": package_id,
        "entrypoint": entry_path,
        "instructions": instructions,
        "content_sha256": observed_entry["sha256"],
        "manifest_sha256": observed["manifest_sha256"],
        "dependency_digest_sha256": expected_dependency,
        "task_scope": task_scope,
        "lease_id": lease["lease_id"],
        "lease_expires_at": lease["expires_at"],
        "selection_receipt_ref": selection["receipt_ref"],
        "admission_receipt_ref": admission["receipt_ref"],
        "execution_authority": False,
    }


class SkillRuntimeVerifier:
    """Prepare exact, task-scoped, non-authorizing worker context."""

    def __init__(self, bindings: Mapping[str, SkillRuntimeBinding]):
        self.bindings = dict(bindings)

    def prepare_task(
        self,
        *,
        task_id: str,
        required_skill_ids: tuple[str, ...],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        required = tuple(required_skill_ids)
        if not task_id:
            raise SkillRuntimeDenied("task identity required")
        if not required or len(required) != len(set(required)):
            raise SkillRuntimeDenied("explicit unique skill set required")
        if set(required) != set(self.bindings):
            raise SkillRuntimeDenied("runtime binding set differs from requested skill set")
        skills = [
            verify_binding(self.bindings[skill_id], task_id=task_id, skill_id=skill_id, now=now)
            for skill_id in required
        ]
        core = {
            "schema": CONTEXT_SCHEMA,
            "task_id": task_id,
            "required_skill_ids": list(required),
            "skills": skills,
            "authority": False,
            "execution_authority": False,
            "current_host_pass_claimed": False,
        }
        encoded = _canonical_bytes(core)
        if len(encoded) > MAX_CONTEXT_BYTES:
            raise SkillRuntimeDenied("verified worker context exceeds budget")
        return {**core, "context_sha256": _sha(encoded)}


def write_private_context(path: Path, context: Mapping[str, Any]) -> None:
    path = Path(path)
    if path.exists() and path.is_symlink():
        raise SkillRuntimeDenied("skill context target may not be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(dict(context), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def load_verified_context(
    path: Path,
    *,
    expected_task_id: str,
    expected_skill_ids: tuple[str, ...],
) -> dict[str, Any]:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise SkillRuntimeDenied("verified skill context file unavailable or unsafe")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise SkillRuntimeDenied("verified skill context must be private")
    try:
        context = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SkillRuntimeDenied("verified skill context malformed") from exc
    if (
        context.get("schema") != CONTEXT_SCHEMA
        or context.get("task_id") != expected_task_id
        or context.get("required_skill_ids") != list(expected_skill_ids)
        or context.get("authority") is not False
        or context.get("execution_authority") is not False
        or context.get("current_host_pass_claimed") is not False
    ):
        raise SkillRuntimeDenied("verified skill context identity/boundary mismatch")
    supplied = context.get("context_sha256")
    core = dict(context)
    core.pop("context_sha256", None)
    if supplied != _sha(_canonical_bytes(core)):
        raise SkillRuntimeDenied("verified skill context digest mismatch")
    skills = context.get("skills")
    if not isinstance(skills, list) or [x.get("skill_id") for x in skills] != list(expected_skill_ids):
        raise SkillRuntimeDenied("verified skill context set mismatch")
    return context
