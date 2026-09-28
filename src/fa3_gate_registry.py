#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("canonical/FA3-GATE-REGISTRY-001.json")
POLICY_PATH = Path("canonical/enforcement-policy.json")
REGISTRY_ID = "FA3-GATE-REGISTRY-001"
GATESET_ID = "FA3-GATE-REGISTRY-GATESET-001"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _source_hits(root: Path, gate_id: str) -> dict[str, list[str]]:
    canonical: list[str] = []
    implementation: list[str] = []
    for path in (root / "canonical").rglob("*.json"):
        rel = path.relative_to(root).as_posix()
        if rel in {REGISTRY_PATH.as_posix(), POLICY_PATH.as_posix()}:
            continue
        try:
            if gate_id in path.read_text(encoding="utf-8"):
                canonical.append(rel)
        except OSError:
            pass
    for base in ("src", "bin", "tools"):
        d = root / base
        if not d.exists():
            continue
        for path in d.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".sh", ""}:
                continue
            try:
                if gate_id in path.read_text(encoding="utf-8"):
                    implementation.append(path.relative_to(root).as_posix())
            except (OSError, UnicodeDecodeError):
                pass
    return {
        "canonical": sorted(set(canonical)),
        "implementation": sorted(set(implementation)),
    }


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    try:
        registry = _load(root / REGISTRY_PATH)
        policy = _load(root / POLICY_PATH)
    except Exception as exc:
        return {
            "schema": "fa3.gate-registry-gate-report.v1",
            "gate_id": GATESET_ID,
            "result": "FAIL",
            "findings": [{"code": "GREG-000", "message": str(exc)}],
            "current_host_runtime_promotion_claim": False,
        }

    ids = registry.get("mandatory_reference_gates", [])
    mirror = policy.get("mandatory_reference_gates", [])
    if registry.get("id") != REGISTRY_ID or registry.get("schema") != "fa3.gate-registry.v1":
        findings.append({"code": "GREG-001", "message": "gate registry identity/schema drift"})
    if not isinstance(ids, list) or not ids:
        findings.append({"code": "GREG-002", "message": "mandatory gate registry is empty or invalid"})
        ids = []
    if len(ids) != len(set(ids)):
        findings.append({"code": "GREG-003", "message": "duplicate mandatory gate IDs"})
    if mirror != ids:
        findings.append({
            "code": "GREG-004",
            "message": "enforcement-policy mandatory_reference_gates mirror differs from canonical registry",
        })
    if registry.get("capability_count") != policy.get("canonical_capability_count"):
        findings.append({"code": "GREG-005", "message": "gate registry capability baseline drift"})
    if registry.get("new_capabilities") != 0 or registry.get("new_architectural_authorities") != 0:
        findings.append({"code": "GREG-006", "message": "gate registry may not add capability or authority"})
    if registry.get("current_host_runtime_promotion_claim") is not False:
        findings.append({"code": "GREG-007", "message": "gate registry may not claim runtime promotion"})

    records: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for gate_id in ids:
        hits = _source_hits(root, gate_id)
        materialized = bool(hits["canonical"] or hits["implementation"])
        if not materialized:
            unresolved.append(gate_id)
        records.append({
            "gate_id": gate_id,
            "canonical_declarations": hits["canonical"],
            "implementation_surfaces": hits["implementation"],
            "materialized": materialized,
        })
    if unresolved:
        findings.append({
            "code": "GREG-008",
            "message": "mandatory gate IDs without canonical declaration or implementation surface",
            "gate_ids": unresolved,
        })

    return {
        "schema": "fa3.gate-registry-gate-report.v1",
        "gate_id": GATESET_ID,
        "registry_id": REGISTRY_ID,
        "result": "PASS" if not findings else "FAIL",
        "mandatory_gate_count": len(ids),
        "materialized_gate_count": len(ids) - len(unresolved),
        "records": records,
        "findings": findings,
        "current_host_runtime_promotion_claim": False,
    }
