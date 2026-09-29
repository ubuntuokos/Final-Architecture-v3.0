"""Regression checks for Oracle, Ubuntu and Kubuntu candidate-only donor capture."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
CURATION = ROOT / "docs/donor-oracle-ubuntu-kubuntu-2026-09-29.md"

EXPECTED = {
    "github:oracle", "github:oracle-devrel", "github:ubuntu",
    "github:kubuntu-team", "github:topics/kubuntu",
    "github:oracle/graal", "github:oracle/opengrok",
    "github:oracle-devrel/technology-engineering",
    "github:oracle-devrel/linux-virt-labs",
    "github:ubuntu/app-center", "github:ubuntu/ubuntu-make",
    "github:kubuntu-team/kubuqa", "github:kubuntu-team/kubuntu-manual",
}
FALSE_FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)


class OracleUbuntuKubuntuDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_canonical_integrity(self):
        self.assertEqual(self.registry["id"], "FA3-DONOR-REFERENCE-REGISTRY-001")
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(len(self.by_key), len(self.entries))
        self.assertEqual(len({e["donor_id"] for e in self.entries}), len(self.entries))

    def test_each_supplied_and_curated_source_is_candidate_only(self):
        self.assertEqual(len(EXPECTED), 13)
        for key in sorted(EXPECTED):
            with self.subTest(source=key):
                self.assertIn(key, self.by_key)
                entry = self.by_key[key]
                self.assertEqual(entry["status"], "CANDIDATE")
                self.assertEqual(entry["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                for flag in FALSE_FLAGS:
                    self.assertIs(entry[flag], False, (key, flag))

    def test_discovery_indexes_remain_indexes(self):
        for key in (
            "github:oracle", "github:oracle-devrel",
            "github:ubuntu", "github:kubuntu-team",
        ):
            self.assertEqual(self.by_key[key]["source"]["kind"], "GITHUB_ORGANIZATION")
            self.assertEqual(self.by_key[key]["donor_modes"], ["DISCOVERY_INDEX"])
        topic = self.by_key["github:topics/kubuntu"]
        self.assertEqual(topic["source"]["kind"], "GITHUB_TOPIC")
        self.assertEqual(topic["discovery_filter"]["language"], "Python")
        self.assertEqual(topic["discovery_filter"]["observed_url"],
                         "https://github.com/topics/kubuntu?l=python")
        self.assertIsNone(topic["discovery_filter"]["observed_count"])

    def test_curation_document_exists(self):
        text = CURATION.read_text(encoding="utf-8")
        for name in ("Oracle", "Ubuntu", "Kubuntu", "605", "175"):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
