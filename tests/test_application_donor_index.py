from __future__ import annotations

import copy
import json
from datetime import date
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_application_donor_index import build_index, capability_refresh_status

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
        self.assertTrue(all(a["fa3_compliance"]["applies_without_declared_dependency"]
                            for a in report["applications"]))
        self.assertTrue(all(a["fa3_compliance"]["capability_non_regression_on_donor_change"]
                            for a in report["applications"]))

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

    def test_timestamp_only_change_is_still_processed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            old = json.loads((root / SOURCES[2]).read_text())
            new = copy.deepcopy(old)
            new["entries"][0]["last_seen"] = "2099-01-01"
            (root / SOURCES[2]).write_text(json.dumps(new))
            changes = build_index(root, previous=old)["reevaluation"]
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0]["changed_fields"], ["last_seen"])
            self.assertEqual(changes[0]["change"], "UPDATED")
            self.assertIn(changes[0]["disposition"], {
                "MANDATORY_APPLICATION_RECONCILIATION",
                "MANDATORY_DONOR_RECONCILIATION",
            })

    def test_explicit_donor_usage_extends_reverse_impact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            old = json.loads((root / SOURCES[2]).read_text())
            donor = old["entries"][0]
            links_path = root / SOURCES[3]
            links = json.loads(links_path.read_text())
            links["donor_usage_records"] = [{
                "id": "FA3-USAGE-TEST-001",
                "application_id": "fa3.quickclip",
                "donor_id": donor["donor_id"],
                "usage_kind": "CAPABILITY_PATTERN",
                "status": "ACTIVE",
            }]
            links_path.write_text(json.dumps(links))
            new = copy.deepcopy(old)
            new["entries"][0]["notes"] = ["changed donor note"]
            (root / SOURCES[2]).write_text(json.dumps(new))
            result = build_index(root, previous=old)
            change = result["reevaluation"][0]
            self.assertIn("fa3.quickclip", change["explicitly_used_by"])
            self.assertIn("fa3.quickclip", change["affected_applications"])
            app = next(a for a in result["applications"]
                       if a["application_id"] == "fa3.quickclip")
            self.assertEqual(app["declared_donor_usage"][0]["usage_id"],
                             "FA3-USAGE-TEST-001")

    def test_monthly_capability_refresh_uses_policy_start_then_review_timestamp(self):
        registry = {
            "planning_policy": {
                "monthly_capability_refresh_days": 31,
                "monthly_capability_refresh_policy_effective_date": "2026-09-30",
            },
            "entries": [{
                "donor_id": "FA3-DONOR-X-001",
                "status": "ACCEPTED_REFERENCE",
                "source": {"normalized_key": "github:example/x"},
            }],
        }
        initial = capability_refresh_status(registry, today=date(2026, 10, 30))
        self.assertEqual(initial["due_count"], 0)
        due = capability_refresh_status(registry, today=date(2026, 10, 31))
        self.assertEqual(due["due_count"], 1)
        self.assertEqual(due["due"][0]["review_clock_source"],
                         "policy_effective_date_initial_grace")
        registry["entries"][0]["capability_reviewed_at"] = "2026-10-20"
        refreshed = capability_refresh_status(registry, today=date(2026, 11, 19))
        self.assertEqual(refreshed["due_count"], 0)

    def test_tutorial_and_shared_capability_policy_is_enforced(self):
        report = build_index(ROOT)
        self.assertEqual(report["validation"]["result"], "PASS",
                         report["validation"]["findings"])
        self.assertTrue(report["tutorial_shared_policy"]["registered_tutorial_only"])
        self.assertTrue(
            report["tutorial_shared_policy"]["multi_application_function_routes_to_shared_layer"]
        )
        self.assertTrue(
            report["tutorial_shared_policy"]["retrospective_application_impact_required"]
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            path = root / SOURCES[3]
            links = json.loads(path.read_text())
            links["shared_capabilities"] = [{
                "id": "FA3-SHARED-TEST-001",
                "owner_layer": "FA3-SHARED-CAPABILITY-FABRIC",
                "consumer_applications": ["fa3.video-editor", "fa3.quickclip"],
                "status": "PROPOSED",
                "authority": False,
                "local_ui_adapter_only": True,
                "retrospective_review_required": True,
                "manual_update_required": True,
                "capability_loss_allowed": False,
                "current_host_alignment_required_for_structural_change": True,
            }]
            path.write_text(json.dumps(links))
            result = build_index(root)
            self.assertEqual(result["validation"]["result"], "PASS",
                             result["validation"]["findings"])
            self.assertEqual(
                result["shared_capabilities"][0]["consumer_applications"],
                ["fa3.quickclip", "fa3.video-editor"],
            )

            links["shared_capabilities"][0]["consumer_applications"] = ["fa3.video-editor"]
            path.write_text(json.dumps(links))
            findings = {row["code"] for row in build_index(root)["validation"]["findings"]}
            self.assertIn("INVALID_SHARED_CAPABILITY", findings)


    def test_tutorial_shared_policy_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            path = root / SOURCES[3]
            links = json.loads(path.read_text())
            links["policy"]["retrospective_shared_impact_required"] = False
            path.write_text(json.dumps(links))
            findings = {row["code"] for row in build_index(root)["validation"]["findings"]}
            self.assertIn("TUTORIAL_SHARED_POLICY_INVALID", findings)



    def test_capability_consumer_reverse_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            profile_rel = "canonical/profiles/FA3-EXTERNAL-LLM-CATALOG-001.json"
            profile_dst = root / profile_rel
            profile_dst.parent.mkdir(parents=True, exist_ok=True)
            profile_dst.write_bytes((ROOT / profile_rel).read_bytes())
            links_path = root / SOURCES[3]
            links = json.loads(links_path.read_text())
            donor = json.loads((root / SOURCES[2]).read_text())["entries"][0]
            links["donor_usage_records"] = [{
                "id": "FA3-USAGE-CAPMAP-TEST-001",
                "application_id": "fa3.quickclip",
                "donor_id": donor["donor_id"],
                "donor_capability_key": "provider-discovery",
                "usage_kind": "CAPABILITY_PATTERN",
                "status": "ACTIVE",
                "fa3_bindings": {
                    "profile_ids": ["FA3-EXTERNAL-LLM-CATALOG-001"],
                    "contract_ids": [],
                    "authority_ids": ["FA3-AUTH-MODEL-ROUTER-001"],
                    "shared_module_ids": [],
                },
                "consumers": [{
                    "kind": "SHARED_MODULE",
                    "id": "FA3-EXTERNAL-LLM-CATALOG-001",
                    "relationship": "DIRECT",
                }],
                "current_host_impact": {"classification": "NO_RUNTIME_IMPACT"},
            }]
            links_path.write_text(json.dumps(links))
            result = build_index(root)
            self.assertEqual(result["validation"]["result"], "PASS", result["validation"]["findings"])
            edge = result["capability_consumer_map"]["edges"][0]
            self.assertEqual(edge["fa3_bindings"]["capability_ids"], ["CAP-005", "CAP-140"])
            self.assertIn(edge["id"], result["capability_consumer_map"]["views"]["by_capability"]["CAP-140"])
            self.assertIn(
                edge["id"],
                result["capability_consumer_map"]["views"]["by_consumer"]["APPLICATION:fa3.quickclip"],
            )

    def test_manual_capability_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            links_path = root / SOURCES[3]
            links = json.loads(links_path.read_text())
            donor = json.loads((root / SOURCES[2]).read_text())["entries"][0]
            links["donor_usage_records"] = [{
                "id": "FA3-USAGE-CAPMAP-BAD-001",
                "application_id": "fa3.quickclip",
                "donor_id": donor["donor_id"],
                "usage_kind": "CAPABILITY_PATTERN",
                "status": "ACTIVE",
                "fa3_bindings": {"capability_ids": ["CAP-140"]},
            }]
            links_path.write_text(json.dumps(links))
            findings = {row["code"] for row in build_index(root)["validation"]["findings"]}
            self.assertIn("MANUAL_CAPABILITY_BINDING_FORBIDDEN", findings)
            self.assertIn("UNRESOLVED_CAPABILITY_BINDING", findings)

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
