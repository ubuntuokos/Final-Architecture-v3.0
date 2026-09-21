#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Iterable

BACKEND_CLASSES = {"native", "portable", "translation"}
_UNHEALTHY = {"UNHEALTHY", "FAILED", "LOST", "OFFLINE"}


class ExecutionPathError(ValueError):
    pass


def _name(value: Any) -> str:
    return str(value or "").strip().lower()


def validate_execution_requirement(requirement: Any) -> list[str]:
    if requirement in (None, {}):
        return []
    if not isinstance(requirement, dict):
        return ["ACCELERATOR_EXECUTION_REQUIREMENT_INVALID"]
    errors: list[str] = []
    paths = requirement.get("acceptable_execution_paths")
    if not isinstance(paths, list) or not paths:
        errors.append("ACCEPTABLE_EXECUTION_PATHS_EMPTY")
        return errors
    allow_translation = requirement.get("allow_translation", False)
    if not isinstance(allow_translation, bool):
        errors.append("ALLOW_TRANSLATION_NOT_BOOLEAN")
    for index, path in enumerate(paths):
        if not isinstance(path, dict):
            errors.append(f"EXECUTION_PATH_INVALID:{index}")
            continue
        backend = _name(path.get("backend"))
        backend_class = _name(path.get("backend_class"))
        if not backend:
            errors.append(f"EXECUTION_PATH_BACKEND_MISSING:{index}")
        if backend_class not in BACKEND_CLASSES:
            errors.append(f"EXECUTION_PATH_CLASS_INVALID:{index}")
        if backend_class == "translation" and allow_translation is not True:
            errors.append(f"TRANSLATION_PATH_NOT_EXPLICITLY_ALLOWED:{index}")
    return errors


def _candidate_backend(candidate: dict[str, Any]) -> str:
    return _name(candidate.get("backend", candidate.get("name")))


def _candidate_backend_class(candidate: dict[str, Any]) -> str:
    return _name(candidate.get("backend_class", candidate.get("class")))


def _candidate_usable(candidate: dict[str, Any]) -> bool:
    if candidate.get("available") is not True:
        return False
    if candidate.get("detected", True) is not True:
        return False
    if str(candidate.get("binding_scope", "DEVICE")).upper() != "DEVICE":
        return False
    if _candidate_backend_class(candidate) not in BACKEND_CLASSES:
        return False
    if str(candidate.get("health", "READY")).upper() in _UNHEALTHY:
        return False
    return bool(_candidate_backend(candidate))


def execution_path_matches(requirement: Any, candidate: dict[str, Any]) -> bool:
    if not isinstance(candidate, dict) or not _candidate_usable(candidate):
        return False
    candidate_class = _candidate_backend_class(candidate)
    allow_translation = bool(requirement.get("allow_translation", False)) if isinstance(requirement, dict) else False
    if candidate_class == "translation" and not allow_translation:
        return False

    if requirement in (None, {}):
        return candidate_class in {"native", "portable"}
    if validate_execution_requirement(requirement):
        return False

    for wanted in requirement["acceptable_execution_paths"]:
        if _name(wanted.get("backend")) != _candidate_backend(candidate):
            continue
        if _name(wanted.get("backend_class")) != candidate_class:
            continue
        wanted_framework = _name(wanted.get("framework_backend"))
        if wanted_framework and wanted_framework != _name(candidate.get("framework_backend")):
            continue
        return True
    return False


def compatible_execution_paths(
    requirement: Any,
    candidates: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [candidate for candidate in candidates if execution_path_matches(requirement, candidate)]


def bind_hrb_execution_path(
    *,
    authority_receipt: str,
    accelerator_id: str,
    requirement: Any,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    if authority_receipt != "HRB_PLACEMENT_RECEIPT":
        raise ExecutionPathError("execution-path binding requires HRB placement authority")
    if str(candidate.get("accelerator_id", "")).strip() != str(accelerator_id).strip():
        raise ExecutionPathError("candidate accelerator identity does not match HRB placement")
    if not execution_path_matches(requirement, candidate):
        raise ExecutionPathError("candidate execution path is incompatible with workload requirement")
    return {
        "schema": "fa3.hrb-accelerator-execution-binding.v1",
        "authority_receipt": authority_receipt,
        "accelerator_id": accelerator_id,
        "backend": _candidate_backend(candidate),
        "backend_class": _candidate_backend_class(candidate),
        "framework_backend": _name(candidate.get("framework_backend")) or None,
        "runtime_version": str(candidate.get("runtime_version") or "") or None,
        "provider_id": str(candidate.get("provider_id") or "") or None,
        "translation_backend": (
            _candidate_backend(candidate)
            if _candidate_backend_class(candidate) == "translation"
            else None
        ),
        "fallback_policy": "DENY_SILENT_SUBSTITUTION",
    }
