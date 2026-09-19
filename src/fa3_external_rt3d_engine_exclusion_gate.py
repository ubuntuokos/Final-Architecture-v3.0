#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

DECISION_PATH = Path("canonical/decisions/FA3-DEC-EXTERNAL-RT3D-ENGINE-EXCLUSION-2026-09-19.json")
ALLOW_CONTENT = {
    DECISION_PATH.as_posix(),
    "src/fa3_external_rt3d_engine_exclusion_gate.py",
    "tests/test_external_rt3d_engine_exclusion_gate.py",
}
FORBIDDEN_SUBSTRINGS = (
    "epic games",
    ".local/share/epic",
)
ENGINE_PATTERN = re.compile(
    r"(?i)(?:\bunreal(?:\s+engine|editor(?:-cmd)?)?\b|fa3_unreal|unreal_runtime|profile-unreal)"
)
UE_PATTERN = re.compile(r"(?i)(?:^|[^a-z0-9])ue5(?:[^a-z0-9]|$)")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def tracked_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))
    return [x.decode("utf-8") for x in proc.stdout.split(b"\0") if x]


def token_findings(path: str, text: str) -> list[str]:
    if path in ALLOW_CONTENT:
        return []
    findings: list[str] = []
    low_path = path.lower()
    low_text = text.lower()
    for token in FORBIDDEN_SUBSTRINGS:
        if token in low_path:
            findings.append(f"forbidden integration token in path: {path}")
            break
    for token in FORBIDDEN_SUBSTRINGS:
        if token in low_text:
            findings.append(f"forbidden integration token in content: {path}")
            break
    if ENGINE_PATTERN.search(path) or ENGINE_PATTERN.search(text):
        findings.append(f"forbidden proprietary RT3D engine integration token: {path}")
    if UE_PATTERN.search(path) or UE_PATTERN.search(text):
        findings.append(f"forbidden UE5 integration token: {path}")
    return findings


def structural_findings(root: Path) -> list[str]:
    findings: list[str] = []
    decision = load_json(root / DECISION_PATH)
    d = decision.get("decision", {})
    if decision.get("status") != "CANONICAL":
        findings.append("external RT3D engine exclusion decision is not CANONICAL")
    if d.get("excluded_engine") != "Unreal Engine":
        findings.append("excluded engine identity drift")
    if d.get("fa3_scope_state") != "OUT_OF_SCOPE":
        findings.append("excluded engine returned to FA3 scope")
    for key in (
        "installation_management",
        "runtime_discovery",
        "runtime_execution",
        "provider_registration",
        "gui_projection",
        "menu_projection",
        "mcp_projection",
        "workflow_dependency",
        "evidence_dependency",
        "promotion_dependency",
        "environment_variable_contract",
    ):
        if d.get(key) != "DENY":
            findings.append(f"exclusion invariant disabled: {key}")

    recipes = load_json(root / "canonical/current-host-capability-proof-recipes.json")
    cap027 = next((x for x in recipes.get("recipes", []) if x.get("capability_id") == "CAP-027"), None)
    if not isinstance(cap027, dict):
        findings.append("CAP-027 proof recipe missing")
    else:
        if cap027.get("subject") != "Realtime / Virtual Production Interchange":
            findings.append("CAP-027 subject is not provider-neutral realtime/virtual production")
        if cap027.get("primitive") != "graphics_3d":
            findings.append("CAP-027 proof primitive is not graphics_3d")
        if cap027.get("engine_specific_dependency") is not False:
            findings.append("CAP-027 engine-specific dependency must be false")
    excluded_primitive = "un" + "real_runtime"
    if excluded_primitive in recipes.get("primitive_counts", {}):
        findings.append("excluded engine proof primitive remains registered")
    if any(x.get("primitive") == excluded_primitive for x in recipes.get("recipes", [])):
        findings.append("a capability still depends on the excluded engine proof primitive")

    registry = load_json(root / "evidence/evidence-registry.json")
    row = next((x for x in registry.get("records", []) if x.get("subject_id") == "CAP-027"), None)
    if not isinstance(row, dict):
        findings.append("CAP-027 Evidence Registry record missing")
    else:
        if row.get("subject") != "Realtime / Virtual Production Interchange":
            findings.append("CAP-027 Evidence Registry subject drift")
        if decision.get("decision_id") not in row.get("source_decision_ids", []):
            findings.append("CAP-027 does not cover the engine-exclusion decision")
    return findings


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings = structural_findings(root)
    scanned = 0
    for rel in tracked_files(root):
        path = root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        findings.extend(token_findings(rel, text))
    findings = sorted(set(findings))
    return {
        "schema": "fa3.external-rt3d-engine-exclusion-gate.v1",
        "gate_id": "FA3-EXTERNAL-RT3D-ENGINE-EXCLUSION-GATESET-001",
        "result": "PASS" if not findings else "BLOCKED",
        "tracked_text_files_scanned": scanned,
        "capability_027_subject": "Realtime / Virtual Production Interchange",
        "capability_count_delta": 0,
        "architectural_authority_delta": 0,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/external-rt3d-engine-exclusion-gate-report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    result = gate(root)
    report = root / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
