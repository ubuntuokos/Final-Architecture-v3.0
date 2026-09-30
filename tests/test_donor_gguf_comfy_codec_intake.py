"""Exact owner-marked GGUF, Comfy, codec donor intake regression tests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-GGUF-COMFY-CODEC-2026-09-30.json"
EXPECTED = {
  "github:topics/gguf": [
    "FA3-DONOR-GGUF-TOPIC-001",
    "https://github.com/topics/gguf",
    "GITHUB_TOPIC"
  ],
  "github:topics/gguf-models": [
    "FA3-DONOR-GGUF-MODELS-TOPIC-001",
    "https://github.com/topics/gguf-models",
    "GITHUB_TOPIC"
  ],
  "github:city96/comfyui-gguf": [
    "FA3-DONOR-CITY96-COMFYUI-GGUF-001",
    "https://github.com/city96/ComfyUI-GGUF",
    "GITHUB"
  ],
  "github:ibm/gguf": [
    "FA3-DONOR-IBM-GGUF-001",
    "https://github.com/IBM/gguf",
    "GITHUB"
  ],
  "github:huggingface": [
    "FA3-DONOR-HUGGINGFACE-ORG-001",
    "https://github.com/huggingface",
    "GITHUB_ORGANIZATION"
  ],
  "github:calcuis": [
    "FA3-DONOR-CALCUIS-PROFILE-001",
    "https://github.com/calcuis",
    "GITHUB_PROFILE"
  ],
  "github:topics/gguf?l=go&o=asc&s=stars": [
    "FA3-DONOR-GGUF-GO-TOPIC-001",
    "https://github.com/topics/gguf?l=go&o=asc&s=stars",
    "GITHUB_TOPIC"
  ],
  "github:mitjafelicijan": [
    "FA3-DONOR-MITJAFELICIJAN-PROFILE-001",
    "https://github.com/mitjafelicijan",
    "GITHUB_PROFILE"
  ],
  "github:comfy-org": [
    "FA3-DONOR-COMFY-ORG-001",
    "https://github.com/orgs/Comfy-Org/repositories",
    "GITHUB_ORGANIZATION"
  ],
  "github:comfy-org/desktop": [
    "FA3-DONOR-COMFY-ORG-DESKTOP-ARCHIVED-001",
    "https://github.com/Comfy-Org/desktop",
    "GITHUB"
  ],
  "github:topics/codec-evaluation": [
    "FA3-DONOR-CODEC-EVALUATION-TOPIC-001",
    "https://github.com/topics/codec-evaluation",
    "GITHUB_TOPIC"
  ],
  "github:topics/quicktime?l=swift": [
    "FA3-DONOR-QUICKTIME-SWIFT-TOPIC-001",
    "https://github.com/topics/quicktime?l=swift",
    "GITHUB_TOPIC"
  ]
}
FLAGS = ("authority", "automatic_selection", "automatic_fetch", "automatic_install",
         "automatic_activation", "automatic_dependency", "automatic_code_import",
         "automatic_provider_admission", "automatic_model_selection")

class GGUFComfyCodecIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {entry["source"]["normalized_key"]: entry for entry in cls.entries}

    def test_derived_counts_and_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(len(self.entries), 1233)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["source_count"], 12)
        self.assertEqual(self.delta["previous_registry_count"], 1221)
        self.assertEqual(self.delta["expected_registry_count"], 1233)

    def test_all_exact_marked_urls_reference_only(self):
        self.assertEqual(len(EXPECTED), 12)
        self.assertEqual(set(EXPECTED), {x["normalized_source_key"] for x in self.delta["sources"]})
        for key, (donor_id, url, kind) in EXPECTED.items():
            with self.subTest(key=key):
                row = self.by_key[key]
                self.assertEqual(row["donor_id"], donor_id)
                self.assertEqual(row["source"]["locator"], url)
                self.assertEqual(row["source"]["kind"], kind)
                self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
                self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
                self.assertFalse(row["submission_review"]["second_registry_approval_required"])
                self.assertTrue(all(row[flag] is False for flag in FLAGS))
                self.assertTrue(row["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))

    def test_dynamic_index_scopes_and_archived_source(self):
        self.assertEqual(self.by_key["github:topics/gguf?l=go&o=asc&s=stars"]["discovery_filter"],
                         {"language": "go", "sort": "stars", "order": "asc",
                          "observed_url": "https://github.com/topics/gguf?l=go&o=asc&s=stars",
                          "observed_at": "2026-09-30"})
        self.assertEqual(self.by_key["github:topics/quicktime?l=swift"]["discovery_filter"]["language"], "swift")
        row = self.by_key["github:comfy-org/desktop"]
        self.assertTrue(row["upstream_archived"])
        self.assertEqual(row["source"]["locator"], "https://github.com/Comfy-Org/desktop")
        self.assertNotIn("github:comfy-org/comfy-desktop", EXPECTED)
        self.assertEqual(self.by_key["github:city96/comfyui-gguf"]["license"]["declared"], "Apache-2.0")
        self.assertEqual(self.by_key["github:ibm/gguf"]["license"]["declared"], "Apache-2.0")

    def test_indexes_do_not_recursively_admit_child_repos(self):
        for key in ("github:huggingface", "github:calcuis", "github:mitjafelicijan", "github:comfy-org"):
            self.assertEqual(self.by_key[key]["donor_modes"][0], "DISCOVERY_INDEX")
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertFalse(self.delta["authority"])

if __name__ == "__main__":
    unittest.main()
