#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OPERATORS = {">=", "<=", "==", "contains"}
FORBIDDEN_ADMISSION_METRICS = {"cu", "tu", "compute_unit", "tensor_unit", "aggregate.cu", "aggregate.tu"}


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    metrics = profile.get("metrics")
    errors: list[str] = []
    if profile.get("schema") != "fa3.compute-profile.v1":
        errors.append("schema")
    if not _sha256(profile.get("host_attestation_sha256")):
        errors.append("host_attestation_sha256")
    if not isinstance(metrics, dict) or not metrics:
        errors.append("metrics")
        metrics = {}
    forbidden = sorted(set(metrics).intersection(FORBIDDEN_ADMISSION_METRICS))
    if forbidden:
        errors.append("forbidden_scalar_admission_metrics:" + ",".join(forbidden))
    diagnostic = profile.get("diagnostic_aggregates", {})
    if diagnostic and not isinstance(diagnostic, dict):
        errors.append("diagnostic_aggregates")
    return {"result": "PASS" if not errors else "FAIL", "errors": errors}


def _compare(actual: Any, op: str, expected: Any) -> bool:
    if op == ">=":
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and actual >= expected
    if op == "<=":
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and actual <= expected
    if op == "==":
        return actual == expected
    if op == "contains":
        return isinstance(actual, (list, tuple, set, str)) and expected in actual
    return False


def evaluate_workload(profile: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    profile_validation = validate_profile(profile)
    findings: list[dict[str, Any]] = []
    if profile_validation["result"] != "PASS":
        findings.append({"metric": "profile", "status": "FAIL", "reason": ";".join(profile_validation["errors"])})
    if envelope.get("schema") != "fa3.workload-resource-envelope.v1":
        findings.append({"metric": "envelope", "status": "FAIL", "reason": "schema"})
    requirements = envelope.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        findings.append({"metric": "envelope", "status": "FAIL", "reason": "requirements"})
        requirements = []
    metrics = profile.get("metrics", {}) if isinstance(profile.get("metrics"), dict) else {}
    for req in requirements:
        if not isinstance(req, dict):
            findings.append({"metric": "unknown", "status": "FAIL", "reason": "invalid_requirement"})
            continue
        metric, op, expected = req.get("metric"), req.get("operator"), req.get("value")
        if metric in FORBIDDEN_ADMISSION_METRICS:
            findings.append({"metric": metric, "status": "FAIL", "reason": "scalar_admission_forbidden"})
            continue
        if op not in OPERATORS:
            findings.append({"metric": metric, "status": "FAIL", "reason": "unknown_operator"})
            continue
        if metric not in metrics:
            findings.append({"metric": metric, "status": "FAIL", "reason": "missing_metric"})
            continue
        actual = metrics[metric]
        ok = _compare(actual, op, expected)
        findings.append({"metric": metric, "status": "PASS" if ok else "FAIL", "actual": actual, "operator": op, "required": expected})
    return {
        "schema": "fa3.workload-resource-admission.v1",
        "result": "PASS" if findings and all(x["status"] == "PASS" for x in findings) else "FAIL",
        "findings": findings,
        "cross_metric_compensation": False,
    }
