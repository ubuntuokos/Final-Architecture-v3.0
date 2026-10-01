# SPDX-License-Identifier: Apache-2.0
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

class OfficeFabricStructureTest(unittest.TestCase):
    def test_reuses_existing_capabilities_and_authority(self):
        p = load("canonical/profiles/FA3-OFFICE-FABRIC-001.json")
        self.assertEqual(p["capability_count"], 175)
        self.assertEqual(p["capability_bindings"], ["CAP-018", "CAP-030"])
        self.assertEqual(p["document_authority"], "FA3-DOC-001")
        self.assertFalse(p["new_capability"])
        self.assertFalse(p["new_architectural_authority"])

    def test_libreoffice_is_candidate_not_silent_runtime_admission(self):
        p = load("canonical/profiles/FA3-OFFICE-FABRIC-001.json")
        self.assertEqual(p["engine"]["canonical_engine_candidate"], "LibreOffice")
        self.assertFalse(p["engine"]["full_upstream_gui_embedded"])
        self.assertFalse(p["engine"]["bundled_upstream_binary"])
        self.assertIn("PENDING", p["engine"]["runtime_admission"])

    def test_format_admission_is_symmetric_and_fail_closed(self):
        c = load("canonical/contracts/FA3-OFFICE-FABRIC-CONTRACTS-001.json")
        self.assertTrue(c["format_admission"]["same_type_import_export_symmetry_required"])
        self.assertEqual(c["format_admission"]["default_state"], "PENDING_GOLDEN_ROUNDTRIP")
        self.assertFalse(c["format_admission"]["pdf_editable_import_claim"])
        self.assertEqual(c["security"]["unknown_format_profile_policy"], "DENY")
        self.assertFalse(c["security"]["silent_fallback"])

    def test_ai_off_and_preview_apply_undo(self):
        c = load("canonical/contracts/FA3-OFFICE-FABRIC-CONTRACTS-001.json")
        self.assertTrue(c["ai"]["disabled_means_no_ai_invocation"])
        self.assertTrue(c["ai"]["non_ai_authoring_path_required"])
        self.assertTrue(c["document_session"]["apply_requires_explicit_human_approval"])
        self.assertTrue(c["document_session"]["undo_required_for_mutation"])

    def test_donor_intake_blocker_preserved(self):
        r = load("canonical/assessments/FA3-OFFICE-FABRIC-REUSE-ASSESSMENT-001.json")
        self.assertEqual(r["donor_intake_status"]["active_pr"], 581)
        self.assertFalse(r["donor_intake_status"]["new_donor_records_published"])
        pending = {x["name"]: x["state"] for x in r["pending_new_donor_candidates"]}
        self.assertEqual(pending["Calligra"], "PENDING_DONOR_INTAKE")
        self.assertEqual(pending["Collabora Online"], "PENDING_DONOR_INTAKE")

    def test_current_host_not_promoted(self):
        h = load("canonical/current-host-impact/FA3-CH-IMPACT-OFFICE-FABRIC-20261001.json")
        self.assertFalse(h["physical_pass_claimed"])
        self.assertEqual(h["central_current_host_reconciliation"]["active_pr"], 559)

    def test_gate(self):
        subprocess.run([sys.executable, str(ROOT / "src/fa3_office_fabric_gate.py")], cwd=ROOT, check=True)

if __name__ == "__main__":
    unittest.main()
