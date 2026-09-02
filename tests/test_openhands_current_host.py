from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_openhands_adapter as a
import fa3_openhands_current_host_gate as g


class OpenHandsCurrentHostTests(unittest.TestCase):
    def _auth(self):
        return {
            "schema": "fa3.canonical-tool-authorization-receipt.v1",
            "issuer_id": "FA3-AUTH-MCP-GATEWAY-001",
            "provider_id": a.PROVIDER_ID,
            "task_id": "t1",
            "authorized": True,
            "single_use": True,
            "issued_at": "2026-09-03T00:00:00Z",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10))
            .isoformat()
            .replace("+00:00", "Z"),
            "scope": {
                "operation": "workspace.write.exact",
                "relative_path": "work/openhands.txt",
                "content_sha256": "a" * 64,
            },
        }

    def test_external_authorization_positive_and_negative(self):
        receipt = self._auth()
        a.validate_external_tool_authorization(
            receipt,
            task_id="t1",
            relative_path="work/openhands.txt",
            content_sha256="a" * 64,
        )
        bad = json.loads(json.dumps(receipt))
        bad["issuer_id"] = a.PROVIDER_ID
        with self.assertRaises(a.OpenHandsAdmissionError):
            a.validate_external_tool_authorization(
                bad,
                task_id="t1",
                relative_path="work/openhands.txt",
                content_sha256="a" * 64,
            )

    def test_path_traversal_is_denied(self):
        for value in ("../x", "/tmp/x", "", ".", "a/../../b"):
            with self.assertRaises(a.OpenHandsAdmissionError):
                a.validate_relative_path(value)

    def test_bwrap_command_is_network_unshared_and_no_root_bind(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "root"
            venv = base / "venv"
            workspace = base / "workspace"
            root.mkdir()
            venv.mkdir()
            workspace.mkdir()
            result = workspace / ".fa3-openhands-worker-result.json"
            with patch("fa3_openhands_adapter.find_bwrap", return_value=Path("/usr/bin/bwrap")):
                command = a.build_bwrap_command(
                    root=root,
                    venv=venv,
                    workspace=workspace,
                    mode="isolated",
                    task_id="t1",
                    relative_path="work/openhands.txt",
                    expected_content="PASS\n",
                    result_path=result,
                )
            joined = "\n".join(command)
            self.assertIn("--unshare-all", command)
            self.assertIn("--clearenv", command)
            self.assertNotIn("--share-net", command)
            self.assertNotIn("--ro-bind\n/\n/", joined)
            self.assertIn("/fa3/src/fa3_openhands_current_host_worker.py", command)

    def test_production_command_requires_external_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "root"
            venv = base / "venv"
            workspace = base / "workspace"
            root.mkdir()
            venv.mkdir()
            workspace.mkdir()
            with patch("fa3_openhands_adapter.find_bwrap", return_value=Path("/usr/bin/bwrap")):
                with self.assertRaises(a.OpenHandsAdmissionError):
                    a.build_bwrap_command(
                        root=root,
                        venv=venv,
                        workspace=workspace,
                        mode="production",
                        task_id="t1",
                        relative_path="work/openhands.txt",
                        expected_content="PASS\n",
                        result_path=workspace / "result.json",
                    )

    def _valid_receipt(self, production: bool):
        mode = "production" if production else "isolated"
        level = g.PRODUCTION_LEVEL if production else g.ISOLATED_LEVEL
        model = {
            "class": "CENTRAL_LITELLM_UNIX_BRIDGE" if production else "OPENHANDS_TEST_LLM_FIXTURE",
            "fixture_only": not production,
            "production_response_count": 2 if production else 0,
            "production_response_sha256": ["b" * 64, "c" * 64] if production else [],
        }
        authorization = {
            "class": "EXTERNAL_CANONICAL_TOOL_AUTHORIZATION" if production else "FIXTURE_NON_PRODUCTION",
            "issuer_id": "FA3-AUTH-MCP-GATEWAY-001" if production else None,
            "single_use": True,
        }
        worker = {
            "status": "PASS",
            "mode": mode,
            "target_sha256": "d" * 64,
            "tool_surface": {
                "registered_tools": ["fa3_delegated_write"],
                "provider_native_execute_tool_used": False,
                "provider_native_mcp_enabled": False,
                "terminal_tool_enabled": False,
                "file_editor_tool_enabled": False,
            },
            "persistence": {"raw_router_secret_persisted": False},
            "resume": {
                "status": "PASS",
                "same_conversation_id": True,
                "prior_persistence_observed": True,
                "new_events_after_reopen": True,
            },
            "event_lineage": {
                "first_run_count": 2,
                "resume_count": 1,
                "first_run_chain_head": "e" * 64,
                "resume_chain_head": "f" * 64,
            },
            "model_route": model,
        }
        return {
            "schema": "fa3.openhands-current-host-receipt.v1",
            "provider_id": g.PROVIDER_ID,
            "runtime_id": g.RUNTIME_ID,
            "status": "PASS",
            "mode": mode,
            "evidence_level": level,
            "source": {
                "repository": "OpenHands/software-agent-sdk",
                "commit": g.PINNED_COMMIT,
                "tree": g.PINNED_TREE,
                "dirty": False,
            },
            "runtime": {
                "python_major_minor": "3.12",
                "packaging": "pip-venv",
                "conda_or_mamba_active": False,
                "component_versions": {name: g.VERSION for name in g.COMPONENTS},
                "pip_freeze_sha256": "1" * 64,
                "venv_python_sha256": "2" * 64,
            },
            "isolation": {
                "bubblewrap": True,
                "unshare_all": True,
                "general_network_egress_denied": True,
                "host_home_not_mounted": True,
                "repository_read_only": True,
                "delegated_workspace_write_only": True,
                "root_filesystem_not_bind_mounted": True,
                "bwrap_binary_sha256": "3" * 64,
            },
            "worker": worker,
            "mutation": {
                "authorized_relative_path": "work/openhands.txt",
                "worker_commit_created": False,
                "changed_paths": ["work/openhands.txt"],
                "before_sha256": "4" * 64,
                "after_sha256": "d" * 64,
            },
            "negative_tests": {
                "path_traversal_denied": True,
                "wrong_path_authorization_denied": True,
                "expired_authorization_denied": True,
                "provider_as_authority_denied": True,
                "command_secret_value_absent": True,
            },
            "cleanup": {
                "workspace_removed": True,
                "router_bridge_stopped": True,
                "temporary_secret_copy_removed": True,
            },
            "authorization": authorization,
            "host": {
                "system": "Linux",
                "machine": "x86_64",
                "current_host_marker": True,
                "github_hosted_runner": False,
            },
            "production_admission_claim": production,
            "capability_count_after": 143,
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "global_promotion_claim": False,
        }

    def test_isolated_receipt_passes_but_cannot_claim_production(self):
        receipt = self._valid_receipt(False)
        self.assertEqual([], g.validate_receipt(receipt, require_production=False))
        self.assertNotEqual([], g.validate_receipt(receipt, require_production=True))

    def test_production_receipt_requires_real_route_and_external_auth(self):
        receipt = self._valid_receipt(True)
        self.assertEqual([], g.validate_receipt(receipt, require_production=True))
        receipt["worker"]["model_route"]["fixture_only"] = True
        self.assertTrue(
            any(
                item["code"] == "OPENHANDS-HOST-011"
                for item in g.validate_receipt(receipt, require_production=True)
            )
        )


if __name__ == "__main__":
    unittest.main()
