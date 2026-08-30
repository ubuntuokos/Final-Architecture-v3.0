from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from fa3_presenton_gate import (
    OCI_INDEX_DIGEST,
    artifact_bytes_valid,
    current_host_gate,
    disabled_zero_cost,
    executable_regressions,
    gate,
    gateway_access_allowed,
    generation_request_allowed,
    runtime_config_valid,
    scan_canonical_authority_assignments,
)

ROOT = Path(__file__).resolve().parents[1]


def good_request():
    return {
        "schema": "fa3.presenton-generation-request.v1",
        "request_id": "request-1",
        "caller_identity": "caller-1",
        "workspace_id": "workspace-1",
        "authorization_decision": {
            "authority": "FA3-AUTH-SECURITY-GOV-001",
            "decision": "ALLOW",
            "capabilities": ["presentation.generate"],
        },
        "content": "FA3 Presenton test",
        "n_slides": 3,
        "language": "Hungarian",
        "export_formats": ["pptx", "pdf"],
        "file_references": ["artifact://document/1"],
        "source_bytes": 4096,
        "web_search": False,
        "trigger_webhook": False,
        "execution_mode": "ASYNC_BOUNDED",
        "timeout_seconds": 600,
    }


def good_runtime():
    return {
        "rootless": True,
        "bind": "127.0.0.1:5001",
        "image": f"ghcr.io/presenton/presenton@{OCI_INDEX_DIGEST}",
        "llm": "litellm",
        "litellm_base_url": "http://host.containers.internal:4000/v1",
        "image_provider": "comfyui",
        "comfyui_url": "http://host.containers.internal:9876",
        "database_url": "postgresql://presenton:redacted@host.containers.internal:5432/presenton",
        "gpu_devices": [],
        "web_grounding": False,
        "anonymous_tracking": False,
        "parallel_image_generation": False,
        "start_ollama": False,
        "can_change_keys": False,
        "memory_scope": "PRESENTATION_LOCAL_NON_AUTHORITATIVE",
        "secrets_externalized": True,
    }


class PresentonGateTests(unittest.TestCase):
    def test_current_canonical_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(143, report["details"]["canonical_capability_count"])

    def test_executable_regression_matrix_passes(self):
        report = executable_regressions()
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(16, report["passed"])

    def test_authorized_request_is_accepted(self):
        self.assertTrue(generation_request_allowed(good_request()))

    def test_web_search_remote_source_and_unbounded_execution_fail_closed(self):
        request = good_request()
        request["web_search"] = True
        self.assertFalse(generation_request_allowed(request))
        request = good_request()
        request["file_references"] = ["https://example.invalid/source.pdf"]
        self.assertFalse(generation_request_allowed(request))
        request = good_request()
        request["timeout_seconds"] = 3601
        self.assertFalse(generation_request_allowed(request))

    def test_gateway_mediation_is_required(self):
        self.assertTrue(gateway_access_allowed(
            authenticated=True,
            via_central_gateway=True,
            access_key_scope="presenton.presentation.generate",
            browser_cookie_used=False,
        ))
        self.assertFalse(gateway_access_allowed(
            authenticated=True,
            via_central_gateway=False,
            access_key_scope="presenton.presentation.generate",
            browser_cookie_used=False,
        ))

    def test_sqlite_direct_gpu_and_direct_llm_fail_closed(self):
        runtime = good_runtime()
        self.assertTrue(runtime_config_valid(runtime))
        self.assertFalse(runtime_config_valid({**runtime, "database_url": "sqlite:///app.db"}))
        self.assertFalse(runtime_config_valid({**runtime, "gpu_devices": ["/dev/nvidia0"]}))
        self.assertFalse(runtime_config_valid({**runtime, "llm": "ollama"}))

    def test_pptx_and_pdf_artifact_integrity(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as package:
            package.writestr("[Content_Types].xml", "<Types/>")
            package.writestr("ppt/presentation.xml", "<p:presentation/>")
        self.assertTrue(artifact_bytes_valid("pptx", stream.getvalue()))
        self.assertFalse(artifact_bytes_valid("pptx", b"invalid"))
        self.assertTrue(artifact_bytes_valid("pdf", b"%PDF-1.7\n", page_count=2, rendered_page_count=2))
        self.assertFalse(artifact_bytes_valid("pdf", b"%PDF-1.7\n", page_count=2, rendered_page_count=1))

    def test_disabled_provider_has_zero_cost(self):
        self.assertTrue(disabled_zero_cost({
            "resident_process_count": 0,
            "background_worker_count": 0,
            "network_session_count": 0,
            "accelerator_reservation_count": 0,
            "active_polling": False,
            "background_fetch": False,
        }))

    def test_authority_assignment_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            canonical = root / "canonical"
            canonical.mkdir()
            (canonical / "bad.json").write_text(json.dumps({"workflow_authority": "FA3-PROVIDER-PRESENTON-001"}), encoding="utf-8")
            report = scan_canonical_authority_assignments(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "PRESENTON-AUTH-001" for item in report["findings"]))

    def test_current_host_pass_is_not_fabricated_by_ci(self):
        with tempfile.TemporaryDirectory() as td:
            report = current_host_gate(Path(td))
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "PRESENTON-HOST-001" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
