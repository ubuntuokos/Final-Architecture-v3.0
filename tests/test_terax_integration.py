import json
import subprocess
import sys
import unittest
from pathlib import Path


class TeraxEnforceIntegrationTests(unittest.TestCase):
    def test_ci_only_terax_command_passes_and_writes_report(self):
        root = Path(__file__).resolve().parents[1]
        report = root / "reports" / "terax-gate-report.json"
        if report.exists():
            report.unlink()
        cp = subprocess.run(
            [sys.executable, str(root / "src" / "fa3_enforce.py"), "--root", str(root), "--ci-only", "terax"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(cp.returncode, 0, cp.stdout + "\n" + cp.stderr)
        self.assertTrue(report.exists())
        data = json.loads(report.read_text())
        self.assertEqual(data["result"], "PASS")
        self.assertEqual(data["mode"], "CI_REFERENCE_ONLY")
        self.assertEqual(data["reference"]["result"], "PASS")
        self.assertEqual(data["regressions"]["passed"], 17)
        self.assertEqual(data["regressions"]["total"], 17)
        self.assertEqual(data["hardware_regressions"]["result"], "PASS")
        self.assertEqual(data["current_host"]["result"], "NOT_REQUIRED_IN_CI")
        self.assertFalse(data["provider_receipt_substitution_allowed"])
        self.assertFalse(data["current_host_is_global_promotion_requirement"])

    def test_current_host_command_passes_reference_gate_without_optional_receipt(self):
        root = Path(__file__).resolve().parents[1]
        receipt = root / "evidence" / "receipts" / "terax-current-host.json"
        if receipt.exists():
            receipt.unlink()
        cp = subprocess.run(
            [sys.executable, str(root / "src" / "fa3_enforce.py"), "--root", str(root), "terax"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(cp.returncode, 0, cp.stdout + "\n" + cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["result"], "PASS")
        self.assertEqual(data["mode"], "REFERENCE_PLUS_AUXILIARY_CURRENT_HOST")
        self.assertEqual(data["current_host"]["result"], "NOT_PRESENT_OPTIONAL")
        self.assertFalse(data["current_host_is_global_promotion_requirement"])
        self.assertFalse(data["provider_receipt_substitution_allowed"])


if __name__ == "__main__":
    unittest.main()
