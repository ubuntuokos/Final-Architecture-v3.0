"""Static donor/plan regression only; never a runtime or current-host quality gate."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "canonical" / "FA3-DONOR-REFERENCE-REGISTRY-001.json"
R2 = ROOT / "docs" / "production-import-selective-quality-curation-round2-2026-09-29.md"
SELECTORS = ROOT / "docs" / "production-import-selective-content-plan-2026-09-29.md"
NEW = {
    "github:ina-foss/inaspeechsegmenter",
    "github:montrealcorpustools/montreal-forced-aligner",
    "github:mtg/essentia",
    "github:audeering/opensmile",
    "github:facebookresearch/stopes",
    "github:wyattblue/auto-editor",
    "github:facebookresearch/sonar",
    "github:sigsep/sigsep-mus-eval",
    "github:librosa/librosa",
}
EXISTING_ENRICHED = "github:laion-ai/clap"


class SelectiveImportQualityRound2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = json.loads(REG.read_text(encoding="utf-8"))
        cls.entries = cls.reg["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}
        cls.research = R2.read_text(encoding="utf-8")
        cls.selector_plan = SELECTORS.read_text(encoding="utf-8")

    def test_registry_source_uniqueness_and_fixed_baseline(self):
        self.assertEqual(len(self.by_key), len(self.entries))
        self.assertEqual(len({e["donor_id"] for e in self.entries}), len(self.entries))
        self.assertEqual(self.reg["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.reg["capability_count"], 175)
        self.assertFalse(self.reg["new_capability"])
        self.assertFalse(self.reg["new_architectural_authority"])

    def test_nine_new_candidates_and_one_existing_donor_enriched(self):
        self.assertEqual(len(NEW), 9)
        for key in NEW:
            with self.subTest(key=key):
                row = self.by_key[key]
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertIn("Production Import & Migration Fabric", row["target_hints"])
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                self.assertFalse(row["authority"])
                for flag in (
                    "automatic_selection", "automatic_fetch", "automatic_install",
                    "automatic_activation", "automatic_dependency", "automatic_code_import",
                    "automatic_provider_admission", "automatic_model_selection"
                ):
                    self.assertFalse(row[flag], (key, flag))
        self.assertIn(EXISTING_ENRICHED, self.by_key)
        self.assertIn(
            "Production Import & Migration Fabric",
            self.by_key[EXISTING_ENRICHED]["target_hints"],
        )

    def test_explicit_noncommercial_and_conda_exclusion(self):
        opensmile = self.by_key["github:audeering/opensmile"]
        self.assertIn("NONCOMMERCIAL", opensmile["license"]["declared"])
        self.assertTrue(any("commercial" in n.lower() and "license" in n.lower()
                            for n in opensmile["notes"]))
        mfa = self.by_key["github:montrealcorpustools/montreal-forced-aligner"]
        self.assertTrue(any("conda" in n.lower() and "venv" in n.lower()
                            for n in mfa["notes"]))
        self.assertIn("Conda/Mamba", self.research)
        self.assertIn("AGPL", self.research)

    def test_quality_boundaries_and_existing_owners_are_explicit(self):
        for value in (
            "singing", "ambience", "SFX", "original discrete tracks",
            "UNSUPPORTED", "estimated", "ground-truth", "source_start",
            "human", "Subtitle Studio", "Language Fabric",
            "Director/Workforce", "HRB", "Model Router", "175",
            "no runtime", "openSMILE", "SONAR", "CLAP",
        ):
            with self.subTest(value=value):
                self.assertIn(value.lower(), self.research.lower())

    def test_parent_17_selectors_unmodified(self):
        rows = re.findall(
            r"^\|\s*(TEXT|AUDIO|VIDEO)\s*\|\s*`([A-Z_]+)`\s*\|\s*([^|]+)\|",
            self.selector_plan, re.MULTILINE
        )
        self.assertEqual(len(rows), 17)
        self.assertEqual({family: sum(f == family for f, _, _ in rows)
                          for family in ("TEXT", "AUDIO", "VIDEO")},
                         {"TEXT": 4, "AUDIO": 6, "VIDEO": 7})


if __name__ == "__main__":
    unittest.main()
