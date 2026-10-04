"""FIFO-waiting ray/path-tracing donor intake."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-RAY-PATH-TRACING-ECOSYSTEM-2026-10-04.json"

EXISTING_KEYS = {
    "github:gpuopen-librariesandsdks",
    "github:intel/intel-graphics-compiler",
}

NEW_KEYS = {
    "github:raytracing",
    "github:topics/ray-tracing",
    "github:topics/raytracing-engine",
    "github:topics/ray-tracing-in-one-weekend",
    "github:topics/ray-tracer",
    "github:seblague/ray-tracing",
    "github:topics/rtx",
    "github:project-10/openrt",
    "github:worldveil/ray-tracing",
    "github:ancientkingg/cuda-raytracer",
    "github:ancientkingg/rust-raytracer",
    "github:nvidia-rtx",
    "github:bicknyers/raytracer-cpp",
    "github:gpuopen-tools/radeon_raytracing_analyzer",
    "github:gpuopen-drivers/gpurt",
    "github:topics/raytracing",
    "github:topics/cpu-raytracing",
    "github:intel/level-zero-raytracing-support",
    "github:renderkit",
    "github:intel/realtimepathtracingresearchframework",
    "github:canonical/kobuk-gfx-intel-compute-runtime",
    "github:canonical/kobuk-gfx-packages",
}


class WaitingRayPathTracingDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.registry_keys = {
            e["source"]["normalized_key"] for e in cls.registry["entries"]
        }

    def test_parent_and_waiting_state(self):
        d = self.delta
        self.assertEqual(d["parent_main"], "b5052f6595a3fdad84ed7a06e6276f8af5a8dcd8")
        self.assertEqual(d["parent_registry_blob_sha"], "1362d75186c6da74e5cf947fdf0b8867d462636a")
        self.assertEqual(d["parent_entry_count"], 1427)
        self.assertFalse(d["canonical_registry_materialized"])
        self.assertTrue(d["waiting_queue_only"])
        self.assertFalse(d["boundaries"]["canonical_planning_visibility"])

    def test_counts_and_normalization(self):
        d = self.delta
        self.assertEqual(d["submitted_url_count"], 29)
        self.assertEqual(d["duplicate_submission_count"], 0)
        self.assertEqual(d["canonical_alias_collapse_count"], 5)
        self.assertEqual(d["unique_source_count"], 24)
        self.assertEqual(d["matched_existing_count"], 2)
        self.assertEqual(set(d["matched_existing_normalized_keys"]), EXISTING_KEYS)
        self.assertEqual(d["new_source_count"], 22)
        self.assertEqual(d["proposed_entry_count"], 1449)
        self.assertEqual(
            {row["normalized_key"] for row in d["canonical_identities"]},
            NEW_KEYS,
        )

    def test_existing_sources_are_reused_not_duplicated(self):
        self.assertTrue(EXISTING_KEYS <= self.registry_keys)
        self.assertTrue(NEW_KEYS.isdisjoint(self.registry_keys))

    def test_aliases_collapse_to_repository_or_topic_identity(self):
        by_key = {row["canonical_key"]: row["submitted_urls"] for row in self.delta["normalization"]}
        self.assertEqual(len(by_key["github:topics/ray-tracing"]), 3)
        self.assertEqual(len(by_key["github:topics/ray-tracing-in-one-weekend"]), 2)
        self.assertEqual(len(by_key["github:topics/ray-tracer"]), 2)
        self.assertEqual(len(by_key["github:intel/level-zero-raytracing-support"]), 2)

    def test_no_capability_authority_or_runtime_admission(self):
        d = self.delta
        self.assertEqual(d["capability_baseline"], 175)
        self.assertEqual(d["capability_delta"], 0)
        self.assertEqual(d["authority_delta"], 0)
        self.assertEqual(d["usage_edges_created"], 0)
        for key, value in d["boundaries"].items():
            self.assertFalse(value, key)

    def test_cuda_and_khronos_boundaries_are_explicit(self):
        req = "\n".join(self.delta["requirements"])
        self.assertIn("FA3-CUDA-PORTABILITY-SHARED-FUNCTION-POLICY-001", req)
        self.assertIn("FA3-KHRONOS-OPEN-STANDARDS-001", req)
        self.assertIn("CAP-127", req)
        self.assertIn("CAP-161", req)


if __name__ == "__main__":
    unittest.main()
