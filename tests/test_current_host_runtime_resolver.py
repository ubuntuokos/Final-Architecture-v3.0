import os
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

    def test_explicit_python_override_is_considered_first(self):
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "python"
            fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake.chmod(0o755)
            with mock.patch.dict(os.environ, {"FA3_AI_PYTHON": str(fake)}, clear=False):
                candidates = resolver.candidate_python_interpreters()
            self.assertEqual(fake.resolve(), candidates[0])

    def test_unreal_override_must_be_executable_and_probe_validated(self):
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "UnrealEditor-Cmd"
            fake.write_text("#!/bin/sh\necho Unreal Engine 5 test\nexit 0\n", encoding="utf-8")
            fake.chmod(0o755)
            with mock.patch.dict(os.environ, {"FA3_UNREAL_EDITOR": str(fake)}, clear=False):
                candidates = resolver.candidate_unreal_binaries()
                self.assertEqual(fake.resolve(), candidates[0])
                result = resolver.resolve_unreal_runtime()
            self.assertEqual(str(fake.resolve()), result["selected"]["path"])
            self.assertEqual("PASS", result["selected"]["probe_status"])

    def test_unreal_probe_failure_is_not_selected(self):
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "UnrealEditor"
            fake.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
            fake.chmod(0o755)
            with mock.patch.object(resolver, "candidate_unreal_binaries", return_value=[fake]):
                result = resolver.resolve_unreal_runtime()
            self.assertIsNone(result["selected"])
            self.assertEqual("ERROR", result["candidates"][0]["probe_status"])

    def test_search_roots_are_bounded_not_whole_home(self):
        roots = [str(p) for p in resolver.approved_python_roots()]
        self.assertNotIn(str(Path.home().resolve()), roots)
        unreal_roots = [str(p) for p in resolver.approved_unreal_roots()]
        self.assertNotIn(str(Path.home().resolve()), unreal_roots)


if __name__ == "__main__":
    unittest.main()
