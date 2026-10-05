from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_uaf_gate import gate


class UafGateTests(unittest.TestCase):
    def test_static_canonical_gate(self) -> None:
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"])
        self.assertEqual(0, report["capability_delta"])
        self.assertEqual(0, report["authority_delta"])
        self.assertFalse(report["global_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
