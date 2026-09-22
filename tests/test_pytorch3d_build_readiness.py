from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import fa3_pytorch3d_build_readiness as readiness


class PyTorch3DBuildReadinessTests(unittest.TestCase):
    def test_parse_nvcc_version(self) -> None:
        self.assertEqual(
            readiness._parse_nvcc_version("Cuda compilation tools, release 13.0, V13.0.88"),
            "13.0",
        )
        self.assertIsNone(readiness._parse_nvcc_version("not nvcc output"))

    @patch.object(readiness, "_tool")
    @patch.object(readiness, "_probe_cuda")
    @patch.object(readiness, "_cuda_candidates")
    @patch.object(readiness, "_probe_build_venv")
    @patch.object(readiness, "_venv_candidates")
    @patch.object(readiness, "_inspect_source")
    @patch.object(readiness, "_source_candidates")
    def test_matching_isolated_tuple_is_ready(
        self,
        source_candidates,
        inspect_source,
        venv_candidates,
        probe_build_venv,
        cuda_candidates,
        probe_cuda,
        tool,
    ) -> None:
        source_candidates.return_value = [Path("/src")]
        inspect_source.return_value = {
            "path": "/src",
            "exact_revision": True,
            "tracked_tree_clean": True,
        }
        venv_candidates.return_value = [Path("/venv")]
        probe_build_venv.return_value = {
            "path": "/venv",
            "probe_status": "PASS",
            "isolated_pip_venv": True,
            "torch_present": True,
            "torchvision_present": True,
            "python_version": "3.12.0",
            "torch_version": "2.4.1+cu121",
            "torchvision_version": "0.19.1+cu121",
            "torch_cuda": "12.1",
        }
        cuda_candidates.return_value = [Path("/cuda")]
        probe_cuda.return_value = {
            "path": "/cuda",
            "probe_status": "PASS",
            "version": "12.1",
        }
        tool.side_effect = lambda names: {
            "available": True,
            "name": names[0],
            "path": f"/usr/bin/{names[0]}",
        }

        report = readiness.collect(Path("."))
        self.assertEqual(report["status"], "READY_FOR_PINNED_SOURCE_BUILD")
        self.assertEqual(len(report["matching_build_tuples"]), 1)
        self.assertFalse(report["runtime_pass_claim"])
        self.assertFalse(report["global_promotion_claim"])

    @patch.object(readiness, "_tool")
    @patch.object(readiness, "_probe_cuda")
    @patch.object(readiness, "_cuda_candidates")
    @patch.object(readiness, "_probe_build_venv")
    @patch.object(readiness, "_venv_candidates")
    @patch.object(readiness, "_inspect_source")
    @patch.object(readiness, "_source_candidates")
    def test_cuda_mismatch_remains_blocked(
        self,
        source_candidates,
        inspect_source,
        venv_candidates,
        probe_build_venv,
        cuda_candidates,
        probe_cuda,
        tool,
    ) -> None:
        source_candidates.return_value = [Path("/src")]
        inspect_source.return_value = {
            "path": "/src",
            "exact_revision": True,
            "tracked_tree_clean": True,
        }
        venv_candidates.return_value = [Path("/venv")]
        probe_build_venv.return_value = {
            "path": "/venv",
            "probe_status": "PASS",
            "isolated_pip_venv": True,
            "torch_present": True,
            "torchvision_present": True,
            "torch_cuda": "12.1",
        }
        cuda_candidates.return_value = [Path("/cuda")]
        probe_cuda.return_value = {
            "path": "/cuda",
            "probe_status": "PASS",
            "version": "13.0",
        }
        tool.side_effect = lambda names: {
            "available": True,
            "name": names[0],
            "path": f"/usr/bin/{names[0]}",
        }

        report = readiness.collect(Path("."))
        self.assertEqual(report["status"], "BLOCKED_BUILD_READINESS")
        self.assertEqual(report["matching_build_tuples"], [])
        self.assertIn(
            "no isolated build venv has a Torch CUDA major.minor matching an installed nvcc toolkit",
            report["findings"],
        )


if __name__ == "__main__":
    unittest.main()
