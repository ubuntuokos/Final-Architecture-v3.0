#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from fa3_accelerator_execution_path import validate_execution_requirement

FORBIDDEN_METRICS = {
    "cu",
    "tu",
    "compute_unit",
    "tensor_unit",
    "aggregate.cu",
    "aggregate.tu",
}

_ACCELERATOR_PREFIXES = ("gpu.", "npu.", "accelerator.")
_RESOURCE_PREFIXES = {
    "cpu.": "cpu",
    "memory.": "memory",
    "storage.": "storage",
    "numa.": "numa",
    "pcie.": "pcie",
}


def metric_resource_class(metric: Any) -> str:
    text = str(metric or "").strip().lower()
    if text.startswith(_ACCELERATOR_PREFIXES):
        return "accelerator"
    for prefix, resource_class in _RESOURCE_PREFIXES.items():
        if text.startswith(prefix):
            return resource_class
    return "other"


def classify_requirements(requirements: Any) -> tuple[list[str], bool]:
    if not isinstance(requirements, list):
        return [], False
    classes = {
        metric_resource_class(item.get("metric"))
        for item in requirements
        if isinstance(item, dict) and str(item.get("metric", "")).strip()
    }
    ordered = sorted(classes)
    return ordered, "accelerator" in classes


def validate_workload_requirements(requirements: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(requirements, list) or not requirements:
        return ["WORKLOAD_REQUIREMENTS_EMPTY"]
    for index, item in enumerate(requirements):
        if not isinstance(item, dict):
            errors.append(f"WORKLOAD_REQUIREMENT_INVALID:{index}")
            continue
        metric = str(item.get("metric", "")).strip().lower()
        if not metric:
            errors.append(f"WORKLOAD_REQUIREMENT_METRIC_MISSING:{index}")
        elif metric in FORBIDDEN_METRICS:
            errors.append(f"FORBIDDEN_ADMISSION_METRIC:{metric}")
    return errors


def validate_accelerator_execution_requirement(requirement: Any) -> list[str]:
    return validate_execution_requirement(requirement)


def validate_workload_envelope(workload: Any) -> list[str]:
    if not isinstance(workload, dict):
        return ["WORKLOAD_ENVELOPE_INVALID"]
    errors = validate_workload_requirements(workload.get("requirements"))
    execution = workload.get("accelerator_execution")
    classes, accelerator_required = classify_requirements(workload.get("requirements"))
    if execution not in (None, {}) and not accelerator_required:
        errors.append("ACCELERATOR_EXECUTION_WITHOUT_ACCELERATOR_RESOURCE_CLASS")
    errors.extend(validate_accelerator_execution_requirement(execution))
    return errors
