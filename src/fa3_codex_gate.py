#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_codex_adapter import (
    ADAPTER_ID,
    ARCHIVE_SHA256,
    CODEX_VERSION,
    CONFIG_OVERRIDES,
    FORBIDDEN_FLAGS,
    PROVIDER_ID,
    build_codex_exec_command,
    parse_codex_jsonl,
    run_ci_adapter_contract_e2e,
    safe_codex_environment,
)

GATE_ID = "FA3-CODEX-GATESET-001"
CONTRACT_ID = "FA3-CODEX-ADAPTER-CONTRACTS-001"
ADMISSION_ID = "FA3-CODEX-RUNTIME-ADMISSION-001"
DECISION_ID = "FA3-DEC-CODEX-ADAPTER-2026-08-31"
REFERENCE_ID = "FA3-CODEX-UPSTREAM-REFERENCE-2026-08-31"
CAPABILITY_COUNT = 143

P0_RULES = [
    "CODEX_IMMUTABLE_RELEASE_AND_ARCHIVE_PIN",
    "CODEX_PROVIDER_NOT_AUTHORITY",
    "CODEX_ADAPTER_BEHIND_AGENT_EXEC_AND_COORDINATION",
    "CODEX_HEADLESS_APPROVAL_NEVER",
    "CODEX_WORKSPACE_WRITE_SANDBOX_REQUIRED",
    "CODEX_DANGEROUS_BYPASS_FORBIDDEN",
    "CODEX_AUTO_REVIEW_FORBIDDEN_V0_1",
    "CODEX_USER_CONFIG_AND_RULES_IGNORED",
    "CODEX_EPHEMERAL_AND_STRICT_CONFIG_REQUIRED",
    "CODEX_WEB_SEARCH_DISABLED_V0_1",
    "CODEX_MCP_DISABLED_V0_1",
    "CODEX_NESTED_MULTI_AGENT_DISABLED_V0_1",
    "CODEX_PLUGINS_DISABLED_V0_1",
    "CODEX_LOGIN_SHELL_DISABLED",
    "CODEX_CHATGPT_LOGIN_ONLY_V0_1",
    "CODEX_SECRET_ENV_PASSTHROUGH_FORBIDDEN",
    "CODEX_EXPLICIT_MUTATION_SCOPE_REQUIRED",
    "CODEX_WORKER_DIRECT_COMMIT_FORBIDDEN",
    "CODEX_EVENT_SURFACE_FAIL_CLOSED",
    "CODEX_CURRENT_HOST_PASS_CANNOT_BE_FABRICATED_BY_CI",
]


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-CODEX-001.json",
        "reference": root / "canonical/references/FA3-CODEX-UPSTREAM-REFERENCE-2026-08-31.json",
        "contracts": root / "canonical/contracts/FA3-CODEX-ADAPTER-CONTRACTS-001.json",
        "admission": root / "canonical/codex-runtime-admission.json",
        "enforcement": root / "canonical/codex-enforcement.json",
        "decision": root / "canonical/decisions/FA3-DEC-CODEX-ADAPTER-2026-08-31.json",
        "evidence": root / "evidence/reference/codex-adapter-ci-2026-08-31.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    for name, path in paths.items():
        if not path.is_file():
            findings.append(finding("CODEX-REF-001", f"missing {name} artifact"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    provider = loadj(paths["provider"])
    reference = loadj(paths["reference"])
    contracts = loadj(paths["contracts"])
    admission = loadj(paths["admission"])
    enforcement = loadj(paths["enforcement"])
    decision = loadj(paths["decision"])
    evidence = loadj(paths["evidence"])
    policy = loadj(paths["policy"])

    pin = provider.get("immutable_runtime_pin", {})
    profile = provider.get("production_execution_profile", {})
    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("parent_profile") == "FA3-AGENT-EXEC-001"
        and provider.get("coordination_contract") == "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001"
        and provider.get("adapter_contract") == CONTRACT_ID
        and provider.get("adapter_id") == ADAPTER_ID
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("runtime_activation_status") == "NOT_ADMITTED_PENDING_CURRENT_HOST"
        and pin.get("version") == CODEX_VERSION
        and pin.get("artifact_sha256") == ARCHIVE_SHA256
        and profile.get("sandbox") == "workspace-write"
        and profile.get("approval_policy") == "NEVER_HEADLESS"
        and profile.get("dangerous_bypass") == "FORBIDDEN"
        and profile.get("auto_review") == "FORBIDDEN_V0_1"
        and profile.get("mcp") == "DISABLED_V0_1"
        and profile.get("nested_codex_multi_agent") == "DISABLED_V0_1"
        and profile.get("web_search") == "DISABLED"
    ):
        findings.append(finding("CODEX-REF-002", "Codex provider identity/boundary/runtime pin drift"))

    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("license") == "Apache-2.0"
        and reference.get("release", {}).get("version") == CODEX_VERSION
        and reference.get("release", {}).get("commit") == "78c290807ce710180111df227df3b7a4fe845452"
        and reference.get("linux_x86_64_pin", {}).get("sha256") == ARCHIVE_SHA256
        and reference.get("production_admission_requires") == "FA3-CODEX-CURRENT-HOST-PASS"
    ):
        findings.append(finding("CODEX-REF-003", "Codex upstream reference pin drift"))

    if not (
        contracts.get("id") == CONTRACT_ID
        and contracts.get("parent_profile") == "FA3-AGENT-EXEC-001"
        and contracts.get("parent_coordination_contract") == "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001"
        and contracts.get("provider_id") == PROVIDER_ID
        and contracts.get("new_capability") is False
        and contracts.get("new_architectural_authority") is False
        and contracts.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append(finding("CODEX-REF-004", "Codex adapter contract family drift"))

    if not (
        admission.get("id") == ADMISSION_ID
        and admission.get("provider_id") == PROVIDER_ID
        and admission.get("status") == "NOT_ADMITTED"
        and admission.get("fail_closed") is True
        and admission.get("current_host_evidence_required") is True
        and admission.get("runtime_required_for_global_promotion_when_disabled") is False
    ):
        findings.append(finding("CODEX-REF-005", "Codex runtime admission drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("provider_id") == PROVIDER_ID
        and enforcement.get("contract_id") == CONTRACT_ID
        and enforcement.get("admission_id") == ADMISSION_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("mandatory_rule_count") == len(P0_RULES)
        and enforcement.get("p0_invariants") == P0_RULES
    ):
        findings.append(finding("CODEX-REF-006", "Codex enforcement rule set drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append(finding("CODEX-REF-007", "Codex canonical decision drift"))

    if not (
        evidence.get("provider_id") == PROVIDER_ID
        and evidence.get("gate_id") == GATE_ID
        and evidence.get("status") == "PASS"
        and evidence.get("current_host_production_evidence") is False
        and evidence.get("archive_sha256") == ARCHIVE_SHA256
        and evidence.get("promotion_effect") == "NONE"
    ):
        findings.append(finding("CODEX-REF-008", "Codex reference CI evidence drift"))

    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(finding("CODEX-REF-009", "Codex gate missing from global mandatory reference gates"))
    if policy.get("codex_provider_id") != PROVIDER_ID:
        findings.append(finding("CODEX-REF-010", "Global Codex provider binding drift"))
    if policy.get("codex_mandatory_p0_rules") != P0_RULES:
        findings.append(finding("CODEX-REF-011", "Global Codex P0 rule set drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def regression_check(root: Path) -> dict[str, Any]:
    cases: dict[str, bool] = {}
    fake_binary = root / "bin/fake-codex-for-regression"
    workspace = root
    last = root / "reports/fake-last-message.txt"
    command = build_codex_exec_command(fake_binary, workspace, last)
    tokens = set(command)
    cases["forbidden_flags_absent"] = not bool(tokens & FORBIDDEN_FLAGS)
    cases["workspace_write_present"] = "workspace-write" in tokens and "--sandbox" in tokens
    cases["prompt_via_stdin"] = command[-1] == "-"
    cases["all_security_overrides_present"] = all(override in command for override in CONFIG_OVERRIDES)
    cases["secret_env_stripped"] = "OPENAI_API_KEY" not in safe_codex_environment(
        {"PATH": "/bin", "HOME": "/tmp", "OPENAI_API_KEY": "secret", "GITHUB_TOKEN": "secret"}
    )
    good_jsonl = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "t"}),
            json.dumps({"type": "turn.started"}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "id": "1",
                        "type": "file_change",
                        "changes": [{"path": "x", "kind": "update"}],
                        "status": "completed",
                    },
                }
            ),
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 1,
                        "cached_input_tokens": 0,
                        "cache_write_input_tokens": 0,
                        "output_tokens": 1,
                        "reasoning_output_tokens": 0,
                    },
                }
            ),
        ]
    )
    cases["safe_event_stream_admitted"] = parse_codex_jsonl(good_jsonl)["forbidden_surface_observed"] is False
    for item_type in ("mcp_tool_call", "collab_tool_call", "web_search"):
        bad = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "t"}),
                json.dumps({"type": "item.completed", "item": {"id": "x", "type": item_type}}),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 0,
                            "cached_input_tokens": 0,
                            "cache_write_input_tokens": 0,
                            "output_tokens": 0,
                            "reasoning_output_tokens": 0,
                        },
                    }
                ),
            ]
        )
        try:
            parse_codex_jsonl(bad)
            cases[f"{item_type}_denied"] = False
        except Exception:
            cases[f"{item_type}_denied"] = True
    ci = run_ci_adapter_contract_e2e()
    cases["adapter_ci_contract_e2e_pass"] = (
        ci.get("result") == "PASS"
        and ci.get("current_host_production_claim") is False
        and ci.get("synthetic_provider_fixture") is True
    )
    return {
        "schema": "fa3.codex-regression-report.v1",
        "result": "PASS" if all(cases.values()) else "FAIL",
        "passed": sum(cases.values()),
        "total": len(cases),
        "cases": cases,
        "ci_adapter_e2e": {
            "result": ci.get("result"),
            "status": ci.get("status"),
            "current_host_production_claim": ci.get("current_host_production_claim"),
            "worker_count": ci.get("coordination", {}).get("worker_count"),
        },
    }


