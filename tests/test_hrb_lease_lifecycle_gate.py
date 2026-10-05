import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hrb_lease_lifecycle_gate import evaluate


class HrbLeaseLifecycleGateTests(unittest.TestCase):
    def test_phase_one_gate_passes(self):
        result = evaluate(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["new_capabilities"], 0)
        self.assertEqual(result["new_architectural_authorities"], 0)
        self.assertFalse(result["global_promotion_claim"])

    def test_authority_crypto_and_runtime_binding_boundaries_pass(self):
        result = evaluate(ROOT)
        by_name = {x["name"]: x for x in result["checks"]}
        for name in (
            "capability-authority-stable",
            "existing-hrb-authority",
            "state-machine-exact",
            "hmac-boundary",
            "runtime-binding-complete",
            "secret-authority-preserved",
            "wrong-runtime-no-kill",
            "durable-evidence-boundary",
            "boot-clock-binding",
            "negative-matrix-declared",
            "negative-matrix-tested",
        ):
            self.assertEqual(by_name[name]["status"], "PASS", name)


if __name__ == "__main__":
    unittest.main()
