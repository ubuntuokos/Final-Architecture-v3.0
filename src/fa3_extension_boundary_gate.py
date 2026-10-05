#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

POLICY_PATH = Path("canonical/FA3-EXTENSION-BOUNDARY-001.json")


class ExtensionBoundaryError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_extension(declaration: dict[str, Any]) -> str:
    changing_flags = (
        "new_user_visible_capability",
        "new_autonomous_decision_right",
        "new_privileged_action_owner",
        "new_architectural_authority",
    )
    if any(bool(declaration.get(flag)) for flag in changing_flags):
        return "CAPABILITY_CHANGING"
    if declaration.get("existing_capability_ids") and declaration.get("new_capabilities", 0) == 0 and declaration.get("new_architectural_authorities", 0) == 0:
        return "CAPABILITY_NEUTRAL"
    raise ExtensionBoundaryError("extension is unclassified or lacks existing capability bindings")


def validate_extension(declaration: dict[str, Any]) -> dict[str, Any]:
    classification = classify_extension(declaration)
    findings: list[str] = []
    if classification == "CAPABILITY_NEUTRAL":
        if declaration.get("new_capabilities", 0) != 0:
            findings.append("capability-neutral extension declares new capabilities")
        if declaration.get("new_architectural_authorities", 0) != 0:
            findings.append("capability-neutral extension declares new architectural authority")
        if declaration.get("device_selection_authority") is True:
            findings.append("capability-neutral extension owns device-selection authority")
        if declaration.get("model_routing_authority") is True:
            findings.append("capability-neutral extension owns model-routing authority")
        if not declaration.get("runtime_evidence_ref"):
            findings.append("runtime evidence binding missing")
        if not declaration.get("security_evidence_ref"):
            findings.append("security evidence binding missing")
    else:
        required = (
            "release_baseline_change_ref",
            "capability_reconciliation_ref",
            "authority_reconciliation_ref",
            "canonical_decision_ref",
        )
        findings.extend(f"missing {key}" for key in required if not declaration.get(key))
    return {
        "schema": "fa3.extension-boundary-gate-report.v1",
        "classification": classification,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def gate(root: Path, declaration_path: Path | None = None) -> dict[str, Any]:
    policy = _load(root / POLICY_PATH)
    if policy.get("default_disposition") != "DENY_UNCLASSIFIED_EXTENSION":
        return {"result": "FAIL", "findings": ["extension default disposition is not fail-closed"]}
    if declaration_path is None:
        return {"result": "PASS", "findings": [], "policy_id": policy.get("id")}
    declaration = _load(declaration_path)
    return validate_extension(declaration)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--declaration")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    decl = Path(args.declaration).resolve() if args.declaration else None
    report = gate(root, decl)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
