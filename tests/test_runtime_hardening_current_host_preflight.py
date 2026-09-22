from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.fa3_runtime_hardening_current_host_preflight import (
    validate_frame_trace,
    validate_json_file,
    validate_quadlet,
)


class RuntimeHardeningCurrentHostPreflightTests(unittest.TestCase):
    def test_quadlet_requires_fail_closed_runtime_controls(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agent.container"
            path.write_text(
                """[Container]
Image=ghcr.io/example/agent@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
Network=none
ReadOnly=true
NoNewPrivileges=true
DropCapability=all
Pull=never
GlobalArgs=--runtime=runsc
""",
                encoding="utf-8",
            )
            self.assertEqual([], validate_quadlet(path))
            path.write_text(path.read_text().replace("Network=none", "Network=host"), encoding="utf-8")
            self.assertIn("Quadlet requirement missing: Network=none", validate_quadlet(path))

    def test_quadlet_rejects_floating_image(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agent.container"
            path.write_text(
                """[Container]
Image=ghcr.io/example/agent:latest
Network=none
ReadOnly=true
NoNewPrivileges=true
DropCapability=all
Pull=never
GlobalArgs=--runtime=runsc
""",
                encoding="utf-8",
            )
            self.assertIn("Quadlet requirement missing: digest-pinned image", validate_quadlet(path))

    def test_frame_trace_proves_zero_host_frame_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trace.json"
            trace = {
                "schema": "fa3.accelerator-copy-trace.v1",
                "status": "PASS",
                "collector": {"kind": "CUPTI", "version": "test"},
                "neural_segment": {
                    "frame_count": 8,
                    "host_to_device_frame_copy_count": 0,
                    "device_to_host_frame_copy_count": 0,
                    "host_frame_round_trips": 0,
                    "shared_accelerator_memory": True,
                },
                "full_pipeline_zero_copy_claim": False,
                "full_pipeline_zero_copy_proven": False,
            }
            path.write_text(json.dumps(trace), encoding="utf-8")
            findings, parsed = validate_frame_trace(path)
            self.assertEqual([], findings)
            self.assertEqual("CUPTI", parsed["collector"]["kind"])

    def test_frame_trace_rejects_pcie_style_claim_without_copy_trace(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trace.json"
            trace = {
                "schema": "fa3.accelerator-copy-trace.v1",
                "status": "PASS",
                "collector": {"kind": "NVML_PCIE", "version": "test"},
                "neural_segment": {
                    "frame_count": 8,
                    "host_to_device_frame_copy_count": 0,
                    "device_to_host_frame_copy_count": 0,
                    "host_frame_round_trips": 0,
                    "shared_accelerator_memory": True,
                },
            }
            path.write_text(json.dumps(trace), encoding="utf-8")
            findings, _ = validate_frame_trace(path)
            self.assertIn("frame-copy trace collector unsupported or unversioned", findings)

    def test_frame_trace_rejects_any_frame_copy(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trace.json"
            trace = {
                "schema": "fa3.accelerator-copy-trace.v1",
                "status": "PASS",
                "collector": {"kind": "NSIGHT_SYSTEMS", "version": "test"},
                "neural_segment": {
                    "frame_count": 8,
                    "host_to_device_frame_copy_count": 0,
                    "device_to_host_frame_copy_count": 1,
                    "host_frame_round_trips": 0,
                    "shared_accelerator_memory": True,
                },
            }
            path.write_text(json.dumps(trace), encoding="utf-8")
            findings, _ = validate_frame_trace(path)
            self.assertIn("frame-copy trace reports host frame transfer", findings)

    def test_json_input_must_be_object(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "metrics.json"
            path.write_text("[]", encoding="utf-8")
            findings = validate_json_file(path, "metrics")
            self.assertTrue(any("unreadable JSON" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
