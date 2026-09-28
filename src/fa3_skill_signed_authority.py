"""Verify task-scoped Skill Fabric claims through existing FA3 PKI and Security Governance.

Claims are inert. This adapter never issues approval, installs skills,
chooses models, grants tool access, or promotes reference evidence.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from fa3_authenticated_approval import (
    DEFAULT_ROOT_CA, DEFAULT_SECURITY_APPROVAL_KEY,
    verify_authenticated_receipt, canonical_bytes,
)

KIND_POLICY = {
    "package_admission": ("SKILL_PACKAGE_ADMISSION", "SKILL_PACKAGE_ADMITTER"),
    "task_selection": ("SKILL_TASK_SELECTION", "SKILL_TASK_SELECTOR"),
    "language_admission": ("SKILL_LANGUAGE_ADMISSION", "SKILL_LANGUAGE_ADMITTER"),
}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SignedSkillAuthorityVerifier:
    """Only an independently pinned release commit and registry SHA are trusted."""

    def __init__(
        self, *, source_commit: str, registry_sha256: str,
        root_ca: Path = DEFAULT_ROOT_CA,
        security_public_key: Path = DEFAULT_SECURITY_APPROVAL_KEY,
        strict_host_permissions: bool = True,
    ) -> None:
        if not isinstance(source_commit, str) or not SHA40.fullmatch(source_commit):
            raise ValueError("trusted immutable source commit required")
        if not isinstance(registry_sha256, str) or not SHA256.fullmatch(registry_sha256):
            raise ValueError("trusted registry SHA-256 required")
        if not isinstance(strict_host_permissions, bool):
            raise ValueError("invalid host-permission enforcement")
        self.source_commit = source_commit
        self.registry_sha256 = registry_sha256
        self.root_ca = Path(root_ca)
        self.security_public_key = Path(security_public_key)
        self.strict_host_permissions = strict_host_permissions

    def verify_registry(self, actual_registry_bytes: bytes) -> bool:
        return (isinstance(actual_registry_bytes, bytes)
                and hashlib.sha256(actual_registry_bytes).hexdigest() == self.registry_sha256)

    def __call__(self, kind: str, record: dict[str, Any], task_id: str) -> bool:
        policy = KIND_POLICY.get(kind)
        if policy is None or not isinstance(record, dict) or not isinstance(task_id, str) or not task_id:
            return False
        signed = record.get("authority_receipt")
        if not isinstance(signed, dict):
            return False
        body = {k: v for k, v in record.items() if k != "authority_receipt"}
        expected = {"schema": "fa3.skill-authority-binding.v1",
                    "kind": kind, "task_id": task_id, "claim": body}
        if not isinstance(signed.get("payload"), dict):
            return False
        if canonical_bytes(signed["payload"]) != canonical_bytes(expected):
            return False
        result = verify_authenticated_receipt(
            signed, expected_receipt_type=policy[0], required_role=policy[1],
            expected_source_commit=self.source_commit,
            root_ca=self.root_ca, security_public_key=self.security_public_key,
            expected_grant_scope="FA3_SKILL_RUNTIME",
            strict_host_permissions=self.strict_host_permissions,
        )
        return result["qualified"] is True
