"""Static metadata/plan regression; never a current-host or fidelity PASS."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "canonical" / "FA3-DONOR-REFERENCE-REGISTRY-001.json"
PARENT = ROOT / "docs" / "production-import-selective-content-plan-2026-09-29.md"
WORKPLAN = ROOT / "docs" / "production-import-selective-implementation-workplan-2026-09-29.md"

ROUND3 = {
    "github:smacke/ffsubsync": "MIT",
    "github:pyav-org/pyav": "BSD-3-Clause",
    "github:translate/translate": "GPL-3.0",
    "github:marl/jams": "ISC",
    "github:python-babel/babel": "BSD-3-Clause",
    "github:cisnlp/simalign": "MIT",
}

class ProductionImportSelectiveWorkplanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(REG.read_text(encoding="utf-8"))
        cls.entries = cls.data["entries"]
        cls.bykey = {x["source"]["normalized_key"]: x for x in cls.entries}
        cls.plan = WORKPLAN.read_text(encoding="utf-8")
        cls.selectors = PARENT.read_text(encoding="utf-8")

    def test_registry_exact_unique_and_fixed_capabilities(self):
        self.assertEqual(len(self.entries), len(self.bykey))
        self.assertEqual(len({x["donor_id"] for x in self.entries}), len(self.entries))
        self.assertEqual(self.data["backfill"]["entry_count"], len(self.entries))
        self.assertGreaterEqual(len(self.entries), 639)
        self.assertEqual(self.data["capability_count"], 175)
        self.assertFalse(self.data["new_capability"])
        self.assertFalse(self.data["new_architectural_authority"])

    def test_six_exact_researched_sources_not_admitted(self):
        self.assertEqual(len(ROUND3), 6)
        for key, license_id in ROUND3.items():
            with self.subTest(key=key):
                row = self.bykey[key]
                self.assertEqual(row["license"]["declared"], license_id)
                self.assertEqual(row["license"]["status"], "UPSTREAM_GITHUB_METADATA_ONLY")
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertIn("Production Import & Migration Fabric", row["target_hints"])
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                self.assertFalse(row["authority"])
                for flag in ("automatic_selection", "automatic_fetch", "automatic_install",
                             "automatic_activation", "automatic_dependency", "automatic_code_import",
                             "automatic_provider_admission", "automatic_model_selection"):
                    self.assertFalse(row[flag], (key, flag))

    def test_exact_original_17_selectors_unmodified(self):
        rows = re.findall(
            r"^\|\s*(TEXT|AUDIO|VIDEO)\s*\|\s*\`([A-Z_]+)\`\s*\|\s*([^|]+)\|",
            self.selectors, re.MULTILINE)
        self.assertEqual(len(rows), 17)
        self.assertEqual({k: sum(f == k for f, _, _ in rows)
                          for k in ("TEXT", "AUDIO", "VIDEO")},
                         {"TEXT": 4, "AUDIO": 6, "VIDEO": 7})

    def test_plan_distinguishes_estimation_and_original_and_existing_owners(self):
        for term in ("ffsubsync", "PyAV", "Translate Toolkit", "JAMS", "Babel", "SimAlign",
                     "Demucs", "AudioSep", "Subtitle Studio", "Language Fabric",
                     "File Conversion", "Temporal", "HRB", "Model Router",
                     "175", "Conda/Mamba", "SOURCE_ORIGINAL", "MODEL_SEPARATED_ESTIMATE",
                     "UNSUPPORTED", "no physical", "no runtime"):
            with self.subTest(term=term):
                self.assertIn(term.lower(), self.plan.lower())

if __name__ == "__main__":
    unittest.main()
