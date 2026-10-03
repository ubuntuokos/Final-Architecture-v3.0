# SPDX-License-Identifier: Apache-2.0
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_engine_selector import (
    EngineSelectionError, materialize_catalog, filter_catalog,
    selection_intent, fallback_candidates, compare_static,
)
from fa3_engine_selector_gate import gate

class EngineSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=materialize_catalog(ROOT)
        cls.by_id={e["engine_id"]:e for e in cls.catalog}

    def test_canonical_gate_passes(self):
        report=gate(ROOT)
        self.assertEqual(report["result"],"PASS",report["findings"])
        self.assertEqual(report["capability_count"],175)

    def test_base_and_native_engines_coexist(self):
        self.assertIn("FA3-ENGINE-MLT-001",self.by_id)
        self.assertIn("FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001",self.by_id)
        self.assertTrue(self.by_id["FA3-ENGINE-MLT-001"]["permanent_parallel_option"])
        self.assertTrue(self.by_id["FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001"]["permanent_parallel_option"])

    def test_digital_human_reuses_existing_capability(self):
        e=self.by_id["FA3-ENGINE-FA3-DIGITAL-HUMAN-NATIVE-001"]
        self.assertIn("CAP-043",e["capability_projection"])
        self.assertFalse(e["architectural_authority"])

    def test_capability_filter(self):
        rows=filter_catalog(self.catalog,required_capabilities=["CAP-043"])
        ids={r["engine_id"] for r in rows}
        self.assertIn("FA3-ENGINE-FA3-DIGITAL-HUMAN-NATIVE-001",ids)
        self.assertNotIn("FA3-ENGINE-MLT-001",ids)

    def test_selection_is_intent_not_execution(self):
        intent=selection_intent(
            self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="CLIP",
            required_capabilities=["CAP-121"],fallback_mode="OFF")
        self.assertFalse(intent["execution_requested"])
        self.assertFalse(intent["silent_fallback"])
        self.assertEqual(intent["provider_model_routing_authority"],"FA3-AUTH-MODEL-ROUTER-001")

    def test_no_silent_fallback(self):
        intent=selection_intent(
            self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",
            required_capabilities=["CAP-121"],fallback_mode="OFF")
        self.assertEqual(fallback_candidates(self.catalog,intent),[])

    def test_approved_only_requires_allowlist(self):
        with self.assertRaises(EngineSelectionError):
            selection_intent(
                self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",
                required_capabilities=["CAP-121"],fallback_mode="APPROVED_ONLY")

    def test_incompatible_capability_fails(self):
        with self.assertRaises(EngineSelectionError):
            selection_intent(
                self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",
                required_capabilities=["CAP-043"])

    def test_static_compare_does_not_execute(self):
        rows=compare_static(self.catalog,[
            "FA3-ENGINE-MLT-001",
            "FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001"])
        self.assertTrue(all(r["static_only"] for r in rows))

if __name__=="__main__":
    unittest.main()
