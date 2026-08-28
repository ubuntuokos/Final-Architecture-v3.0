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
        self.assertEqual(data["current_host"]["result"], "NOT_REQUIRED_IN_CI")

    def test_current_host_command_fails_closed_without_receipt(self):
        root = Path(__file__).resolve().parents[1]
        receipt = root / "evidence" / "receipts" / "terax-current-host.json"
        if receipt.exists():
            receipt.unlink()
        cp = subprocess.run(
            [sys.executable, str(root / "src" / "fa3_enforce.py"), "--root", str(root), "terax"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(cp.returncode, 2, cp.stdout + "\n" + cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["result"], "FAIL")
        self.assertEqual(data["mode"], "CURRENT_HOST")
        self.assertEqual(data["current_host"]["result"], "FAIL")


if __name__ == "__main__":
    unittest.main()
