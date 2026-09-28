from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_application_donor_index import build_index

SOURCES = (
    "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json",
    "canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
    "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
    "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
)


def fixture(root: Path) -> None:
    for rel in SOURCES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / rel).read_bytes())


class ApplicationDonorIndexTests(unittest.TestCase):
    def test_curated_catalog_and_gui_surface_coverage(self):
        report = build_index(ROOT)
        catalog = json.loads((ROOT / SOURCES[0]).read_text())
        gui = json.loads((ROOT / SOURCES[1]).read_text())
        ids = {app["application_id"] for app in report["applications"]}
        self.assertEqual(report["validation"]["result"], "PASS", report["validation"]["findings"])
        self.assertEqual({("studio." + app["id"]) for app in catalog["applications"]} & ids,
                         {("studio." + app["id"]) for app in catalog["applications"]})
        self.assertEqual(len(report["gui_surfaces"]), len(gui["surfaces"]))
        self.assertTrue(all(not row["is_application"] for row in report["gui_surfaces"]))

    def test_new_curated_application_automatically_registered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            path = root / SOURCES[0]
            catalog = json.loads(path.read_text())
            catalog["applications"].append({
                "id": "future-safe", "name": "Future Safe App", "admission": "PENDING"
            })
            path.write_text(json.dumps(catalog))
            index = build_index(root)
            by_id = {row["application_id"]: row for row in index["applications"]}
            self.assertIn("studio.future-safe", by_id)
            self.assertEqual(by_id["studio.future-safe"]["donor_assessment"],
                             "NOT_AUTOMATICALLY_ASSESSED")

    def test_declared_internal_and_reference_applications(self):
        report = build_index(ROOT)
        by_id = {app["application_id"]: app for app in report["applications"]}
        for aid in ("fa3.video-editor", "fa3.quickclip", "fa3.story-screenplay",
                    "fa3.music-studio", "fa3.character-studio"):
            self.assertEqual(by_id[aid]["lifecycle"], "PLANNED")
        self.assertIn("FA3-DONOR-KRITA-001", by_id["reference.krita"]["existing_source_donors"])
        self.assertIn("FA3-DONOR-ARDOUR-001", by_id["reference.ardour"]["existing_source_donors"])
        quickclip = next(row for row in report["cross_application_links"]
                         if row["id"] == "FA3-APP-LINK-QUICKCLIP-EDITOR")
        self.assertIn(".fa3clip timeline", quickclip["offered_artifacts"])
        self.assertIn("project.fa3video", quickclip["integration_boundary"])
        self.assertTrue(all(e["human_approval_required"] and not e["automatic_activation"]
                            for e in report["cross_application_links"]))

    def test_quickclip_donor_and_planned_handovers(self):
        registry = json.loads((ROOT / SOURCES[2]).read_text())
        self.assertEqual(registry["backfill"]["entry_count"], len(registry["entries"]))
        matches = [row for row in registry["entries"]
                   if row["source"]["normalized_key"] == "github:yils-lin/short-video-factory"]
        self.assertEqual(len(matches), 1)
        donor = matches[0]
        self.assertEqual(donor["status"], "CANDIDATE")
        self.assertEqual(donor["license"]["declared"], "AGPL-3.0")
        self.assertEqual(donor["code_reuse_policy"],
                         "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW")
        self.assertFalse(donor["automatic_code_import"])
        self.assertFalse(donor["automatic_provider_admission"])
        self.assertFalse(donor["automatic_model_selection"])
        self.assertTrue((ROOT / donor["selection_scope"]["implementation_plan"]).exists())

        report = build_index(ROOT)
        self.assertEqual(report["validation"]["result"], "PASS", report["validation"]["findings"])
        by_id = {row["application_id"]: row for row in report["applications"]}
        donor_suggestions = {row["donor_id"] for row in by_id["fa3.quickclip"]["suggested_donors"]}
        self.assertIn(donor["donor_id"], donor_suggestions)
        by_edge = {row["id"]: row for row in report["cross_application_links"]}
        expected_edges = {
            "FA3-APP-LINK-STORY-QUICKCLIP": ("fa3.story-screenplay", "fa3.quickclip"),
            "FA3-APP-LINK-MUSIC-QUICKCLIP": ("fa3.music-studio", "fa3.quickclip"),
            "FA3-APP-LINK-QUICKCLIP-MAUTIC": ("fa3.quickclip", "studio.mautic"),
        }
        for edge_id, (source, target) in expected_edges.items():
            self.assertIn(edge_id, by_edge)
            edge = by_edge[edge_id]
            self.assertEqual((edge["from_application"], edge["to_application"]),
                             (source, target))
            self.assertEqual(edge["status"], "PROPOSED")
            self.assertTrue(edge["human_approval_required"])
            self.assertFalse(edge["automatic_activation"])
            self.assertFalse(edge["automatic_code_import"])

    def test_new_donor_targets_only_matching_application(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            old = json.loads((root / SOURCES[2]).read_text())
            donor = copy.deepcopy(old["entries"][0])
            donor["donor_id"] = "FA3-DONOR-TEST-QUICKCLIP-001"
            donor["name"] = "Test QuickClip"
            donor["source"] = {"kind": "PROJECT", "locator": "project:Test QuickClip",
                               "normalized_key": "project:test quickclip"}
            donor["status"] = "CANDIDATE"
            donor["target_hints"] = ["QuickClip"]
            donor["discovered_from"] = ["test"]
            new = copy.deepcopy(old)
            new["entries"].append(donor)
            new["backfill"]["entry_count"] = len(new["entries"])
            (root / SOURCES[2]).write_text(json.dumps(new))
            result = build_index(root, previous=old)
            self.assertEqual(result["validation"]["result"], "PASS", result["validation"]["findings"])
            changed = next(x for x in result["reevaluation"]
                           if x["source_key"] == "project:test quickclip")
            self.assertEqual(changed["affected_applications"], ["fa3.quickclip"])
            self.assertFalse(changed["automatic_adoption"])

    def test_timestamp_only_change_does_not_reopen_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            old = json.loads((root / SOURCES[2]).read_text())
            new = copy.deepcopy(old)
            new["entries"][0]["last_seen"] = "2099-01-01"
            (root / SOURCES[2]).write_text(json.dumps(new))
            self.assertEqual(build_index(root, previous=old)["reevaluation"], [])

    def test_fail_closed_auto_admission_and_bad_cross_app_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            donors = json.loads((root / SOURCES[2]).read_text())
            donors["entries"][0]["automatic_code_import"] = True
            (root / SOURCES[2]).write_text(json.dumps(donors))
            self.assertIn("DONOR_AUTO_ADMISSION_FORBIDDEN",
                          {f["code"] for f in build_index(root)["validation"]["findings"]})
            links = json.loads((root / SOURCES[3]).read_text())
            links["relationships"][0]["to_application"] = "unknown.application"
            (root / SOURCES[3]).write_text(json.dumps(links))
            self.assertIn("INVALID_CROSS_APP_EDGE",
                          {f["code"] for f in build_index(root)["validation"]["findings"]})


if __name__ == "__main__":
    unittest.main()
