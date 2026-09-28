#!/usr/bin/env python3
"""Read-only, task-scoped verification boundary for admitted FA3 skill snapshots.

This module is NOT an admission or authorization authority. Its caller must obtain
registry, admission and selection records from their existing FA3 authorities.
Neither records nor the returned lease authorize tool, model, resource or secret use.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from fa3_skill_fabric_gate import package_admission_allowed, skill_use_allowed

MANIFEST_SCHEME = "fa3.skill-snapshot-manifest.v1"
MAX_SKILL_FILE_BYTES = 4 * 1024 * 1024
MAX_PACKAGE_BYTES = 16 * 1024 * 1024


class SkillSnapshotDenied(ValueError):
    """A snapshot, selection, admission or activation boundary was not met."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative_parts(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or "\\" in value or not value:
        raise SkillSnapshotDenied("invalid relative path")
    path = PurePosixPath(value)
    parts = tuple(value.split("/"))
    if (path.is_absolute() or parts != path.parts
            or any(x in ("", ".", "..") for x in parts)):
        raise SkillSnapshotDenied("noncanonical or escaping skill path")
    return parts


def _read_regular_nofollow(root: Path, relative: str) -> bytes:
    """Open every component relative to an anchored dir fd, refusing symlinks."""
    parts = _relative_parts(relative)
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
                raise SkillSnapshotDenied("skill asset is not a bounded regular file")
            # Read through the held descriptor; no path-based reopen after validation.
            with os.fdopen(fd, "rb", closefd=False) as handle:
                data = handle.read(MAX_SKILL_FILE_BYTES + 1)
            if len(data) > MAX_SKILL_FILE_BYTES:
                raise SkillSnapshotDenied("skill asset exceeds byte budget")
            return data
        finally:
            os.close(fd)
    except OSError as exc:
        raise SkillSnapshotDenied("skill asset inaccessible or unsafe") from exc
    finally:
        os.close(dfd)


def snapshot_digests(root: Path, paths: list[str]) -> dict[str, Any]:
    """Compute deterministic SHA-256 of actual file bytes and a sorted manifest."""
    if not isinstance(paths, list) or not paths or len(paths) > 128:
        raise SkillSnapshotDenied("invalid skill asset list")
    if len(paths) != len(set(paths)):
        raise SkillSnapshotDenied("duplicate skill asset path")
    entries = []
    total = 0
    for path in sorted(paths):
        data = _read_regular_nofollow(root, path)
        total += len(data)
        if total > MAX_PACKAGE_BYTES:
            raise SkillSnapshotDenied("skill package exceeds byte budget")
        entries.append({"path": path, "sha256": _sha(data)})
    manifest = json.dumps({"scheme": MANIFEST_SCHEME, "files": entries},
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"scheme": MANIFEST_SCHEME, "files": entries,
            "manifest_sha256": _sha(manifest)}


def verify_admitted_snapshot(
    root: Path, package: dict[str, Any], registry_entry: dict[str, Any],
    admission: dict[str, Any], selection: dict[str, Any], task_scope: str,
) -> dict[str, Any]:
    """Bind source bytes to caller-supplied FA3 authority receipts; fail closed.

    No remote fetch, asset execution, installation, writing, or implicit permission
    is performed. The authoritative caller is responsible for authenticating receipts.
    """
    if not isinstance(task_scope, str) or not task_scope:
        raise SkillSnapshotDenied("task scope required")
    if not package_admission_allowed(package):
        raise SkillSnapshotDenied("package admission contract denied")
    entrypoints = package["entrypoints"]
    if len(entrypoints) != 1:
        raise SkillSnapshotDenied("one selected entrypoint required")
    entry = entrypoints[0]
    skill_id = registry_entry.get("skill_id")
    pkg_id = package["package_id"]
    content_expected = package["digests"]["content_sha256"]
    manifest_expected = package["digests"]["manifest_sha256"]
    dependencies_expected = package["dependencies"]["digest_sha256"]
    if (registry_entry.get("admission_status") != "ADMITTED"
            or registry_entry.get("package_id") != pkg_id
            or registry_entry.get("entrypoint") != entry["path"]
            or registry_entry.get("version") != entry["version"]):
        raise SkillSnapshotDenied("registry identity or admission mismatch")
    if (admission.get("result") != "PASS" or not admission.get("receipt_ref")
            or admission.get("package_id") != pkg_id
            or admission.get("content_sha256") != content_expected
            or admission.get("manifest_sha256") != manifest_expected
            or admission.get("dependency_digest_sha256") != dependencies_expected):
        raise SkillSnapshotDenied("admission receipt does not bind snapshot")
    if (not selection.get("receipt_ref")
            or selection.get("package_id") != pkg_id
            or selection.get("skill_id") != skill_id
            or selection.get("task_scope") != task_scope
            or skill_id not in selection.get("eligible_skill_ids", [])):
        raise SkillSnapshotDenied("selection receipt is out of scope")
    classes = registry_entry.get("eligibility", {}).get("task_classes", [])
    if classes and task_scope not in classes:
        raise SkillSnapshotDenied("skill is not eligible for task class")
    if (task_scope not in package.get("compatibility", {}).get("task_classes", [])
            or entry["path"] not in package["files"]):
        raise SkillSnapshotDenied("package entrypoint or scope mismatch")
    if package.get("symlinks"):
        raise SkillSnapshotDenied("symlinks forbidden in verified snapshot profile")
    observed = snapshot_digests(Path(root), package["files"])
    matching = next(x for x in observed["files"] if x["path"] == entry["path"])
    if (matching["sha256"] != content_expected
            or observed["manifest_sha256"] != manifest_expected):
        raise SkillSnapshotDenied("actual snapshot bytes differ from admitted digests")
    return {"schema": "fa3.skill-materialization-verification.v1", "result": "PASS",
            "package_id": pkg_id, "skill_id": skill_id, "task_scope": task_scope,
            "entrypoint": entry["path"], "content_sha256": matching["sha256"],
            "manifest_sha256": observed["manifest_sha256"],
            "dependency_digest_sha256": dependencies_expected,
            "selection_receipt_ref": selection["receipt_ref"],
            "admission_receipt_ref": admission["receipt_ref"],
            "execution_performed": False, "authority": False}


