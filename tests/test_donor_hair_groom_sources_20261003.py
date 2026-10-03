import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-HAIR-GROOM-SOURCES-2026-10-03.json"
EXPECTED = [('FA3-DONOR-KYLEOLSZ-001', 'github:kyleolsz', 'https://github.com/kyleolsz'), ('FA3-DONOR-FACEBOOKRESEARCH-IPHG-001', 'github:facebookresearch/iphg', 'https://github.com/facebookresearch/iphg'), ('FA3-DONOR-SAMURAIGPT-AI-HAIR-STYLE-SIMULATOR-001', 'github:samuraigpt/ai-hair-style-simulator', 'https://github.com/SamurAIGPT/ai-hair-style-simulator'), ('FA3-DONOR-FACEBOOKRESEARCH-CT2HAIR-001', 'github:facebookresearch/ct2hair', 'https://github.com/facebookresearch/CT2Hair'), ('FA3-DONOR-VANESSIK-001', 'github:vanessik', 'https://github.com/Vanessik'), ('FA3-DONOR-HAIRGPT-001', 'https://haiminluo.github.io/hairgpt/', 'https://haiminluo.github.io/hairgpt/'), ('FA3-DONOR-C-HE-001', 'github:c-he', 'https://github.com/c-he'), ('FA3-DONOR-MENGZEPHYR-001', 'github:mengzephyr', 'https://github.com/MengZephyr'), ('FA3-DONOR-XIAOJIU-Z-001', 'github:xiaojiu-z', 'https://github.com/Xiaojiu-z'), ('FA3-DONOR-CYCHUNGG-001', 'github:cychungg', 'https://github.com/cychungg'), ('FA3-DONOR-AIRI-INSTITUTE-001', 'github:airi-institute', 'https://github.com/AIRI-Institute'), ('FA3-DONOR-JIN-CAO-TMA-001', 'github:jin-cao-tma', 'https://github.com/jin-cao-tma'), ('FA3-DONOR-YIMIN-PAN-001', 'github:yimin-pan', 'https://github.com/yimin-pan'), ('FA3-DONOR-SKETCHHAIRSALON-001', 'https://chufengxiao.github.io/sketchhairsalon/', 'https://chufengxiao.github.io/SketchHairSalon/'), ('FA3-DONOR-GITHUB-TOPIC-HAIR-COLOR-001', 'github:topics/hair-color', 'https://github.com/topics/hair-color'), ('FA3-DONOR-DEEPMANCER-001', 'github:deepmancer', 'https://github.com/deepmancer')]


class HairGroomDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.by_id = {row["donor_id"]: row for row in cls.registry["entries"]}

    def test_registry_count_and_baseline(self):
        self.assertEqual(len(self.registry["entries"]), 1421)
        self.assertEqual(self.registry["backfill"]["entry_count"], 1421)
        self.assertEqual(self.delta["parent_entry_count"], 1405)
        self.assertEqual(self.delta["new_source_count"], 16)
        self.assertEqual(self.delta["resulting_entry_count"], 1421)
        self.assertEqual(self.delta["capability_baseline"], 175)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edges_created"], 0)

    def test_expected_sources_are_reference_only(self):
        for donor_id, key, locator in EXPECTED:
            row = self.by_id[donor_id]
            self.assertEqual(row["source"]["normalized_key"], key)
            self.assertEqual(row["source"]["locator"], locator)
            self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
            self.assertFalse(row["authority"])
            for flag in (
                "automatic_selection",
                "automatic_fetch",
                "automatic_install",
                "automatic_activation",
                "automatic_dependency",
                "automatic_code_import",
                "automatic_provider_admission",
                "automatic_model_selection",
            ):
                self.assertFalse(row[flag], (donor_id, flag))
            self.assertEqual(
                row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY"
            )

    def test_submitted_resolution_is_preserved(self):
        resolutions = self.delta["source_resolutions"]
        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0]["submitted"], "https://github.com/Vanessi k")
        self.assertEqual(resolutions[0]["canonical"], "https://github.com/Vanessik")


if __name__ == "__main__":
    unittest.main()
