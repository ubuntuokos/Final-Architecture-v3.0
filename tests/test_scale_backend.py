from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_scale_backend import (
    evaluate_scale_execution_rights,
    parse_scaleinfo,
    probe_scale,
)


class ScaleBackendUnitTests(unittest.TestCase):
    def test_scaleinfo_parser_binds_documented_short_domain_bdf(self):
        rows = parse_scaleinfo(
            "Found 1 CUDA devices\n"
            "Device 0 (00:23:00.0): AMD Radeon Pro W6800 - gfx1030 (AMD) "
            "<amdgcn-amd-amdhsa--gfx1030>\n"
        )
        self.assertIn("0000:23:00.0", rows)
        self.assertEqual("gfx1030", rows["0000:23:00.0"]["target"])
        self.assertEqual("AMD", rows["0000:23:00.0"]["vendor"])

    def test_scale_rights_fail_closed_without_receipt(self):
        result = evaluate_scale_execution_rights(None)
        self.assertEqual("FAIL", result["result"])
        self.assertFalse(result["admitted"])

    def test_scale_commercial_execution_requires_entitlement_reference(self):
        receipt = {
            "schema": "fa3.scale-execution-rights-receipt.v1",
            "authority": "FA3-AUTH-SECURITY-GOV-001",
            "subject_id": "FA3-EXTERNAL-SCALE-TOOLKIT",
            "result": "PASS",
            "execution_allowed": True,
            "commercial_use_allowed": True,
            "raw_secret_material_present": False,
        }
        result = evaluate_scale_execution_rights(receipt)
        self.assertEqual("FAIL", result["result"])
        self.assertIn("SCALE_COMMERCIAL_ENTITLEMENT_REFERENCE_MISSING", result["findings"])

    def test_scale_rights_receipt_can_admit_external_commercial_entitlement(self):
        receipt = {
            "schema": "fa3.scale-execution-rights-receipt.v1",
            "authority": "FA3-AUTH-SECURITY-GOV-001",
            "subject_id": "FA3-EXTERNAL-SCALE-TOOLKIT",
            "result": "PASS",
            "execution_allowed": True,
            "commercial_use_allowed": True,
            "entitlement_reference": "secret-broker://license/scale/customer-entitlement",
            "raw_secret_material_present": False,
        }
        result = evaluate_scale_execution_rights(receipt)
        self.assertEqual("PASS", result["result"])
        self.assertTrue(result["admitted"])

    @mock.patch("fa3_scale_backend._run")
    @mock.patch("fa3_scale_backend.shutil.which", return_value="/opt/scale/bin/scaleinfo")
    @mock.patch("fa3_scale_backend.Path.is_file", return_value=False)
    def test_probe_is_read_only_and_reports_exact_devices(self, _is_file, _which, run):
        run.return_value = (
            0,
            "Device 0 (0000:0a:00.0): AMD Radeon RX 7900 XTX - gfx1100 (AMD) "
            "<amdgcn-amd-amdhsa--gfx1100>",
            "",
        )
        result = probe_scale({})
        self.assertTrue(result["detected"])
        self.assertTrue(result["usable"])
        self.assertIn("0000:0a:00.0", result["devices"])
        self.assertIn("scale-discovery:read-only", result["evidence"])
        run.assert_called_once_with(["/opt/scale/bin/scaleinfo"])


if __name__ == "__main__":
    unittest.main()
