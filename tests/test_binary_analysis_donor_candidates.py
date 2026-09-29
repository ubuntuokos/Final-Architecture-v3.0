"""Scope-specific regression for the Binary Analysis donor candidate capture."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
EXPECTED = {
    "github:nationalsecurityagency/ghidra",
    "github:rizinorg/rizin",
    "github:radareorg/radare2",
    "github:unicorn-engine/unicorn",
    "github:frida/frida",
    "github:hexrayssa/ida-sdk",
    "github:perfare/il2cppdumper",
    "github:samboycoding/cpp2il",
}

class BinaryAnalysisDonorCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.by_source = {e["source"]["normalized_key"]: e for e in cls.registry["entries"]}

    def test_eight_verified_distinct_source_candidates(self):
        self.assertEqual(self.registry["id"], "FA3-DONOR-REFERENCE-REGISTRY-001")
        self.assertTrue(EXPECTED.issubset(self.by_source.keys()))
        self.assertEqual(len(self.by_source), len(self.registry["entries"]))
        self.assertEqual(len(self.registry["entries"]), self.registry["backfill"]["entry_count"])
        self.assertEqual(self.registry["capability_count"], 175)

    def test_candidate_capture_is_non_authoritative_fail_closed(self):
        for source in EXPECTED:
            with self.subTest(source=source):
                row = self.by_source[source]
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertFalse(row["authority"])
                self.assertTrue(row["discoverable_for_planning"])
                self.assertIn("Binary & Software Analysis Fabric", row["target_hints"])
                self.assertIn("CAP-080", row["capability_hints"])
                self.assertEqual(row["license"]["status"], "UNKNOWN")
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                for field in (
                    "automatic_selection", "automatic_fetch", "automatic_install",
                    "automatic_activation", "automatic_dependency", "automatic_code_import",
                    "automatic_provider_admission", "automatic_model_selection",
                ):
                    self.assertIs(row[field], False, field)

    def test_preexisting_reverse_skills_record_is_preserved(self):
        row = self.by_source["github:p4nda0s/reverse-skills"]
        self.assertEqual(row["status"], "ANALYZED")
        self.assertFalse(row["authority"])
        self.assertEqual(
            row["code_reuse_policy"],
            "REFERENCE_ONLY_PENDING_LICENSE_AND_BUNDLED_BINARY_PROVENANCE",
        )

if __name__ == "__main__":
    unittest.main()
