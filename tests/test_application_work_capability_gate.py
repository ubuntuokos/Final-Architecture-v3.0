from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_application_work_capability_gate import gate


class ApplicationWorkCapabilityGateTests(unittest.TestCase):
    def test_materialization_gate_passes(self) -> None:
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report["findings"])
        self.assertEqual(report["capability_count"], 175)
        self.assertEqual(report["new_capabilities"], 0)
        self.assertEqual(report["new_architectural_authorities"], 0)
        self.assertFalse(report["current_host_promotion_claim"])
        self.assertEqual(report["source_inventory_record_count"], 102)
        self.assertEqual(report["normalized_consumer_count"], 52)


if __name__ == "__main__":
    unittest.main()
