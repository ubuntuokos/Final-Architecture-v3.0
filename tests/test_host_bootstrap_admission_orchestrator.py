from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fa3_host_bootstrap_admission_orchestrator import (
    CommandResult,
    WORKLOAD_SCHEMA,
    admit,
    discover_candidate,
    load_workload,
)

GPU_UUID = "GPU-f17bc7a0-573c-48d2-5463-6d9474db2333"


def workload() -> dict:
    return {
        "schema": WORKLOAD_SCHEMA,
        "workload_id": "workload-1",
        "requirements": [
            {"metric": "cpu.physical_cores", "operator": ">=", "value": 1},
            {"metric": "gpu.vram_gib", "operator": ">=", "value": 1},
            {"metric": "gpu.cuda_compute_capability", "operator": ">=", "value": 8.6},
        ],
    }


class HostBootstrapAdmissionOrchestratorTests(unittest.TestCase):
    def test_cu_tu_cannot_regain_admission_authority(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "workload.json"
            value = workload()
            value["requirements"].append({"metric": "tu", "operator": ">=", "value": 1})
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "FORBIDDEN_CU_TU"):
                load_workload(path)

    def test_candidate_discovery_is_capability_and_vram_based_not_sku_based(self) -> None:
        def runner(command, timeout):
            return CommandResult(
                0,
                "0, " + GPU_UUID + ", 00000000:A1:00.0, 8188, 8.6\n",
                "",
            )

        candidate = discover_candidate(workload(), runner)
        self.assertEqual(candidate["uuid"], GPU_UUID)
        self.assertEqual(candidate["pci_bdf"], "0000:a1:00.0")
        self.assertNotIn("sku", candidate)

    def test_full_orchestration_requires_real_acquire_then_existing_collector_and_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "evidence/receipts").mkdir(parents=True)
            collector = root / "evidence/collect-resource-admission-current-host.py"
            collector.write_text("# fixture\n", encoding="utf-8")
            (root / "bin").mkdir()
            enforcer = root / "bin/fa3-enforce"
            enforcer.write_text("#!/bin/sh\n", encoding="utf-8")
            enforcer.chmod(0o755)
            acquire_client = root / "fa3-host-resource-broker-acquire"
            acquire_client.write_text("#!/bin/sh\n", encoding="utf-8")
            acquire_client.chmod(0o755)
            workload_path = root / "workload.json"
            workload_path.write_text(json.dumps(workload()), encoding="utf-8")
            lease_path = root / "lease.json"
            calls: list[list[str]] = []

            def runner(command, timeout):
                command = list(command)
                calls.append(command)
                if command[0] == "nvidia-smi":
                    return CommandResult(0, f"0, {GPU_UUID}, 00000000:A1:00.0, 8188, 8.6\n", "")
                if command[0] == str(acquire_client):
                    lease_path.write_text("{}\n", encoding="utf-8")
                    return CommandResult(0, "", "")
                if len(command) > 1 and command[1] == str(collector):
                    return CommandResult(0, "", "")
                if command == [str(enforcer), "resource-admission-current-host"]:
                    (root / "evidence/receipts/resource-admission-current-host.json").write_text(
                        "{}\n", encoding="utf-8"
                    )
                    return CommandResult(0, "", "")
                raise AssertionError(command)

            code, report = admit(
                root,
                workload_path,
                lease_path=lease_path,
                report_path=root / "report.json",
                runner=runner,
                acquire_client=acquire_client,
            )
            self.assertEqual(code, 0)
            self.assertEqual(report["result"], "PASS")
            self.assertFalse(report["authority"]["orchestrator_is_authority"])
            self.assertEqual(report["claims"], ["CURRENT_HOST_RESOURCE_ADMISSION_PASS"])
            self.assertIn("GLOBAL_FA3_PROMOTION", report["non_claims"])
            self.assertTrue(any(call and call[0] == str(acquire_client) for call in calls))
            self.assertTrue(any(call == [str(enforcer), "resource-admission-current-host"] for call in calls))

    def test_missing_acquire_bridge_is_pending_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "reports").mkdir()
            workload_path = root / "workload.json"
            workload_path.write_text(json.dumps(workload()), encoding="utf-8")

            def runner(command, timeout):
                if command[0] == "nvidia-smi":
                    return CommandResult(0, f"0, {GPU_UUID}, 00000000:A1:00.0, 8188, 8.6\n", "")
                raise AssertionError(command)

            code, report = admit(
                root,
                workload_path,
                report_path=root / "reports/report.json",
                runner=runner,
                acquire_client=root / "missing-client",
            )
            self.assertEqual(code, 2)
            self.assertEqual(report["result"], "PENDING")
            self.assertEqual(report["claims"], [])


if __name__ == "__main__":
    unittest.main()
