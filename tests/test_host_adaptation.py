import json
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_host_adaptation import (
    CAPABILITY_COUNT, canonical_check, compare_snapshots, installation_profile,
    materialization_plan, regression_check, self_test, synthetic_snapshot,
)

class HostAdaptationTests(unittest.TestCase):
    def test_canonical_contract_preserves_authorities(self):
        report=canonical_check(ROOT)
        self.assertEqual(report["result"],"PASS",report)
        profile=json.loads((ROOT/"canonical/profiles/FA3-HOST-ADAPTATION-001.json").read_text())
        self.assertEqual(profile["capability_count"],CAPABILITY_COUNT)
        self.assertFalse(profile["new_capability"])
        self.assertFalse(profile["new_architectural_authority"])
        self.assertEqual(profile["authority"]["resource_admission_placement_lease"],"FA3-AUTH-HOST-RESOURCE-BROKER-001")

    def test_self_test_never_claims_current_host_promotion(self):
        report=self_test(ROOT)
        self.assertEqual(report["result"],"PASS",report)
        self.assertFalse(report["current_host_production_evidence"])
        self.assertFalse(report["current_host_promotion_claim"])

    def test_installation_profile_is_immutable_reference(self):
        profile=installation_profile(synthetic_snapshot())
        self.assertEqual(profile["profile_kind"],"INSTALLATION_BASELINE")
        self.assertTrue(profile["immutable"])
        self.assertFalse(profile["current_host_promotion_claim"])

    def test_kernel_only_change_is_observational(self):
        report=compare_snapshots(synthetic_snapshot(kernel="a"),synthetic_snapshot(kernel="b"),physical_core_min=8)
        self.assertEqual(report["classification"],"OBSERVATIONAL_DRIFT")

    def test_wayland_x11_change_is_rebind(self):
        report=compare_snapshots(synthetic_snapshot(session="wayland"),synthetic_snapshot(session="x11"),physical_core_min=8)
        self.assertEqual(report["classification"],"RUNTIME_REBIND")

    def test_added_accelerator_requires_component_admission(self):
        amd={"discovery_id":"pci:0000:03:00.0","vendor":"AMD","pci_bdf":"0000:03:00.0","kernel_driver":"amdgpu","workload_compatible":True,"backends":[]}
        report=compare_snapshots(synthetic_snapshot(),synthetic_snapshot(accelerators=[amd]),physical_core_min=8)
        self.assertEqual(report["classification"],"COMPONENT_ADMISSION")
        self.assertFalse(report["current_host_promotion_claim"])

    def test_missing_accelerator_does_not_plan_uninstall(self):
        gpu={"discovery_id":"pci:0000:01:00.0","vendor":"NVIDIA","pci_bdf":"0000:01:00.0","kernel_driver":"nvidia","workload_compatible":True,"backends":[]}
        report=compare_snapshots(synthetic_snapshot(accelerators=[gpu]),synthetic_snapshot(),physical_core_min=8)
        self.assertEqual(report["classification"],"RUNTIME_REBIND")
        self.assertTrue(any("NO_AUTOMATIC_UNINSTALL" in x["recommended_action"] for x in report["changes"]))

    def test_cpu_floor_violation_is_safety_block(self):
        report=compare_snapshots(synthetic_snapshot(cores=16),synthetic_snapshot(cores=4),physical_core_min=8)
        self.assertEqual(report["classification"],"SAFETY_BLOCK")

    def test_qt_desktop_plan_uses_native_and_kf6(self):
        plan=materialization_plan(synthetic_snapshot())
        self.assertIn("FA3_QT_NATIVE_DESKTOP_ADAPTER",plan["components"])
        self.assertIn("FA3_KF6_ENHANCEMENT_ADAPTER",plan["components"])
        self.assertFalse(plan["plan_is_install_authority"])

    def test_non_qt_desktop_keeps_qt_core_and_xdg(self):
        snap=synthetic_snapshot(desktop="GNOME",strategy="QT6_XDG_FREEDESKTOP")
        plan=materialization_plan(snap)
        self.assertIn("FA3_QT6_QML_CORE",plan["components"])
        self.assertIn("FA3_XDG_FREEDESKTOP_INTEROP",plan["components"])
        self.assertNotIn("FA3_KF6_ENHANCEMENT_ADAPTER",plan["components"])

    def test_cpu_only_plan_has_no_accelerator_selector(self):
        plan=materialization_plan(synthetic_snapshot())
        self.assertTrue(plan["cpu_only"])
        self.assertEqual(plan["accelerator_provider_selectors"],[])

    def test_regression_matrix_complete(self):
        report=regression_check()
        self.assertEqual(report["result"],"PASS",report)
        self.assertEqual(report["passed"],report["total"])
        self.assertGreaterEqual(report["total"],8)

if __name__=="__main__":
    unittest.main()
