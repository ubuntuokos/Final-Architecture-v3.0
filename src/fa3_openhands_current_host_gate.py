#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-OPENHANDS-001"
RUNTIME_ID = "FA3-OPENHANDS-RUNTIME-CONFORMANCE-001"
GATE_ID = "FA3-GATE-OPENHANDS-CURRENT-HOST-001"
PINNED_COMMIT = "a9e0a8a1aab2164b46bae00a18157a343aaa94c9"
PINNED_TREE = "342a369f498b826cf51d1644bcbef8d503af7628"
VERSION = "1.44.1"
COMPONENTS = {
    "openhands-sdk",
    "openhands-agent-server",
    "openhands-tools",
    "openhands-workspace",
}
ISOLATED_LEVEL = "CURRENT_HOST_OPENHANDS_ISOLATED_RUNTIME_PASS"
PRODUCTION_LEVEL = "CURRENT_HOST_OPENHANDS_PRODUCTION_E2E_PASS"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_receipt(receipt: dict[str, Any], *, require_production: bool) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str, **extra: Any) -> None:
        findings.append({"code": code, "severity": "P0", "message": message, **extra})

    expected_mode = "production" if require_production else "isolated"
    expected_level = PRODUCTION_LEVEL if require_production else ISOLATED_LEVEL
    if (
        receipt.get("schema") != "fa3.openhands-current-host-receipt.v1"
        or receipt.get("provider_id") != PROVIDER_ID
        or receipt.get("runtime_id") != RUNTIME_ID
        or receipt.get("status") != "PASS"
        or receipt.get("mode") != expected_mode
        or receipt.get("evidence_level") != expected_level
    ):
        fail("OPENHANDS-HOST-001", "receipt identity, mode, status or evidence level mismatch")

    source = receipt.get("source", {})
    if (
        source.get("repository") != "OpenHands/software-agent-sdk"
        or source.get("commit") != PINNED_COMMIT
        or source.get("tree") != PINNED_TREE
        or source.get("dirty") is not False
    ):
        fail("OPENHANDS-HOST-002", "immutable OpenHands source identity mismatch")

    runtime = receipt.get("runtime", {})
    versions = runtime.get("component_versions", {})
    if (
        runtime.get("python_major_minor") != "3.12"
        or runtime.get("packaging") != "pip-venv"
        or runtime.get("conda_or_mamba_active") is not False
        or set(versions) != COMPONENTS
        or any(v != VERSION for v in versions.values())
        or not _digest(runtime.get("pip_freeze_sha256"))
        or not _digest(runtime.get("venv_python_sha256"))
    ):
        fail("OPENHANDS-HOST-003", "Python/venv/component tuple evidence mismatch")

    isolation = receipt.get("isolation", {})
    required_isolation = {
        "bubblewrap": True,
        "unshare_all": True,
        "general_network_egress_denied": True,
        "host_home_not_mounted": True,
        "repository_read_only": True,
        "delegated_workspace_write_only": True,
        "root_filesystem_not_bind_mounted": True,
    }
    if any(isolation.get(k) is not v for k, v in required_isolation.items()):
        fail("OPENHANDS-HOST-004", "bubblewrap isolation evidence incomplete", isolation=isolation)
    if not _digest(isolation.get("bwrap_binary_sha256")):
        fail("OPENHANDS-HOST-005", "bubblewrap binary identity missing")

    worker = receipt.get("worker", {})
    surface = worker.get("tool_surface", {})
    if not (
        worker.get("status") == "PASS"
        and worker.get("mode") == expected_mode
        and surface.get("registered_tools") == ["fa3_delegated_write"]
        and surface.get("provider_native_execute_tool_used") is False
        and surface.get("provider_native_mcp_enabled") is False
        and surface.get("terminal_tool_enabled") is False
        and surface.get("file_editor_tool_enabled") is False
    ):
        fail("OPENHANDS-HOST-006", "OpenHands worker/tool surface boundary evidence mismatch")

    mutation = receipt.get("mutation", {})
    if not (
        mutation.get("worker_commit_created") is False
        and mutation.get("changed_paths") == [mutation.get("authorized_relative_path")]
        and _digest(mutation.get("before_sha256"))
        and _digest(mutation.get("after_sha256"))
        and mutation.get("before_sha256") != mutation.get("after_sha256")
        and mutation.get("after_sha256") == worker.get("target_sha256")
    ):
        fail("OPENHANDS-HOST-007", "exact mutation scope / no-commit evidence mismatch")

    negatives = receipt.get("negative_tests", {})
    required_negatives = {
        "path_traversal_denied",
        "wrong_path_authorization_denied",
        "expired_authorization_denied",
        "provider_as_authority_denied",
        "command_secret_value_absent",
    }
    if set(negatives) != required_negatives or not all(negatives.values()):
        fail("OPENHANDS-HOST-008", "negative authorization/scope tests incomplete")

    persistence = worker.get("persistence", {})
    resume = worker.get("resume", {})
    lineage = worker.get("event_lineage", {})
    if not (
        persistence.get("raw_router_secret_persisted") is False
        and resume.get("status") == "PASS"
        and resume.get("same_conversation_id") is True
        and resume.get("prior_persistence_observed") is True
        and resume.get("new_events_after_reopen") is True
        and int(lineage.get("first_run_count", 0)) > 0
        and int(lineage.get("resume_count", 0)) > 0
        and _digest(lineage.get("first_run_chain_head"))
        and _digest(lineage.get("resume_chain_head"))
    ):
        fail("OPENHANDS-HOST-009", "persistence/resume/event-lineage evidence incomplete")

    cleanup = receipt.get("cleanup", {})
    if not (
        cleanup.get("workspace_removed") is True
        and cleanup.get("router_bridge_stopped") is True
        and cleanup.get("temporary_secret_copy_removed") is True
    ):
        fail("OPENHANDS-HOST-010", "cleanup evidence incomplete")

    model = worker.get("model_route", {})
    auth = receipt.get("authorization", {})
    if require_production:
        if not (
            model.get("class") == "CENTRAL_LITELLM_UNIX_BRIDGE"
            and model.get("fixture_only") is False
            and int(model.get("production_response_count", 0)) >= 2
            and all(_digest(x) for x in model.get("production_response_sha256", []))
            and auth.get("class") == "EXTERNAL_CANONICAL_TOOL_AUTHORIZATION"
            and auth.get("issuer_id") == "FA3-AUTH-MCP-GATEWAY-001"
            and auth.get("single_use") is True
            and receipt.get("production_admission_claim") is True
        ):
            fail("OPENHANDS-HOST-011", "production model-route/tool-authorization evidence incomplete")
    else:
        if not (
            model.get("class") == "OPENHANDS_TEST_LLM_FIXTURE"
            and model.get("fixture_only") is True
            and int(model.get("production_response_count", 0)) == 0
            and auth.get("class") == "FIXTURE_NON_PRODUCTION"
            and receipt.get("production_admission_claim") is False
        ):
            fail("OPENHANDS-HOST-012", "isolated fixture evidence attempted to claim production semantics")

    host = receipt.get("host", {})
    if not (
        host.get("system") == "Linux"
        and host.get("machine") in {"x86_64", "amd64"}
        and host.get("current_host_marker") is True
        and host.get("github_hosted_runner") is False
    ):
        fail("OPENHANDS-HOST-013", "receipt is not attributable to the FA3 current-host execution context")

    if not (
        receipt.get("capability_count_after") == 143
        and receipt.get("new_capabilities") == 0
        and receipt.get("new_architectural_authorities") == 0
        and receipt.get("global_promotion_claim") is False
    ):
        fail("OPENHANDS-HOST-014", "capability/authority/global-promotion invariant drift")
    return findings


