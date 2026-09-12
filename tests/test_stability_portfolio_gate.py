import json
import unittest
from pathlib import Path
from fa3_stability_portfolio_gate import gate

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class StabilityPortfolioGateTests(unittest.TestCase):
    def test_free_only_stability_portfolio_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["capability_count"], 143)
        self.assertFalse(report["paid_provider_fallback"])

    def test_nim_is_not_active(self):
        profile = load("canonical/profiles/FA3-STABILITY-PORTFOLIO-001.json")
        self.assertNotIn("FA3-PROVIDER-SD35-NVIDIA-NIM-001", profile["providers"])
        nim = load("canonical/providers/FA3-PROVIDER-SD35-NVIDIA-NIM-001.json")
        self.assertFalse(nim["active"])
        self.assertFalse(nim["routing_eligible"])
        self.assertEqual(nim["production_admission"], "DENY")

    def test_economics_policy_is_bound(self):
        profile = load("canonical/profiles/FA3-STABILITY-PORTFOLIO-001.json")
        contract = load("canonical/contracts/FA3-STABILITY-PORTFOLIO-CONTRACTS-001.json")
        self.assertEqual(profile["economics_policy"], "FA3-FREE-SELF-HOSTED-ONLY-001")
        self.assertEqual(contract["economics_policy"], "FA3-FREE-SELF-HOSTED-ONLY-001")
        self.assertFalse(contract["runtime_policy"]["paid_cloud_fallback"])


if __name__ == "__main__":
    unittest.main()
