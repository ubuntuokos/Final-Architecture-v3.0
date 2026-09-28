#!/usr/bin/env python3
"""Non-authoritative FA3 Skill Fabric -> Developer Agent + Language Gateway adapter.

Skill content is untrusted data. A task binding grants no execution, model,
network, filesystem, secret, provider or language-bridge authority. Existing
issuers must validate every admission/selection/lease and language receipt.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from fa3_language_gateway_gate import (
    LanguagePolicyDenied, language_capability_is_operable, normalize_locale,
)
from fa3_skill_activation import ActiveSkillContext, SkillActivationDenied

SHA256 = re.compile(r"^[0-9a-f]{64}$")
ReceiptVerifier = Callable[[Mapping[str, Any]], bool]


class SkillTaskBindingDenied(RuntimeError):
    pass


@dataclass(frozen=True)
class TaskSkillBinding:
    task_id: str
    skill_id: str
    package_id: str
    materialization_receipt_ref: str
    content_sha256: str
    original_content_sha256: str
    content_text: str = field(repr=False)
    language_context: dict[str, str] = field(default_factory=dict)
    language_status: str = ""
    language_receipt_ref: str = ""
    activation_lease_ref: str = ""
    expires_at_epoch: int = 0
    source_context: ActiveSkillContext = field(repr=False, compare=False, default=None)

    def check_live(self, *, now_epoch: int | None = None) -> None:
        current = int(time.time()) if now_epoch is None else now_epoch
        if type(current) is not int or current >= self.expires_at_epoch:
            raise SkillTaskBindingDenied("SKILL_TASK_LEASE_EXPIRED")
        if self.source_context is None:
            raise SkillTaskBindingDenied("SKILL_SOURCE_CONTEXT_REQUIRED")
        try:
            original = self.source_context.read_text()
        except (SkillActivationDenied, UnicodeError) as exc:
            raise SkillTaskBindingDenied("SKILL_SOURCE_CONTEXT_CLOSED") from exc
        if hashlib.sha256(original.encode("utf-8")).hexdigest() != self.original_content_sha256:
            raise SkillTaskBindingDenied("SKILL_SOURCE_CHANGED")
        if hashlib.sha256(self.content_text.encode("utf-8")).hexdigest() != self.content_sha256:
            raise SkillTaskBindingDenied("SKILL_CONTEXT_CHANGED")

    def safe_metadata(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "skill_id": self.skill_id,
            "package_id": self.package_id,
            "materialization_receipt_ref": self.materialization_receipt_ref,
            "content_sha256": self.content_sha256,
            "language_context": dict(self.language_context),
            "language_status": self.language_status,
            "language_receipt_ref": self.language_receipt_ref,
            "activation_lease_ref": self.activation_lease_ref,
            "expires_at_epoch": self.expires_at_epoch,
            "authority": False,
            "current_host_production_claim": False,
        }


def _require(cond: bool, reason: str) -> None:
    if not cond:
        raise SkillTaskBindingDenied(reason)


def _issuer_verified(verifier: ReceiptVerifier, receipt: Mapping[str, Any], reason: str) -> None:
    _require(callable(verifier), reason)
    try:
        verified = verifier(receipt)
    except Exception as exc:
        raise SkillTaskBindingDenied(reason) from exc
    _require(verified is True, reason)


def bind_language_checked_skill(
    *,
    context: ActiveSkillContext,
    task_id: str,
    skill_id: str,
    language_context: Mapping[str, str],
    language_evidence: Mapping[str, Any],
    verify_language_evidence: ReceiptVerifier,
    mediated_text: str | None = None,
    mediation_receipt: Mapping[str, Any] | None = None,
    verify_mediation_receipt: ReceiptVerifier | None = None,
    now_epoch: int | None = None,
) -> TaskSkillBinding:
    """Prepare content for a task only after existing language-issuer validation.

    BRIDGED content requires a separately issuer-verified bridge receipt
    cryptographically bound to the source and translated bytes. No implicit
    translation, silent fallback or automatic provider selection occurs.
    """
    _require(bool(task_id) and bool(skill_id), "TASK_OR_SKILL_MISSING")
    rec = context.receipt
    original = context.read_text()
    original_hash = hashlib.sha256(original.encode("utf-8")).hexdigest()
    _require(
        rec.get("state") == "ACTIVE_FOR_TASK"
        and rec.get("task_id") == task_id
        and rec.get("skill_id") == skill_id
        and rec.get("content_sha256") == original_hash
        and SHA256.fullmatch(original_hash) is not None
        and bool(rec.get("materialization_receipt_ref"))
        and bool(rec.get("activation_lease_ref"))
        and type(rec.get("expires_at_epoch")) is int,
        "MATERIALIZATION_TASK_BINDING_MISMATCH",
    )
    current = int(time.time()) if now_epoch is None else now_epoch
    _require(type(current) is int and current < rec["expires_at_epoch"], "SKILL_TASK_LEASE_EXPIRED")

    _require(
        isinstance(language_context, Mapping)
        and all(language_context.get(k) for k in ("user_language", "work_language", "output_language")),
        "TASK_LANGUAGE_CONTEXT_MISSING",
    )
    try:
        locales = {key: normalize_locale(language_context[key]) for key in
                   ("user_language", "work_language", "output_language")}
    except (LanguagePolicyDenied, AttributeError, TypeError) as exc:
        raise SkillTaskBindingDenied("TASK_LANGUAGE_CONTEXT_INVALID") from exc

    _issuer_verified(verify_language_evidence, language_evidence, "LANGUAGE_EVIDENCE_UNVERIFIED")
    status = language_evidence.get("status")
    _require(
        status in ("NATIVE", "VALIDATED", "BRIDGED")
        and language_capability_is_operable(status)
        and language_evidence.get("skill_id") == skill_id
        and language_evidence.get("source_content_sha256") == original_hash
        and language_evidence.get("language") == locales["output_language"]
        and language_evidence.get("admission_profile_id") == "FA3-LANGUAGE-ADMISSION-001"
        and bool(language_evidence.get("language_receipt_ref")),
        "SKILL_LANGUAGE_NOT_ADMITTED",
    )

    content = original
    if status == "BRIDGED":
        _require(isinstance(mediated_text, str) and bool(mediated_text),
                 "LANGUAGE_MEDIATED_CONTENT_REQUIRED")
        _require(isinstance(mediation_receipt, Mapping), "LANGUAGE_MEDIATION_RECEIPT_REQUIRED")
        _issuer_verified(verify_mediation_receipt, mediation_receipt,
                         "LANGUAGE_MEDIATION_RECEIPT_UNVERIFIED")
        _require(
            mediation_receipt.get("bridge_id") == "FA3-LANGUAGE-BRIDGE-001"
            and mediation_receipt.get("native_or_mediated") == "MEDIATED"
            and mediation_receipt.get("input_sha256") == original_hash
            and mediation_receipt.get("output_sha256")
            == hashlib.sha256(mediated_text.encode("utf-8")).hexdigest()
            and mediation_receipt.get("target_language") == locales["output_language"]
            and mediation_receipt.get("protected_token_validation") == "PASS"
            and mediation_receipt.get("authority_expanded_by_mediation") is False
            and bool(mediation_receipt.get("provider_id")),
            "LANGUAGE_MEDIATION_BINDING_MISMATCH",
        )
        content = mediated_text
    else:
        _require(mediated_text is None and mediation_receipt is None and verify_mediation_receipt is None,
                 "UNREQUESTED_LANGUAGE_MEDIATION_DENIED")

    result = TaskSkillBinding(
        task_id=task_id,
        skill_id=skill_id,
        package_id=rec["package_id"],
        materialization_receipt_ref=rec["materialization_receipt_ref"],
        content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        original_content_sha256=original_hash,
        content_text=content,
        language_context=locales,
        language_status=status,
        language_receipt_ref=language_evidence["language_receipt_ref"],
        activation_lease_ref=rec["activation_lease_ref"],
        expires_at_epoch=rec["expires_at_epoch"],
        source_context=context,
    )
    result.check_live(now_epoch=current)
    return result
