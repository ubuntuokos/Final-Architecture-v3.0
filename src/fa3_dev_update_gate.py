#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "dev": ROOT / "canonical/FA3-DEV-MODE-001.json",
    "update": ROOT / "canonical/FA3-UPDATE-FABRIC-001.json",
    "security": ROOT / "canonical/FA3-SECURITY-UPDATE-001.json",
    "restart": ROOT / "canonical/FA3-UPDATE-RESTART-001.json",
    "dev_policy": ROOT / "config/fa3-dev-policy.json",
    "update_policy": ROOT / "config/fa3-update-policy.json",
}


def load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssertionError(f"{path.relative_to(ROOT)} unavailable/invalid: {exc}")
    if not isinstance(data, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} must be a JSON object")
    return data


def check(root: Path = ROOT) -> dict[str, Any]:
    del root
    docs = {name: load(path) for name, path in FILES.items()}
    findings: list[str] = []

    for name in ("dev", "update", "security", "restart"):
        doc = docs[name]
        if doc.get("status") != "CANONICAL":
            findings.append(f"{name}: status must be CANONICAL")
        if doc.get("priority") != "P0":
            findings.append(f"{name}: priority must be P0")
        if doc.get("new_capabilities") != 0 or doc.get("new_architectural_authorities") != 0:
            findings.append(f"{name}: capability/authority delta must remain zero")
        if doc.get("capability_count") != 143:
            findings.append(f"{name}: capability_count must remain 143")

    dev = docs["dev"]
    if dev.get("production_invariant") != "FAIL_CLOSED_UNCHANGED":
        findings.append("dev: production fail-closed invariant missing")
    if dev.get("trust_domains", {}).get("development", {}).get("canonical_write") != "DENY":
        findings.append("dev: development canonical write must be DENY")
    if dev.get("operations", {}).get("freeze", {}).get("canonical_write") is not False:
        findings.append("dev: freeze must not write canonical state")
    if dev.get("operations", {}).get("promote", {}).get("requires") != ["STATIC_PASS", "HOST_PASS", "PROMOTION_READY"]:
        findings.append("dev: promotion prerequisites changed")

    dev_policy = docs["dev_policy"]
    if dev_policy.get("production_eligible") is not False:
        findings.append("dev policy: production_eligible must be false")
    if dev_policy.get("trust_domain", {}).get("production_secrets") != "DENY":
        findings.append("dev policy: production secrets must be denied")
    if dev_policy.get("network", {}).get("default_egress") != "DENY":
        findings.append("dev policy: unknown/default egress must be denied")
    if dev_policy.get("snapshot", {}).get("source") != "GIT_INDEX":
        findings.append("dev policy: snapshot must bind to Git index")

    update = docs["update"]
    if update.get("operations", {}).get("blind_update_all") is not False:
        findings.append("update: blind Update All must remain disabled")
    if update.get("operations", {}).get("check_all") is not True:
        findings.append("update: Check All discovery must remain available")
    if update.get("models", {}).get("separate_queue") is not True:
        findings.append("update: models require a separate queue")
    if update.get("host_critical", {}).get("automatic_blind_activation") is not False:
        findings.append("update: host-critical blind activation must be disabled")

    security = docs["security"]
    if security.get("silent_forced_reboot") != "DENY":
        findings.append("security: silent forced reboot must be denied")
    if security.get("protected_workload_interruption") != "DENY":
        findings.append("security: protected workload interruption must be denied")

    restart = docs["restart"]
    if restart.get("recommended_default") != "WHEN_IDLE_SAFE":
        findings.append("restart: WHEN_IDLE_SAFE must remain recommended")
    if restart.get("scheduling", {}).get("scheduled_time_overrides_protected_workload") is not False:
        findings.append("restart: schedule must not override protected workload")
    required_choices = {"RESTART_NOW", "WHEN_IDLE_SAFE", "SCHEDULE", "LATER"}
    if set(restart.get("choices", [])) != required_choices:
        findings.append("restart: user choice set changed")

    update_policy = docs["update_policy"]
    if update_policy.get("allow_blind_update_all") is not False:
        findings.append("update policy: blind Update All must remain disabled")
    if update_policy.get("automatic_security_updates") is not True:
        findings.append("update policy: automatic security maintenance must remain enabled")
    if update_policy.get("restart", {}).get("allow_silent_forced_reboot") is not False:
        findings.append("update policy: silent forced reboot must remain disabled")

    result = {
        "schema": "fa3.dev-update-gate-report.v1",
        "gate": "FA3-DEV-MODE-001+FA3-UPDATE-FABRIC-001",
        "status": "PASS" if not findings else "FAIL",
        "blocking_findings": findings,
        "capability_delta": 0,
        "authority_delta": 0,
        "capability_count": 143,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="reports/fa3-dev-update-gate-report.json")
    args = parser.parse_args()
    result = check()
    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
