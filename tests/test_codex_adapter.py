from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_codex_adapter as adapter
import fa3_codex_gate as gate


class CodexAdapterTests(unittest.TestCase):
    def test_provider_is_non_authoritative_and_pinned(self):
        provider = json.loads(
            (ROOT / "canonical/providers/FA3-PROVIDER-CODEX-001.json").read_text(encoding="utf-8")
        )
        self.assertEqual(provider["id"], adapter.PROVIDER_ID)
        self.assertFalse(provider["canonical_root"])
        self.assertFalse(provider["architectural_authority"])
        self.assertFalse(provider["new_capability"])
        self.assertEqual(provider["capability_count"], 143)
        self.assertEqual(provider["parent_profile"], "FA3-AGENT-EXEC-001")
        self.assertEqual(
            provider["coordination_contract"],
            "FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001",
        )
        self.assertEqual(provider["immutable_runtime_pin"]["version"], adapter.CODEX_VERSION)
        self.assertEqual(
            provider["immutable_runtime_pin"]["artifact_sha256"],
            adapter.ARCHIVE_SHA256,
        )

    def test_command_profile_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            command = adapter.build_codex_exec_command(
                base / "codex",
                base,
                base / "last.txt",
            )
        joined = "\n".join(command)
        self.assertIn("exec", command)
        self.assertIn("--strict-config", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--json", command)
        self.assertIn("--sandbox", command)
        self.assertIn("workspace-write", command)
        self.assertEqual(command[-1], "-")
        for forbidden in adapter.FORBIDDEN_FLAGS:
            self.assertNotIn(forbidden, command)
        for override in adapter.CONFIG_OVERRIDES:
            self.assertIn(override, command)
        self.assertIn('web_search="disabled"', joined)
        self.assertIn("mcp_servers={}", joined)
        self.assertIn("features.multi_agent=false", joined)
        self.assertIn("features.multi_agent_v2=false", joined)

    def test_secret_environment_is_not_passed(self):
        env = adapter.safe_codex_environment(
            {
                "PATH": "/usr/bin",
                "HOME": "/home/example",
                "OPENAI_API_KEY": "secret",
                "GITHUB_TOKEN": "secret",
                "CODEX_ACCESS_TOKEN": "secret",
                "SOME_PASSWORD": "secret",
            }
        )
        self.assertEqual(env["PATH"], "/usr/bin")
        self.assertEqual(env["HOME"], "/home/example")
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("CODEX_ACCESS_TOKEN", env)
        self.assertNotIn("SOME_PASSWORD", env)

    def test_safe_jsonl_event_stream_is_accepted(self):
        stream = "\n".join(
            [
                json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                json.dumps({"type": "turn.started"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "f",
                            "type": "file_change",
                            "changes": [{"path": "work/a.txt", "kind": "update"}],
                            "status": "completed",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 3,
                            "cached_input_tokens": 0,
                            "cache_write_input_tokens": 0,
                            "output_tokens": 2,
                            "reasoning_output_tokens": 0,
                        },
                    }
                ),
            ]
        )
        parsed = adapter.parse_codex_jsonl(stream)
        self.assertEqual(parsed["thread_id"], "thread-1")
        self.assertFalse(parsed["forbidden_surface_observed"])
        self.assertIn("file_change", parsed["item_types"])

    def test_mcp_collab_and_web_are_denied(self):
        for item_type in ("mcp_tool_call", "collab_tool_call", "web_search"):
            stream = "\n".join(
                [
                    json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"id": "x", "type": item_type},
                        }
                    ),
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
            with self.assertRaises(adapter.CodexAdapterDenied, msg=item_type):
                adapter.parse_codex_jsonl(stream)

    def test_fatal_event_is_denied(self):
        with self.assertRaises(adapter.CodexAdapterDenied):
            adapter.parse_codex_jsonl(
                "\n".join(
                    [
                        json.dumps({"type": "thread.started", "thread_id": "t"}),
                        json.dumps({"type": "turn.failed", "error": {"message": "boom"}}),
                    ]
                )
            )

    def test_ci_adapter_contract_e2e_passes_without_production_claim(self):
        report = adapter.run_ci_adapter_contract_e2e()
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["status"], "CI_ADAPTER_CONTRACT_PASS")
        self.assertTrue(report["synthetic_provider_fixture"])
        self.assertFalse(report["current_host_production_claim"])
        self.assertEqual(report["coordination"]["worker_count"], 2)
        self.assertEqual(report["coordination"]["integration_author"], "FA3 Integration")
        self.assertTrue(
            all(not worker["event_summary"]["forbidden_surface_observed"] for worker in report["workers"])
        )

    def test_reference_gate_passes(self):
        report = gate.gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["reference"]["result"], "PASS", report)
        self.assertEqual(report["regressions"]["result"], "PASS", report)
        self.assertEqual(report["current_host_production_state"], "PENDING_SEPARATE_REAL_CURRENT_HOST_RECEIPT")

    def test_current_host_gate_fails_without_real_receipt(self):
        receipt = ROOT / "evidence/receipts/codex-current-host.json"
        self.assertFalse(receipt.exists(), "repository must not commit a synthetic current-host receipt")
        report = gate.current_host_gate(ROOT)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["evidence_level"], "PENDING_OR_FAIL")
        self.assertTrue(any(x["code"] == "CODEX-HOST-001" for x in report["findings"]))

    def test_enforcement_has_exact_twenty_rules(self):
        enforcement = json.loads(
            (ROOT / "canonical/codex-enforcement.json").read_text(encoding="utf-8")
        )
        self.assertEqual(enforcement["mandatory_rule_count"], 20)
        self.assertEqual(enforcement["p0_invariants"], gate.P0_RULES)


if __name__ == "__main__":
    unittest.main()
