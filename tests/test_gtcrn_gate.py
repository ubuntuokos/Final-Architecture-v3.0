import json, tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fa3_gtcrn_gate import gate, PATHS

class GTCRNGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
    def test_reference_gate_passes(self):
        self.assertEqual(gate(self.root)["result"], "PASS")
    def test_negative_authority_claim_fails(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            for rel in PATHS.values():
                src = self.root / rel; dst = td / rel; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(src.read_bytes())
            p = td / PATHS["provider"]; d = json.loads(p.read_text()); d["authority_boundaries"]["audio"] = True; p.write_text(json.dumps(d))
            self.assertEqual(gate(td)["result"], "FAIL")
    def test_negative_runtime_promotion_claim_fails(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            for rel in PATHS.values():
                src = self.root / rel; dst = td / rel; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(src.read_bytes())
            p = td / PATHS["release"]; d = json.loads(p.read_text()); d["production_promotion_claimed"] = True; p.write_text(json.dumps(d))
            self.assertEqual(gate(td)["result"], "FAIL")

if __name__ == "__main__":
    unittest.main()
