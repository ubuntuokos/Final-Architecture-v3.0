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


SUPERSEDING_DECISION_PATH = Path("canonical/decisions/FA3-DEC-UNREAL-CONDITIONAL-ADMISSION-2026-09-29.json")


def structural_findings(root: Path) -> list[str]:
    findings: list[str] = []
    historical = load_json(root / DECISION_PATH)
    decision = load_json(root / SUPERSEDING_DECISION_PATH)
    d = decision.get("decision", {})
    if historical.get("status") != "CANONICAL":
        findings.append("historical exclusion decision record must remain intact")
    if decision.get("status") != "CANONICAL" or decision.get("supersedes") != historical.get("decision_id"):
        findings.append("superseding optional-admission decision missing or not canonical")
    if d.get("engine") != "Unreal Engine" or d.get("fa3_scope_state") != "OPTIONAL_CONDITIONAL_ADMISSION":
        findings.append("Unreal Engine optional admission decision drift")
    for key in ("runtime_discovery", "runtime_execution", "provider_registration", "gui_projection", "mcp_projection"):
        if d.get(key) != "CONDITIONAL":
            findings.append(f"conditional admission boundary disabled: {key}")
    if d.get("installation_management") != "NOT_AUTOMATIC":
        findings.append("automatic installation not permitted")
    if d.get("capability_delta") != 0 or d.get("canonical_capability_count") != 175:
        findings.append("capability baseline drift")
    if decision.get("non_claims", {}).get("unreal_current_host_pass") is not False:
        findings.append("physical current-host evidence must not be invented")
    recipes = load_json(root / "canonical/current-host-capability-proof-recipes.json")
    cap027 = next((x for x in recipes.get("recipes", []) if x.get("capability_id") == "CAP-027"), None)
    if not isinstance(cap027, dict) or cap027.get("subject") != "Realtime / Virtual Production Interchange" or cap027.get("primitive") != "graphics_3d" or cap027.get("engine_specific_dependency") is not False:
        findings.append("CAP-027 provider-neutral graphics_3d proof contract drift")
    registry = load_json(root / "evidence/evidence-registry.json")
    row = next((x for x in registry.get("records", []) if x.get("subject_id") == "CAP-027"), None)
    if not isinstance(row, dict) or row.get("subject") != "Realtime / Virtual Production Interchange":
        findings.append("CAP-027 Evidence Registry record missing or changed")
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
        # Historical references and donor notes are permitted by the superseding decision.
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
