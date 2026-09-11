#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

CONFORMANCE_ID = "FA3-CURRENT-HOST-RUNNER-CONFORMANCE-001"
GATE_ID = "FA3-CURRENT-HOST-RUNNER-GATESET-001"
REPO = "ubuntuokos/Final-Architecture-v3.0"
VERSION = "2.337.0"
ASSET = "actions-runner-linux-x64-2.337.0.tar.gz"
SHA256 = "70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613"
LABELS = ["self-hosted", "linux", "x64", "fa3-current-host"]
P0 = [
    "RUNNER_REPOSITORY_BINDING_EXACT",
    "RUNNER_REQUIRED_LABEL_SET_EXACT_OR_SUPERSET",
    "RUNNER_IMMUTABLE_VERSION_AND_SHA256_PIN",
    "RUNNER_NETWORK_TO_SHELL_BOOTSTRAP_FORBIDDEN",
    "RUNNER_REGISTRATION_TOKEN_NOT_PERSISTED",
    "RUNNER_NON_ROOT_EXECUTION_REQUIRED",
    "RUNNER_SYSTEMD_USER_SERVICE_REQUIRED",
    "RUNNER_SERVICE_ACTIVE_FOR_EVIDENCE",
    "RUNNER_SERVER_SIDE_ONLINE_STATE_REQUIRED",
    "RUNNER_WORKSPACE_USER_OWNED",
    "RUNNER_GITHUB_HOSTED_SUBSTITUTION_FORBIDDEN",
    "RUNNER_RECEIPT_SECRET_FREE",
    "RUNNER_DOCTOR_PASS_NOT_GLOBAL_PROMOTION",
    "RUNNER_PROVIDER_E2E_RECEIPT_REQUIRED_SEPARATELY",
]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_conformance(obj: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    runner = obj.get("runner", {})
    reg = obj.get("registration", {})
    service = obj.get("service", {})
    evidence = obj.get("evidence", {})
    promotion = obj.get("promotion_semantics", {})
    checks = [
        (obj.get("id") == CONFORMANCE_ID, "conformance id drift"),
        (obj.get("repository") == REPO, "repository binding drift"),
        (obj.get("required_labels") == LABELS, "required labels drift"),
        (obj.get("capability_count") == 143, "capability count drift"),
        (obj.get("new_capabilities") == 0, "new capability introduced"),
        (obj.get("new_architectural_authorities") == 0, "new authority introduced"),
        (obj.get("architectural_authority") is False, "runner became architectural authority"),
        (runner.get("version") == VERSION, "runner version drift"),
        (runner.get("asset") == ASSET, "runner asset drift"),
        (runner.get("sha256") == SHA256, "runner sha256 drift"),
        (runner.get("auto_update") == "DISABLED_IMMUTABLE_PIN", "runner auto-update not disabled"),
        (runner.get("run_as_root") == "FORBIDDEN", "root runner permitted"),
        (reg.get("token_persistence") == "FORBIDDEN", "registration token persistence permitted"),
        (reg.get("server_side_label_revalidation") == "REQUIRED", "server-side label revalidation missing"),
        (service.get("manager") == "systemd --user", "service manager drift"),
        (evidence.get("github_hosted_substitution") == "FORBIDDEN", "GitHub-hosted substitution permitted"),
        (promotion.get("runner_doctor_pass_is_global_promotion") is False, "doctor PASS promotes globally"),
        (promotion.get("provider_e2e_must_run_separately") is True, "provider E2E separation missing"),
    ]
    for ok, msg in checks:
        if not ok:
            errors.append(msg)
    return errors


def validate_enforcement(obj: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if obj.get("id") != GATE_ID:
        errors.append("gate id drift")
    if obj.get("conformance_id") != CONFORMANCE_ID:
        errors.append("gate conformance binding drift")
    if obj.get("fail_closed") is not True:
        errors.append("gate not fail-closed")
    if obj.get("mandatory_rule_count") != len(P0):
        errors.append("mandatory rule count drift")
    if obj.get("p0_invariants") != P0:
        errors.append("P0 invariant set drift")
    return errors


def validate_bootstrap_text(text: str) -> list[str]:
    errors: list[str] = []
    needles = [
        f'RUNNER_VERSION="{VERSION}"',
        f'RUNNER_SHA256="{SHA256}"',
        'CUSTOM_LABEL="fa3-current-host"',
        '--disableupdate',
        '--unattended',
        '--labels "$CUSTOM_LABEL"',
        'systemctl --user enable --now',
        'FA3_GITHUB_RUNNER_TOKEN',
        'actions/runners/registration-token',
        'if [[ ${EUID:-$(id -u)} -eq 0 ]]',
    ]
    for needle in needles:
        if needle not in text:
            errors.append(f"bootstrap missing: {needle}")
    if re.search(r"curl[^\n|]*\|\s*(?:sh|bash)\b", text):
        errors.append("bootstrap contains network-to-shell pipeline")
    if re.search(r"(?:echo|printf)[^\n]*(?:RUNNER_TOKEN|FA3_GITHUB_RUNNER_TOKEN)[^\n]*>", text):
        errors.append("bootstrap may persist registration token")
    return errors


def validate_doctor_text(text: str) -> list[str]:
    errors: list[str] = []
    for needle in (
        'systemctl --user is-active --quiet',
        'actions/runners?per_page=100',
        'remote.get("status") != "online"',
        'required_labels_present',
        'registration_secret_recorded',
        'global_promotion_claim',
    ):
        if needle not in text:
            errors.append(f"doctor missing: {needle}")
    return errors


def validate_workflow_text(text: str) -> list[str]:
    errors: list[str] = []
    if "runs-on: [self-hosted, linux, x64, fa3-current-host]" not in text:
        errors.append("workflow missing exact current-host label set")
    if "workflow_dispatch:" not in text:
        errors.append("workflow is not operator-dispatchable")
    if "execute_current_host" not in text:
        errors.append("workflow lacks explicit current-host execution switch")
    return errors


def run(root: Path) -> dict[str, Any]:
    paths = {
        "conformance": root / "canonical/FA3-CURRENT-HOST-RUNNER-CONFORMANCE-001.json",
        "enforcement": root / "canonical/current-host-runner-enforcement.json",
        "decision": root / "canonical/decisions/FA3-DEC-CURRENT-HOST-RUNNER-2026-09-11.json",
        "bootstrap": root / "bin/fa3-current-host-runner-bootstrap.sh",
        "doctor": root / "bin/fa3-current-host-runner-doctor",
        "workflow": root / ".github/workflows/fa3-current-host-runner.yml",
        "docs": root / "docs/current-host-runner.md",
    }
    errors: list[str] = []
    for name, path in paths.items():
        if not path.exists():
            errors.append(f"missing {name}: {path.relative_to(root)}")
    if not errors:
        errors += validate_conformance(load(paths["conformance"]))
        errors += validate_enforcement(load(paths["enforcement"]))
        decision = load(paths["decision"])
        if not (decision.get("status") == "CANONICAL_CLOSED" and decision.get("capability_count_after") == 143 and decision.get("new_architectural_authorities") == 0):
            errors.append("decision invariant drift")
        errors += validate_bootstrap_text(paths["bootstrap"].read_text(encoding="utf-8"))
        errors += validate_doctor_text(paths["doctor"].read_text(encoding="utf-8"))
        errors += validate_workflow_text(paths["workflow"].read_text(encoding="utf-8"))
    report = {
        "schema": "fa3.current-host-runner-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not errors else "FAIL",
        "finding_count": len(errors),
        "findings": errors,
        "capability_count": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "current_host_runtime_promotion_claim": False,
    }
    out = root / "reports/current-host-runner-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    args = p.parse_args()
    report = run(Path(args.root).resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
