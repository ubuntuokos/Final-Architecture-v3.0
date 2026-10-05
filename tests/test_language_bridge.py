from __future__ import annotations

import unittest

from fa3_language_bridge import (
    LanguageBridgeDenied,
    MediationRequest,
    ProviderDescriptor,
    mediate_text,
    run_reference_conformance,
)


class LanguageBridgeTests(unittest.TestCase):
    def test_reference_conformance_passes_without_quality_claim(self):
        report = run_reference_conformance()
        self.assertEqual(report["result"], "PASS", report)
        self.assertFalse(report["translation_quality_claim"])
        self.assertFalse(report["current_host_production_claim"])

    def test_secret_external_route_is_denied(self):
        provider = ProviderDescriptor(
            "TEST-EXTERNAL", "EXTERNAL", ("hu-HU",), external_policy_allowed=True
        )
        request = MediationRequest("secret", "en-US", "hu-HU", "SECRET")
        with self.assertRaises(LanguageBridgeDenied):
            mediate_text(request, provider, lambda text, _src, _dst: text)

    def test_critical_mediation_requires_semantic_validator(self):
        provider = ProviderDescriptor("TEST-LOCAL", "LOCAL", ("hu-HU",))
        request = MediationRequest("critical", "en-US", "hu-HU", "INTERNAL", critical=True)
        with self.assertRaises(LanguageBridgeDenied):
            mediate_text(request, provider, lambda text, _src, _dst: "HU: " + text)


if __name__ == "__main__":
    unittest.main()
