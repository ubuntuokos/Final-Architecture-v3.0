"""Guard canonical donor identity uniqueness and legacy-key continuity."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"


class DonorIdentityUniquenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]

    def test_unique_ids_and_primary_source_keys(self):
        ids = [entry["donor_id"] for entry in self.entries]
        keys = [entry["source"]["normalized_key"] for entry in self.entries]
        self.assertEqual(len(ids), len(set(ids)), "Repeated canonical donor ID")
        self.assertEqual(len(keys), len(set(keys)), "Repeated primary source key")
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))

    def test_project_aliases_resolve_to_single_upstream_identity(self):
        for donor_id, canonical_key, legacy_key, expected_status in (
            ("FA3-DONOR-G-MIC-001", "github:greyclab/gmic", "project:g'mic", "ANALYZED"),
            ("FA3-DONOR-NVIDIA-MODEL-OPTIMIZER-001",
             "github:nvidia/model-optimizer", "project:nvidia-model-optimizer",
             "ACCEPTED_REFERENCE"),
        ):
            with self.subTest(donor_id=donor_id):
                records = [e for e in self.entries if e["donor_id"] == donor_id]
                self.assertEqual(len(records), 1)
                record = records[0]
                self.assertEqual(record["source"]["normalized_key"], canonical_key)
                self.assertIn(legacy_key, record["legacy_source_keys"])
                self.assertNotIn(legacy_key, {
                    e["source"]["normalized_key"] for e in self.entries
                })
                self.assertIn("prior-fa3-research-backfill", record["discovered_from"])
                self.assertEqual(record["status"], expected_status)
                for flag in (
                    "authority", "automatic_selection", "automatic_fetch",
                    "automatic_install", "automatic_activation", "automatic_dependency",
                    "automatic_code_import", "automatic_provider_admission",
                    "automatic_model_selection",
                ):
                    self.assertIs(record[flag], False, (donor_id, flag))


    def test_pr435_verified_upstream_pins_preserve_historical_aliases(self):
        pins = (
            ("FA3-DONOR-DONKEY-001", "github:donkeycut/donkey", "project:donkey", "f1238b4dadb21f2505433de0bac6c4b3c5746bfe"),
            ("FA3-DONOR-OPENCUT-001", "github:opencut-app/opencut", "project:opencut", "e668010778568641babef2cc40be4703ae6916d6"),
            ("FA3-DONOR-HYPERFRAMES-001", "github:heygen-com/hyperframes", "project:hyperframes", "b41ef425cc0700f6a5d8d29b23a812af2f2f2f06"),
            ("FA3-DONOR-VIBE-001", "github:thewh1teagle/vibe", "project:vibe", "4d1db65fd07d7927d7b4ef3a3d949539010147dc"),
            ("FA3-DONOR-WAN2-2-001", "github:wan-video/wan2.2", "project:wan2.2", "1ea34ff48f87168174e12956e200b1d908b1c5ff"),
            ("FA3-DONOR-PRESENTON-001", "github:presenton/presenton", "project:presenton", "f9d3eba1a25712e25766b35a7af3b25f93ec1c01"),
        )
        by_id = {row["donor_id"]: row for row in self.entries}
        canonical = {row["source"]["normalized_key"] for row in self.entries}
        aliases = [key for row in self.entries for key in row.get("legacy_source_keys", [])]
        # Preserve the original #435 pinned donors while allowing serial donor expansion.
        self.assertGreaterEqual(len(self.entries), 1116)
        self.assertEqual(len(aliases), 9)
        self.assertEqual(len(aliases), len(set(aliases)))
        self.assertFalse(canonical.intersection(aliases))
        for donor_id, new_key, old_key, pinned_commit in pins:
            with self.subTest(donor_id=donor_id):
                record = by_id[donor_id]
                self.assertEqual(record["source"]["normalized_key"], new_key)
                self.assertIn(old_key, record["legacy_source_keys"])
                self.assertEqual(record["source"]["upstream_pin"]["commit_sha"], pinned_commit)
                self.assertIn("historical-pr-435-verified-upstream-identity", record["discovered_from"])
                self.assertIs(record["automatic_code_import"], False)
                self.assertIs(record["automatic_provider_admission"], False)
                self.assertIs(record["authority"], False)
        anil = by_id["FA3-DONOR-ANIL-MATCHA-OPEN-GENERATIVE-AI-001"]
        self.assertEqual(anil["source"]["normalized_key"], "github:anil-matcha/open-generative-ai")
        self.assertEqual(anil["source"]["upstream_pin"]["commit_sha"], "9d939bc8f29ae39b778a2ce4146a9c1df12700f4")

    def test_historical_alias_capture_is_idempotent(self):
        from tempfile import TemporaryDirectory
        from fa3_donor_registry import capture_candidate
        with TemporaryDirectory() as d:
            root = Path(d)
            path = root / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
            path.parent.mkdir(parents=True)
            row = next(e for e in self.entries if e["donor_id"] == "FA3-DONOR-OPENCUT-001")
            path.write_text(json.dumps({"id": "FA3-DONOR-REFERENCE-REGISTRY-001",
                                        "entries": [row]}, ensure_ascii=False))
            result = capture_candidate(root, name="OpenCut", source_kind="PROJECT",
                                       source_locator="project:OpenCut", seen_date="2026-09-29")
            after = json.loads(path.read_text())
            self.assertFalse(result["created"])
            self.assertEqual(result["normalized_key"], "github:opencut-app/opencut")
            self.assertEqual(len(after["entries"]), 1)
            self.assertIn("project:opencut", after["entries"][0]["legacy_source_keys"])


if __name__ == "__main__":
    unittest.main()