def task_activation_lease(verified: dict[str, Any], *, ttl_seconds: int = 300,
                          now: datetime | None = None) -> dict[str, Any]:
    """Create a short-lived context lease; never grant execution authority."""
    if verified.get("result") != "PASS" or verified.get("authority") is not False:
        raise SkillSnapshotDenied("verified snapshot required")
    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or not 1 <= ttl_seconds <= 3600:
        raise SkillSnapshotDenied("invalid activation TTL")
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise SkillSnapshotDenied("timezone-aware timestamp required")
    return {"schema": "fa3.skill-activation-lease.v1",
            "lease_id": "skill-lease:" + str(uuid4()),
            "task_scope": verified["task_scope"], "package_id": verified["package_id"],
            "skill_id": verified["skill_id"], "content_sha256": verified["content_sha256"],
            "manifest_sha256": verified["manifest_sha256"],
            "selection_receipt_ref": verified["selection_receipt_ref"],
            "admission_receipt_ref": verified["admission_receipt_ref"],
            "expires_at": (timestamp + timedelta(seconds=ttl_seconds)).isoformat(),
            "grants_execution_authority": False}


def verified_use_receipt(
    root: Path, package: dict[str, Any], registry_entry: dict[str, Any],
    admission: dict[str, Any], selection: dict[str, Any], lease: dict[str, Any],
    intent: dict[str, Any], *, now: datetime | None = None,
) -> dict[str, Any]:
    """Rehash actual bytes at each use, check lease, then apply existing use gate."""
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise SkillSnapshotDenied("timezone-aware timestamp required")
    try:
        expiry = datetime.fromisoformat(lease["expires_at"])
    except (KeyError, ValueError, TypeError) as exc:
        raise SkillSnapshotDenied("invalid activation expiry") from exc
    if expiry.tzinfo is None or timestamp >= expiry:
        raise SkillSnapshotDenied("expired activation lease")
    checked = verify_admitted_snapshot(root, package, registry_entry, admission,
                                       selection, lease.get("task_scope", ""))
    for key in ("package_id", "skill_id", "task_scope", "content_sha256",
                "manifest_sha256", "selection_receipt_ref", "admission_receipt_ref"):
        if lease.get(key) != checked[key]:
            raise SkillSnapshotDenied("activation lease does not bind verified snapshot")
    if lease.get("grants_execution_authority") is not False or not lease.get("lease_id"):
        raise SkillSnapshotDenied("invalid lease authority claim")
    receipt = {
        "package_admission_status": "PASS", "materialization_state": "ACTIVE_FOR_TASK",
        "selection_receipt_ref": checked["selection_receipt_ref"],
        "admission_receipt_ref": checked["admission_receipt_ref"],
        "skill_name": package["entrypoints"][0]["name"],
        "skill_version": package["entrypoints"][0]["version"],
        "content_sha256": checked["content_sha256"],
        "dependency_digest_sha256": checked["dependency_digest_sha256"],
        "task_scope": checked["task_scope"], "unsandboxed_execution": False,
        "candidate_expanded_after_eligibility": False,
        "tool_intent": intent.get("tool_intent", {}),
        "model_intent": intent.get("model_intent", {}),
        "resource_intent": intent.get("resource_intent", {}),
        "secret_intent": intent.get("secret_intent", {}),
        "snapshot_verification": checked, "activation_lease_id": lease["lease_id"],
    }
    if not skill_use_allowed(receipt):
        raise SkillSnapshotDenied("existing FA3 skill use gate denied intent")
    return receipt
