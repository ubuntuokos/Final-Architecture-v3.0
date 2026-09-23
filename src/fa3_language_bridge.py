#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

OPERABLE_STATUSES = {"NATIVE", "VALIDATED", "BRIDGED"}
DATA_CLASSES = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"}
LOCALITIES = {"LOCAL", "EXTERNAL"}
PROTECTED_TOKEN_PATTERN = re.compile(
    r"```[\s\S]*?```"
    r"|`[^`\n]+`"
    r"|https?://[^\s<>]+"
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|\b[a-fA-F0-9]{32,128}\b"
    r"|(?:^|(?<=\s))/(?:[^\s/]+/)*[^\s/]+",
    re.MULTILINE,
)
PLACEHOLDER_RE = re.compile(r"⟦FA3P\d{4}⟧")


class LanguageBridgeDenied(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    locality: str
    target_languages: tuple[str, ...]
    status: str = "VALIDATED"
    admitted: bool = True
    external_policy_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise LanguageBridgeDenied("provider_id is required")
        if self.locality not in LOCALITIES:
            raise LanguageBridgeDenied(f"unsupported provider locality: {self.locality}")
        if self.status not in OPERABLE_STATUSES | {"UNVERIFIED", "UNSUPPORTED"}:
            raise LanguageBridgeDenied(f"unknown provider language status: {self.status}")


@dataclass(frozen=True)
class MediationRequest:
    text: str
    source_language: str
    target_language: str
    data_classification: str
    critical: bool = False
    detection_confidence: float = 1.0
    terminology_revision: str = "none"
    protected_terms: tuple[str, ...] = field(default_factory=tuple)
    capability_scope: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.text:
            raise LanguageBridgeDenied("source text is required")
        if not self.source_language or not self.target_language:
            raise LanguageBridgeDenied("source and target languages are required")
        if self.data_classification not in DATA_CLASSES:
            raise LanguageBridgeDenied(f"unsupported data classification: {self.data_classification}")
        if not (0.0 <= self.detection_confidence <= 1.0):
            raise LanguageBridgeDenied("detection_confidence must be in [0,1]")


@dataclass(frozen=True)
class MediationResult:
    text: str
    receipt: dict[str, Any]


TranslateFn = Callable[[str, str, str], str]
ValidateFn = Callable[[str, str, str, str], bool]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _provider_can_route(request: MediationRequest, provider: ProviderDescriptor) -> bool:
    if not provider.admitted or provider.status not in OPERABLE_STATUSES:
        return False
    if request.target_language not in provider.target_languages and "*" not in provider.target_languages:
        return False
    if provider.locality == "EXTERNAL":
        if request.data_classification == "SECRET":
            return False
        if not provider.external_policy_allowed:
            return False
    return True


def select_provider(request: MediationRequest, providers: Iterable[ProviderDescriptor]) -> ProviderDescriptor:
    eligible = [provider for provider in providers if _provider_can_route(request, provider)]
    if not eligible:
        raise LanguageBridgeDenied("no admitted policy-equivalent language provider")
    eligible.sort(key=lambda item: (item.locality != "LOCAL", item.provider_id))
    return eligible[0]


def _collect_protected_spans(text: str, protected_terms: tuple[str, ...]) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = [(m.start(), m.end(), m.group(0)) for m in PROTECTED_TOKEN_PATTERN.finditer(text)]
    for term in sorted({term for term in protected_terms if term}, key=len, reverse=True):
        for match in re.finditer(re.escape(term), text):
            candidate = (match.start(), match.end(), match.group(0))
            if not any(not (candidate[1] <= start or candidate[0] >= end) for start, end, _ in spans):
                spans.append(candidate)
    spans.sort(key=lambda item: item[0])
    return spans


def protect_text(text: str, protected_terms: tuple[str, ...] = ()) -> tuple[str, dict[str, str]]:
    spans = _collect_protected_spans(text, protected_terms)
    if not spans:
        return text, {}
    output: list[str] = []
    mapping: dict[str, str] = {}
    cursor = 0
    for index, (start, end, original) in enumerate(spans):
        if start < cursor:
            continue
        placeholder = f"⟦FA3P{index:04d}⟧"
        output.append(text[cursor:start])
        output.append(placeholder)
        mapping[placeholder] = original
        cursor = end
    output.append(text[cursor:])
    return "".join(output), mapping


def restore_protected_text(translated: str, mapping: dict[str, str]) -> str:
    expected = set(mapping)
    observed = PLACEHOLDER_RE.findall(translated)
    if set(observed) != expected or len(observed) != len(expected):
        raise LanguageBridgeDenied("protected-token round-trip integrity failure")
    restored = translated
    for placeholder, original in mapping.items():
        restored = restored.replace(placeholder, original)
    if PLACEHOLDER_RE.search(restored):
        raise LanguageBridgeDenied("unresolved protected-token placeholder")
    return restored


def semantic_validation_required(request: MediationRequest, confidence_threshold: float = 0.85) -> bool:
    return request.critical or request.detection_confidence < confidence_threshold


def mediate_text(
    request: MediationRequest,
    provider: ProviderDescriptor,
    translate: TranslateFn,
    validate: ValidateFn | None = None,
) -> MediationResult:
    if not _provider_can_route(request, provider):
        raise LanguageBridgeDenied("provider is not admitted for this language/data-class route")
    if request.source_language == request.target_language:
        raise LanguageBridgeDenied("mediation route is unnecessary for identical source/target language")

    protected_text, mapping = protect_text(request.text, request.protected_terms)
    translated = translate(protected_text, request.source_language, request.target_language)
    if not isinstance(translated, str) or not translated:
        raise LanguageBridgeDenied("translation provider returned empty or invalid output")
    restored = restore_protected_text(translated, mapping)

    validation_required = semantic_validation_required(request)
    semantic_validation = "NOT_REQUIRED"
    if validation_required:
        if validate is None:
            raise LanguageBridgeDenied("semantic validator is required for critical/low-confidence mediation")
        if not validate(request.text, restored, request.source_language, request.target_language):
            raise LanguageBridgeDenied("semantic validation failed")
        semantic_validation = "PASS"

    receipt = {
        "schema": "fa3.language-bridge-mediation-receipt.v1",
        "bridge_id": "FA3-LANGUAGE-BRIDGE-001",
        "source_language": request.source_language,
        "target_language": request.target_language,
        "route": "LANGUAGE_MEDIATION",
        "provider_id": provider.provider_id,
        "provider_locality": provider.locality,
        "native_or_mediated": "MEDIATED",
        "input_sha256": sha256_text(request.text),
        "output_sha256": sha256_text(restored),
        "terminology_revision": request.terminology_revision,
        "protected_token_count": len(mapping),
        "protected_token_validation": "PASS",
        "semantic_validation": semantic_validation,
        "data_classification": request.data_classification,
        "capability_scope": list(request.capability_scope),
        "authority_expanded_by_mediation": False,
        "current_host_production_claim": False,
    }
    return MediationResult(text=restored, receipt=receipt)


def run_reference_conformance() -> dict[str, Any]:
    local = ProviderDescriptor("FA3-TEST-LOCAL", "LOCAL", ("en-US", "hu-HU"))
    external = ProviderDescriptor(
        "FA3-TEST-EXTERNAL",
        "EXTERNAL",
        ("en-US", "hu-HU"),
        external_policy_allowed=True,
    )
    cases: list[dict[str, str]] = []

    def record(case_id: str, passed: bool, detail: str) -> None:
        cases.append({"id": case_id, "result": "PASS" if passed else "FAIL", "detail": detail})

    base = MediationRequest(
        text="Use `FA3-AUTH-HOST-RESOURCE-BROKER-001` at https://example.invalid and keep ModelRegistry.",
        source_language="en-US",
        target_language="hu-HU",
        data_classification="INTERNAL",
        protected_terms=("ModelRegistry",),
        terminology_revision="terminology-v1",
        capability_scope=("read",),
    )
    record("LB-REF-001", select_provider(base, (external, local)).provider_id == local.provider_id, "local-first provider selection")

    translated = mediate_text(base, local, lambda text, _src, _dst: "HU: " + text)
    record("LB-REF-002", "`FA3-AUTH-HOST-RESOURCE-BROKER-001`" in translated.text and "ModelRegistry" in translated.text, "protected-token and terminology round-trip")
    record("LB-REF-003", translated.receipt.get("authority_expanded_by_mediation") is False and translated.receipt.get("protected_token_validation") == "PASS", "receipt preserves authority and token evidence")

    secret_denied = False
    try:
        secret = MediationRequest("secret", "en-US", "hu-HU", "SECRET")
        mediate_text(secret, external, lambda text, _src, _dst: text)
    except LanguageBridgeDenied:
        secret_denied = True
    record("LB-REF-004", secret_denied, "SECRET external route denied")

    mutation_denied = False
    try:
        mediate_text(base, local, lambda text, _src, _dst: text.replace("⟦FA3P0000⟧", "lost"))
    except LanguageBridgeDenied:
        mutation_denied = True
    record("LB-REF-005", mutation_denied, "protected-token mutation denied")

    validation_denied = False
    try:
        critical = MediationRequest("critical", "en-US", "hu-HU", "INTERNAL", critical=True)
        mediate_text(critical, local, lambda text, _src, _dst: "HU: " + text)
    except LanguageBridgeDenied:
        validation_denied = True
    record("LB-REF-006", validation_denied, "critical mediation without validator denied")

    critical = MediationRequest("critical", "en-US", "hu-HU", "INTERNAL", critical=True)
    validated = mediate_text(critical, local, lambda text, _src, _dst: "HU: " + text, lambda *_args: True)
    record("LB-REF-007", validated.receipt.get("semantic_validation") == "PASS", "critical mediation with validator passes")

    passed = sum(case["result"] == "PASS" for case in cases)
    return {
        "schema": "fa3.language-bridge-reference-conformance.v1",
        "bridge_id": "FA3-LANGUAGE-BRIDGE-001",
        "result": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "cases": cases,
        "reference_only": True,
        "translation_quality_claim": False,
        "current_host_production_claim": False,
    }
