from __future__ import annotations

import json
import stat
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_mcp_gateway import McpGateway
from fa3_pageindex_mcp_adapter import PageIndexAdapterConfig, build_adapters
from fa3_pageindex_mcp_gate import gate

FAKE_SERVER = r"""
import json, sys
tools = [
 {"name":"process_document","description":"x","inputSchema":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}},
 {"name":"get_document","description":"x","inputSchema":{"type":"object","properties":{"doc_name":{"type":"string"}},"required":["doc_name"]}},
 {"name":"get_document_structure","description":"x","inputSchema":{"type":"object","properties":{"doc_name":{"type":"string"}},"required":["doc_name"]}},
 {"name":"get_page_content","description":"x","inputSchema":{"type":"object","properties":{"doc_name":{"type":"string"},"pages":{"type":"string"}},"required":["doc_name","pages"]}}
]
for line in sys.stdin:
    try:
        msg=json.loads(line)
    except Exception:
        continue
    if "id" not in msg:
        continue
    method=msg.get("method")
    if method=="initialize":
        result={"protocolVersion":"2025-06-18","capabilities":{"tools":{}},"serverInfo":{"name":"fake-pageindex","version":"1.8.2"}}
    elif method=="tools/list":
        result={"tools":tools}
    elif method=="tools/call":
        name=msg["params"]["name"]
        args=msg["params"].get("arguments",{})
        if name=="process_document":
            result={"content":[{"type":"text","text":json.dumps({"doc_id":"doc-test","status":"submitted"})}],"isError":False}
        elif name=="get_document":
            result={"content":[{"type":"text","text":json.dumps({"name":args["doc_name"],"status":"completed","pageNum":1})}],"isError":False}
        elif name=="get_document_structure":
            result={"content":[{"type":"text","text":json.dumps({"doc_name":args["doc_name"],"structure":[{"title":"A","page":1}]})}],"isError":False}
        elif name=="get_page_content":
            result={"content":[{"type":"text","text":json.dumps({"doc_name":args["doc_name"],"pages":args["pages"],"content":[{"page":1,"text":"hello"}]})}],"isError":False}
        else:
            result={"content":[{"type":"text","text":"bad"}],"isError":True}
    else:
        result={}
    sys.stdout.write(json.dumps({"jsonrpc":"2.0","id":msg["id"],"result":result})+"\n")
    sys.stdout.flush()
"""


def connected_registry() -> dict:
    return {
        "schema": "fa3.mcp.capability-registry.v1",
        "profile": "FA3-MCP-CURRENT-HOST-001",
        "authority": "FA3-AUTH-MCP-GATEWAY-001",
        "policy_authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
        "status": "PENDING_CURRENT_HOST",
        "fail_closed": True,
        "automatic_provider_activation": False,
        "direct_agent_provider_bypass": "DENY",
        "capability_delta": 0,
        "authority_delta": 0,
        "capabilities": [
            {
                "capability_id": "fa3.document.index",
                "risk_class": "R1",
                "side_effects": ["filesystem-read", "filesystem-write"],
                "approval": "policy",
                "hrb_required": False,
                "providers": [{
                    "provider_id": "FA3-PROVIDER-PAGEINDEX-MCP-001",
                    "adapter_id": "fa3.adapter.pageindex.index",
                    "state": "CONNECTED",
                    "priority": 100,
                    "approval_override": "explicit",
                    "evidence_ref": "fixture",
                    "asset_egress_mode": "LOCAL_FILE_UPLOAD",
                    "asset_egress_profile": "FA3-ASSET-EGRESS-POLICY-001",
                    "asset_egress_destination_uri": "https://app.pageindex.ai/mcp",
                    "asset_egress_data_class": "USER_DOCUMENT",
                    "asset_egress_purpose": "PageIndex Cloud document indexing",
                }],
            },
            {
                "capability_id": "fa3.document.retrieve",
                "risk_class": "R0",
                "side_effects": ["filesystem-read"],
                "approval": "policy",
                "hrb_required": False,
                "providers": [{
                    "provider_id": "FA3-PROVIDER-PAGEINDEX-MCP-001",
                    "adapter_id": "fa3.adapter.pageindex.retrieve",
                    "state": "CONNECTED",
                    "priority": 100,
                    "evidence_ref": "fixture",
                }],
            },
        ],
    }


