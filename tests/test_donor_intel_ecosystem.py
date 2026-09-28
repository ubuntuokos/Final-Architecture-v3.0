from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DISCOVERY = "official-intel-github-ecosystem-review-2026-09-28"
EXPECTED_KEYS = set([
    "github:habanaai",
    "github:habanaai/gaudi-pytorch-bridge",
    "github:habanaai/model-references",
    "github:intel",
    "github:intel/ai-playground",
    "github:intel/auto-round",
    "github:intel/compute-runtime",
    "github:intel/confidential-computing.sgx",
    "github:intel/gmmlib",
    "github:intel/intel-cmt-cat",
    "github:intel/intel-device-plugins-for-kubernetes",
    "github:intel/intel-extension-for-pytorch",
    "github:intel/intel-extension-for-tensorflow",
    "github:intel/intel-extension-for-transformers",
    "github:intel/intel-graphics-compiler",
    "github:intel/intel-npu-acceleration-library",
    "github:intel/intel-resource-drivers-for-kubernetes",
    "github:intel/intel-xpu-backend-for-triton",
    "github:intel/ipex-llm",
    "github:intel/ittapi",
    "github:intel/libvpl",
    "github:intel/linux-npu-driver",
    "github:intel/linux-sgx",
    "github:intel/llm-scaler",
    "github:intel/llvm",
    "github:intel/media-driver",
    "github:intel/metrics-discovery",
    "github:intel/metrics-library",
    "github:intel/neural-compressor",
    "github:intel/pcm",
    "github:intel/pepc",
    "github:intel/pti-gpu",
    "github:intel/scikit-learn-intelex",
    "github:intel/sgxdatacenterattestationprimitives",
    "github:intel/torch-xpu-ops",
    "github:intel/xpumanager",
    "github:oneapi-src",
    "github:oneapi-src/level-zero",
    "github:oneapi-src/oneapi-samples",
    "github:oneapi-src/oneccl",
    "github:oneapi-src/onedal",
    "github:oneapi-src/onednn",
    "github:oneapi-src/onedpl",
    "github:oneapi-src/onemkl",
    "github:oneapi-src/onetbb",
    "github:oneapi-src/syclomatic",
    "github:opea-project",
    "github:opea-project/genaicomps",
    "github:opea-project/genaiexamples",
    "github:openvinotoolkit",
    "github:openvinotoolkit/model_server",
    "github:openvinotoolkit/open_model_zoo",
    "github:openvinotoolkit/openvino",
    "github:openvinotoolkit/openvino.genai",
    "github:openvinotoolkit/openvino_notebooks"
])
ARCHIVED = {"github:intel/ipex-llm", "github:intel/intel-extension-for-transformers",
            "github:intel/intel-extension-for-pytorch", "github:intel/intel-npu-acceleration-library",
            "github:habanaai/model-references"}
ORGANIZATION_INDEXES = {"github:intel", "github:oneapi-src", "github:openvinotoolkit",
                        "github:habanaai", "github:opea-project"}


class IntelEcosystemDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.rows = cls.registry["entries"]
        cls.new = [row for row in cls.rows if DISCOVERY in row.get("discovered_from", [])]

    def test_exact_source_identity_and_counts(self):
        keys = [row["source"]["normalized_key"] for row in self.rows]
        ids = [row["donor_id"] for row in self.rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({row["source"]["normalized_key"] for row in self.new}, EXPECTED_KEYS)
        self.assertEqual(len(self.new), 55)
        self.assertEqual(len(EXPECTED_KEYS - ORGANIZATION_INDEXES), 50)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.rows))
        self.assertGreaterEqual(len(self.rows), 306)

    def test_all_intel_sources_remain_non_authoritative_and_unadmitted(self):
        for row in self.new:
            with self.subTest(row=row["donor_id"]):
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertTrue(row["discoverable_for_planning"])
                self.assertTrue(row["target_hints"])
                self.assertEqual(row["license"]["status"], "UNKNOWN")
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                for field in ("authority", "automatic_selection", "automatic_fetch",
                              "automatic_install", "automatic_activation", "automatic_dependency",
                              "automatic_code_import", "automatic_provider_admission",
                              "automatic_model_selection"):
                    self.assertIs(row[field], False, field)
                self.assertIs(row["upstream_observation"]["source_copy_allowed"], False)
                self.assertIs(row["upstream_observation"]["license_audited"], False)

    def test_archive_is_restricted_to_historical_patterns(self):
        actual = {r["source"]["normalized_key"] for r in self.new
                  if r["upstream_observation"]["archived"]}
        self.assertEqual(actual, ARCHIVED)
        for row in self.new:
            if row["upstream_observation"]["archived"]:
                self.assertIn("historical", " ".join(row["notes"]).lower())
        for index in ORGANIZATION_INDEXES:
            row = next(r for r in self.new if r["source"]["normalized_key"] == index)
            self.assertIn("official-ecosystem-index", row["tags"])
            self.assertTrue(any("Standing discovery index" in note for note in row["notes"]))

    def test_hardware_and_prior_donor_lifecycle_not_modified(self):
        audit = self.registry["hardware_audit"]
        self.assertIs(audit["vendor_neutral"], True)
        self.assertIs(audit["cpu_only_viable"], True)
        self.assertEqual(audit["accelerator_cardinality"], "0..N")
        self.assertIs(audit["runtime_hardware_dependency"], False)
        self.assertEqual(audit["live_resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")
        self.assertEqual(self.registry["capability_count"], 175)
        original = next(r for r in self.rows if r["donor_id"] == "FA3-DONOR-NVIDIA-MODEL-OPTIMIZER-001")
        self.assertEqual(original["status"], "ACCEPTED_REFERENCE")


if __name__ == "__main__":
    unittest.main()
