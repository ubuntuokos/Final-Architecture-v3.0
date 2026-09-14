from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_language_gateway_gate import (
    LanguagePolicyDenied,
    language_capability_is_operable,
    requires_hungarian_support,
    run_conformance,
    validate_language_selection,
)


class TestLanguagePolicyFunctions(unittest.TestCase):
    def test_primary_secondary_are_required_and_distinct(self) -> None:
        selection = validate_language_selection("hu-HU", "en-US", ["de-DE", "hu-HU"])
        self.assertEqual(selection["primary_language"], "hu-HU")
        self.assertEqual(selection["secondary_language"], "en-US")
        self.assertEqual(selection["additional_languages"], ["de-DE"])

        with self.assertRaises(LanguagePolicyDenied):
            validate_language_selection("en-US", "en-US")

        with self.assertRaises(LanguagePolicyDenied):
            validate_language_selection("", "en-US")

    def test_hungarian_support_is_conditional(self) -> None:
        self.assertTrue(requires_hungarian_support(validate_language_selection("hu-HU", "en-US")))
        self.assertTrue(requires_hungarian_support(validate_language_selection("de-DE", "hu-HU")))
        self.assertFalse(requires_hungarian_support(validate_language_selection("en-US", "de-DE")))

    def test_language_status_semantics(self) -> None:
        for status in ("NATIVE", "VALIDATED", "BRIDGED"):
            self.assertTrue(language_capability_is_operable(status))
        for status in ("UNVERIFIED", "UNSUPPORTED"):
            self.assertFalse(language_capability_is_operable(status))
        with self.assertRaises(LanguagePolicyDenied):
            language_capability_is_operable("MAGIC")


class TestLanguageGatewayConformance(unittest.TestCase):
    def test_repository_conformance(self) -> None:
        report = run_conformance(ROOT)
        self.assertEqual(report["result"], "PASS", report.get("findings"))
        self.assertFalse(report["current_host_production_claim"])
        self.assertEqual(report["current_host_status"], "PENDING_CURRENT_HOST")

    def test_invalid_locale_fails_closed(self) -> None:
        with self.assertRaises(LanguagePolicyDenied):
            validate_language_selection("not a locale", "en-US")


if __name__ == "__main__":
    unittest.main()
