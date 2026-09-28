"""Regression checks for the selective NVIDIA GitHub donor curation.

Metadata-only: these checks cannot grant provider, model or runtime admission.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"


class NvidiaDonorCurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.curated = [
            x for x in cls.entries if "nvidia-curation-2026-09-28" in x.get("tags", [])
        ]
        cls.by_key = {x["source"]["normalized_key"]: x for x in cls.entries}

    def test_curated_repository_count_and_discovery_index(self):
        repo_rows = [x for x in self.curated if x["source"]["normalized_key"].startswith("github:nvidia/")]
        self.assertEqual(len(repo_rows), 39)
        self.assertEqual(len(self.curated), 40)
        self.assertIn("github:nvidia", self.by_key)
        self.assertEqual(self.registry["nvidia_github_curation"]["repository_count"], 39)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))

    def test_cross_fabric_targets_and_preserved_model_optimizer_identity(self):
        for source in (
            "github:nvidia/model-optimizer",
            "github:nvidia/tensorrt-llm",
            "github:nvidia/nemo-retriever",
            "github:nvidia/skillSpector".lower(),
            "github:nvidia/openshell",
            "github:nvidia/cosmos",
            "github:nvidia/warp",
            "github:nvidia/nvimagecodec",
            "github:nvidia/cuvs",
            "github:nvidia/personaplex",
            "github:nvidia/dcgm",
            "github:nvidia/gpu-operator",
        ):
            self.assertIn(source, self.by_key)
            self.assertTrue(self.by_key[source]["target_hints"])
        modelopt = self.by_key["github:nvidia/model-optimizer"]
        self.assertEqual(modelopt["donor_id"], "FA3-DONOR-NVIDIA-MODEL-OPTIMIZER-001")
        self.assertEqual(modelopt["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(
            sum(row["source"]["normalized_key"] == "github:nvidia/model-optimizer" for row in self.entries), 1
        )

    def test_no_implicit_admission_or_vendor_requirement(self):
        self.assertTrue(self.registry["hardware_audit"]["vendor_neutral"])
        self.assertTrue(self.registry["hardware_audit"]["cpu_only_viable"])
        self.assertEqual(self.registry["hardware_audit"]["accelerator_cardinality"], "0..N")
        self.assertTrue(self.registry["nvidia_github_curation"]["non_authoritative"])
        for row in self.curated:
            for key in (
                "authority", "automatic_selection", "automatic_fetch",
                "automatic_install", "automatic_activation",
                "automatic_dependency", "automatic_code_import",
                "automatic_provider_admission", "automatic_model_selection",
            ):
                self.assertIs(row[key], False, (row["donor_id"], key))
        archived = self.by_key["github:nvidia/videoprocessingframework"]
        self.assertIn("archived-upstream", archived["tags"])
        self.assertEqual(archived["donor_modes"], ["ARCHITECTURE_PATTERN"])

    def test_registry_source_keys_remain_unique(self):
        self.assertEqual(len(self.entries), len({x["donor_id"] for x in self.entries}))
        self.assertEqual(len(self.entries), len({x["source"]["normalized_key"] for x in self.entries}))


if __name__ == "__main__":
    unittest.main()
