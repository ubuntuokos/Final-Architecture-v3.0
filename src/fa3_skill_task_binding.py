"""Opt-in binding of existing FA3 Skill Fabric and Language Gateway to agent tasks.

The caller supplies authority-issued records and a language admission snapshot.
This module validates their contents and rehashes skill assets at each preflight.
It does not itself issue, sign, or authenticate those authority records.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from fa3_language_gateway_gate import (
    LanguagePolicyDenied, language_capability_is_operable, normalize_locale,
    validate_language_selection,
)
from fa3_skill_materialization import SkillSnapshotDenied, verified_use_receipt


class SkillTaskBindingDenied(ValueError):
    pass


@dataclass(frozen=True)
class SkillTaskBinding:
    root: Path
    package: dict[str, Any]
    registry_entry: dict[str, Any]
    admission: dict[str, Any]
    selection: dict[str, Any]
    lease: dict[str, Any]
    intent: dict[str, Any]


def validate_language_context(context: dict[str, Any]) -> dict[str, str]:
    """Require explicit, Gateway-compatible task languages without silent fallback."""
    try:
        validate_language_selection(context["primary_language"], context["secondary_language"],
                                    context.get("additional_languages", []))
        status = context["admitted_language_status"]
        normalized = {}
        for key in ("user_language", "work_language", "output_language"):
            language = normalize_locale(context[key])
            normalized[key] = language
            if key in ("work_language", "output_language"):
                # NATIVE, VALIDATED, or BRIDGED, established by the existing
                # Language Admission authority, never assumed from a locale.
                if not language_capability_is_operable(status[language]):
                    raise SkillTaskBindingDenied("language not admitted: " + language)
        return normalized
    except (KeyError, TypeError, LanguagePolicyDenied) as exc:
        raise SkillTaskBindingDenied("invalid or unadmitted task language context") from exc


def task_skill_preflight(task: Any, bindings: Mapping[str, SkillTaskBinding],
                         language_context: dict[str, Any]) -> list[dict[str, Any]]:
    """Return verified receipts for a coordinator task immediately before spawn."""
    validate_language_context(language_context)
    required = tuple(task.required_skill_ids)
    if len(set(required)) != len(required) or set(bindings) != set(required):
        raise SkillTaskBindingDenied("skill binding set does not match explicit task request")
    receipts: list[dict[str, Any]] = []
    for skill_id in required:
        row = bindings[skill_id]
        if row.registry_entry.get("skill_id") != skill_id:
            raise SkillTaskBindingDenied("skill identity mismatch")
        try:
            receipt = verified_use_receipt(
                row.root, row.package, row.registry_entry, row.admission,
                row.selection, row.lease, row.intent,
            )
        except SkillSnapshotDenied as exc:
            raise SkillTaskBindingDenied("Skill Fabric denied task activation") from exc
        if (receipt["task_scope"] != "developer"
                or receipt["snapshot_verification"]["skill_id"] != skill_id):
            raise SkillTaskBindingDenied("skill activation outside developer task scope")
        receipts.append(receipt)
    return receipts
