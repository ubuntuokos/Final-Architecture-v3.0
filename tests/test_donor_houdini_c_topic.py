"""Regression guard for 2026-09-28 SideFX Houdini C-topic donor capture.

No upstream download, Houdini install, GPU requirement or runtime admission is tested.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
TOPIC = "https://github.com/topics/houdini?l=c&o=desc&s="
EXCLUDED = "github:luruizhe953-netizen/android-houdini-injection"
SCOPED_REPOS = {
    "jtomori/vex_tutorial",
    "wdas/partio",
    "jtomori/vft",
    "MysteryPancake/Houdini-VBD",
    "NiklasRosenstein/houdini-library",
    "lcrs/_.hips",
    "MonkeyRaveProduction/houdini_configs",
    "AdrianPanGithub/HoudiniPackage",
    "groundflyer/physhader-for-mantra",
    "thi-ng/vexed-generation",
    "csdjk/LcLLib-for-Houdini",
    "ttvd/houdini-sop-shapefile",
    "jtomori/VDB_activate_from_points",
    "melMass/cops-cl",
    "alt-shiftov/Houdini-Snippets",
    "a-riccardi/ar_tools",
    "drichardson/HoudiniExamples",
    "ttvd/houdini-rop-cop-gif",
    "jdvfx/houdini_vex_python",
    "ttvd/houdini-sop-triangulate-earcut",
    "tangentbloom/Hinge-Energy",
    "ttvd/erlang-houdini-engine-nif",
    "AreChen/VEX.Tutorial.Chinese.Version",
    "glebnovodran/groundwork",
    "robertkist/houdini",
    "Wambosa/houdini-wrangler",
}


class HoudiniTopicDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.keys = {r["source"]["normalized_key"]: r for r in cls.entries}
        cls.topic_entries = [r for r in cls.entries if TOPIC in r.get("discovered_from", [])]

    def test_exact_dated_scoped_collection(self):
        self.assertEqual(len(SCOPED_REPOS), 26)
        for name in SCOPED_REPOS:
            with self.subTest(name=name):
                key = "github:" + name.casefold()
                self.assertIn(key, self.keys)
                self.assertIn(TOPIC, self.keys[key]["discovered_from"])
                self.assertTrue(self.keys[key]["target_hints"])
        self.assertEqual(len(self.topic_entries), 27)
        index = self.keys["github:topics/houdini?l=c&o=desc&s="]
        self.assertEqual(index["source"]["kind"], "GITHUB_TOPIC")
        self.assertEqual(index["topic_review"]["source_count"], 27)
        self.assertEqual(index["topic_review"]["curated_sidefx_repos"], 26)
        self.assertNotIn(EXCLUDED, self.keys)

    def test_uniqueness_and_non_authority(self):
        self.assertEqual(len(self.entries), self.registry["backfill"]["entry_count"])
        self.assertEqual(len(self.entries), len(self.keys))
        self.assertEqual(len(self.entries), len({r["donor_id"] for r in self.entries}))
        for row in self.topic_entries:
            with self.subTest(donor=row["donor_id"]):
                self.assertEqual(row["status"], "CANDIDATE")
                self.assertTrue(row["discoverable_for_planning"])
                self.assertFalse(row["authority"])
                for prop in (
                    "automatic_selection", "automatic_fetch", "automatic_install",
                    "automatic_activation", "automatic_dependency", "automatic_code_import",
                    "automatic_provider_admission", "automatic_model_selection",
                ):
                    self.assertIs(row[prop], False, prop)
                self.assertEqual(
                    row["code_reuse_policy"], "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW"
                )
                self.assertNotIn("Unreal Engine", row["target_hints"])

    def test_archived_and_backend_specific_references_stay_bounded(self):
        partio = self.keys["github:wdas/partio"]
        self.assertIn("Asset Graph", partio["target_hints"])
        self.assertIn("particle-io", partio["capability_hints"])
        vbd = self.keys["github:mysterypancake/houdini-vbd"]
        self.assertIn("experimental", vbd["tags"])
        cuda_ref = self.keys["github:adrianpangithub/houdinipackage"]
        self.assertIn("CUDA", " ".join(cuda_ref["notes"]))
        self.assertEqual(cuda_ref["status"], "CANDIDATE")
        legacy = self.keys["github:ttvd/erlang-houdini-engine-nif"]
        self.assertTrue(legacy["upstream_snapshot"]["archived"])
        self.assertIn("HISTORICAL_REFERENCE", legacy["donor_modes"])
        self.assertFalse(self.registry["hardware_audit"]["global_accelerator_requirement"])
        self.assertTrue(self.registry["hardware_audit"]["cpu_only_viable"])
        self.assertEqual(self.registry["hardware_audit"]["accelerator_cardinality"], "0..N")
        self.assertEqual(
            self.registry["hardware_audit"]["live_resource_authority"],
            "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        )


if __name__ == "__main__":
    unittest.main()
