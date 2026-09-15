from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
GPU_UUID = "GPU-f17bc7a0-573c-48d2-5463-6d9474db2333"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


root_helper = load_module("fa3_hrb_acquire_root", ROOT / "libexec/fa3-host-resource-broker-acquire-root.py")
client = load_module("fa3_hrb_acquire_client", ROOT / "libexec/fa3-host-resource-broker-acquire.py")


class HrbAcquireBridgeTests(unittest.TestCase):
    def test_root_helper_parses_typed_request(self) -> None:
        request = root_helper.parse_request(
            json.dumps(
                {
                    "schema": root_helper.REQUEST_SCHEMA,
                    "workload_id": "workload-1",
                    "accelerator_uuid": GPU_UUID,
                    "memory_bytes": 1073741824,
                }
            ).encode()
        )
        self.assertEqual(request["accelerator_uuid"], GPU_UUID)
        self.assertEqual(request["memory_bytes"], 1073741824)

    def test_root_helper_rejects_invalid_uuid_and_boolean_memory(self) -> None:
        with self.assertRaises(root_helper.AcquireError):
            root_helper.parse_request(
                json.dumps(
                    {
                        "schema": root_helper.REQUEST_SCHEMA,
                        "workload_id": "workload-1",
                        "accelerator_uuid": "0",
                        "memory_bytes": 1,
                    }
                ).encode()
            )
        with self.assertRaises(root_helper.AcquireError):
            root_helper.parse_request(
                json.dumps(
                    {
                        "schema": root_helper.REQUEST_SCHEMA,
                        "workload_id": "workload-1",
                        "accelerator_uuid": GPU_UUID,
                        "memory_bytes": True,
                    }
                ).encode()
            )

    def test_client_derives_exact_lease_budget_from_vram_requirement(self) -> None:
        workload = {
            "schema": client.WORKLOAD_SCHEMA,
            "workload_id": "workload-1",
            "requirements": [{"metric": "gpu.vram_gib", "operator": ">=", "value": 1.25}],
        }
        self.assertEqual(client.required_gpu_memory_bytes(workload), 1342177280)

    def test_client_rejects_cu_tu_and_requires_explicit_vram(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "workload.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": client.WORKLOAD_SCHEMA,
                        "workload_id": "workload-1",
                        "requirements": [{"metric": "tu", "operator": ">=", "value": 1}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(client.ClientError):
                client.load_workload(path)

        with self.assertRaises(client.ClientError):
            client.required_gpu_memory_bytes(
                {
                    "requirements": [
                        {"metric": "gpu.cuda_compute_capability", "operator": ">=", "value": 8.6}
                    ]
                }
            )

    def test_client_uses_explicit_helper_argv_without_shell_and_writes_private_lease(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workload_path = root / "workload.json"
            output = root / "lease.json"
            helper = root / "helper"
            helper.write_text("fixture\n", encoding="utf-8")
            helper.chmod(0o755)
            workload_path.write_text(
                json.dumps(
                    {
                        "schema": client.WORKLOAD_SCHEMA,
                        "workload_id": "workload-1",
                        "requirements": [{"metric": "gpu.vram_gib", "operator": ">=", "value": 1}],
                    }
                ),
                encoding="utf-8",
            )
            lease = {
                "schema": client.LEASE_SCHEMA,
                "accelerator_uuid": GPU_UUID,
                "purpose": "workload-1",
                "memory_max_bytes": 1073741824,
            }
            completed = mock.Mock(returncode=0, stdout=json.dumps(lease), stderr="")
            with mock.patch.object(os, "geteuid", return_value=1000), mock.patch.object(
                client.subprocess, "run", return_value=completed
            ) as invoked:
                result = client.acquire(workload_path, GPU_UUID, output, helper=helper)
            self.assertEqual(result["accelerator_uuid"], GPU_UUID)
            argv = invoked.call_args.args[0]
            self.assertEqual(argv[:3], ["sudo", "-n", str(helper)])
            self.assertNotIn("shell", invoked.call_args.kwargs)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
