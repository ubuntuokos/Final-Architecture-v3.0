"""Metadata-only regression for the 2026-09-28 video/editing/clip donor intake.

No upstream install, code copying or current-host/runtime admission is performed.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
CURATION_TAG = "video-clip-topic-curation-2026-09-28"
EXPECTED_REPOSITORIES = {
    "github:0xsline/openchatcut",
    "github:mutonby/openshorts",
    "github:zhouxiaoka/autoclip",
    "github:f-r-l/forge-film",
    "github:anil-matcha/ai-youtube-shorts-generator",
    "github:xixihhhh/hotclip",
    "github:6174/recut",
    "github:bilibili/carocut",
    "github:artbyjazi/autoclip",
    "github:kwakseongjae/dawn-cut",
    "github:makemyclip/editor",
    "github:monet-ai-editor/monet",
    "github:gml-mmgroup/cliptalk",
}
EXPECTED_TOPICS = {
    "github:topics/ai-video-editor",
    "github:topics/open-source-video",
    "github:topics/ai-clip-generator",
}
AUTOMATIC_FLAGS = (
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


class VideoClipDonorCurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.rows = cls.registry["entries"]
        cls.by_key = {row["source"]["normalized_key"]: row for row in cls.rows}
        cls.curated = [row for row in cls.rows if CURATION_TAG in row.get("tags", [])]

    def test_exact_candidate_set_and_unique_identity(self) -> None:
        self.assertEqual(
            {row["source"]["normalized_key"] for row in self.curated},
            EXPECTED_REPOSITORIES | EXPECTED_TOPICS,
        )
        self.assertEqual(len(self.curated), 16)
        self.assertEqual(len(self.rows), len({row["donor_id"] for row in self.rows}))
        self.assertEqual(len(self.rows), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.rows))

    def test_non_authoritative_candidate_only(self) -> None:
        for row in self.curated:
            self.assertEqual(row["status"], "CANDIDATE", row["donor_id"])
            self.assertTrue(row["discoverable_for_planning"])
            for flag in AUTOMATIC_FLAGS:
                self.assertIs(row[flag], False, (row["donor_id"], flag))
            self.assertNotEqual(
                row["code_reuse_policy"], "AUTOMATIC_SOURCE_COPY"
            )

    def test_separate_unknown_and_agpl_licensing(self) -> None:
        for key in (
            "github:0xsline/openchatcut",
            "github:xixihhhh/hotclip",
        ):
            row = self.by_key[key]
            self.assertEqual(row["license"]["declared"], "AGPL-3.0")
            self.assertEqual(
                row["code_reuse_policy"],
                "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW",
            )
        for key in ("github:6174/recut", "github:gml-mmgroup/cliptalk"):
            self.assertEqual(self.by_key[key]["license"]["declared"], "UNKNOWN")
        for key in EXPECTED_TOPICS:
            modes = set(self.by_key[key]["donor_modes"])
            self.assertIn("DISCOVERY_INDEX", modes)
            self.assertTrue(modes <= {"DISCOVERY_INDEX", "KNOWLEDGE_REFERENCE"})
            self.assertIs(self.by_key[key]["automatic_code_import"], False)
            self.assertEqual(
                self.by_key[key]["code_reuse_policy"], "INDEX_ONLY_NO_CODE_IMPORT"
            )

    def test_repo_snapshots_hardware_boundaries_and_existing_references(self) -> None:
        for key in EXPECTED_REPOSITORIES:
            row = self.by_key[key]
            self.assertEqual(len(row["upstream_snapshot"]["commit_sha"]), 40)
        hardware = self.registry["hardware_audit"]
        self.assertTrue(hardware["vendor_neutral"])
        self.assertTrue(hardware["cpu_only_viable"])
        self.assertEqual(hardware["accelerator_cardinality"], "0..N")
        self.assertFalse(self.registry["new_capability"])
        self.assertFalse(self.registry["new_architectural_authority"])
        self.assertIn("project:opencut", self.by_key)


if __name__ == "__main__":
    unittest.main()
