from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_marketing_security import (
    MarketingSecurityDenied,
    consent_allows,
    decide_voice_route,
    delivery_allowed,
    require_hungarian_locale,
    run_security_regressions,
    suppression_allows,
    validate_native_hungarian_copy,
    voice_cloning_consent_allows,
)


class MarketingSecurityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc)
        self.consent = {
            "backend_available": True,
            "status": "GRANTED",
            "revoked": False,
            "revocation_status": "CLEAR",
            "revocation_checked_at": "2026-09-14T05:59:00Z",
            "subject_authorized": True,
            "tenant_id": "tenant-a",
            "purposes": ["MARKETING_CAMPAIGN"],
            "channels": ["email", "voice"],
            "scopes": ["VOICE_SYNTHESIS", "VOICE_CLONING"],
            "provenance_ref": "consent-ledger:123",
            "revocation_ref": "consent-ledger:123/revocation",
            "issued_at": "2026-01-01T00:00:00Z",
            "expires_at": "2027-01-01T00:00:00Z",
        }
        self.suppression = {
            "backend_available": True,
            "checked_at": "2026-09-14T05:59:00Z",
            "global": False,
            "unsubscribed": False,
            "channels": [],
            "campaign_ids": [],
            "recipient_ids": [],
        }

    def test_non_hungarian_locale_is_fail_closed(self):
        with self.assertRaises(MarketingSecurityDenied):
            require_hungarian_locale({"target_locale": "en-US"})

    def test_english_leakage_is_rejected(self):
        with self.assertRaises(MarketingSecurityDenied):
            validate_native_hungarian_copy("Vásároljon most, mert the christmas sale is here and minden termék akciós!")

    def test_secret_leakage_is_rejected(self):
        with self.assertRaises(MarketingSecurityDenied):
            validate_native_hungarian_copy("Biztonságos magyar üzenet, api_key=SUPERSECRET0123456789 értékkel.")

    def test_revoked_and_stale_consent_are_fail_closed(self):
        revoked = dict(self.consent, revoked=True)
        stale = dict(self.consent, revocation_checked_at="2026-09-14T05:00:00Z")
        self.assertFalse(consent_allows(revoked, purpose="MARKETING_CAMPAIGN", channel="email", tenant_id="tenant-a", now=self.now))
        self.assertFalse(consent_allows(stale, purpose="MARKETING_CAMPAIGN", channel="email", tenant_id="tenant-a", now=self.now))

    def test_tenant_mismatch_is_fail_closed(self):
        self.assertFalse(consent_allows(self.consent, purpose="MARKETING_CAMPAIGN", channel="email", tenant_id="tenant-b", now=self.now))

    def test_suppression_global_channel_campaign_recipient_are_denied(self):
        for update in (
            {"global": True},
            {"channels": ["email"]},
            {"campaign_ids": ["c1"]},
            {"recipient_ids": ["r1"]},
        ):
            with self.subTest(update=update):
                self.assertFalse(suppression_allows({**self.suppression, **update}, channel="email", campaign_id="c1", recipient_id="r1", now=self.now))

    def test_suppression_backend_outage_and_stale_snapshot_are_fail_closed(self):
        self.assertFalse(suppression_allows(dict(self.suppression, backend_available=False), channel="email", campaign_id="c1", recipient_id="r1", now=self.now))
        self.assertFalse(suppression_allows(dict(self.suppression, checked_at="2026-09-14T05:00:00Z"), channel="email", campaign_id="c1", recipient_id="r1", now=self.now))

    def test_positive_delivery_path(self):
        self.assertTrue(delivery_allowed(
            consent=self.consent,
            suppression=self.suppression,
            purpose="MARKETING_CAMPAIGN",
            channel="email",
            campaign_id="c1",
            recipient_id="r1",
            tenant_id="tenant-a",
            recipient_resolved=True,
            via_central_mcp=True,
            human_approved=True,
            now=self.now,
        ))

    def test_voice_consent_delegation_semantics(self):
        self.assertTrue(voice_cloning_consent_allows(self.consent, purpose="MARKETING_CAMPAIGN", tenant_id="tenant-a", now=self.now))
        self.assertFalse(voice_cloning_consent_allows(dict(self.consent, scopes=["VOICE_SYNTHESIS"]), purpose="MARKETING_CAMPAIGN", tenant_id="tenant-a", now=self.now))

    def test_revoked_cloning_consent_never_falls_back(self):
        decision = decide_voice_route(
            requested_mode="voice_clone",
            cloning_consent_valid=False,
            cloning_provider_available=False,
            generic_hu_tts_available=True,
            degraded_fallback_allowed=True,
        )
        self.assertEqual("DENY", decision.status)
        self.assertIsNone(decision.selected_mode)
        self.assertFalse(decision.uses_speaker_reference)

    def test_generic_piper_style_fallback_cannot_use_speaker_reference(self):
        decision = decide_voice_route(
            requested_mode="voice_clone",
            cloning_consent_valid=True,
            cloning_provider_available=False,
            generic_hu_tts_available=True,
            degraded_fallback_allowed=True,
        )
        self.assertEqual("ALLOW", decision.status)
        self.assertEqual("plain", decision.selected_mode)
        self.assertEqual("GENERIC_HU_TTS", decision.selected_provider_role)
        self.assertFalse(decision.uses_speaker_reference)
        self.assertTrue(decision.degraded)

    def test_full_negative_matrix_passes(self):
        report = run_security_regressions()
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(28, report["total"])
        self.assertEqual(28, report["passed"])
        self.assertFalse(report["current_host_runtime_claim"])


if __name__ == "__main__":
    unittest.main()
