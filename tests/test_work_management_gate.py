import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_release_baseline import load_active_release_baseline
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_work_management_gate as wm


class WorkManagementGateTests(unittest.TestCase):
    def test_baseline_gate_passes(self):
        report = wm.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual((5, 5), (report["regressions"]["passed"], report["regressions"]["total"]))
        self.assertEqual(load_active_release_baseline(ROOT).capability_count, report["capability_count"])
        self.assertEqual(0, report["new_architectural_authorities"])

    def test_provider_identity_cannot_own_canonical_identity(self):
        self.assertFalse(wm.work_item_projection_valid(
            canonical_id="", provider_id=wm.KANBOARD_ID, external_id="task:42",
            provider_revision="rev:2", reconciliation_state="SYNCED",
            provider_owns_canonical_identity=True,
        ))

    def test_event_cannot_self_authorize_transition(self):
        self.assertFalse(wm.transition_valid(
            actor="event", scope="project:1", capability="work_item.transition",
            authorization_authority="FA3-AUTH-SECURITY-GOV-001", decision="ALLOW",
            event_implies_authorization=True,
        ))

    def test_cpu_lightweight_does_not_require_accelerator_lease(self):
        self.assertTrue(wm.resource_request_valid(
            resource_class="CPU_LIGHTWEIGHT", accelerator_required=False,
            hrb_authorized=True, accelerator_lease_present=False, silent_fallback=False,
        ))
        self.assertFalse(wm.resource_request_valid(
            resource_class="CPU_LIGHTWEIGHT", accelerator_required=False,
            hrb_authorized=True, accelerator_lease_present=True, silent_fallback=False,
        ))

    def test_accelerator_requires_fresh_lease(self):
        self.assertFalse(wm.resource_request_valid(
            resource_class="GPU", accelerator_required=True,
            hrb_authorized=True, accelerator_lease_present=False, silent_fallback=False,
        ))

    def test_silent_fallback_denied(self):
        self.assertFalse(wm.resource_request_valid(
            resource_class="GPU", accelerator_required=True,
            hrb_authorized=True, accelerator_lease_present=True, silent_fallback=True,
        ))

    def _copy_repo(self):
        td = tempfile.TemporaryDirectory()
        dst = Path(td.name) / "repo"
        for rel in ("canonical", "apps/fa3-control-center"):
            shutil.copytree(ROOT / rel, dst / rel)
        (dst / "reports").mkdir(parents=True, exist_ok=True)
        return td, dst

    def test_missing_work_management_menu_fails_closed(self):
        td, dst = self._copy_repo()
        try:
            main = dst / "apps/fa3-control-center/qml/Main.qml"
            text = main.read_text(encoding="utf-8").replace('label: "Work Management"; routeId: "home.work-management"', 'label: "Work"; routeId: "home.work-management"', 1)
            main.write_text(text, encoding="utf-8")
            report = wm.gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "WM-014" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_provider_resource_authority_drift_fails_closed(self):
        td, dst = self._copy_repo()
        try:
            path = dst / "canonical/providers/FA3-PROVIDER-KANEO-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["resource_admission"]["accelerator_required_by_default"] = True
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = wm.gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "WM-008" for x in report["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
