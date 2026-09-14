#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

PROFILE_ID = "FA3-MARKETING-001"
VOICE_PROFILE_ID = "FA3-VOICE-001"
SECURITY_GATE_ID = "FA3-MARKETING-SECURITY-GATESET-001"
MAX_POLICY_STATE_AGE_SECONDS = 300


class MarketingSecurityDenied(PermissionError):
    pass


_ENGLISH_LEAKAGE = re.compile(
    r"\b(the|and|sale|discount|christmas|buy now|limited time|shop now)\b",
    re.IGNORECASE,
)
_SECRET_LEAKAGE = re.compile(
    r"(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:api[_-]?key|password|secret|token)\s*[:=]\s*\S+|\bsk-[A-Za-z0-9_-]{16,})",
    re.IGNORECASE,
)


def _parse_utc(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise MarketingSecurityDenied("FAIL-CLOSED: Hibás időbélyeg a policy-bizonyítékban") from exc
    if dt.tzinfo is None:
        raise MarketingSecurityDenied("FAIL-CLOSED: Az időbélyegnek időzónát kell tartalmaznia")
    return dt.astimezone(timezone.utc)


def _fresh(value: str, now: datetime, max_age_seconds: int = MAX_POLICY_STATE_AGE_SECONDS) -> bool:
    try:
        checked = _parse_utc(value)
    except MarketingSecurityDenied:
        return False
    age = (now - checked).total_seconds()
    return 0 <= age <= max_age_seconds


def require_hungarian_locale(context: dict[str, Any]) -> None:
    if context.get("target_locale") != "hu-HU":
        raise MarketingSecurityDenied(
            "FAIL-CLOSED: Az FA3-MARKETING-001 kizárólag hu-HU cél-lokációt fogad el ezen a natív magyar útvonalon"
        )


def validate_marketing_content_safety(text: str) -> None:
    candidate = str(text or "")
    if _SECRET_LEAKAGE.search(candidate):
        raise MarketingSecurityDenied("FAIL-CLOSED: Titok vagy hitelesítési adat szivárgása észlelve")


def validate_native_hungarian_copy(text: str, *, allow_terms: tuple[str, ...] = ()) -> None:
    candidate = str(text or "").strip()
    if len(candidate) < 12:
        raise MarketingSecurityDenied("FAIL-CLOSED: A generált magyar szöveg üres vagy túl rövid")
    validate_marketing_content_safety(candidate)
    scrubbed = candidate
    for term in allow_terms:
        if term:
            scrubbed = re.sub(re.escape(term), " ", scrubbed, flags=re.IGNORECASE)
    if _ENGLISH_LEAKAGE.search(scrubbed):
        raise MarketingSecurityDenied("FAIL-CLOSED: Angol nyelvi maradványok észlelve")
    if not any(ch in candidate for ch in "áéíóöőúüűÁÉÍÓÖŐÚÜŰ"):
        raise MarketingSecurityDenied("FAIL-CLOSED: A natív magyar nyelvi minimum nem igazolható")


def consent_allows(
    consent: dict[str, Any] | None,
    *,
    purpose: str,
    channel: str,
    tenant_id: str,
    now: datetime | None = None,
) -> bool:
    if not isinstance(consent, dict):
        return False
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if consent.get("backend_available") is not True:
        return False
    if consent.get("status") != "GRANTED" or consent.get("revoked") is True:
        return False
    if consent.get("revocation_status") != "CLEAR":
        return False
    if not _fresh(str(consent.get("revocation_checked_at", "")), current):
        return False
    if consent.get("subject_authorized") is not True:
        return False
    if consent.get("tenant_id") != tenant_id:
        return False
    if purpose not in set(consent.get("purposes") or []):
        return False
    if channel not in set(consent.get("channels") or []):
        return False
    if not consent.get("provenance_ref") or not consent.get("revocation_ref"):
        return False
    try:
        issued_at = _parse_utc(str(consent["issued_at"]))
        expires_at = _parse_utc(str(consent["expires_at"]))
    except (KeyError, MarketingSecurityDenied):
        return False
    return issued_at <= current < expires_at


def voice_cloning_consent_allows(
    consent: dict[str, Any] | None,
    *,
    purpose: str,
    tenant_id: str,
    now: datetime | None = None,
) -> bool:
    if not isinstance(consent, dict):
        return False
    scopes = set(consent.get("scopes") or [])
    if not {"VOICE_SYNTHESIS", "VOICE_CLONING"}.issubset(scopes):
        return False
    return consent_allows(
        consent,
        purpose=purpose,
        channel="voice",
        tenant_id=tenant_id,
        now=now,
    )


def suppression_allows(
    suppression: dict[str, Any] | None,
    *,
    channel: str,
    campaign_id: str,
    recipient_id: str,
    now: datetime | None = None,
) -> bool:
    if not isinstance(suppression, dict):
        return False
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if suppression.get("backend_available") is not True:
        return False
    if not _fresh(str(suppression.get("checked_at", "")), current):
        return False
    if suppression.get("global") is True or suppression.get("unsubscribed") is True:
        return False
    if channel in set(suppression.get("channels") or []):
        return False
    if campaign_id in set(suppression.get("campaign_ids") or []):
        return False
    if recipient_id in set(suppression.get("recipient_ids") or []):
        return False
    return True


def delivery_allowed(
    *,
    consent: dict[str, Any] | None,
    suppression: dict[str, Any] | None,
    purpose: str,
    channel: str,
    campaign_id: str,
    recipient_id: str,
    tenant_id: str,
    recipient_resolved: bool,
    via_central_mcp: bool,
    human_approved: bool,
    now: datetime | None = None,
) -> bool:
    return (
        recipient_resolved
        and via_central_mcp
        and human_approved
        and consent_allows(
            consent,
            purpose=purpose,
            channel=channel,
            tenant_id=tenant_id,
            now=now,
        )
        and suppression_allows(
            suppression,
            channel=channel,
            campaign_id=campaign_id,
            recipient_id=recipient_id,
            now=now,
        )
    )


@dataclass(frozen=True)
class VoiceRouteDecision:
    status: str
    selected_mode: str | None
    selected_provider_role: str | None
    uses_speaker_reference: bool
    degraded: bool
    reason: str


def decide_voice_route(
    *,
    requested_mode: str,
    cloning_consent_valid: bool,
    cloning_provider_available: bool,
    generic_hu_tts_available: bool,
    degraded_fallback_allowed: bool,
) -> VoiceRouteDecision:
    if requested_mode != "voice_clone":
        if generic_hu_tts_available:
            return VoiceRouteDecision("ALLOW", "plain", "GENERIC_HU_TTS", False, False, "PLAIN_TTS")
        return VoiceRouteDecision("DENY", None, None, False, False, "NO_TTS_ROUTE")

    # Consent failure is a terminal policy denial, never a provider-fallback condition.
    if not cloning_consent_valid:
        return VoiceRouteDecision("DENY", None, None, False, False, "CLONING_CONSENT_INVALID_OR_REVOKED")

    if cloning_provider_available:
        return VoiceRouteDecision("ALLOW", "voice_clone", "ADMITTED_CLONING_PROVIDER", True, False, "CLONING_ROUTE_AVAILABLE")

    # Degraded fallback changes the requested operation from cloning to generic TTS.
    # It MUST NOT consume the speaker reference or speaker embedding.
    if generic_hu_tts_available and degraded_fallback_allowed:
        return VoiceRouteDecision(
            "ALLOW",
            "plain",
            "GENERIC_HU_TTS",
            False,
            True,
            "CLONING_UNAVAILABLE_GENERIC_TTS_DEGRADED_FALLBACK",
        )

    return VoiceRouteDecision("DENY", None, None, False, False, "NO_CONFORMANT_VOICE_ROUTE")


def run_security_regressions() -> dict[str, Any]:
    now = datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc)
    good_consent = {
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
    good_suppression = {
        "backend_available": True,
        "checked_at": "2026-09-14T05:59:00Z",
        "global": False,
        "unsubscribed": False,
        "channels": [],
        "campaign_ids": [],
        "recipient_ids": [],
    }

    cases: list[tuple[str, bool]] = []
    ca = lambda c: consent_allows(c, purpose="MARKETING_CAMPAIGN", channel="email", tenant_id="tenant-a", now=now)
    cases.append(("MKTSEC-001", ca(good_consent)))
    cases.append(("MKTSEC-002", not ca(dict(good_consent, revoked=True))))
    cases.append(("MKTSEC-003", not ca(dict(good_consent, status="REVOKED"))))
    cases.append(("MKTSEC-004", not ca(dict(good_consent, expires_at="2026-01-01T00:00:00Z"))))
    cases.append(("MKTSEC-005", not ca(dict(good_consent, purposes=["SERVICE"]))))
    cases.append(("MKTSEC-006", not ca(dict(good_consent, channels=["voice"]))))
    cases.append(("MKTSEC-007", not ca(dict(good_consent, backend_available=False))))
    cases.append(("MKTSEC-008", not ca(dict(good_consent, subject_authorized=False))))
    cases.append(("MKTSEC-009", not ca(dict(good_consent, tenant_id="tenant-b"))))
    cases.append(("MKTSEC-010", not ca(dict(good_consent, revocation_checked_at="2026-09-14T05:00:00Z"))))
    cases.append(("MKTSEC-011", not ca(dict(good_consent, expires_at="not-a-time"))))

    sa = lambda s: suppression_allows(s, channel="email", campaign_id="c1", recipient_id="r1", now=now)
    cases.append(("MKTSEC-012", sa(good_suppression)))
    cases.append(("MKTSEC-013", not sa({**good_suppression, "global": True})))
    cases.append(("MKTSEC-014", not sa(dict(good_suppression, unsubscribed=True))))
    cases.append(("MKTSEC-015", not sa(dict(good_suppression, channels=["email"]))))
    cases.append(("MKTSEC-016", not sa(dict(good_suppression, campaign_ids=["c1"]))))
    cases.append(("MKTSEC-017", not sa(dict(good_suppression, recipient_ids=["r1"]))))
    cases.append(("MKTSEC-018", not sa(dict(good_suppression, backend_available=False))))
    cases.append(("MKTSEC-019", not sa(dict(good_suppression, checked_at="2026-09-14T05:00:00Z"))))

    delivery_args = dict(
        consent=good_consent,
        suppression=good_suppression,
        purpose="MARKETING_CAMPAIGN",
        channel="email",
        campaign_id="c1",
        recipient_id="r1",
        tenant_id="tenant-a",
        recipient_resolved=True,
        via_central_mcp=True,
        human_approved=True,
        now=now,
    )
    cases.append(("MKTSEC-020", delivery_allowed(**delivery_args)))
    cases.append(("MKTSEC-021", not delivery_allowed(**{**delivery_args, "human_approved": False})))

    cases.append(("MKTSEC-022", voice_cloning_consent_allows(good_consent, purpose="MARKETING_CAMPAIGN", tenant_id="tenant-a", now=now)))
    cases.append(("MKTSEC-023", not voice_cloning_consent_allows(dict(good_consent, revoked=True), purpose="MARKETING_CAMPAIGN", tenant_id="tenant-a", now=now)))

    denied = decide_voice_route(requested_mode="voice_clone", cloning_consent_valid=False, cloning_provider_available=False, generic_hu_tts_available=True, degraded_fallback_allowed=True)
    cases.append(("MKTSEC-024", denied.status == "DENY" and denied.selected_mode is None and not denied.uses_speaker_reference))
    degraded = decide_voice_route(requested_mode="voice_clone", cloning_consent_valid=True, cloning_provider_available=False, generic_hu_tts_available=True, degraded_fallback_allowed=True)
    cases.append(("MKTSEC-025", degraded.status == "ALLOW" and degraded.selected_mode == "plain" and degraded.uses_speaker_reference is False and degraded.degraded is True))

    def rejects_copy(text: str) -> bool:
        try:
            validate_native_hungarian_copy(text)
        except MarketingSecurityDenied:
            return True
        return False

    cases.append(("MKTSEC-026", rejects_copy("Vásároljon most, mert the christmas sale is here and minden termék akciós!")))
    cases.append(("MKTSEC-027", rejects_copy("Biztonságos magyar szöveg, api_key=SUPERSECRET0123456789 értékkel.")))
    cases.append(("MKTSEC-028", not rejects_copy("Fedezze fel új magyar ajánlatainkat, és válassza az Önnek megfelelő lehetőséget.")))

    result_cases = [{"case_id": cid, "status": "PASS" if ok else "FAIL"} for cid, ok in cases]
    return {
        "schema": "fa3.marketing-security-regression-report.v1",
        "gate_id": SECURITY_GATE_ID,
        "result": "PASS" if all(ok for _, ok in cases) else "FAIL",
        "total": len(cases),
        "passed": sum(1 for _, ok in cases if ok),
        "cases": result_cases,
        "current_host_runtime_claim": False,
    }
