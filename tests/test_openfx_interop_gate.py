from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from fa3_openfx_interop_gate import PATHS, gate, plugin_descriptor_allowed, render_manifest_allowed, editorial_handoff_allowed, regression_cases

ROOT=Path(__file__).resolve().parents[1]

class OpenFXInteropGateTests(unittest.TestCase):
    def test_canonical_gate_passes(self):
        report=gate(ROOT)
        self.assertEqual("PASS",report["result"],report)
        self.assertEqual(20,report["regression_count"])
        self.assertEqual("NOT_CLAIMED",report["current_host_runtime_evidence"])
    def test_positive_negative_regressions_pass(self):
        cases=regression_cases()
        self.assertEqual(20,len(cases))
        self.assertTrue(all(x["positive"] for x in cases))
        self.assertTrue(all(x["negative_refusal"] for x in cases))
    def test_plugin_admission_is_fail_closed(self):
        good={"schema":"fa3.openfx-plugin-descriptor.v1","plugin_id":"x","bundle_sha256":"sha256:x","api_version":"1.5.1","host_abi":"linux-x86_64","license_id":"BSD","allowlisted_path":"/opt/fa3/x.ofx.bundle","network_fetch_during_render":False}
        self.assertTrue(plugin_descriptor_allowed(good))
        self.assertFalse(plugin_descriptor_allowed({**good,"bundle_sha256":""}))
        self.assertFalse(plugin_descriptor_allowed({**good,"network_fetch_during_render":True}))
    def test_render_requires_lineage_and_hrb_lease(self):
        good={"schema":"fa3.openfx-render-manifest.v1","source_artifact_sha256":"sha256:s","derived_artifact_sha256":"sha256:d","plugin_parameter_digest":"sha256:p","frame_range":"1-2","fps":"24/1","timebase":"24/1","alpha_mode":"premultiplied","pixel_format":"RGBA16F","color_management":"OCIO:ACEScg","ffprobe_receipt":"sha256:f","rollback_artifact_sha256":"sha256:r","hrb_lease_id":"lease"}
        self.assertTrue(render_manifest_allowed(good))
        self.assertFalse(render_manifest_allowed({**good,"hrb_lease_id":None}))
    def test_handoff_forbids_xml_mutation_and_requires_hitl(self):
        good={"schema":"fa3.openfx-kdenlive-handoff.v1","timeline_ir":"OpenTimelineIO","kdenlive_project_xml_mutation":False,"picture_lock_requires_human_approval":True,"relink_target_artifact_sha256":"sha256:d","derived_artifact_sha256":"sha256:d"}
        self.assertTrue(editorial_handoff_allowed(good))
        self.assertFalse(editorial_handoff_allowed({**good,"kdenlive_project_xml_mutation":True}))
        self.assertFalse(editorial_handoff_allowed({**good,"picture_lock_requires_human_approval":False}))
    def test_provider_escalation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst=Path(tmp)/"repo"
            shutil.copytree(ROOT,dst,ignore=shutil.ignore_patterns(".git","reports","__pycache__"))
            p=dst/PATHS["provider"]; obj=json.loads(p.read_text()); obj["architectural_authority"]=True; p.write_text(json.dumps(obj)+"\n")
            report=gate(dst)
            self.assertEqual("FAIL",report["result"])
            self.assertTrue(any(x["code"]=="OPENFX-REF-005" for x in report["findings"]))
if __name__=="__main__":
    unittest.main()
