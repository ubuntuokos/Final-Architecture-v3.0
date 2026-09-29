"""Static metadata and plan-level checks; never current-host or model-quality evidence."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "canonical" / "FA3-DONOR-REFERENCE-REGISTRY-001.json"
SELECTORS = ROOT / "docs" / "production-import-selective-content-plan-2026-09-29.md"
RESEARCH = ROOT / "docs" / "production-import-selective-donor-research-2026-09-29.md"

NEW_SOURCES = {
    "argosopentech/argos-translate", "libretranslate/libretranslate",
    "opennmt/ctranslate2", "opennmt/opennmt-py", "m-bain/whisperx",
    "systran/faster-whisper", "ggml-org/whisper.cpp",
    "pyannote/pyannote-audio", "snakers4/silero-vad",
    "nomadkaraoke/python-audio-separator", "breakthrough/pyscenedetect",
    "audio-agi/audiosep", "facebookresearch/denoiser",
    "microsoft/dns-challenge", "asteroid-team/asteroid",
    "zfturbo/music-source-separation-training", "openai/whisper",
    "adefossez/demucs", "tkarabela/pysubs2", "xiph/rnnoise",
    "facebookresearch/svoice",
}
SELECTOR_IDS = {
    "ORIGINAL_LANGUAGE", "ONE_TRANSLATION", "MULTI_TRANSLATION",
    "ORIGINAL_PLUS_TRANSLATIONS", "FULL_AUDIO", "TRANSCRIPT_ONLY",
    "SPEECH_OR_SINGING_SEPARATE", "INSTRUMENTAL_ONLY",
    "AMBIENCE_AND_SFX", "DENOISED_SPEECH", "FULL_VIDEO",
    "VIDEO_WITHOUT_AUDIO", "FULL_AUDIO_ONLY", "MUSIC_OR_INSTRUMENTAL_ONLY",
    "AMBIENCE_AND_SFX_ONLY", "FRAMES_OR_SCENES",
}


class SelectiveContentDonorPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REG.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {x["source"]["normalized_key"]: x for x in cls.entries}
        cls.parent = SELECTORS.read_text(encoding="utf-8")
        cls.research = RESEARCH.read_text(encoding="utf-8")

    def test_source_keys_and_ids_unique(self):
        self.assertEqual(len(self.by_key), len(self.entries))
        self.assertEqual(len({x["donor_id"] for x in self.entries}), len(self.entries))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.registry["new_capability"])
        self.assertFalse(self.registry["new_architectural_authority"])

    def test_all_21_verified_repositories_captured_once(self):
        self.assertEqual(len(NEW_SOURCES), 21)
        for source in NEW_SOURCES:
            with self.subTest(source=source):
                row = self.by_key["github:" + source]
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertIn("Production Import & Migration Fabric", row["target_hints"])
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                self.assertFalse(row["authority"])
                for flag in ("automatic_selection", "automatic_fetch", "automatic_install",
                             "automatic_activation", "automatic_dependency", "automatic_code_import",
                             "automatic_provider_admission", "automatic_model_selection"):
                    self.assertFalse(row[flag], (source, flag))

    def test_prior_donors_and_provider_preserved(self):
        self.assertIn("github:ffmpeg/ffmpeg", self.by_key)
        self.assertIn("selective-import-demux", self.by_key["github:ffmpeg/ffmpeg"]["tags"])
        self.assertIn("github:academysoftwarefoundation/opentimelineio", self.by_key)
        for key in ("project:ayon", "project:openassetio", "github:contentauth/c2pa-rs"):
            self.assertIn(key, self.by_key)
        self.assertIn("github:adefossez/demucs", self.by_key)
        self.assertEqual(len(self.by_key), len(self.entries))

    def test_exact_17_stable_selector_rows_and_gui_labels(self):
        rows = re.findall(r"^\|\s*(TEXT|AUDIO|VIDEO)\s*\|\s*`([A-Z_]+)`\s*\|\s*([^|]+)\|",
                          self.parent, re.MULTILINE)
        counts = {"TEXT": 0, "AUDIO": 0, "VIDEO": 0}
        for source, selector, label in rows:
            counts[source] += 1
            self.assertTrue(label.strip())
            self.assertIn(selector, SELECTOR_IDS)
        self.assertEqual(counts, {"TEXT": 4, "AUDIO": 6, "VIDEO": 7})
        self.assertEqual(len(rows), 17)
        self.assertEqual(set(selector for _, selector, _ in rows), SELECTOR_IDS)

    def test_design_reuses_existing_authorities(self):
        for name in ("FA3-FILE-CONVERSION-001", "FA3-CONVERSION-FABRIC-001",
                     "FA3-LANGUAGE-FABRIC-001", "FA3-AUDIO-SEPARATION-CONTRACTS-001",
                     "FA3-CREATIVE-PROJECT-WORKFLOW-CONTRACTS-001", "CAP-171",
                     "Temporal", "HRB", "Model Router", "SECRET", "current-host",
                     "EXPERIMENTAL", "source", "17", "175"):
            with self.subTest(marker=name):
                self.assertIn(name.lower(), self.research.lower())
        self.assertIn("one test video", self.research.lower())
        self.assertIn("do **not** publish", self.research.lower())


if __name__ == "__main__":
    unittest.main()
