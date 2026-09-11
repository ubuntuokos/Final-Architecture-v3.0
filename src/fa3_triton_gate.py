#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-TRITON-001"
CONTRACT_ID = "FA3-TRITON-INFERENCE-SERVER-CONTRACTS-001"
DECISION_ID = "FA3-DEC-TRITON-2026-09-11"
GATE_ID = "FA3-GATE-TRITON-001"
PARENT_GATE_ID = "FA3-INFERENCE-PORTABILITY-GATESET-001"
CAPABILITY_COUNT = 143
EXPECTED_RULES = 17


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "P0", "message": message}


def _report(findings: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema": "fa3.triton-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "result": "PASS" if not findings else "FAIL",
        "capability_count": CAPABILITY_COUNT,
        "current_host_production_claim": False,
        "findings": findings,
    }


def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-TRITON-001.json",
        "contract": root / "canonical/contracts/FA3-TRITON-INFERENCE-SERVER-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-TRITON-2026-09-11.json",
        "enforcement": root / "canonical/triton-inference-server-enforcement.json",
        "parent": root / "canonical/inference-portability-enforcement.json",
        "launcher": root / "deployment/triton/fa3-triton-start",
        "installer": root / "deployment/triton/install-fa3-triton",
        "service": root / "deployment/triton/fa3-triton.service",
        "rollback": root / "deployment/triton/rollback-fa3-triton",
    }
    for name, path in paths.items():
        if not path.exists():
            findings.append(_finding("TRITON-REF-001", f"missing required artifact: {name}"))
    if findings:
        return _report(findings)

    provider = _load(paths["provider"])
    contract = _load(paths["contract"])
    decision = _load(paths["decision"])
    enforcement = _load(paths["enforcement"])
    parent = _load(paths["parent"])
    launcher = paths["launcher"].read_text(encoding="utf-8")
    installer = paths["installer"].read_text(encoding="utf-8")
    service = paths["service"].read_text(encoding="utf-8")

    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("parent_profile") == "FA3-INFERENCE-PORTABILITY-001"
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("requirement") == "MUST-IF-SELECTED"
        and provider.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT"
    ):
        findings.append(_finding("TRITON-REF-002", "provider authority/capability/classification invariant drift"))

    boundaries = provider.get("authority_boundaries", {})
    if PROVIDER_ID in boundaries.values():
        findings.append(_finding("TRITON-AUTH-001", "Triton assigned itself an authority boundary"))
    if provider.get("model_repository_semantics") != "NON_AUTHORITATIVE_IMMUTABLE_RUNTIME_PROJECTION":
        findings.append(_finding("TRITON-MODEL-001", "Triton repository is not constrained to a non-authoritative projection"))

    model_control = contract.get("model_control", {})
    if model_control.get("default_mode") != "none" or model_control.get("poll_mode") != "FORBIDDEN_PRODUCTION":
        findings.append(_finding("TRITON-CTRL-001", "model-control policy must default to none and forbid poll"))
    if "MODEL_MANAGER" not in str(model_control.get("explicit_mode", "")):
        findings.append(_finding("TRITON-CTRL-002", "explicit mode is not bound to Model Manager authorization"))

    placement = contract.get("device_placement", {})
    if placement.get("runtime_visibility") != "EXACT_HRB_GRANTED_SCOPE":
        findings.append(_finding("TRITON-HRB-001", "runtime visibility is not bound to exact HRB grant"))
    if placement.get("all_devices_wildcard") != "FORBIDDEN":
        findings.append(_finding("TRITON-HRB-002", "all-device wildcard is not forbidden"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("runtime_promotion") == "PENDING_REAL_CURRENT_HOST_E2E"
    ):
        findings.append(_finding("TRITON-DEC-001", "canonical decision invariant drift"))

    p0 = enforcement.get("p0_invariants", [])
    rules = enforcement.get("rules", [])
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("current_host_runtime_promotion_claim") is False
        and enforcement.get("mandatory_rule_count") == EXPECTED_RULES
        and len(p0) == EXPECTED_RULES
        and len(rules) == EXPECTED_RULES
        and len(set(p0)) == EXPECTED_RULES
        and all(r.get("priority") == "P0" and r.get("mandatory") is True for r in rules)
    ):
        findings.append(_finding("TRITON-GATE-001", "fail-closed P0 enforcement shape drift"))

    if parent.get("gate_id") != PARENT_GATE_ID or PROVIDER_ID not in parent.get("provider_ids", []):
        findings.append(_finding("TRITON-PARENT-001", "Triton is not bound into inference-portability provider set"))

    forbidden_launcher = ("--gpus all", "--gpus=all", "--model-control-mode=poll", ":latest")
    if any(token in launcher for token in forbidden_launcher):
        findings.append(_finding("TRITON-RUN-001", "launcher contains a forbidden wildcard/poll/latest runtime path"))
    required_launcher = (
        '--gpus "device=${FA3_TRITON_GPU_UUIDS}"',
        "FA3_TRITON_HRB_RECEIPT",
        "FA3_TRITON_PLACEMENT_RECEIPT",
        ":/models:ro",
        "127.0.0.1:8000:8000",
        "127.0.0.1:8001:8001",
        "127.0.0.1:8002:8002",
        "--disable-auto-complete-config",
        "--strict-readiness=true",
        "--exit-on-error=true",
        "--read-only",
        "--cap-drop=ALL",
        "no-new-privileges:true",
    )
    if any(token not in launcher for token in required_launcher):
        findings.append(_finding("TRITON-RUN-002", "launcher is missing required HRB/read-only/loopback/hardening controls"))

    forbidden_installer = ("apt-get ", "apt install", "nvidia-ctk runtime configure", "docker-ce")
    if any(token in installer for token in forbidden_installer):
        findings.append(_finding("TRITON-INSTALL-001", "provider materializer attempts to own host runtime installation"))
    required_installer = (
        "@sha256:[0-9a-f]{64}",
        "FA3_TRITON_HRB_RECEIPT",
        "FA3_TRITON_PLACEMENT_RECEIPT",
        "/var/lib/fa3/evidence/outbox",
        "/v2/health/ready",
        "docker pull",
    )
    if any(token not in installer for token in required_installer):
        findings.append(_finding("TRITON-INSTALL-002", "materializer is missing digest/receipt/readiness/evidence controls"))

    if not all(token in service for token in ("Restart=on-failure", "StartLimitBurst=3", "NoNewPrivileges=yes", "ProtectSystem=strict")):
        findings.append(_finding("TRITON-SYSTEMD-001", "systemd projection lacks bounded restart or hardening controls"))

    return _report(findings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/triton-gate-report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = gate(root)
    out = root / args.report
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
