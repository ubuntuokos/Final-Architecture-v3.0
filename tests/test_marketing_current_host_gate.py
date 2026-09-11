import json
import tempfile
import unittest
from pathlib import Path

from src.fa3_marketing_current_host_gate import REQUIRED_PROVIDERS, REQUIRED_TESTS, evaluate


def receipt():
    return {
        "schema": "fa3.marketing-current-host-evidence.v1",
        "execution_context": "CURRENT_HOST_REAL_EXECUTION",
        "provider_ids": sorted(REQUIRED_PROVIDERS),
        "runtime_status": "CURRENT_HOST_PRODUCTION_E2E_PASS",
        "capability_count": 143,
        "new_architectural_authorities": 0,
        "tests": {name: {"status": "PASS"} for name in REQUIRED_TESTS},
    }


class MarketingCurrentHostGateTests(unittest.TestCase):
    def test_pass(self):
        self.assertEqual("PASS", evaluate(receipt())["result"])

    def test_reference_ci_cannot_impersonate_current_host(self):
        r = receipt()
        r["execution_context"] = "CI_REFERENCE"
        self.assertEqual("FAIL", evaluate(r)["result"])

    def test_one_provider_failure_fails_closed(self):
        r = receipt()
        r["tests"]["twenty_person_roundtrip"]["status"] = "FAIL"
        self.assertEqual("FAIL", evaluate(r)["result"])

    def test_missing_provider_fails_closed(self):
        r = receipt()
        r["provider_ids"] = r["provider_ids"][:-1]
        self.assertEqual("FAIL", evaluate(r)["result"])

    def test_architecture_drift_fails_closed(self):
        r = receipt()
        r["capability_count"] = 144
        self.assertEqual("FAIL", evaluate(r)["result"])


if __name__ == "__main__":
    unittest.main()
