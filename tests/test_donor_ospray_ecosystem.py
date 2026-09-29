#!/usr/bin/env python3
"""Constrain OSPRay donor ecosystem capture to non-authoritative metadata."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
EXPECTED = {
    "renderkit/ospray", "renderkit/embree", "renderkit/openvkl",
    "renderkit/oidn", "renderkit/rkcommon", "ispc/ispc",
    "oneapi-src/onetbb", "llvm/llvm-project",
    "khronosgroup/sycl-docs", "intel/llvm",
    "oneapi-src/level-zero", "intel/compute-runtime",
    "open-mpi/ompi", "google/snappy", "kitware/cmake",
    "khronosgroup/opengl-registry", "glfw/glfw",
    "google/googletest", "google/benchmark",
    "arm-software/acle", "gcc-mirror/gcc",
    "microsoftdocs/cpp-docs",
}
INTEL_PR_RECONCILIATION = {
    "oneapi-src/onetbb": "FA3-DONOR-ONEAPI-SRC-ONETBB-001",
    "intel/llvm": "FA3-DONOR-INTEL-LLVM-001",
    "oneapi-src/level-zero": "FA3-DONOR-ONEAPI-SRC-LEVEL-ZERO-001",
    "intel/compute-runtime": "FA3-DONOR-INTEL-COMPUTE-RUNTIME-001",
}

class OSPRayDonorEcosystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.rows = cls.registry["entries"]
        cls.by_key = {r["source"]["normalized_key"]: r for r in cls.rows}

    def test_all_22_upstream_sources_present_once(self):
        self.assertEqual(len(EXPECTED), 22)
        self.assertEqual(len(self.rows), len(self.by_key), "duplicate normalized source key")
        self.assertEqual(len(self.rows), len({r["donor_id"] for r in self.rows}), "duplicate donor id")
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.rows))
        self.assertTrue({f"github:{x}" for x in EXPECTED} <= self.by_key.keys())

    def test_candidate_only_fail_closed_and_targeted(self):
        for name in EXPECTED:
            with self.subTest(repo=name):
                row = self.by_key["github:" + name]
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertTrue(row["discoverable_for_planning"])
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                self.assertFalse(row["authority"])
                self.assertTrue(row["target_hints"])
                self.assertTrue(row["capability_hints"])
                for attr in (
                    "automatic_selection", "automatic_fetch", "automatic_install",
                    "automatic_activation", "automatic_dependency", "automatic_code_import",
                    "automatic_provider_admission", "automatic_model_selection"
                ):
                    self.assertIs(row[attr], False, (name, attr))

    def test_hardware_and_upstream_optional_feature_boundaries(self):
        audit = self.registry["hardware_audit"]
        self.assertTrue(audit["vendor_neutral"])
        self.assertTrue(audit["cpu_only_viable"])
        self.assertEqual(audit["accelerator_cardinality"], "0..N")
        self.assertFalse(audit["global_accelerator_requirement"])
        self.assertEqual(audit["live_resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")
        osp = self.by_key["github:renderkit/ospray"]
        self.assertEqual(osp["license"]["declared"], "Apache-2.0")
        self.assertIn("SSE4.1", " ".join(osp["notes"]))
        self.assertIn("NEON", " ".join(osp["notes"]))
        self.assertIn("optional", " ".join(osp["notes"]).lower())
        for key in ("renderkit/openvkl", "renderkit/oidn", "open-mpi/ompi", "khronosgroup/sycl-docs", "intel/llvm"):
            row = self.by_key["github:" + key]
            self.assertTrue(any("option" in note.lower() or "only" in note.lower() for note in row["notes"]))

    def test_pending_intel_source_ids_stable_for_merge_reconciliation(self):
        for name, expected_id in INTEL_PR_RECONCILIATION.items():
            self.assertEqual(self.by_key["github:" + name]["donor_id"], expected_id)

if __name__ == "__main__":
    unittest.main()
