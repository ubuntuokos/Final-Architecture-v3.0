"""Metadata-only donor research regression. Not a physical runtime/quality proof."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
PLAN = ROOT / "docs/production-import-selective-content-plan-2026-09-29.md"
ANNEX = ROOT / "docs/production-import-selective-quality-extension-2026-09-29.md"

NEW_SOURCES = {
    "unbabel/comet",
    "marian-nmt/marian",
    "browsermt/bergamot-translator",
    "rikorose/deepfilternet",
    "deezer/spleeter",
    "sigsep/open-unmix-pytorch",
    "qiuqiangkong/audioset_tagging_cnn",
    "laion-ai/clap",
    "speechbrain/speechbrain",
    "facebookresearch/seamless_communication",
    "sonic-visualiser/sonic-visualiser",
}
BLOCKED_FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class ProductionImportQualityResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = json.loads(REG.read_text(encoding="utf-8"))
        cls.entries = cls.reg["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}
        cls.plan = PLAN.read_text(encoding="utf-8")
        cls.annex = ANNEX.read_text(encoding="utf-8")

    def test_lossless_registry_identity_and_175_fixed(self):
        self.assertGreaterEqual(len(self.entries), 624)
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(len(self.entries), len({e["donor_id"] for e in self.entries}))
        self.assertEqual(self.reg["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.reg["capability_count"], 175)
        self.assertIs(self.reg["new_capability"], False)
        self.assertIs(self.reg["new_architectural_authority"], False)

    def test_all_11_source_unique_references_are_non_authoritative(self):
        self.assertEqual(len(NEW_SOURCES), 11)
        for name in sorted(NEW_SOURCES):
            with self.subTest(repo=name):
                item = self.by_key["github:" + name]
                self.assertEqual(item["status"], "CANDIDATE")
                self.assertEqual(item["source"]["locator"].lower(), "https://github.com/" + name)
                self.assertIn("Production Import & Migration Fabric", item["target_hints"])
                self.assertEqual(item["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                self.assertEqual(item["first_seen"], "2026-09-29")
                for flag in BLOCKED_FLAGS:
                    self.assertIs(item[flag], False, (name, flag))
                self.assertIn("https://github.com/" + name, self.annex.lower())

    def test_seamless_nc_reference_never_auto_admitted(self):
        item = self.by_key["github:facebookresearch/seamless_communication"]
        self.assertEqual(item["license"]["declared"], "CC-BY-NC-4.0")
        self.assertIn("NONCOMMERCIAL", item["license"]["status"])
        self.assertFalse(item["automatic_activation"])
        self.assertFalse(item["automatic_code_import"])
        self.assertIn("noncommercial reference-only", self.annex.lower())

    def test_existing_separation_and_conversion_donors_preserved(self):
        for key in (
            "github:ffmpeg/ffmpeg", "github:adefossez/demucs",
            "github:academysoftwarefoundation/opentimelineio",
            "project:ayon", "project:openassetio",
            "github:argosopentech/argos-translate",
            "github:m-bain/whisperx",
            "github:audio-agi/audiosep",
        ):
            with self.subTest(existing=key):
                self.assertIn(key, self.by_key)

    def test_17_existing_hungarian_labels_remain_source_of_truth(self):
        rows = re.findall(
            r"^\\|\\s*(TEXT|AUDIO|VIDEO)\\s*\\|\\s*`([A-Z_]+)`\\s*\\|\\s*([^|]+)\\|",
            self.plan, re.MULTILINE,
        )
        # Avoid a competing selector enum in the quality annex.
        self.assertEqual(len(rows), 17)
        self.assertEqual(
            {kind: sum(1 for row in rows if row[0] == kind) for kind in ("TEXT", "AUDIO", "VIDEO")},
            {"TEXT": 4, "AUDIO": 6, "VIDEO": 7},
        )
        self.assertEqual(len({row[1] for row in rows}), 16)  # TRANSCRIPT_ONLY shared between audio and video
        self.assertIn("17-selector plan", self.annex)

    def test_method_fidelity_and_negative_exclusions_documented(self):
        for marker in (
            "ORIGINAL_TRACK_EXTRACT", "ESTIMATED_SEPARATION",
            "TRANSLATED_DERIVATIVE", "INSPECT_ONLY",
            "classification is not source separation",
            "Denoiser", "SFX-only", "Q7 release gates",
            "Temporal", "HRB", "Model Router", "175",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker.lower(), self.annex.lower())

if __name__ == "__main__":
    unittest.main()
