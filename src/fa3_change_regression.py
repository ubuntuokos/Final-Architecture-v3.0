#!/usr/bin/env python3
"""Regression diagnostics for CHIF."""
from __future__ import annotations

from typing import Any, Iterable


def diagnose(*, previous: dict[str, Any], current: dict[str, Any],
             evidence_states: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    previous_caps = set(previous.get("capability_ids", []))
    current_caps = set(current.get("capability_ids", []))
    missing = sorted(previous_caps - current_caps)
    if missing:
        findings.append({"code": "CAPABILITY_REGRESSION", "severity": "P0", "missing": missing})
    previous_gates = set(previous.get("mandatory_gates", []))
    current_gates = set(current.get("mandatory_gates", []))
    removed_gates = sorted(previous_gates - current_gates)
    if removed_gates:
        findings.append({"code": "MANDATORY_GATE_REGRESSION", "severity": "P0", "missing": removed_gates})
    stale = [state for state in evidence_states if state.get("current") is False]
    if stale:
        findings.append({
            "code": "EVIDENCE_STALE_AFTER_CHANGE",
            "severity": "P0",
            "count": len(stale),
        })
    return {
        "schema": "fa3.change-regression-diagnostic.v1",
        "result": "FAIL" if findings else "PASS",
        "findings": findings,
        "authoritative_promotion_decision": False,
    }
