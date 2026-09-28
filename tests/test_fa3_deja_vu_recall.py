"""Offline positive/negative tests for the optional scoped deja-vu provider."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fa3_deja_vu_recall import DejaRecall, factory
from fa3_mcp_gateway import GatewayDenied, McpGateway

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "73ad34e5fdc2b0c245a0fb69b65a17f3cbb123c8"


class ScopedDejaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fa3-deja-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "private"
        self.root.mkdir(mode=0o700)
        self.partition = self.root / "alpha"
        self.partition.mkdir(mode=0o700)
        for name in ("home", "index", "claude"):
            (self.partition / name).mkdir(mode=0o700)
        self.transcript = self.partition / "claude" / "session.jsonl"
        self.transcript.write_text('{"type":"fixture"}\n', encoding="utf-8")
        self.binary = Path(self.temp.name) / "fake-deja"
        self.manifest = Path(self.temp.name) / "runtime.json"
        self.payload = self.envelope()
        self.configure()

    def envelope(self, *, project="alpha", path=None, tier="exact", strict=True):
        return {
            "schema_version": 2,
            "tier": tier,
            "hits": [{
                "session": {
                    "id": "S1", "harness": "claude", "project": project,
                    "path": str(path or getattr(self, "transcript", "/missing")),
                },
                "score": 2.5, "tier": tier, "strict": strict,
                "snippets": ["Resolved the compiler failure by rebuilding the cache"],
            }],
        }

    def configure(self):
        # A fake pinned binary exercises real argument, env and JSON parsing.
        self.binary.write_text(
            "#!/usr/bin/env python3\n"
            "import os,sys\n"
            "assert sys.argv[1:5] == ['search','--json','--limit','5']\n"
            "assert os.environ['DEJA_STORES'] == 'claude'\n"
            "assert os.environ['HOME'].endswith('/alpha/home')\n"
            "assert os.environ['DEJA_INDEX_DIR'].endswith('/alpha/index')\n"
            "sys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n",
            encoding="utf-8",
        )
        self.binary.chmod(0o700)
        self.config = {
            "schema": "fa3.deja.scoped-runtime.v1",
            "upstream_sha": UPSTREAM,
            "admission_status": "RUNTIME_ADMITTED",  # isolated test fixture, never canonical admission
            "partition_root": str(self.root),
            "binary_path": str(self.binary),
            "binary_sha256": hashlib.sha256(self.binary.read_bytes()).hexdigest(),
            "projects": {
                "alpha": {
                    "partition_dir": str(self.partition),
                    "stores": {"claude": str(self.partition / "claude")},
                    "exact_project_aliases": ["alpha"],
                }
            },
        }
        self.save_manifest()

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.config), encoding="utf-8")
        self.manifest.chmod(0o600)

    def retrieve(self, **updates):
        return DejaRecall(self.manifest).retrieve({
            "project_id": "alpha", "query": "compiler failure",
            **updates,
        })

    def assert_code(self, expected, action):
        with self.assertRaises(GatewayDenied) as caught:
            action()
        self.assertEqual(expected, caught.exception.code)

    def test_success_with_provenance_no_raw_path(self):
        result = self.retrieve()
        self.assertEqual(result["item_count"], 1)
        self.assertEqual(result["items"][0]["project_id"], "alpha")
        self.assertTrue(result["items"][0]["source_ref"].startswith("FA3-DEJA-"))
        self.assertNotIn(str(self.transcript), json.dumps(result))
        self.assertFalse(result["source_authority"])
        self.assertFalse(result["model_used"])

    def test_cross_project_session_filtered(self):
        self.payload = self.envelope(project="alpha-secret")
        self.configure()
        self.assertEqual(self.retrieve()["item_count"], 0)

    def test_external_source_path_filtered(self):
        outside = Path(self.temp.name) / "other.jsonl"
        outside.write_text("no", encoding="utf-8")
        self.payload = self.envelope(path=outside)
        self.configure()
        self.assertEqual(self.retrieve()["item_count"], 0)

    def test_relevance_fallback_is_not_false_match(self):
        self.payload = self.envelope(tier="relevance", strict=False)
        self.configure()
        self.assertEqual(self.retrieve()["item_count"], 0)
        self.payload = self.envelope(tier="relevance", strict=True)
        self.configure()
        self.assertEqual(self.retrieve()["item_count"], 1)

    def test_unsupported_semantic_tier_fails_closed(self):
        self.payload["semantic"] = True
        self.configure()
        self.assert_code("UNADMITTED_RETRIEVAL_TIER", self.retrieve)

    def test_unsupported_json_version_fails_closed(self):
        self.payload["schema_version"] = 3
        self.configure()
        self.assert_code("UPSTREAM_SCHEMA_MISMATCH", self.retrieve)

    def test_wrong_project_and_invalid_budgets_denied(self):
        self.assert_code("PROJECT_NOT_ADMITTED", lambda: self.retrieve(project_id="beta"))
        self.assert_code("INVALID_PROJECT_ID", lambda: self.retrieve(project_id=".."))
        self.assert_code("INVALID_BUDGET", lambda: self.retrieve(max_items=True))
        self.assert_code("INVALID_BUDGET", lambda: self.retrieve(max_context_chars=9000))
        self.assert_code("UNSUPPORTED_ARGUMENT", lambda: self.retrieve(binary="/tmp/other"))

    def test_manifest_and_binary_integrity_fail_closed(self):
        self.manifest.chmod(0o644)
        self.assert_code("UNTRUSTED_MANIFEST", self.retrieve)
        self.manifest.chmod(0o600)
        self.config["binary_sha256"] = "0" * 64
        self.save_manifest()
        self.assert_code("BINARY_DIGEST_MISMATCH", self.retrieve)
        self.config["binary_sha256"] = hashlib.sha256(self.binary.read_bytes()).hexdigest()
        self.config["admission_status"] = "PENDING_CURRENT_HOST"
        self.save_manifest()
        self.assert_code("PROVIDER_NOT_ADMITTED", self.retrieve)

    def test_untrusted_partition_denied(self):
        self.partition.chmod(0o755)
        self.addCleanup(lambda: self.partition.chmod(0o700))
        self.assert_code("UNTRUSTED_PARTITION", self.retrieve)

    def test_redacts_high_risk_secrets_in_results(self):
        self.payload["hits"][0]["snippets"] = ["token=longsecretvalue12345 sk-abcdefghijklmnopqrstuvwxyz12"]
        self.configure()
        snippet = self.retrieve()["items"][0]["snippets"][0]
        self.assertNotIn("longsecretvalue", snippet)
        self.assertNotIn("sk-abcdefghijklmnop", snippet)
        self.assertIn("[redacted:fa3]", snippet)

    def test_external_policy_resolver_and_required_audit(self):
        registry = json.loads(
            (ROOT / "canonical/mcp-capability-registry.json").read_text(encoding="utf-8")
        )
        # Local E2E simulation; production registry stays PENDING_CURRENT_HOST.
        simulated = copy.deepcopy(registry)
        cap = next(x for x in simulated["capabilities"] if x["capability_id"] == "fa3.memory.retrieve")
        pending = next(x for x in cap["providers"] if x["provider_id"] == "FA3-PROVIDER-DEJA-VU-001")
        self.assertEqual(pending["state"], "PENDING_CURRENT_HOST")
        pending["state"] = "CONNECTED"
        decision_projects = ["alpha"]

        def external_policy(_request, _cap, _binding, _peer):
            return {
                "authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
                "status": "ALLOW", "capability_id": "fa3.memory.retrieve",
                "decision_id": "fixture-authorization", "purpose": "test-scoped-recall",
                "scope": {"project_ids": decision_projects},
            }

        gateway = McpGateway(simulated, policy_resolver=external_policy)
        with patch.dict(os.environ, {"FA3_DEJA_RUNTIME_MANIFEST": str(self.manifest)}):
            gateway.register_adapter(factory())
        request = {
            "actor_id": "FA3-AGENT-TEST", "client_id": "fa3-agent-runtime",
            "session_id": "fixture-session", "capability_id": "fa3.memory.retrieve",
            "provider_id": "FA3-PROVIDER-DEJA-VU-001",
            "arguments": {"project_id": "alpha", "query": "compiler failure"},
        }
        receipt = gateway.invoke(request)
        self.assertEqual(receipt["result_status"], "success")
        audit_file = self.root / "retrieval-audit.jsonl"
        self.assertTrue(audit_file.exists())
        audit_text = audit_file.read_text(encoding="utf-8")
        self.assertIn("fixture-authorization", audit_text)
        self.assertNotIn("compiler failure", audit_text)
        self.assertNotIn("Resolved the compiler", audit_text)
        decision_projects.clear()
        denied = gateway.invoke(request)
        self.assertEqual(denied["result_status"], "denied")
        self.assertEqual(denied["reason_code"], "POLICY_SCOPE_MISMATCH")

    def test_missing_factory_admission_refused(self):
        with patch.dict(os.environ, {"FA3_DEJA_RUNTIME_MANIFEST": ""}):
            self.assert_code("PROVIDER_NOT_ADMITTED", factory)


if __name__ == "__main__":
    unittest.main()
