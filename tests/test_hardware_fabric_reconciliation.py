from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hardware_fabric_reconciliation import CAPABILITY_COUNT, audit  # noqa: E402


class HardwareFabricReconciliationTests(unittest.TestCase):
    def test_repository_semantics_reconciled(self) -> None:
        report = audit(ROOT)
        self.assertEqual(report["result"], "PASS", report.get("findings"))

    def test_static_reconciliation_never_promotes_current_host(self) -> None:
        report = audit(ROOT)
        self.assertEqual(report["current_host_status"], "PENDING_VENDOR_NEUTRAL_MULTI_VENDOR_CURRENT_HOST_EVIDENCE")
        self.assertFalse(report["global_promotion_claim"])
        self.assertEqual(report["new_capabilities"], 0)
        self.assertEqual(report["new_architectural_authorities"], 0)
        self.assertEqual(report["capability_count"], CAPABILITY_COUNT)


if __name__ == "__main__":
    unittest.main()