def gate(root: Path, *, require_production: bool) -> dict[str, Any]:
    receipt_name = (
        "evidence/receipts/openhands-current-host.json"
        if require_production
        else "evidence/receipts/openhands-current-host-isolated.json"
    )
    path = root / receipt_name
    try:
        receipt = _load(path)
        findings = validate_receipt(receipt, require_production=require_production)
    except Exception as exc:
        receipt = {}
        findings = [{
            "code": "OPENHANDS-HOST-000",
            "severity": "P0",
            "message": "OpenHands current-host receipt missing or unreadable",
            "error": repr(exc),
        }]
    report = {
        "schema": "fa3.openhands-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "runtime_id": RUNTIME_ID,
        "mode": "production" if require_production else "isolated",
        "result": "PASS" if not findings else "FAIL",
        "evidence_level": receipt.get("evidence_level"),
        "findings": findings,
        "promotion_effect": (
            "OPENHANDS_PROVIDER_CURRENT_HOST_PRODUCTION_ADMISSION_ELIGIBLE_GLOBAL_PROMOTION_UNCHANGED"
            if require_production
            else "ISOLATED_RUNTIME_EVIDENCE_ONLY_NO_PRODUCTION_PROMOTION"
        ),
    }
    _write(root / "reports/openhands-current-host-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate FA3 OpenHands current-host evidence")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--mode", choices=("isolated", "production"), default="production")
    args = ap.parse_args()
    report = gate(Path(args.root).resolve(), require_production=args.mode == "production")
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
