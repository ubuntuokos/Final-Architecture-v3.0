import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import fa3_current_host_runtime_resolver as resolver


class CurrentHostRuntimeResolverTests(unittest.TestCase):
    def test_python_resolver_requires_requested_modules_and_cuda(self):
        candidates = [Path("/fake/cpu-python"), Path("/fake/gpu-python")]
        probes = {
            "/fake/cpu-python": {
                "path": "/fake/cpu-python",
                "probe_status": "PASS",
                "modules": {"torch": True, "pytorch3d": True},
                "cuda_available": False,
                "cuda_count": 0,
            },
            "/fake/gpu-python": {
                "path": "/fake/gpu-python",
                "probe_status": "PASS",
                "modules": {"torch": True, "pytorch3d": False},
                "cuda_available": True,
                "cuda_count": 1,
                "torch_version": "test",
            },
        }
        with mock.patch.object(resolver, "candidate_python_interpreters", return_value=candidates),              mock.patch.object(resolver, "probe_python", side_effect=lambda p: probes[str(p)]):
            gpu = resolver.resolve_python_runtime(
                require_torch=True, require_pytorch3d=False, require_cuda=True
            )
            self.assertEqual("/fake/gpu-python", gpu["selected"]["path"])
            p3d = resolver.resolve_python_runtime(
                require_torch=True, require_pytorch3d=True, require_cuda=False
            )
            self.assertEqual("/fake/cpu-python", p3d["selected"]["path"])

    def test_python_resolver_fails_closed_when_requirements_absent(self):
        row = {
            "path": "/fake/python",
            "probe_status": "PASS",
            "modules": {"torch": False, "pytorch3d": False},
            "cuda_available": False,
            "cuda_count": 0,
        }
        with mock.patch.object(resolver, "candidate_python_interpreters", return_value=[Path("/fake/python")]),              mock.patch.object(resolver, "probe_python", return_value=row):
            result = resolver.resolve_python_runtime(
                require_torch=True, require_pytorch3d=False, require_cuda=True
            )
            self.assertIsNone(result["selected"])

    def test_probe_timeout_is_recorded_without_aborting_discovery(self):
        timeout = subprocess.TimeoutExpired(cmd=["/fake/slow-python"], timeout=30)
        with mock.patch.object(resolver, "run", side_effect=timeout):
            result = resolver.probe_python(Path("/fake/slow-python"))
        self.assertEqual("TIMEOUT", result["probe_status"])
        self.assertEqual("/fake/slow-python", result["path"])
        self.assertEqual(30, result["timeout_seconds"])

    def test_resolver_skips_timeout_and_selects_later_candidate(self):
        candidates = [Path("/fake/slow-python"), Path("/fake/gpu-python")]
        probes = {
            "/fake/slow-python": {
                "path": "/fake/slow-python",
                "probe_status": "TIMEOUT",
                "timeout_seconds": 30,
            },
            "/fake/gpu-python": {
                "path": "/fake/gpu-python",
                "probe_status": "PASS",
                "modules": {"torch": True, "pytorch3d": False},
                "cuda_available": True,
                "cuda_count": 1,
                "torch_version": "test",
            },
        }
        with mock.patch.object(resolver, "candidate_python_interpreters", return_value=candidates),              mock.patch.object(resolver, "probe_python", side_effect=lambda p: probes[str(p)]):
            result = resolver.resolve_python_runtime(
                require_torch=True, require_pytorch3d=False, require_cuda=True
            )
        self.assertEqual("/fake/gpu-python", result["selected"]["path"])
        self.assertEqual("TIMEOUT", result["candidates"][0]["probe_status"])

    def test_explicit_python_override_is_considered_first(self):
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "python"
            fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake.chmod(0o755)
            with mock.patch.dict(os.environ, {"FA3_AI_PYTHON": str(fake)}, clear=False):
                candidates = resolver.candidate_python_interpreters()
            self.assertEqual(fake.resolve(), candidates[0])

    def test_python_override_preserves_venv_symlink_launcher(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = root / "base-python"
            base.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            base.chmod(0o755)
            venv_bin = root / "venv" / "bin"
            venv_bin.mkdir(parents=True)
            launcher = venv_bin / "python"
            launcher.symlink_to(base)
            with mock.patch.dict(os.environ, {"FA3_AI_PYTHON": str(launcher)}, clear=False):
                candidates = resolver.candidate_python_interpreters()
            self.assertEqual(launcher.absolute(), candidates[0])
            self.assertNotEqual(base.resolve(), candidates[0])

    def test_search_roots_are_bounded_not_whole_home(self):
        roots = [str(p) for p in resolver.approved_python_roots()]
        self.assertNotIn(str(Path.home().resolve()), roots)


if __name__ == "__main__":
    unittest.main()
