from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_lut_color_gate import (
    PATHS,
    color_pipeline_allowed,
    execution_receipt_allowed,
    fixture_artifact,
    fixture_pipeline,
    fixture_receipt,
    gate,
    lut_artifact_allowed,
    regression_cases,
)

ROOT = Path(__file__).resolve().parents[1]


class LUTColorGateTests(unittest.TestCase):
    def test_canonical_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(24, report["regression_count"])
        self.assertEqual("NOT_CLAIMED", report["current_host_runtime_evidence"])

    def test_positive_negative_regressions_pass(self):
        cases = regression_cases()
        self.assertEqual(24, len(cases))
        self.assertTrue(all(case["positive"] for case in cases), cases)
        self.assertTrue(all(case["negative_refusal"] for case in cases), cases)

    def test_artifact_admission_is_fail_closed(self):
        artifact = fixture_artifact()
        self.assertTrue(lut_artifact_allowed(artifact))
        self.assertFalse(lut_artifact_allowed({**artifact, "sha256": "not-a-sha256"}))
        self.assertFalse(lut_artifact_allowed({**artifact, "input_color_space": "UNKNOWN"}))
        self.assertFalse(lut_artifact_allowed({**artifact, "runtime_download": True}))
        self.assertFalse(lut_artifact_allowed({**artifact, "executable_payload": True}))
        self.assertFalse(lut_artifact_allowed({**artifact, "artifact_kind": "OCIO_CONFIG"}))
        self.assertFalse(lut_artifact_allowed({**artifact, "parser_validation": "UNKNOWN"}))

    def test_pipeline_order_and_provider_boundary_are_fail_closed(self):
        pipeline = fixture_pipeline()
        self.assertTrue(color_pipeline_allowed(pipeline))
        self.assertFalse(color_pipeline_allowed({**pipeline, "stage_order": list(reversed(pipeline["stage_order"]))}))
        self.assertFalse(color_pipeline_allowed({**pipeline, "provider_surface": "OPENFX_IN_PROCESS_KDENLIVE"}))
        self.assertFalse(color_pipeline_allowed({**pipeline, "kdenlive_project_xml_mutation": True}))
        without_primary = {**pipeline, "transforms": [item for item in pipeline["transforms"] if item["stage"] != "PRIMARY_CORRECTION"]}
        self.assertFalse(color_pipeline_allowed(without_primary))

    def test_execution_receipt_requires_qc_human_approval_and_rollback(self):
        receipt = fixture_receipt()
        self.assertTrue(execution_receipt_allowed(receipt))
        self.assertFalse(execution_receipt_allowed({**receipt, "gamut_check": "UNKNOWN"}))
        self.assertFalse(execution_receipt_allowed({**receipt, "picture_lock_human_approval": False}))
        self.assertFalse(execution_receipt_allowed({**receipt, "rollback_ref": ""}))
        self.assertFalse(execution_receipt_allowed({**receipt, "provider_surface": "UNREGISTERED"}))

    def test_registry_authority_escalation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "reports", "__pycache__"))
            path = dst / PATHS["registry"]
            record = json.loads(path.read_text(encoding="utf-8"))
            record["architectural_authority"] = True
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            report = gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "LUT-COLOR-REF-005" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
