#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("canonical/FA3-UPSTREAM-LOCK-REGISTRY-001.json")
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    policy = registry.get("policy", {})
    if policy.get("floating_main_allowed_for_runtime") is not False:
        findings.append("floating runtime refs are not denied")
    if policy.get("floating_main_allowed_for_promotion_evidence") is not False:
        findings.append("floating promotion refs are not denied")
    if policy.get("immutable_identity_required") is not True:
        findings.append("immutable identity is not required")

    locks = registry.get("locks", {})
    if not locks:
        findings.append("lock registry is empty")
    for name, lock in locks.items():
        revision = str(lock.get("revision", ""))
        kind = lock.get("kind")
        if not revision:
            findings.append(f"{name}: revision missing")
        if kind in {"git_commit", "release_plus_commit", "model_revision"} and not SHA40.match(revision):
            findings.append(f"{name}: immutable 40-hex revision required")
        if lock.get("update_policy") != "CONTROLLED":
            findings.append(f"{name}: update policy is not CONTROLLED")
        if not lock.get("provider_id"):
            findings.append(f"{name}: provider_id missing")

    pipeline = registry.get("promotion_pipeline", [])
    required_steps = {
        "RESOLVE_IMMUTABLE_IDENTITY",
        "SECURITY_SCAN",
        "SANDBOX_CONFORMANCE",
        "WRITE_EVIDENCE",
        "REVIEW_LOCK_DIFF",
        "PROMOTE_LOCK",
    }
    if not required_steps.issubset(set(pipeline)):
        findings.append("managed promotion pipeline is incomplete")
    return {
        "schema": "fa3.upstream-lock-gate-report.v1",
        "result": "PASS" if not findings else "FAIL",
        "lock_count": len(locks),
        "findings": findings,
    }


def gate(root: Path) -> dict[str, Any]:
    return validate_registry(_load(root / REGISTRY_PATH))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
