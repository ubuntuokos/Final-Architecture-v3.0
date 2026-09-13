import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_openmodeldb_provider_gate import (
    GATE_ID,
    PROVIDER_ID,
    UPSTREAM_COMMIT,
    gate,
    reference_check,
    resource_admission,
    run_regressions,
)


class OpenModelDBProviderGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for name in ("canonical", "evidence"):
            shutil.copytree(ROOT / name, root / name)
        return td, root

    def _write(self, path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(GATE_ID, report["gate_id"])
        self.assertEqual(PROVIDER_ID, report["provider_id"])
        self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_eight_fail_closed_regressions_pass(self):
        report = run_regressions()
        self.assertEqual("PASS", report["result"])
        self.assertEqual(8, report["passed"])
        self.assertEqual(8, report["total"])

    def test_checksum_mismatch_blocks_resource(self):
        self.assertFalse(resource_admission(
            expected_sha256="a" * 64,
            observed_sha256="b" * 64,
            license_id="MIT",
            format_name="safetensors",
            security_admitted=True,
            mediated=True,
            lineage_known=True,
            runtime_verified=True,
            runtime_evidence="EVID-1",
        ))

    def test_unknown_license_blocks_resource(self):
        self.assertFalse(resource_admission(
            expected_sha256="a" * 64,
            observed_sha256="a" * 64,
            license_id="UNKNOWN",
            format_name="safetensors",
            security_admitted=True,
            mediated=True,
            lineage_known=True,
            runtime_verified=True,
            runtime_evidence="EVID-1",
        ))

    def test_pth_without_security_admission_blocks_resource(self):
        self.assertFalse(resource_admission(
            expected_sha256="a" * 64,
            observed_sha256="a" * 64,
            license_id="MIT",
            format_name="pth",
            security_admitted=False,
            mediated=True,
            lineage_known=True,
            runtime_verified=True,
            runtime_evidence="EVID-1",
        ))

    def test_provider_cannot_become_artifact_trust_authority(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-OPENMODELDB-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["artifact_trust_authority"] = True
            self._write(path, obj)
            report = reference_check(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "OPENMODELDB-REF-010" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_floating_catalog_pin_is_rejected(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-OPENMODELDB-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["upstream_commit"] = "main"
            self._write(path, obj)
            report = reference_check(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "OPENMODELDB-REF-010" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_upstream_reference_is_immutable_commit(self):
        self.assertEqual(40, len(UPSTREAM_COMMIT))
        self.assertNotIn(UPSTREAM_COMMIT, {"main", "master", "latest"})


if __name__ == "__main__":
    unittest.main()