def base_request(capability: str, arguments: dict) -> dict:
    return {
        "actor_id": "actor",
        "client_id": "client",
        "session_id": "session",
        "capability_id": capability,
        "arguments": arguments,
        "policy_decision": {
            "authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
            "decision_id": "p1",
            "capability_id": capability,
            "status": "ALLOW",
        },
    }


class PageIndexMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        home = self.root / "home"
        token = home / ".pageindex-mcp" / "oauth-tokens.json"
        token.parent.mkdir(parents=True)
        token.write_text(json.dumps({"tokens": {"access_token": "fixture"}}), encoding="utf-8")
        token.chmod(stat.S_IRUSR | stat.S_IWUSR)
        server = self.root / "fake_pageindex.py"
        server.write_text(textwrap.dedent(FAKE_SERVER), encoding="utf-8")
        self.pdf = self.root / "sample.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nfixture")
        config = PageIndexAdapterConfig(
            command=(sys.executable, str(server)),
            oauth_home=home,
            allowed_roots=(self.root,),
            timeout_seconds=3,
            strict_supply_chain=False,
        )
        self.adapters = build_adapters(config)

    def tearDown(self) -> None:
        self.td.cleanup()

    def gateway(self) -> McpGateway:
        gw = McpGateway(connected_registry())
        for adapter in self.adapters:
            gw.register_adapter(adapter)
        return gw

    def test_static_gate_passes(self) -> None:
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)

    def test_cap140_governance_is_canonical_and_fail_closed(self) -> None:
        provider = json.loads((ROOT / "canonical/providers/FA3-PROVIDER-PAGEINDEX-MCP-001.json").read_text(encoding="utf-8"))
        enforcement = json.loads((ROOT / "canonical/pageindex-mcp-enforcement.json").read_text(encoding="utf-8"))
        gate_record = json.loads((ROOT / "canonical/FA3-GATE-PAGEINDEX-MCP-001.json").read_text(encoding="utf-8"))
        governance = provider["data_governance"]
        self.assertEqual("FA3-ASSET-EGRESS-POLICY-001", governance["asset_egress_profile"])
        self.assertEqual("CAP-140", governance["asset_egress_capability"])
        self.assertTrue(governance["gateway_generated_egress_decision_required"])
        self.assertTrue(governance["local_upload_requires_source_sha256"])
        self.assertEqual("FA3-ASSET-EGRESS-POLICY-001", enforcement["asset_egress_profile"])
        self.assertTrue(enforcement["gateway_generated_egress_decision_required"])
        self.assertIn("CAP_140_GATEWAY_ISSUED_ASSET_EGRESS_DECISION", gate_record["requirements"])

    def test_index_requires_provider_specific_explicit_approval(self) -> None:
        req = base_request("fa3.document.index", {"source": str(self.pdf)})
        denied = self.gateway().invoke(req)
        self.assertEqual("denied", denied["result_status"])
        self.assertEqual("MISSING_REQUIRED_APPROVAL", denied["reason_code"])
        req["approval"] = {"status": "APPROVED", "approval_id": "a1", "capability_id": "fa3.document.index"}
        passed = self.gateway().invoke(req)
        self.assertEqual("success", passed["result_status"], passed)
        self.assertEqual("doc-test", passed["result"]["doc_id"])
        self.assertEqual("sample.pdf", passed["result"]["document_name"])
        self.assertTrue(str(passed.get("asset_egress_decision_id", "")).startswith("FA3-EGRESS-"))

    def test_asset_egress_destination_drift_denied(self) -> None:
        registry = connected_registry()
        binding = registry["capabilities"][0]["providers"][0]
        binding["asset_egress_destination_uri"] = "https://example.invalid/upload"
        gw = McpGateway(registry)
        for adapter in self.adapters:
            gw.register_adapter(adapter)
        req = base_request("fa3.document.index", {"source": str(self.pdf)})
        req["approval"] = {"status": "APPROVED", "approval_id": "a1", "capability_id": "fa3.document.index"}
        receipt = gw.invoke(req)
        self.assertEqual("denied", receipt["result_status"])
        self.assertEqual("ASSET_EGRESS_DENIED", receipt["reason_code"])

    def test_retrieve_translation(self) -> None:
        gw = self.gateway()
        for operation, extra in (("metadata", {}), ("structure", {}), ("pages", {"pages": "1"})):
            req = base_request(
                "fa3.document.retrieve",
                {"operation": operation, "document_name": "sample.pdf", **extra},
            )
            receipt = gw.invoke(req)
            self.assertEqual("success", receipt["result_status"], receipt)
            self.assertEqual(operation, receipt["result"]["operation"])
            self.assertEqual("sample.pdf", receipt["result"]["document_name"])

    def test_local_path_escape_denied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            other = Path(td) / "outside-pageindex.pdf"
            other.write_bytes(b"%PDF-1.4\noutside")
            req = base_request("fa3.document.index", {"source": str(other)})
            req["approval"] = {"status": "APPROVED", "approval_id": "a1", "capability_id": "fa3.document.index"}
            receipt = self.gateway().invoke(req)
            self.assertEqual("denied", receipt["result_status"])
            self.assertEqual("PAGEINDEX_LOCAL_SCOPE_DENIED", receipt["reason_code"])

    def test_remote_source_is_fail_closed_without_allowlist(self) -> None:
        req = base_request("fa3.document.index", {"source": "https://example.com/a.pdf", "document_name": "a.pdf"})
        req["approval"] = {"status": "APPROVED", "approval_id": "a1", "capability_id": "fa3.document.index"}
        receipt = self.gateway().invoke(req)
        self.assertEqual("denied", receipt["result_status"])
        self.assertEqual("PAGEINDEX_REMOTE_SOURCE_DENIED", receipt["reason_code"])

    def test_remote_contract_drift_is_fail_closed(self) -> None:
        server = self.root / "bad_server.py"
        bad = FAKE_SERVER.replace('"required":["doc_name","pages"]', '"required":["doc_name"]')
        server.write_text(textwrap.dedent(bad), encoding="utf-8")
        config = PageIndexAdapterConfig(
            command=(sys.executable, str(server)),
            oauth_home=self.root / "home",
            allowed_roots=(self.root,),
            timeout_seconds=3,
            strict_supply_chain=False,
        )
        adapter = build_adapters(config)[1]
        req = base_request("fa3.document.retrieve", {"operation": "pages", "document_name": "sample.pdf", "pages": "1"})
        gw = McpGateway(connected_registry())
        gw.register_adapter(adapter)
        receipt = gw.invoke(req)
        self.assertEqual("denied", receipt["result_status"])
        self.assertEqual("PAGEINDEX_REMOTE_CONTRACT_DRIFT", receipt["reason_code"])

    def test_current_host_surfaces_do_not_escape_runtime_expressions(self) -> None:
        runner = (ROOT / "bin/fa3-pageindex-mcp-current-host.sh").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/fa3-pageindex-mcp-current-host.yml").read_text(encoding="utf-8")
        self.assertNotIn(r"\${", runner)
        self.assertNotIn(r"\${{", workflow)
        self.assertIn("${FA3_PAGEINDEX_MCP_SOURCE_ROOT:-}", runner)
        self.assertIn("${{ inputs.source_root }}", workflow)

    def test_current_host_pass_is_not_fabricated(self) -> None:
        report = gate(ROOT, current_host=True)
        self.assertEqual("BLOCKED", report["result"])
        self.assertTrue(any(x["code"] == "PAGEINDEX-HOST-000" for x in report["findings"]))


if __name__ == "__main__":
    unittest.main()
