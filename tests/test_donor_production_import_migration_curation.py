"""Metadata-only regression for production import and legacy converter donor reconciliation.

No test in this file constitutes a current-host runtime, external-codec
round-trip, provider-admission or release-projection receipt.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
PLAN = ROOT / "docs/production-import-migration-plan-2026-09-29.md"

PRODUCTION_SOURCES = {
    "academysoftwarefoundation/opentimelineio",
    "opentimelineio/otio-aaf-adapter",
    "opentimelineio/otio-fcpx-xml-adapter",
    "opentimelineio/otio-fcp-adapter",
    "opentimelineio/otio-xges-adapter",
    "academysoftwarefoundation/xstudio",
    "academysoftwarefoundation/opencue",
    "openjobdescription/openjd-specifications",
    "ynput/ayon-core",
    "ynput/ayon-backend",
    "ynput/ayon-openassetio-manager-plugin",
    "cgwire/kitsu",
    "cgwire/zou",
    "cgwire/gazu",
    "openassetio/openassetio-mediacreation",
    "openassetio/usdopenassetioresolver",
    "netflix/photon",
    "mediaarea/mediainfolib",
    "mediaarea/mediaconch_sourcecode",
    "mediaarea/bwfmetaedit",
    "mediaarea/rawcooked",
    "libraryofcongress/bagit-python",
    "ocfl/spec",
    "casparcg/server",
    "markreidvfx/pyaaf2",
    "markreidvfx/pyavb",
    "markreidvfx/otio-avb-adapter",
}
CONVERTER_SOURCES = {
    "vert-sh/vert",
    "vert-sh/vertd",
    "c4illin/convertx",
    "jgm/pandoc",
    "imagemagick/imagemagick",
    "assimp/assimp",
    "libreoffice/core",
    "ffmpeg/ffmpeg",
    "libvips/libvips",
    "tesseract-ocr/tesseract",
    "kovidgoyal/calibre",
}
CANDIDATE_KEYS = {"github:" + key for key in PRODUCTION_SOURCES | CONVERTER_SOURCES}
NON_AUTH_FLAGS = (
    "authority",
    "automatic_selection",
    "automatic_fetch",
    "automatic_install",
    "automatic_activation",
    "automatic_dependency",
    "automatic_code_import",
    "automatic_provider_admission",
    "automatic_model_selection",
)


class ProductionImportMigrationDonorCurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_source = {
            row["source"]["normalized_key"]: row for row in cls.entries
        }

    def test_concurrent_donor_history_retained_and_source_unique(self):
        self.assertEqual(len(CANDIDATE_KEYS), 38)
        self.assertGreaterEqual(len(self.entries), 588)
        self.assertEqual(len(self.by_source), len(self.entries))
        self.assertEqual(len({e["donor_id"] for e in self.entries}), len(self.entries))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.registry["new_capability"])
        self.assertFalse(self.registry["new_architectural_authority"])

    def test_researched_sources_present_once_as_non_authoritative_candidates(self):
        self.assertTrue(CANDIDATE_KEYS.issubset(self.by_source))
        for key in sorted(CANDIDATE_KEYS):
            with self.subTest(source=key):
                item = self.by_source[key]
                self.assertEqual(item["status"], "CANDIDATE")
                self.assertTrue(item["target_hints"])
                self.assertTrue(item["capability_hints"])
                self.assertEqual(item["code_reuse_policy"],
                                 "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
                for flag in NON_AUTH_FLAGS:
                    self.assertIs(item[flag], False, (key, flag))

    def test_existing_openimageio_source_enriched_not_duplicated(self):
        old = [e for e in self.entries
               if e["source"]["normalized_key"] == "project:openimageio"]
        self.assertEqual(len(old), 1)
        self.assertIn(
            "https://github.com/AcademySoftwareFoundation/OpenImageIO",
            old[0]["upstream_repository_references"],
        )
        self.assertNotIn("github:academysoftwarefoundation/openimageio",
                         self.by_source)

    def test_other_prior_source_records_not_duplicated(self):
        for key in ("project:ayon", "project:openassetio",
                    "github:contentauth/c2pa-rs"):
            self.assertIn(key, self.by_source)
            self.assertIn(
                "Production Import & Migration Fabric",
                self.by_source[key]["target_hints"],
            )

    def test_planning_receipt_not_runtime_admission(self):
        plan = PLAN.read_text(encoding="utf-8")
        for marker in ("#195", "#459", "#520", "FA3-FILE-CONVERSION-001",
                       "FA3-TOOLS-FABRIC-001", "FA3-3D-GEOM-001", "VERT",
                       "QUARANTINED", "175", "current-host", "CAP-171"):
            self.assertIn(marker, plan)
        self.assertIn("CPU", plan)
        self.assertIn("INSPECT_ONLY", plan)


if __name__ == "__main__":
    unittest.main()
