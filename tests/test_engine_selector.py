# SPDX-License-Identifier: Apache-2.0
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_engine_selector import (
    EngineSelectionError,
    compare_static,
    compatibility_report,
    fallback_candidates,
    filter_catalog,
    materialize_catalog,
    selection_intent,
)
from fa3_engine_selector_gate import donor_registry_fingerprint, donor_snapshot_findings, gate

class EngineSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=materialize_catalog(ROOT)
        cls.by_id={e["engine_id"]:e for e in cls.catalog}
        cls.by_provider={e.get("provider_record"):e for e in cls.catalog if e.get("provider_record")}

    def test_canonical_gate_passes(self):
        report=gate(ROOT)
        self.assertEqual(report["result"],"PASS",report["findings"])
        self.assertEqual(report["capability_count"],175)

    def test_canonical_records_share_175_baseline(self):
        for rel in (
            "canonical/profiles/FA3-ENGINE-SELECTION-FABRIC-001.json",
            "canonical/contracts/FA3-ENGINE-SELECTION-CONTRACTS-001.json",
            "canonical/FA3-ENGINE-REGISTRY-001.json",
        ):
            row=json.loads((ROOT/rel).read_text(encoding="utf-8"))
            self.assertEqual(row["capability_count"],175,rel)

    def test_donor_snapshot_fingerprint_matches_declared_published_main(self):
        assessment=json.loads((ROOT/"canonical/assessments/FA3-ENGINE-SELECTION-REUSE-ASSESSMENT-2026-10-03.json").read_text(encoding="utf-8"))
        snap=assessment["donor_planning_snapshot"]
        self.assertEqual(donor_snapshot_findings(ROOT,snap),[])

    def test_donor_snapshot_changes_on_registry_mutation(self):
        source=ROOT/"canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
        live=donor_registry_fingerprint(source)
        with tempfile.TemporaryDirectory() as td:
            altered=Path(td)/"registry.json"
            altered.write_bytes(source.read_bytes()+b" ")
            changed=donor_registry_fingerprint(altered)
        self.assertNotEqual(live["donor_registry_blob_sha"],changed["donor_registry_blob_sha"])
        self.assertNotEqual(live["donor_registry_sha256"],changed["donor_registry_sha256"])

    def test_decision_fabric_is_not_selection_authority(self):
        p=ROOT/"canonical/assessments/FA3-ENGINE-SELECTION-DECISION-ASSESSMENT-2026-10-03.json"
        row=json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(row["assessment"],"NOT_APPLICABLE")
        self.assertIn("FA3-ENGINE-SELECTION-FABRIC-001",row["covered_ids"])
        self.assertFalse(row["security_boundary"]["may_expand_candidate_set"])

    def test_base_and_native_engines_coexist(self):
        self.assertIn("FA3-ENGINE-MLT-001",self.by_id)
        self.assertIn("FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001",self.by_id)
        self.assertTrue(self.by_id["FA3-ENGINE-MLT-001"]["permanent_parallel_option"])
        self.assertTrue(self.by_id["FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001"]["permanent_parallel_option"])

    def test_explicit_provider_records_are_not_duplicated(self):
        providers=[e.get("provider_record") for e in self.catalog if e.get("provider_record")]
        self.assertEqual(len(providers),len(set(providers)))
        self.assertEqual(sum(x=="FA3-PROVIDER-KDENLIVE-001" for x in providers),1)
        self.assertEqual(sum(x=="FA3-PROVIDER-FFMPEG-001" for x in providers),1)

    def test_required_provider_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"canonical/profiles").mkdir(parents=True)
            (root/"canonical/providers").mkdir(parents=True)
            (root/"canonical/FA3-ENGINE-REGISTRY-001.json").write_text(json.dumps({
                "schema":"fa3.engine-registry.v1","id":"FA3-ENGINE-REGISTRY-001",
                "authority":False,"selection_is_execution_authority":False,"default_engine":None,
                "engine_records":[],
                "provider_projection_rules":[{
                    "source":"canonical/profiles/test.json","pointer":"provider",
                    "engine_classes":["CUSTOM"],"execution_mode_default":["LOCAL"],
                    "require_provider_record":True
                }]
            }),encoding="utf-8")
            (root/"canonical/profiles/test.json").write_text(
                json.dumps({"provider":"FA3-PROVIDER-MISSING-001"}),encoding="utf-8")
            with self.assertRaises(EngineSelectionError):
                materialize_catalog(root)

    def test_non_admitted_provider_is_not_selectable(self):
        e=self.by_provider["FA3-PROVIDER-OPEN-SORA-PLAN-001"]
        self.assertNotIn(e["health_state"],{"READY","AVAILABLE_CONDITIONAL"})
        with self.assertRaises(EngineSelectionError):
            selection_intent(
                self.catalog,engine_id=e["engine_id"],scope="PROJECT",scope_target_id="project:x",
                required_capabilities=["CAP-126"])

    def test_capability_bindings_are_normalized(self):
        e=self.by_provider["FA3-PROVIDER-OPENDLSS-NR-001"]
        self.assertIn("CAP-136",e["capability_projection"])
        self.assertIn("CAP-071",e["capability_projection"])

    def test_hybrid_execution_modes_are_preserved(self):
        e=self.by_provider["FA3-PROVIDER-MINIMAX-H3-001"]
        self.assertTrue({"LOCAL","REMOTE","HYBRID"}.issubset(set(e["execution_modes"])))

    def test_materialized_profile_capabilities_have_engine_bindings(self):
        profile=json.loads((ROOT/"canonical/profiles/FA3-ENGINE-SELECTION-FABRIC-001.json").read_text(encoding="utf-8"))
        for cap in profile["capabilities"]:
            self.assertTrue(any(cap in e.get("capability_projection",[]) for e in self.catalog),cap)
        self.assertNotIn("CAP-162",profile["capabilities"])

    def test_digital_human_reuses_existing_capability(self):
        e=self.by_id["FA3-ENGINE-FA3-DIGITAL-HUMAN-NATIVE-001"]
        self.assertIn("CAP-043",e["capability_projection"])
        self.assertFalse(e["architectural_authority"])

    def test_capability_filter(self):
        rows=filter_catalog(self.catalog,required_capabilities=["CAP-043"])
        ids={r["engine_id"] for r in rows}
        self.assertIn("FA3-ENGINE-FA3-DIGITAL-HUMAN-NATIVE-001",ids)
        self.assertNotIn("FA3-ENGINE-MLT-001",ids)

    def test_non_global_scope_requires_target(self):
        with self.assertRaises(EngineSelectionError):
            selection_intent(
                self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",
                required_capabilities=["CAP-121"])
        intent=selection_intent(
            self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",
            scope_target_id="project:alpha",required_capabilities=["CAP-121"])
        self.assertEqual(intent["scope_target_id"],"project:alpha")

    def test_selection_is_intent_not_execution(self):
        intent=selection_intent(
            self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="CLIP",scope_target_id="clip:42",
            required_capabilities=["CAP-121"],fallback_mode="OFF")
        self.assertFalse(intent["execution_requested"])
        self.assertFalse(intent["silent_fallback"])
        self.assertEqual(intent["provider_model_routing_authority"],"FA3-AUTH-MODEL-ROUTER-001")

    def test_no_silent_fallback(self):
        intent=selection_intent(
            self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",scope_target_id="project:a",
            required_capabilities=["CAP-121"],fallback_mode="OFF")
        self.assertEqual(fallback_candidates(self.catalog,intent),[])

    def test_approved_only_requires_and_accepts_allowlist(self):
        with self.assertRaises(EngineSelectionError):
            selection_intent(
                self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",scope_target_id="project:a",
                required_capabilities=["CAP-121"],fallback_mode="APPROVED_ONLY")
        intent=selection_intent(
            self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",scope_target_id="project:a",
            required_capabilities=["CAP-121"],fallback_mode="APPROVED_ONLY",
            approved_fallback_engine_ids=["FA3-ENGINE-KDENLIVE-001"])
        self.assertEqual(intent["fallback_policy"]["approved_engine_ids"],["FA3-ENGINE-KDENLIVE-001"])

    def test_incompatible_capability_fails(self):
        with self.assertRaises(EngineSelectionError):
            selection_intent(
                self.catalog,engine_id="FA3-ENGINE-MLT-001",scope="PROJECT",scope_target_id="project:a",
                required_capabilities=["CAP-043"])

    def test_compatibility_report_is_explicit(self):
        report=compatibility_report(
            self.catalog,engine_id="FA3-ENGINE-MLT-001",
            required_capabilities=["CAP-121","CAP-043"])
        self.assertEqual(report["grade"],"PARTIAL")
        self.assertEqual(report["missing_capabilities"],["CAP-043"])
        report2=compatibility_report(
            self.catalog,engine_id="FA3-ENGINE-MLT-001",
            required_capabilities=["CAP-043"])
        self.assertEqual(report2["grade"],"UNSUPPORTED")

    def test_control_center_engine_manager_wiring(self):
        main=(ROOT/"apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        main_cpp=(ROOT/"apps/fa3-control-center/src/main.cpp").read_text(encoding="utf-8")
        cmake=(ROOT/"apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")
        service=(ROOT/"apps/fa3-control-center/src/EngineSelectorService.cpp").read_text(encoding="utf-8")
        qml=(ROOT/"apps/shared/engine-selector/qml/EngineSelectorPanel.qml").read_text(encoding="utf-8")
        self.assertIn('"models.engines"',main)
        self.assertIn("EngineManagerPage",main)
        self.assertIn('setContextProperty("fa3EngineSelector"',main_cpp)
        self.assertIn("EngineSelectorService.cpp",cmake)
        self.assertIn("compatibilityReport",service)
        self.assertIn("scopeTarget",qml)
        self.assertIn("compareIds.indexOf",qml)

    def test_static_compare_includes_compatibility_without_execution(self):
        rows=compare_static(
            self.catalog,
            ["FA3-ENGINE-MLT-001","FA3-ENGINE-KDENLIVE-001"],
            ["CAP-121"])
        self.assertTrue(all(r["static_only"] for r in rows))
        self.assertTrue(all(r["compatibility_grade"]=="NATIVE" for r in rows))

if __name__=="__main__":
    unittest.main()
