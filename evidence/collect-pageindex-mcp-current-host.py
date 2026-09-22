#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_mcp_gateway import Adapter, McpGateway
from fa3_pageindex_mcp_adapter import (
    INDEX_ADAPTER_ID,
    MCPB_SHA256,
    PROVIDER_ID,
    RETRIEVE_ADAPTER_ID,
    UPSTREAM_COMMIT,
    PageIndexAdapterConfig,
    PageIndexMcpAdapter,
    extract_json_text,
)


def policy(capability: str) -> dict[str, Any]:
    return {
        "authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
        "decision_id": "pageindex-current-host-policy",
        "capability_id": capability,
        "status": "ALLOW",
    }


def request(capability: str, arguments: dict[str, Any], *, approval: bool = False) -> dict[str, Any]:
    req: dict[str, Any] = {
        "actor_id": "fa3-current-host-e2e",
        "client_id": "fa3-pageindex-collector",
        "session_id": "pageindex-e2e",
        "capability_id": capability,
        "arguments": arguments,
        "policy_decision": policy(capability),
    }
    if approval:
        req["approval"] = {
            "status": "APPROVED",
            "approval_id": "pageindex-current-host-explicit-upload-approval",
            "capability_id": capability,
        }
    return req


def decoded_payload(receipt: dict[str, Any]) -> list[Any]:
    result = receipt.get("result", {})
    upstream = result.get("upstream_result", {}) if isinstance(result, dict) else {}
    return extract_json_text(upstream) if isinstance(upstream, dict) else []


