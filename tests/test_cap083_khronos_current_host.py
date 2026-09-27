import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fa3_cap083_khronos_current_host as cap083

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "e98a9a44372df017213e618762dcbcbd871d2989ac5643b1cbf30d3f4d5e1be9"


class Cap083KhronosCurrentHostTests(unittest.TestCase):
    def _coverage_env(self):
        ids = cap083._expected_source_decisions(ROOT)
        return {"FA3_COVERS_SOURCE_DECISION_IDS_JSON": json.dumps(ids, separators=(",", ":"))}

    def _verified(self):
        return {
            "sdk_root": str(ROOT / ".fa3-test-sdk"),
            "prefix": str(ROOT / ".fa3-test-sdk/prefix"),
            "source_count": 19,
            "sources": [],
            "build_receipt_sha256": "a" * 64,
            "source_commit": "test",
        }

    def test_registry_binds_only_cap083_to_dedicated_producer(self):
        reg = json.loads(
            (ROOT / "canonical/current-host-capability-qualification-constituent-producers.json").read_text(encoding="utf-8")
        )
        rows = [x for x in reg["entries"] if x["subject_id"] == "CAP-083"]
        self.assertEqual(3, len(rows))
        self.assertEqual({"positive", "negative", "rollback"}, {x["test_kind"] for x in rows})
        for row in rows:
            self.assertEqual("src/fa3_cap083_khronos_current_host.py", row["adapter_path"])
            self.assertEqual(DIGEST, row["adapter_sha256"])
            self.assertEqual(["--mode", row["test_kind"], "--producer-id", row["producer_id"]], row["argv"])

    def test_source_decision_coverage_includes_khronos_materialization(self):
        ids = cap083._expected_source_decisions(ROOT)
        self.assertIn("FA3-DEC-KHRONOS-OPEN-STANDARDS-2026-09-27", ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_child_environment_is_scoped_and_does_not_mutate_parent(self):
        prefix = ROOT / ".fa3-test-sdk/prefix"
        before = dict(os.environ)
        child = cap083._child_env(prefix)
        self.assertEqual(before, dict(os.environ))
        self.assertEqual(str(prefix / "bin"), child["PATH"].split(os.pathsep)[0])
        self.assertNotIn("VK_LAYER_PATH", child)
        self.assertNotIn("VK_ICD_FILENAMES", child)
        self.assertNotIn("OCL_ICD_VENDORS", child)
        self.assertNotIn("XR_RUNTIME_JSON", child)

    def test_positive_logic_requires_khronos_build_and_functional_smoke(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td, patch.dict(
            os.environ, self._coverage_env(), clear=False
        ), patch.object(
            cap083, "_verify_sources_and_build", return_value=self._verified()
        ), patch.object(
            cap083, "_functional_smoke", return_value={
                "shader_source_sha256": "b" * 64,
                "spirv_sha256": "c" * 64,
                "optimized_spirv_sha256": "d" * 64,
                "reflection_keys": ["entryPoints"],
                "ktx_tool": "/fa3/bin/ktx",
                "ktx_version": "test",
                "installed_runtime_artifacts": {},
                "physical_accelerator_required": False,
                "xr_device_required": False,
                "opencl_device_required": False,
                "child_process_scoped_environment": True,
            }
        ):
            result = cap083.run_mode(ROOT, Path(td), "positive")
        self.assertEqual("PASS", result["status"])
        self.assertFalse(result["functional_smoke"]["physical_accelerator_required"])
        self.assertTrue(result["functional_smoke"]["child_process_scoped_environment"])

    def test_negative_matrix_preserves_host_non_interference(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td, patch.dict(
            os.environ, self._coverage_env(), clear=False
        ), patch.object(cap083, "_verify_sources_and_build", return_value=self._verified()):
            result = cap083.run_mode(ROOT, Path(td), "negative")
        self.assertEqual("PASS", result["status"])
        self.assertTrue(all(result["cases"].values()))

    def test_rollback_restores_exact_child_runtime_projection(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td, patch.dict(
            os.environ, self._coverage_env(), clear=False
        ), patch.object(cap083, "_verify_sources_and_build", return_value=self._verified()):
            result = cap083.run_mode(ROOT, Path(td), "rollback")
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["rollback_hash_equal"])
        self.assertEqual(result["pre_sha256"], result["post_sha256"])
        self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])


if __name__ == "__main__":
    unittest.main()
