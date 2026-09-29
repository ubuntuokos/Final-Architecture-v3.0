"""Static live-selective-import design/registry checks only; NOT live capture or current-host evidence."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
LIVE = ROOT / "docs/production-import-live-source-intake-2026-09-29.md"
SELECTORS = ROOT / "docs/production-import-selective-content-plan-2026-09-29.md"
PARENT = ROOT / "docs/production-import-migration-plan-2026-09-29.md"

NEW_SOURCES = {
    "github:haivision/srt",
    "github:obsproject/obs-studio",
    "github:xiph/icecast-server",
    "github:ebu/ebu-tt-live-toolkit",
    "github:szatmary/libcaption",
    "github:pion/webrtc",
    "github:bluenviron/mediamtx",
    "github:video-dev/hls.js",
    "github:streamlink/streamlink",
    "github:glut23/webvtt-py",
}
OLD_ENRICHED = {"github:ffmpeg/ffmpeg", "github:gstreamer/gstreamer", "github:tkarabela/pysubs2"}


class LiveIntakePlanAndDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REG.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_source = {e["source"]["normalized_key"]: e for e in cls.entries}
        cls.plan = LIVE.read_text(encoding="utf-8")
        cls.selector = SELECTORS.read_text(encoding="utf-8")
        cls.parent = PARENT.read_text(encoding="utf-8")

    def test_source_unique_and_unchanged_capability_baseline(self):
        self.assertEqual(len(self.by_source), len(self.entries))
        self.assertEqual(len({e["donor_id"] for e in self.entries}), len(self.entries))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertGreaterEqual(len(self.entries), 649)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.registry["new_capability"])
        self.assertFalse(self.registry["new_architectural_authority"])

    def test_ten_live_sources_capture_only_no_runtime_admission(self):
        self.assertEqual(len(NEW_SOURCES), 10)
        for key in NEW_SOURCES:
            with self.subTest(source=key):
                row = self.by_source[key]
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertIn("Production Import & Migration Fabric", row["target_hints"])
                self.assertEqual(row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                self.assertFalse(row["authority"])
                for flag in ("automatic_selection", "automatic_fetch", "automatic_install",
                             "automatic_activation", "automatic_dependency", "automatic_code_import",
                             "automatic_provider_admission", "automatic_model_selection"):
                    self.assertFalse(row[flag], (key, flag))

    def test_existing_media_donors_enriched_in_place(self):
        for key in OLD_ENRICHED:
            self.assertIn(key, self.by_source)
            self.assertIn("live-selective-import-reference", self.by_source[key]["tags"])

    def test_stable_seventeen_selectors_unmodified(self):
        rows = re.findall(
            r"^\|\s*(TEXT|AUDIO|VIDEO)\s*\|\s*`([A-Z_]+)`\s*\|\s*([^|]+)\|",
            self.selector, re.MULTILINE
        )
        self.assertEqual(len(rows), 17)
        self.assertEqual(
            {kind: sum(k == kind for k, _, _ in rows) for kind in ("TEXT", "AUDIO", "VIDEO")},
            {"TEXT": 4, "AUDIO": 6, "VIDEO": 7},
        )

    def test_caption_only_is_true_independent_input_no_av_required(self):
        for marker in ("LIVE_VIDEO", "LIVE_AUDIO", "LIVE_CAPTIONS", "CAPTION_ONLY",
                       "NO_AV_FETCH", "zero", "without any requirement",
                       "EBU-TT Live", "WebVTT", "PARTIAL", "FINAL", "CORRECTED",
                       "RETRACTED", "no audio/video", "NO default outgoing stream"):
            with self.subTest(marker=marker):
                self.assertIn(marker.lower(), self.plan.lower())
        self.assertIn("production-import-live-source-intake-2026-09-29.md", self.parent)

    def test_security_and_existing_authority_boundaries(self):
        for marker in ("SSRF", "rights", "Secret Broker", "CAP", "UAF",
                       "Temporal", "HRB", "Model Router", "Logistics",
                       "current-host", "Software Coexistence", "175",
                       "CPU-only", "source", "no fixed"):
            with self.subTest(marker=marker):
                self.assertIn(marker.lower(), self.plan.lower())
        self.assertIn("This stage does not create a running receiver", self.plan)


if __name__ == "__main__":
    unittest.main()
