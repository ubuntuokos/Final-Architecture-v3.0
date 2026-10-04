#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from fa3_permanent_gate_hardening import (
    current_host_protected_workflows,
    loadj,
    scan_workflow_action_pins,
)

CONFIG_REL = Path("canonical/FA3-PERMANENT-GATE-HARDENING-001.json")


def changed_paths(
    candidate_root: Path, base_sha: str, head_sha: str
) -> list[str]:
    cp = subprocess.run(
        [
            "git",
            "-C",
            str(candidate_root),
            "diff",
            "--name-only",
            base_sha,
            head_sha,
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if cp.returncode != 0:
        raise ValueError(
            "unable to compute candidate diff from trusted evaluator"
        )
    return sorted(
        {
            line.strip()
            for line in cp.stdout.splitlines()
            if line.strip()
        }
    )


def classify(path: str, config: dict[str, Any]) -> str:
    protected = set(config.get("protected_control_plane_paths", []))
    prefixes = tuple(config.get("protected_control_plane_prefixes", []))
    if path in protected or any(path.startswith(p) for p in prefixes):
        return "CONTROL_PLANE"
    if path.startswith("canonical/"):
        return "CANONICAL_DATA"
    if path.startswith("evidence/"):
        return "EVIDENCE_CARRIER"
    if path.startswith("reports/"):
        return "TRACE_OR_READER"
    if path.startswith("tests/"):
        return "TEST_ONLY"
    if path.startswith("docs/"):
        return "READER_ONLY"
    return "IMPLEMENTATION"


def gate(
    trusted_root: Path,
    candidate_root: Path,
    base_sha: str,
    head_sha: str,
) -> dict[str, Any]:
    trusted_root = trusted_root.resolve()
    candidate_root = candidate_root.resolve()
    findings: list[dict[str, Any]] = []
    config = loadj(trusted_root / CONFIG_REL)
    candidate_config = loadj(candidate_root / CONFIG_REL)

    if (
        candidate_config.get("new_capabilities") != 0
        or candidate_config.get("new_architectural_authorities") != 0
    ):
        findings.append(
            {
                "code": "TCP-001",
                "message": (
                    "candidate hardening config introduces "
                    "capability/authority delta"
                ),
            }
        )
    if candidate_config.get("carrier_roles") != config.get("carrier_roles"):
        findings.append(
            {
                "code": "TCP-002",
                "message": "candidate changes authority carrier model",
            }
        )

    protected_workflows = current_host_protected_workflows(
        candidate_root, config.get("sha_pinned_workflows", [])
    )
    findings.extend(
        scan_workflow_action_pins(candidate_root, protected_workflows)
    )

    paths = changed_paths(candidate_root, base_sha, head_sha)
    classified = [
        {"path": path, "class": classify(path, config)}
        for path in paths
    ]
    control_plane = [
        row["path"]
        for row in classified
        if row["class"] == "CONTROL_PLANE"
    ]

    return {
        "schema": "fa3.trusted-control-plane-report.v1",
        "gate_id": "FA3-TRUSTED-CONTROL-PLANE-GATESET-001",
        "result": "PASS" if not findings else "FAIL",
        "trusted_evaluator_source": base_sha,
        "candidate_head": head_sha,
        "candidate_code_executed": False,
        "changed_paths": classified,
        "authority_impact_review_required": bool(control_plane),
        "control_plane_paths": control_plane,
        "findings": findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trusted-root", required=True)
    ap.add_argument("--candidate-root", required=True)
    ap.add_argument("--base-sha", required=True)
    ap.add_argument("--head-sha", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    report = gate(
        Path(args.trusted_root),
        Path(args.candidate_root),
        args.base_sha,
        args.head_sha,
    )
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
