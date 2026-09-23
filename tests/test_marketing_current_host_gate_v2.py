from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_marketing_current_host_gate import REQUIRED_LABELS, REQUIRED_PROVIDERS, REQUIRED_TESTS, evaluate


def receipt():
    return {
        "schema": "fa3.marketing-current-host-evidence.v2",
        "execution_context": "CURRENT_HOST_REAL_EXECUTION",
        "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "synthetic": False,
        "runner_labels": sorted(REQUIRED_LABELS),
        "provider_ids": sorted(REQUIRED_PROVIDERS),
        "runtime_status": "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "secret_values_collected": False,
        "capability_count": 143,
        "new_architectural_authorities": 0,
        "current_host_commit_sha": "0123456789abcdef",
        "tests": {name: {"status": "PASS"} for name in REQUIRED_TESTS},
    }


class MarketingCurrentHostGateV2Tests(unittest.TestCase):
    def test_exact_current_host_receipt_passes_component_gate(self):
        self.assertEqual("PASS", evaluate(receipt())["result"])

    def test_reference_or_synthetic_receipt_cannot_pass(self):
        value = receipt()
        value["execution_context"] = "CI_REFERENCE"
        value["synthetic"] = True
        value["evidence_level"] = "STATIC_AND_REFERENCE_PASS_NOT_RUNTIME"
        self.assertEqual("BLOCKED", evaluate(value)["result"])

    def test_each_negative_marketing_control_is_required(self):
        for name in ("consent_missing_blocks_dispatch", "suppression_blocks_dispatch", "approval_missing_blocks_launch"):
            value = receipt()
            value["tests"][name]["status"] = "FAIL"
            self.assertEqual("BLOCKED", evaluate(value)["result"], name)

    def test_missing_runner_label_or_commit_blocks(self):
        value = receipt()
        value["runner_labels"].remove("fa3-current-host")
        value["current_host_commit_sha"] = "UNKNOWN"
        self.assertEqual("BLOCKED", evaluate(value)["result"])


if __name__ == "__main__":
    unittest.main()
