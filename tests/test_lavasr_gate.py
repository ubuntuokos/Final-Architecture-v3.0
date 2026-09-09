import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fa3_lavasr_gate import PATHS, gate


class LavaSRGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def copy_gate_fixture(self, target: Path) -> None:
        for rel in PATHS.values():
            src = self.root / rel
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())

    def test_reference_gate_passes(self):
        report = gate(self.root)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["rules_checked"], 40)

    def test_negative_authority_claim_fails(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            self.copy_gate_fixture(target)
            path = target / PATHS["provider"]
            data = json.loads(path.read_text())
            data["authority_boundaries"]["inference"] = True
            path.write_text(json.dumps(data))
            self.assertEqual(gate(target)["result"], "FAIL")

    def test_negative_runtime_promotion_claim_fails(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            self.copy_gate_fixture(target)
            path = target / PATHS["release"]
            data = json.loads(path.read_text())
            data["production_promotion_claimed"] = True
            path.write_text(json.dumps(data))
            self.assertEqual(gate(target)["result"], "FAIL")

    def test_negative_asset_hash_drift_fails(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            self.copy_gate_fixture(target)
            path = target / PATHS["allowlist"]
            data = json.loads(path.read_text())
            data["bundle"]["assets"][0]["sha256"] = "0" * 64
            path.write_text(json.dumps(data))
            self.assertEqual(gate(target)["result"], "FAIL")

    def test_negative_double_denoise_policy_drift_fails(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            self.copy_gate_fixture(target)
            path = target / PATHS["contract"]
            data = json.loads(path.read_text())
            data["denoise"]["implicit_double_denoise"] = "ALLOWED"
            path.write_text(json.dumps(data))
            self.assertEqual(gate(target)["result"], "FAIL")


if __name__ == "__main__":
    unittest.main()