def document_status(receipt: dict[str, Any]) -> str | None:
    def walk(value: Any) -> str | None:
        if isinstance(value, dict):
            status = value.get("status")
            if isinstance(status, str) and status.lower() in {"pending", "queued", "processing", "completed", "failed"}:
                return status.lower()
            for item in value.values():
                found = walk(item)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = walk(item)
                if found:
                    return found
        return None
    return walk(decoded_payload(receipt))


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real authenticated PageIndex MCP current-host E2E evidence")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--oauth-home", required=True)
    parser.add_argument("--sample-pdf", required=True)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--output", default="evidence/receipts/pageindex-mcp-current-host.json")
    args = parser.parse_args()

    source_root = Path(args.source_root).expanduser().resolve()
    oauth_home = Path(args.oauth_home).expanduser().resolve()
    pdf = Path(args.sample_pdf).expanduser().resolve()
    if pdf.parent == Path("/"):
        raise SystemExit("sample PDF must be inside a scoped directory, not filesystem root")

    config = PageIndexAdapterConfig(
        command=("node", str(source_root / "build" / "index.js")),
        oauth_home=oauth_home,
        source_root=source_root,
        allowed_roots=(pdf.parent,),
        allowed_remote_hosts=(),
        timeout_seconds=args.timeout,
        strict_supply_chain=True,
        source_commit=UPSTREAM_COMMIT,
        release_sha256=MCPB_SHA256,
    )
    impl = PageIndexMcpAdapter(config)
    probe = impl.probe()

    registry = json.loads((ROOT / "canonical/mcp-capability-registry.json").read_text(encoding="utf-8"))
    for cap in registry["capabilities"]:
        if cap["capability_id"] in {"fa3.document.index", "fa3.document.retrieve"}:
            for binding in cap.get("providers", []):
                if binding.get("provider_id") == PROVIDER_ID:
                    binding["state"] = "CONNECTED"
                    binding["evidence_ref"] = "RUNTIME_PROVISIONAL_CURRENT_INVOCATION"

    gw = McpGateway(registry)
    gw.register_adapter(Adapter(INDEX_ADAPTER_ID, PROVIDER_ID, impl.index))
    gw.register_adapter(Adapter(RETRIEVE_ADAPTER_ID, PROVIDER_ID, impl.retrieve))
    checks: dict[str, str] = {}

    unknown = gw.invoke(request("fa3.unknown", {}))
    checks["UNKNOWN_CAPABILITY"] = "DENY" if unknown.get("reason_code") == "UNKNOWN_CAPABILITY" else "FAIL"

    missing_policy = request("fa3.document.retrieve", {"operation": "metadata", "document_name": pdf.name})
    missing_policy.pop("policy_decision")
    denied = gw.invoke(missing_policy)
    checks["MISSING_POLICY"] = "DENY" if denied.get("reason_code") == "MISSING_POLICY_DECISION" else "FAIL"

    no_approval = gw.invoke(request("fa3.document.index", {"source": str(pdf)}))
    checks["MISSING_UPLOAD_APPROVAL"] = "DENY" if no_approval.get("reason_code") == "MISSING_REQUIRED_APPROVAL" else "FAIL"

    outside = pdf.parent.parent / "__fa3_pageindex_outside__" / "outside.pdf"
    path_escape = gw.invoke(request("fa3.document.index", {"source": str(outside)}, approval=True))
    checks["OUT_OF_SCOPE_LOCAL_PATH"] = "DENY" if path_escape.get("reason_code") == "PAGEINDEX_LOCAL_SCOPE_DENIED" else "FAIL"
    checks["DIRECT_PROVIDER_BYPASS"] = "DENY" if registry.get("direct_agent_provider_bypass") == "DENY" else "FAIL"

    index_receipt = gw.invoke(request("fa3.document.index", {"source": str(pdf)}, approval=True))
    if index_receipt.get("result_status") != "success":
        raise SystemExit("real PageIndex process_document invocation failed")
    checks["GATEWAY_INDEX_INVOCATION"] = "PASS"
    checks["ASSET_EGRESS_DECISION"] = "PASS" if str(index_receipt.get("asset_egress_decision_id", "")).startswith("FA3-EGRESS-") else "FAIL"
    indexed_result = index_receipt.get("result", {})
    document_name = indexed_result.get("document_name") if isinstance(indexed_result, dict) else None
    if not isinstance(document_name, str) or not document_name:
        raise SystemExit("PageIndex adapter did not preserve canonical document_name")

    metadata_receipt = gw.invoke(request(
        "fa3.document.retrieve",
        {"operation": "metadata", "document_name": document_name, "wait_for_completion": True},
    ))
    if metadata_receipt.get("result_status") != "success" or document_status(metadata_receipt) != "completed":
        raise SystemExit("PageIndex document did not reach completed state")
    checks["GATEWAY_METADATA_RETRIEVAL"] = "PASS"

    structure_receipt = gw.invoke(request(
        "fa3.document.retrieve",
        {"operation": "structure", "document_name": document_name, "wait_for_completion": True},
    ))
    if structure_receipt.get("result_status") != "success":
        raise SystemExit("PageIndex document structure retrieval failed")
    checks["GATEWAY_STRUCTURE_RETRIEVAL"] = "PASS"

    pages_receipt = gw.invoke(request(
        "fa3.document.retrieve",
        {"operation": "pages", "document_name": document_name, "pages": "1", "wait_for_completion": True},
    ))
    if pages_receipt.get("result_status") != "success":
        raise SystemExit("PageIndex page-content retrieval failed")
    checks["GATEWAY_PAGE_CONTENT_RETRIEVAL"] = "PASS"

    gateway_receipts = [index_receipt, metadata_receipt, structure_receipt, pages_receipt]
    checks["PROVIDER_ADAPTER_RECEIPTS"] = (
        "PASS"
        if all(
            x.get("provider_id") == PROVIDER_ID and str(x.get("adapter_id", "")).startswith("fa3.adapter.pageindex.")
            for x in gateway_receipts
        )
        else "FAIL"
    )
    serialized = json.dumps(gateway_receipts, ensure_ascii=False).lower()
    checks["SECRET_NON_DISCLOSURE"] = (
        "PASS"
        if all(marker not in serialized for marker in ("access_token", "authorization", "oauth-tokens.json"))
        else "FAIL"
    )
    checks["AUTHORITY_NONREGRESSION"] = (
        "PASS" if registry.get("authority") == "FA3-AUTH-MCP-GATEWAY-001" else "FAIL"
    )

    receipt = {
        "schema": "fa3.pageindex-mcp.current-host-evidence.v1",
        "provider_id": PROVIDER_ID,
        "gate_id": "FA3-GATE-PAGEINDEX-MCP-001",
        "status": "PASS" if all(v in {"PASS", "DENY"} for v in checks.values()) else "FAIL",
        "timestamp_epoch": int(time.time()),
        "source_proof": {
            "upstream_commit": UPSTREAM_COMMIT,
            "source_root": str(source_root),
            "build_entrypoint_sha256": hashlib.sha256((source_root / "build" / "index.js").read_bytes()).hexdigest(),
        },
        "probe": probe,
        "document": {
            "sample_pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "document_name_sha256": hashlib.sha256(document_name.encode()).hexdigest(),
        },
        "checks": checks,
        "gateway_health": gw.health(),
        "gateway_readiness": gw.readiness(),
        "global_promotion_claim": False,
    }
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    impl.close()
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
