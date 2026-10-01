#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import re
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SOURCE_ID = "FA3-SOURCE-API-MEGA-LIST-001"
SOURCE_REPOSITORY = "cporter202/API-mega-list"

TRACKING_KEYS = {
    "affiliate",
    "aff",
    "fpr",
    "ref",
    "referrer",
    "tag",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}
SECRET_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "credential",
    "credentials",
    "key",
    "password",
    "secret",
    "token",
}
_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\((https?://[^)\s]+)\)", re.IGNORECASE)
_HTML_TAG = re.compile(r"<[^>]+>")
_TOKEN = re.compile(r"[a-z0-9][a-z0-9._+-]{1,63}", re.IGNORECASE)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean_label(value: str) -> str:
    value = html.unescape(_HTML_TAG.sub("", value))
    value = value.replace("**", "").replace("__", "").replace("`", "")
    return " ".join(value.split()).strip()


def _normalized_netloc(scheme: str, host: str, port: int | None) -> str:
    if not port or (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        return host
    return f"{host}:{port}"


def sanitize_locator(url: str) -> dict[str, Any]:
    """Normalize identity while removing tracking and possible secret query values."""
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if scheme not in {"http", "https"} or not host:
        raise ValueError("only absolute http(s) locators are accepted")

    tracking_present = False
    secret_parameter_present = False
    retained: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lk = key.strip().lower()
        if lk in TRACKING_KEYS or lk.startswith("utm_"):
            tracking_present = True
            continue
        if lk in SECRET_KEYS or any(token in lk for token in ("token", "secret", "password", "credential", "api_key", "apikey")):
            secret_parameter_present = True
            continue
        retained.append((key, value))

    retained.sort(key=lambda pair: (pair[0].casefold(), pair[1]))
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    canonical = urlunsplit(
        (
            scheme,
            _normalized_netloc(scheme, host, parsed.port),
            path,
            urlencode(retained, doseq=True),
            "",
        )
    )
    return {
        "canonical_locator": canonical,
        "host": host,
        "affiliate_or_tracking_present": tracking_present,
        "secret_parameter_present": secret_parameter_present,
        "raw_locator_sha256": _sha256_text(url),
    }


def identity_hints(canonical_locator: str) -> tuple[str, str]:
    parsed = urlsplit(canonical_locator)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]

    if host in {"apify.com", "www.apify.com"}:
        provider = "apify"
        service = "apify:" + "/".join(parts[:2]) if parts else "apify:root"
        return provider, service
    if host in {"github.com", "www.github.com"}:
        provider = "github"
        service = "github:" + "/".join(parts[:2]) if parts else "github:root"
        return provider, service

    provider = host.removeprefix("www.")
    service_path = "/".join(parts[:3]) or "root"
    return provider, f"{provider}:{service_path}"


def category_from_source_path(source_path: str) -> str:
    path = PurePosixPath(source_path)
    if len(path.parts) >= 2:
        return path.parts[-2]
    return "root"


def _line_is_candidate_surface(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(("- ", "* ", "|"))


def parse_api_mega_list_markdown(text: str, *, source_path: str) -> list[dict[str, Any]]:
    """Extract untrusted candidate listings without persisting raw URLs or descriptions."""
    rows: list[dict[str, Any]] = []
    category = category_from_source_path(source_path)
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not _line_is_candidate_surface(line):
            continue
        for match in _LINK.finditer(line):
            label = _clean_label(match.group(1))
            if not label:
                continue
            raw_url = match.group(2)
            try:
                locator = sanitize_locator(raw_url)
            except (ValueError, UnicodeError):
                continue
            provider, service = identity_hints(locator["canonical_locator"])
            lower_line = line.casefold()
            sponsorship = any(token in lower_line for token in ("sponsor", "sponsored", "featured partner"))
            listing_digest = _sha256_text(
                f"{SOURCE_ID}\\0{source_path}\\0{line_number}\\0{label}\\0{locator['canonical_locator']}"
            )
            terms = sorted(
                {
                    token.casefold()
                    for token in _TOKEN.findall(f"{label} {category}")
                    if len(token) >= 3
                }
            )
            rows.append(
                {
                    "schema": "fa3.external-api-discovery-candidate-observation.v1",
                    "source_id": SOURCE_ID,
                    "source_repository": SOURCE_REPOSITORY,
                    "source_path": source_path,
                    "source_line": line_number,
                    "source_category": category,
                    "source_listing_digest": listing_digest,
                    "listing_name": label[:240],
                    "canonical_locator": locator["canonical_locator"],
                    "raw_locator_sha256": locator["raw_locator_sha256"],
                    "provider_identity": provider,
                    "service_identity": service,
                    "affiliate_or_tracking_present": locator["affiliate_or_tracking_present"],
                    "secret_parameter_present": locator["secret_parameter_present"],
                    "sponsorship_or_featured_present": sponsorship,
                    "ranking_signal_allowed": False,
                    "authorization_signal_allowed": False,
                    "discovery_terms": terms[:64],
                    "authority": False,
                    "runtime_provider": False,
                }
            )
    return rows
