"""Verified, non-authorizing SKILL.md projection for developer worker tasks.

Reference-only unless an existing FA3 authority supplies a real verifier for
admission, task selection and language admission. A permissive callback is NOT
issuer authentication and must never be installed by a production caller.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from fa3_skill_materialization import _read_regular_nofollow
from fa3_skill_task_binding import (
    SkillTaskBinding, SkillTaskBindingDenied, task_skill_preflight,
    validate_language_context,
)

MAX_INSTRUCTION_BYTES = 131072


class SkillProjectionDenied(ValueError):
    pass


class SkillTaskPreflight:
    """Concrete coordinator-bound preflight rather than a PASS-dictionary callback."""

    def __init__(
        self, bindings: Mapping[str, SkillTaskBinding], language_context: dict[str, Any],
        registry_root: Path, *,
        authority_verifier: Callable[[str, dict[str, Any], str], bool] | None = None,
        reference_only: bool = False,
    ) -> None:
        if not isinstance(reference_only, bool):
            raise SkillProjectionDenied("invalid evidence mode")
        if not reference_only and authority_verifier is None:
            raise SkillProjectionDenied("existing-authority verifier required")
        self.bindings = dict(bindings)
        self.language_context = language_context
        self.registry_root = Path(registry_root)
        self.authority_verifier = authority_verifier
        self.reference_only = reference_only

    def prepare_task(self, task: Any) -> dict[str, Any]:
        required = tuple(task.required_skill_ids)
        if not required or len(required) != len(set(required)) or set(required) != set(self.bindings):
            raise SkillProjectionDenied("explicit unique skill selection mismatch")
        try:
            registry = json.loads(_read_regular_nofollow(self.registry_root, "canonical/skill-registry.json"))
        except (ValueError, OSError, TypeError) as exc:
            raise SkillProjectionDenied("skill registry unavailable") from exc
        if registry.get("id") != "FA3-SKILL-REGISTRY-001" or not isinstance(registry.get("entries"), list):
            raise SkillProjectionDenied("invalid canonical skill registry")
        for skill_id in required:
            if self.bindings[skill_id].lease.get("task_id") != task.task_id:
                raise SkillProjectionDenied("activation lease not bound to this task ID")
            matches = [row for row in registry["entries"] if isinstance(row, dict)
                       and row.get("skill_id") == skill_id]
            if len(matches) != 1 or matches[0] != self.bindings[skill_id].registry_entry:
                raise SkillProjectionDenied("skill not identically registered")
        if not self.reference_only:
            claims = [("language_admission", self.language_context)]
            for skill_id in required:
                binding = self.bindings[skill_id]
                claims.extend((("package_admission", binding.admission),
                               ("task_selection", binding.selection)))
            for kind, record in claims:
                try:
                    verified = self.authority_verifier(kind, record, task.task_id)
                except Exception as exc:
                    raise SkillProjectionDenied("authority verifier unavailable") from exc
                if verified is not True:
                    raise SkillProjectionDenied("authority denied " + kind)
        try:
            languages = validate_language_context(self.language_context)
            receipts = task_skill_preflight(task, self.bindings, self.language_context)
        except (SkillTaskBindingDenied, ValueError, TypeError, KeyError) as exc:
            raise SkillProjectionDenied("task skill or language preflight denied") from exc
        if len(receipts) != len(required):
            raise SkillProjectionDenied("incomplete preflight")
        skills = []
        for skill_id, receipt in zip(required, receipts):
            relative = receipt["snapshot_verification"]["entrypoint"]
            try:
                data = _read_regular_nofollow(self.bindings[skill_id].root, relative)
                if not data or len(data) > MAX_INSTRUCTION_BYTES:
                    raise SkillProjectionDenied("instruction byte limit exceeded")
                instructions = data.decode("utf-8", errors="strict")
            except (OSError, UnicodeDecodeError) as exc:
                raise SkillProjectionDenied("invalid SKILL.md byte content") from exc
            digest = hashlib.sha256(data).hexdigest()
            if digest != receipt["content_sha256"] or receipt["snapshot_verification"]["skill_id"] != skill_id:
                raise SkillProjectionDenied("skill bytes changed since preflight")
            skills.append({
                "skill_id": skill_id, "entrypoint": relative, "instructions": instructions,
                "content_sha256": digest,
                "manifest_sha256": receipt["snapshot_verification"]["manifest_sha256"],
                "selection_receipt_ref": receipt["selection_receipt_ref"],
                "admission_receipt_ref": receipt["admission_receipt_ref"],
                "activation_lease_id": self.bindings[skill_id].lease["lease_id"],
                "lease_expires_at": self.bindings[skill_id].lease["expires_at"],
                "bound_task_id": self.bindings[skill_id].lease["task_id"],
            })
        return {
            "schema": "fa3.developer-task-skill-projection.v1",
            "task_id": task.task_id, "agent_id": task.agent_id,
            "task_scope": "developer", "languages": languages, "skills": skills,
            "evidence_scope": "CI_REFERENCE_ONLY" if self.reference_only else "AUTHORITY_ADAPTER_REPORTED_NOT_CRYPTOGRAPHICALLY_VERIFIED",
            "grants_execution_authority": False, "remote_fetch": False,
        }
