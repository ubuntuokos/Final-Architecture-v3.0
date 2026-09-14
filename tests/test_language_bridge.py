from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_language_bridge import (
    LanguageBridgeDenied,
    MediationRequest,
    ProviderDescriptor,
    mediate_text,
    run_reference_conformance,
    select_provider,
)


class TestLanguageBridgeRuntime(unittest.TestCase):
    def setUp(self) -> None:
        self.local = ProviderDescriptor("LOCAL", "LOCAL", ("en-US", "hu-HU"))
        self.external = ProviderDescriptor(
            "EXTERNAL",
            "EXTERNAL",
            ("en-US", "hu-HU"),
            external_policy_allowed=True,
        )

    def test_reference_conformance_passes_without_production_claim(self) -> None:
        report = run_reference_conformance()
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["passed"], 7)
        self.assertFalse(report["translation_quality_claim"])
        self.assertFalse(report["current_host_production_claim"])

    def test_local_first_selection(self) -> None:
        request = MediationRequest("hello", "en-US", "hu-HU", "PUBLIC")
        self.assertEqual(select_provider(request, (self.external, self.local)).provider_id, "LOCAL")

    def test_secret_external_route_is_denied(self) -> None:
        request = MediationRequest("secret", "en-US", "hu-HU", "SECRET")
        with self.assertRaises(LanguageBridgeDenied):
            mediate_text(request, self.external, lambda text, _src, _dst: text)

    def test_protected_token_loss_is_denied(self) -> None:
        request = MediationRequest(
            "Call `FA3-AUTH-HOST-RESOURCE-BROKER-001` and keep ModelRegistry.",
            "en-US",
            "hu-HU",
            "INTERNAL",
            protected_terms=("ModelRegistry",),
        )
        with self.assertRaises(LanguageBridgeDenied):
            mediate_text(request, self.local, lambda text, _src, _dst: text.replace("⟦FA3P0000⟧", "removed"))

    def test_critical_route_requires_semantic_validator(self) -> None:
        request = MediationRequest("critical", "en-US", "hu-HU", "INTERNAL", critical=True)
        with self.assertRaises(LanguageBridgeDenied):
            mediate_text(request, self.local, lambda text, _src, _dst: "HU: " + text)

        result = mediate_text(
            request,
            self.local,
            lambda text, _src, _dst: "HU: " + text,
            lambda *_args: True,
        )
        self.assertEqual(result.receipt["semantic_validation"], "PASS")
        self.assertFalse(result.receipt["authority_expanded_by_mediation"])


if __name__ == "__main__":
    unittest.main()