def validate_current_host_receipt(root: Path) -> dict[str, Any]:
    receipt_path = root / "evidence/receipts/codex-current-host.json"
    findings: list[dict[str, Any]] = []
    if not receipt_path.is_file():
        return {
            "result": "FAIL",
            "findings": [finding("CODEX-HOST-001", "real Codex current-host receipt is missing")],
        }
    receipt = loadj(receipt_path)
    supply = receipt.get("supply_chain", {})
    runtime = receipt.get("runtime", {})
    auth = receipt.get("authentication", {})
    controls = receipt.get("execution_controls", {})
    e2e = receipt.get("production_e2e", {})
    if not (
        receipt.get("schema") == "fa3.codex-current-host-receipt.v1"
        and receipt.get("provider_id") == PROVIDER_ID
        and receipt.get("adapter_id") == ADAPTER_ID
        and receipt.get("status") == "PASS"
        and receipt.get("evidence_level") == "CURRENT_HOST_PRODUCTION_E2E_PASS"
        and receipt.get("collector_mode") == "REAL_CODEX_CLI_CURRENT_HOST"
        and receipt.get("synthetic") is False
    ):
        findings.append(finding("CODEX-HOST-002", "Codex current-host receipt identity/evidence-level mismatch"))
    if not (
        supply.get("archive_sha256") == ARCHIVE_SHA256
        and supply.get("archive_integrity") == "PASS"
        and supply.get("installed_binary_matches_pinned_archive") is True
        and runtime.get("version") == CODEX_VERSION
    ):
        findings.append(finding("CODEX-HOST-003", "Codex current-host supply-chain/runtime identity mismatch"))
    if not (
        auth.get("mode") == "CHATGPT"
        and auth.get("credential_material_captured") is False
        and auth.get("api_key_env_passthrough") is False
    ):
        findings.append(finding("CODEX-HOST-004", "Codex current-host authentication boundary mismatch"))
    required_controls = {
        "sandbox": "workspace-write",
        "approval_policy": "never",
        "ignore_user_config": True,
        "ignore_rules": True,
        "ephemeral": True,
        "strict_config": True,
        "web_search": False,
        "mcp": False,
        "nested_multi_agent": False,
        "plugins": False,
        "login_shell": False,
        "auto_review": False,
        "dangerous_bypass": False,
        "secret_env_passthrough": False,
    }
    if any(controls.get(key) != value for key, value in required_controls.items()):
        findings.append(finding("CODEX-HOST-005", "Codex current-host execution controls weakened"))
    if not (
        e2e.get("worker_count", 0) >= 2
        and e2e.get("integration_author") == "FA3 Integration"
        and e2e.get("worker_heads_unchanged") is True
        and e2e.get("forbidden_provider_surface_observed") is False
        and e2e.get("exact_mutation_scope") is True
        and e2e.get("cleanup", {}).get("live_processes") == 0
        and e2e.get("cleanup", {}).get("worktrees") == 0
        and e2e.get("cleanup", {}).get("active_leases") == 0
        and e2e.get("cleanup", {}).get("pending_messages") == 0
    ):
        findings.append(finding("CODEX-HOST-006", "Codex real production coordination E2E invariant mismatch"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings, "receipt": receipt}


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    regressions = regression_check(root)
    ok = reference["result"] == "PASS" and regressions["result"] == "PASS"
    report = {
        "schema": "fa3.codex-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "adapter_id": ADAPTER_ID,
        "result": "PASS" if ok else "FAIL",
        "reference": reference,
        "regressions": regressions,
        "current_host_production_state": "PENDING_SEPARATE_REAL_CURRENT_HOST_RECEIPT",
        "promotion_effect": "NONE_WHILE_DISABLED_OR_CURRENT_HOST_PENDING",
    }
    writej(root / "reports/codex-gate-report.json", report)
    return report


def current_host_gate(root: Path) -> dict[str, Any]:
    static = gate(root)
    host = validate_current_host_receipt(root)
    ok = static["result"] == "PASS" and host["result"] == "PASS"
    report = {
        "schema": "fa3.codex-current-host-gate-report.v1",
        "provider_id": PROVIDER_ID,
        "adapter_id": ADAPTER_ID,
        "result": "PASS" if ok else "FAIL",
        "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS" if ok else "PENDING_OR_FAIL",
        "static_gate": static["result"],
        "current_host_receipt": host["result"],
        "findings": host.get("findings", []),
    }
    writej(root / "reports/codex-current-host-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--current-host", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    report = current_host_gate(root) if args.current_host else gate(root)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
