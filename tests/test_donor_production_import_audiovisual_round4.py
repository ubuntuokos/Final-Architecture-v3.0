"""Static round-4 donor and selective-import planning checks; NOT runtime/current-host tests."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG_PATH = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
SEL_PATH = ROOT / "docs/production-import-selective-content-plan-2026-09-29.md"
R4_PATH = ROOT / "docs/production-import-selective-audiovisual-research-round4-2026-09-29.md"
NEW = {
    "github:sony/mmaudiosep",
    "github:openmirlab/bs-roformer-infer",
    "github:kahozue/traduko",
    "github:lucidrains/bs-roformer",
    "github:hkchengrex/av-benchmark",
}
TEXT_LABELS = {
    "Eredeti nyelven",
    "Egy kiválasztott nyelven",
    "Több nyelvre lefordítva",
    "Eredeti és fordított változatok együtt",
}
AUDIO_LABELS = {
    "Teljes hang",
    "Csak szöveges átirat",
    "Beszéd vagy ének külön",
    "Csak zene, ének nélkül",
    "Környezeti hangok és hangeffektusok",
    "Zajcsökkentett beszéd",
}
VIDEO_LABELS = {
    "Teljes videó",
    "Csak kép, hang nélkül",
    "Csak teljes hang",
    "Csak beszédátirat",
    "Csak zene vagy instrumentális rész",
    "Csak környezeti hangok és effektek",
    "Képkockák vagy kiválasztott jelenetek",
}


class ProductionImportAudiovisualRound4StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REG_PATH.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_source = {x["source"]["normalized_key"]: x for x in cls.entries}
        cls.selectors = SEL_PATH.read_text(encoding="utf-8")
        cls.research = R4_PATH.read_text(encoding="utf-8")

    def test_canonical_registry_unique_and_capability_175(self):
        self.assertEqual(len(self.entries), len(self.by_source))
        self.assertEqual(len(self.entries), len({e["donor_id"] for e in self.entries}))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertGreaterEqual(len(self.entries), 654)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.registry["new_capability"])
        self.assertFalse(self.registry["new_architectural_authority"])

    def test_five_candidate_sources_and_non_authoritative_flags(self):
        for key in NEW:
            with self.subTest(source=key):
                item = self.by_source[key]
                self.assertEqual(item["status"], "CANDIDATE")
                self.assertIn("Production Import & Migration Fabric", item["target_hints"])
                self.assertEqual(
                    item["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW"
                )
                self.assertFalse(item["authority"])
                for k in (
                    "automatic_selection", "automatic_fetch", "automatic_install",
                    "automatic_activation", "automatic_dependency",
                    "automatic_code_import", "automatic_provider_admission",
                    "automatic_model_selection",
                ):
                    self.assertIs(item[k], False, (key, k))

    def test_existing_blender_enriched_not_duplicated(self):
        blender = self.by_source["github:blender/blender"]
        self.assertIn("Production Import & Migration Fabric", blender["target_hints"])
        self.assertTrue(any("OpenTimelineIO" in s for s in blender.get("notes", [])))

    def test_all_exact_seventeen_user_selectors_unchanged(self):
        rows = re.findall(
            r"^\|\s*(TEXT|AUDIO|VIDEO)\s*\|\s*`([A-Z_]+)`\s*\|\s*([^|]+)\|",
            self.selectors, re.MULTILINE
        )
        self.assertEqual(len(rows), 17)
        for family, expected in (("TEXT", TEXT_LABELS), ("AUDIO", AUDIO_LABELS),
                                 ("VIDEO", VIDEO_LABELS)):
            with self.subTest(family=family):
                labels = {label.strip() for row_family, _, label in rows
                          if row_family == family}
                self.assertEqual(labels, expected)

    def test_separation_and_license_boundaries_documented(self):
        for token in (
            "Conda/Mamba", "pretrained models", "10 GB", "checkpoint",
            "SOURCE", "ESTIMATED", "UNSUPPORTED", "MMAudioSep", "BS-RoFormer",
            "Video Editor", "Model Router", "HRB", "Music Studio",
            "NO_AV_FETCH", "caption-only", "zero", "175",
        ):
            with self.subTest(token=token):
                self.assertIn(token.lower(), self.research.lower())

    def test_existing_authorities_and_physical_evidence_retained(self):
        for token in (
            "Language Fabric", "Subtitle Studio", "Temporal", "Evidence",
            "Reuse Discovery", "Software Coexistence", "current-host",
            "original", "per-output", "17", "source", "licens",
        ):
            with self.subTest(token=token):
                self.assertIn(token.lower(), self.research.lower())


if __name__ == "__main__":
    unittest.main()
