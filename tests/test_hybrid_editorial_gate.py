from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_hybrid_editorial_gate as gate_module
from fa3_hybrid_editorial_reference import (
    ai_job_allowed,
    final_master_source_allowed,
    run_reference_e2e,
)


class HybridEditorialGateTests(unittest.TestCase):
    def _copy_root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        return temp, root

    def test_reference_e2e_passes(self):
        report = run_reference_e2e({"name": "unit"})
        self.assertEqual(report["result"], "PASS", report)
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["current_host_krita_runtime_claim"])
        self.assertFalse(report["current_host_kdenlive_runtime_claim"])

    def test_exact_18_case_executable_matrix_passes(self):
        report = gate_module.run_regressions()
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["passed"], 18)
        self.assertEqual(report["total"], 18)
        self.assertTrue(report["case_ids_exact"])
        self.assertEqual(
            [item["case_id"] for item in report["cases"]],
            gate_module.CASE_IDS,
        )

    def test_full_gate_passes(self):
        report = gate_module.gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(
            report["gate_id"],
            "FA3-GATE-HYBRID-EDITORIAL-001",
        )

    def test_direct_mcp_bypass_fails(self):
        job = {
            "intent": "speech.transcribe",
            "via_central_mcp": False,
            "execution_mode": "ASYNC",
            "cancellable": True,
            "delegated_profile": "FA3-STT-MEDIA-001",
            "local_accelerator": False,
            "destructive": False,
        }
        self.assertFalse(ai_job_allowed(job))

    def test_proxy_cannot_be_final_master_source(self):
        self.assertFalse(
            final_master_source_allowed({"quality_role": "PROXY"})
        )
        self.assertTrue(
            final_master_source_allowed({"quality_role": "ORIGINAL"})
        )

    def test_krita_authority_drift_fails_closed(self):
        temp, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-KRITA-001.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["architectural_authority"] = True
            path.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
            )
            report = gate_module.gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(
                any(
                    item["code"] == "HYB-CANON-005"
                    for item in report["canonical"]["findings"]
                )
            )
        finally:
            temp.cleanup()

    def test_otio_drift_fails_closed(self):
        temp, root = self._copy_root()
        try:
            path = (
                root
                / "canonical/contracts/"
                "FA3-HYBRID-EDITORIAL-CONTRACTS-001.json"
            )
            value = json.loads(path.read_text(encoding="utf-8"))
            value["canonical_timeline_ir"] = "MLT XML"
            path.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
            )
            report = gate_module.gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(
                any(
                    item["code"] == "HYB-CANON-003"
                    for item in report["canonical"]["findings"]
                )
            )
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
