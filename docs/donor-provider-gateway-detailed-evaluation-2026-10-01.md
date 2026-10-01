# Provider/Gateway donor detailed evaluation — 2026-10-01

This closure evaluates the two ACCEPTED_REFERENCE records whose intake explicitly required later detailed review.

## ferdiunal/laravel-ai-router

Pinned upstream main: `5aa8e3f0a3f971522692049becb7c29f1bda27f3`.

FA3 reuses only architecture/operational patterns: constrained public HTTPS custom-provider definition validation; provider+label model visibility; secret-free provider health, rate-window and cooldown observations; request/token/latency/error analytics; bounded transport and SSE parsing. The FA3 implementation remains provider-neutral and is not a Laravel/PHP dependency.

Rejected from FA3 authority: random-provider/auto selection, internal autonomous failover, package-local credential persistence/encryption as secret authority, package SQLite as canonical FA3 state, and model/provider discovery as admission. Model Router remains exclusive route authority and Secret Broker remains credential authority.

Upstream declares MIT in `composer.json` and GitHub repository metadata. A root LICENSE file was not observed at the pinned revision, so no source-copy path is selected by this assessment.

## ai-resource-radar/ai-resource-radar

Pinned upstream main: `c3a27246801e5b5d8945d2cd4627aae75858c449`; observed package version `0.9.0`; MIT LICENSE file verified.

FA3 reuses deterministic allow-listed public-source collection, bounded fetches, ETag/Last-Modified caching, per-source failure isolation, official/community separation, freshness and evidence timestamps, parser-drift last-trusted-value handling, two-success removal confirmation, country availability, normalized price/quota metadata, and change detection.

The upstream A–D resource tier is not an FA3 admission or routing score. Community discovery cannot upgrade verification. No macOS service/Keychain dependency, dashboard runtime, AGENTS.md mutation path, provider activation, model activation, or routing authority is imported.

## Result

Both donors are **APPROVED_FOR_PATTERN_REUSE_ONLY**. Capability delta **0**; authority delta **0**; runtime dependency **false**; physical Current Host requalification **not required** for this static materialization. Actual future code copying or runtime adoption requires a separate exact-revision license/dependency/security/coexistence admission and, if runtime behavior changes, fresh physical Current Host evidence.
