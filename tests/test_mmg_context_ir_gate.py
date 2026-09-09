import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_mmg_context_ir import run_reference_conformance
from fa3_mmg_context_ir_gate import gate


class TestMMGContextIRExecutableGate(unittest.TestCase):
    def test_reference_conformance_matrix_passes_18_of_18(self):
        report = run_reference_conformance()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], 18)
        self.assertEqual(report["total"], 18)
        self.assertFalse(report["current_host_runtime_claim"])
        self.assertFalse(report["provider_runtime_execution_claim"])

    def test_canonical_executable_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report["findings"])
        self.assertEqual(report["blocking_findings"], 0)
        self.assertEqual(report["capability_count"], 143)
        self.assertEqual(report["new_capabilities"], 0)
        self.assertEqual(report["new_architectural_authorities"], 0)

    def test_bin_fa3_enforce_dispatches_mmg_gate(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(
            [str(ROOT / "bin/fa3-enforce"), "mmg-context-ir"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["executable_conformance"]["passed"], 18)


if __name__ == "__main__":
    unittest.main()
