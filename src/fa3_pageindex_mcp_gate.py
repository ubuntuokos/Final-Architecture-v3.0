#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-PAGEINDEX-MCP-001"
CONTRACT_ID = "FA3-PAGEINDEX-MCP-CONTRACTS-001"
GATE_ID = "FA3-GATE-PAGEINDEX-MCP-001"
AUTHORITY_ID = "FA3-AUTH-MCP-GATEWAY-001"
UPSTREAM_COMMIT = "bda946b4b6fffaaf6926aa8809bc62e0098f30e8"
MCPB_SHA256 = "972705b6991a5291112db368fafccf2ce89926a8a0318601cba89bff4adc5de2"
REQUIRED_TOOLS = {"process_document", "get_document", "get_document_structure", "get_page_content"}
RECEIPT = Path("evidence/receipts/pageindex-mcp-current-host.json")


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def validate_static(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    provider = loadj(root / "canonical/providers/FA3-PROVIDER-PAGEINDEX-MCP-001.json")
    contract = loadj(root / "canonical/contracts/FA3-PAGEINDEX-MCP-CONTRACTS-001.json")
    reference = loadj(root / "canonical/references/FA3-PAGEINDEX-MCP-UPSTREAM-REFERENCE-2026-09-18.json")
    enforcement = loadj(root / "canonical/pageindex-mcp-enforcement.json")
    registry = loadj(root / "canonical/mcp-capability-registry.json")

    if provider.get("id") != PROVIDER_ID or provider.get("architectural_authority") is not False:
        findings.append(finding("PAGEINDEX-STATIC-001", "Provider identity/authority contract mismatch"))
    if provider.get("parent_authority") != AUTHORITY_ID or provider.get("authority_delta") != 0:
        findings.append(finding("PAGEINDEX-STATIC-002", "PageIndex must not create or replace MCP authority"))
    if provider.get("new_capability") is not False or provider.get("capability_count_delta") != 0:
        findings.append(finding("PAGEINDEX-STATIC-003", "PageIndex must project existing capabilities only"))
    runtime = provider.get("runtime_projection", {})
    if runtime.get("upstream_release") != "v1.8.2" or runtime.get("upstream_commit") != UPSTREAM_COMMIT:
        findings.append(finding("PAGEINDEX-STATIC-004", "Upstream release/commit pin mismatch"))
    if runtime.get("mcpb_sha256") != MCPB_SHA256:
        findings.append(finding("PAGEINDEX-STATIC-005", "MCPB digest pin mismatch"))
    if contract.get("id") != CONTRACT_ID or contract.get("parent_authority") != AUTHORITY_ID:
        findings.append(finding("PAGEINDEX-STATIC-006", "Contract authority binding mismatch"))
    if set(contract.get("upstream_tool_allowlist", [])) != REQUIRED_TOOLS:
        findings.append(finding("PAGEINDEX-STATIC-007", "Strict upstream tool allowlist mismatch"))
    if enforcement.get("interactive_oauth_during_tool_invocation") != "DENY":
        findings.append(finding("PAGEINDEX-STATIC-008", "Interactive OAuth during invocation must be denied"))
    if enforcement.get("dynamic_remote_tool_passthrough") != "DENY":
        findings.append(finding("PAGEINDEX-STATIC-009", "Dynamic remote tool passthrough must be denied"))
    if reference.get("commit") != UPSTREAM_COMMIT or reference.get("mcpb_sha256") != MCPB_SHA256:
        findings.append(finding("PAGEINDEX-STATIC-010", "Upstream reference is not immutable-pinned"))
    cloud_ref = reference.get("cloud_contract_reference", {})
    remote_contract = contract.get("remote_contract", {})
    if (
        cloud_ref.get("commit") != "18eb5c9b3c31d305c022974aa194a7047950228b"
        or remote_contract.get("source_commit") != "18eb5c9b3c31d305c022974aa194a7047950228b"
        or remote_contract.get("runtime_tools_list_schema_must_match") is not True
    ):
        findings.append(finding("PAGEINDEX-STATIC-014", "Cloud MCP retrieval contract reference is not frozen"))
    if enforcement.get("production_execution") != "CLEAN_PINNED_SOURCE_BUILD_ONLY" or enforcement.get("floating_npx_execution") != "DENY":
        findings.append(finding("PAGEINDEX-STATIC-015", "Production supply-chain execution policy mismatch"))
    governance = provider.get("data_governance", {})
    if (
        governance.get("asset_egress_profile") != "FA3-ASSET-EGRESS-POLICY-001"
        or governance.get("asset_egress_capability") != "CAP-140"
        or governance.get("gateway_generated_egress_decision_required") is not True
        or governance.get("local_upload_requires_source_sha256") is not True
    ):
        findings.append(finding("PAGEINDEX-STATIC-016", "CAP-140 asset-egress governance binding mismatch"))
    if (
        enforcement.get("asset_egress_profile") != "FA3-ASSET-EGRESS-POLICY-001"
        or enforcement.get("asset_egress_capability") != "CAP-140"
        or enforcement.get("gateway_generated_egress_decision_required") is not True
        or enforcement.get("source_sha256_required") is not True
    ):
        findings.append(finding("PAGEINDEX-STATIC-017", "PageIndex cloud enforcement does not require gateway-issued CAP-140 decision"))

    bindings: dict[str, list[dict[str, Any]]] = {}
    for cap in registry.get("capabilities", []):
        if isinstance(cap, dict):
            bindings[cap.get("capability_id")] = [
                item for item in cap.get("providers", []) if isinstance(item, dict) and item.get("provider_id") == PROVIDER_ID
            ]
    for capability_id, adapter_id in (
        ("fa3.document.index", "fa3.adapter.pageindex.index"),
        ("fa3.document.retrieve", "fa3.adapter.pageindex.retrieve"),
    ):
        rows = bindings.get(capability_id, [])
        if len(rows) != 1 or rows[0].get("adapter_id") != adapter_id:
            findings.append(finding("PAGEINDEX-STATIC-011", "Capability binding missing or duplicated", capability_id=capability_id))
            continue
        if rows[0].get("state") == "CONNECTED":
            if not rows[0].get("evidence_ref"):
                findings.append(finding("PAGEINDEX-STATIC-012", "CONNECTED binding lacks E2E evidence", capability_id=capability_id))
        elif rows[0].get("state") != "PENDING_CURRENT_HOST":
            findings.append(finding("PAGEINDEX-STATIC-013", "Pre-E2E binding must remain PENDING_CURRENT_HOST", capability_id=capability_id))
    return findings


def validate_current_host(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if receipt.get("schema") != "fa3.pageindex-mcp.current-host-evidence.v1":
        findings.append(finding("PAGEINDEX-HOST-001", "Current-host receipt schema mismatch"))
    if receipt.get("provider_id") != PROVIDER_ID or receipt.get("gate_id") != GATE_ID:
        findings.append(finding("PAGEINDEX-HOST-002", "Current-host receipt binding mismatch"))
    if receipt.get("status") != "PASS":
        findings.append(finding("PAGEINDEX-HOST-003", "Authenticated PageIndex current-host E2E did not PASS"))
    if receipt.get("global_promotion_claim") is not False:
        findings.append(finding("PAGEINDEX-HOST-004", "Provider receipt may not claim global promotion"))
    probe = receipt.get("probe", {})
    if not isinstance(probe, dict) or not REQUIRED_TOOLS.issubset(set(probe.get("tools", []))):
        findings.append(finding("PAGEINDEX-HOST-005", "Authenticated tools/list lacks required allowlisted tools"))
    checks = receipt.get("checks", {})
    required_pass = {
        "GATEWAY_INDEX_INVOCATION", "GATEWAY_METADATA_RETRIEVAL", "GATEWAY_STRUCTURE_RETRIEVAL",
        "GATEWAY_PAGE_CONTENT_RETRIEVAL", "PROVIDER_ADAPTER_RECEIPTS", "SECRET_NON_DISCLOSURE",
        "AUTHORITY_NONREGRESSION", "ASSET_EGRESS_DECISION",
    }
    for name in sorted(required_pass):
        if checks.get(name) != "PASS":
            findings.append(finding("PAGEINDEX-HOST-006", "Required PageIndex current-host check missing", check=name))
    required_deny = {"DIRECT_PROVIDER_BYPASS", "MISSING_POLICY", "MISSING_UPLOAD_APPROVAL", "OUT_OF_SCOPE_LOCAL_PATH", "UNKNOWN_CAPABILITY"}
    for name in sorted(required_deny):
        if checks.get(name) != "DENY":
            findings.append(finding("PAGEINDEX-HOST-007", "Required PageIndex negative check missing", check=name))
    return findings


def gate(root: Path, *, current_host: bool = False) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    try:
        findings.extend(validate_static(root))
    except Exception as exc:
        findings.append(finding("PAGEINDEX-STATIC-000", "Static PageIndex materialization unreadable", error=repr(exc)))
    evidence_refs = [
        "canonical/providers/FA3-PROVIDER-PAGEINDEX-MCP-001.json",
        "canonical/contracts/FA3-PAGEINDEX-MCP-CONTRACTS-001.json",
        "canonical/references/FA3-PAGEINDEX-MCP-UPSTREAM-REFERENCE-2026-09-18.json",
        "canonical/mcp-capability-registry.json",
    ]
    if current_host and not findings:
        evidence_refs.append(str(RECEIPT))
        try:
            findings.extend(validate_current_host(loadj(root / RECEIPT)))
        except Exception as exc:
            findings.append(finding("PAGEINDEX-HOST-000", "Real authenticated PageIndex current-host receipt missing", error=repr(exc)))
    return {
        "schema_id": "FA3-ENFORCEMENT-RESULT-001", "schema_version": "1.0.0",
        "gate": {"id": GATE_ID, "mode": "CURRENT_HOST" if current_host else "STATIC"},
        "result": "PASS" if not findings else "BLOCKED", "findings": findings, "evidence_refs": evidence_refs,
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--current-host", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args()
    report = gate(Path(args.root), current_host=args.current_host)
    report_path = args.report or (
        "reports/pageindex-mcp-current-host-gate-report.json" if args.current_host else "reports/pageindex-mcp-gate-report.json"
    )
    path = Path(args.root) / report_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
