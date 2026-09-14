from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_resource_admission_smoke import (  # noqa: E402
    CUDA_COMPUTE_CAPABILITY_MIN,
    CommandResult,
    WORKLOAD_ID,
    build_smoke_workload,
    normalize_bdf,
    render_acquire_command,
    run_smoke,
)


class ResourceAdmissionSmokeTests(unittest.TestCase):
    def test_smoke_workload_is_small_multidimensional_and_has_no_cu_tu(self) -> None:
        workload = build_smoke_workload()
        self.assertEqual(workload["workload_id"], WORKLOAD_ID)
        metrics = {item["metric"]: item["value"] for item in workload["requirements"]}
        self.assertEqual(metrics["cpu.physical_cores"], 1)
        self.assertEqual(metrics["memory.total_gib"], 1)
        self.assertEqual(metrics["gpu.vram_gib"], 1)
        self.assertEqual(metrics["gpu.cuda_compute_capability"], CUDA_COMPUTE_CAPABILITY_MIN)
        self.assertFalse(any(metric.lower() in {"cu", "tu"} for metric in metrics))
        self.assertFalse(workload["global_promotion_claim"])

    def test_bdf_normalization_handles_eight_digit_domain(self) -> None:
        self.assertEqual(normalize_bdf("00000000:01:00.0"), "0000:01:00.0")
        self.assertEqual(normalize_bdf("0000:AB:0C.1"), "0000:ab:0c.1")

    def test_acquire_command_is_tokenized_without_shell_and_preserves_spaced_paths(self) -> None:
        values = {
            "workload": "/tmp/work load.json",
            "lease": "/tmp/lease file.json",
            "gpu_uuid": "GPU-TEST",
            "pci_bdf": "0000:01:00.0",
            "hostname": "test-host",
            "workload_id": WORKLOAD_ID,
        }
        command = render_acquire_command(
            'fa3-hrb-client acquire --workload "{workload}" --output "{lease}" --gpu {gpu_uuid}',
            values,
        )
        self.assertEqual(command[0], "fa3-hrb-client")
        self.assertEqual(command[3], "/tmp/work load.json")
        self.assertEqual(command[5], "/tmp/lease file.json")
        self.assertNotIn("sh", command[:1])

    def test_unknown_acquire_placeholder_is_input_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown HRB acquire placeholder"):
            render_acquire_command(
                "fa3-hrb-client acquire --bad {secret}",
                {
                    "workload": "w",
                    "lease": "l",
                    "gpu_uuid": "g",
                    "pci_bdf": "b",
                    "hostname": "h",
                    "workload_id": WORKLOAD_ID,
                },
            )

    def test_missing_acquire_interface_is_pending_and_fail_closed(self) -> None:
        calls: list[list[str]] = []

        def runner(command, **kwargs):
            calls.append(list(command))
            if command[0] == "nvidia-smi":
                return CommandResult(0, "0, GPU-TEST, 00000000:01:00.0, 8.6\n", "")
            return CommandResult(99, "", "unexpected")

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {}, clear=True):
                code, report = run_smoke(Path(tmp), runner=runner)
            self.assertEqual(code, 2)
            self.assertEqual(report["result"], "PENDING")
            self.assertEqual(report["decision"]["reason_code"], "HRB_ACQUIRE_COMMAND_UNCONFIGURED")
            self.assertFalse(report["authority"]["bootstrap_can_mint_or_sign_lease"])
            self.assertEqual(report["capability_delta"], 0)
            self.assertEqual(report["authority_delta"], 0)
            self.assertEqual(len(calls), 1)

    def test_prepare_only_never_claims_pass(self) -> None:
        def runner(command, **kwargs):
            return CommandResult(0, "0, GPU-TEST, 00000000:01:00.0, 8.6\n", "")

        with tempfile.TemporaryDirectory() as tmp:
            code, report = run_smoke(Path(tmp), prepare_only=True, runner=runner)
            self.assertEqual(code, 2)
            self.assertEqual(report["result"], "PENDING")
            self.assertEqual(report["decision"]["reason_code"], "PREPARED_AWAITING_HRB_LEASE")
            self.assertEqual(report["claims"], [])
            self.assertIn("GLOBAL_FA3_PROMOTION", report["non_claims"])

    def test_preexisting_lease_still_requires_collector_and_canonical_gate(self) -> None:
        calls: list[list[str]] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lease = root / "real-lease.json"
            lease.write_text('{"external":"fixture-only"}\n', encoding="utf-8")

            def runner(command, **kwargs):
                command = list(command)
                calls.append(command)
                if "collect-resource-admission-current-host.py" in " ".join(command):
                    receipt = root / "evidence/receipts/resource-admission-current-host.json"
                    receipt.parent.mkdir(parents=True, exist_ok=True)
                    receipt.write_text('{"scoped":"fixture-only"}\n', encoding="utf-8")
                    return CommandResult(0, "", "")
                if command[-1:] == ["resource-admission-current-host"]:
                    return CommandResult(0, "", "")
                return CommandResult(99, "", "unexpected")

            code, report = run_smoke(root, hrb_lease=lease, runner=runner)
            self.assertEqual(code, 0)
            self.assertEqual(report["result"], "PASS")
            self.assertEqual(report["claims"], ["CURRENT_HOST_RESOURCE_ADMISSION_PASS"])
            self.assertTrue(any("collect-resource-admission-current-host.py" in " ".join(c) for c in calls))
            self.assertTrue(any(c[-1:] == ["resource-admission-current-host"] for c in calls))

    def test_external_acquire_failure_blocks_before_collector(self) -> None:
        calls: list[list[str]] = []

        def runner(command, **kwargs):
            command = list(command)
            calls.append(command)
            if command[0] == "nvidia-smi":
                return CommandResult(0, "0, GPU-TEST, 00000000:01:00.0, 8.6\n", "")
            if command[0] == "fa3-hrb-client":
                return CommandResult(1, "sensitive-output-not-logged", "sensitive-error-not-logged")
            return CommandResult(99, "", "unexpected")

        with tempfile.TemporaryDirectory() as tmp:
            code, report = run_smoke(
                Path(tmp),
                hrb_acquire_command="fa3-hrb-client acquire --workload {workload} --output {lease} --gpu {gpu_uuid}",
                runner=runner,
            )
            self.assertEqual(code, 2)
            self.assertEqual(report["result"], "BLOCKED")
            self.assertEqual(report["decision"]["reason_code"], "HRB_ACQUIRE_FAILED")
            self.assertEqual(report["acquire"]["return_code"], 1)
            self.assertFalse(any("collect-resource-admission-current-host.py" in " ".join(c) for c in calls))

    def test_self_hosted_workflow_uses_smoke_bootstrap_not_legacy_collect_path(self) -> None:
        workflow = (ROOT / ".github/workflows/fa3-resource-admission-current-host.yml").read_text(encoding="utf-8")
        production = workflow.split("  production-e2e:\n", 1)[1]
        self.assertIn('args=(smoke --workload-envelope "${{ inputs.workload_envelope }}")', production)
        self.assertIn('./bin/fa3-resource-admission-current-host.sh "${args[@]}"', production)
        self.assertNotIn("fa3-resource-admission-current-host.sh collect", production)
        self.assertIn("Re-validate current-host receipt independently", production)

    def test_workflow_does_not_accept_hrb_acquire_command_from_dispatch_ui(self) -> None:
        workflow = (ROOT / ".github/workflows/fa3-resource-admission-current-host.yml").read_text(encoding="utf-8")
        dispatch = workflow.split("  workflow_dispatch:\n", 1)[1].split("\npermissions:\n", 1)[0]
        self.assertNotIn("hrb_acquire_command", dispatch)
        self.assertIn("hrb_lease:", dispatch)
        self.assertIn("default: ''", dispatch)


if __name__ == "__main__":
    unittest.main()
