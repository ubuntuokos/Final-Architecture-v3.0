from __future__ import annotations

import unittest
from pathlib import Path

from fa3_language_gateway_gate import (
    LanguagePolicyDenied,
    gate,
    language_capability_is_operable,
    requires_hungarian_support,
    validate_language_selection,
)

ROOT = Path(__file__).resolve().parents[1]


class LanguageGatewayGateTests(unittest.TestCase):
    def test_primary_secondary_must_be_distinct(self):
        with self.assertRaises(LanguagePolicyDenied):
            validate_language_selection("en-US", "en-US")

    def test_selected_hungarian_conditionally_activates_support(self):
        selection = validate_language_selection("hu-HU", "en-US", ["de-DE"])
        self.assertTrue(requires_hungarian_support(selection))
        international = validate_language_selection("en-US", "de-DE", [])
        self.assertFalse(requires_hungarian_support(international))

    def test_language_status_taxonomy_is_fail_closed(self):
        for status in ("NATIVE", "VALIDATED", "BRIDGED"):
            self.assertTrue(language_capability_is_operable(status))
        for status in ("UNVERIFIED", "UNSUPPORTED", "UNKNOWN"):
            self.assertFalse(language_capability_is_operable(status))

    def test_full_reference_gate_passes_without_production_claim(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertFalse(report["current_host_production_claim"])


if __name__ == "__main__":
    unittest.main()
