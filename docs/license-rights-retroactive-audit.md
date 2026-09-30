# FA3 retroactive License & Rights audit

The retroactive audit reviews pre-existing FA3 repository material under the
canonical License & Rights Authority.

## Critical distinction

A successful inventory/gate run means the **audit machinery works**. It does
not mean that every historical file, donor, dependency, model, dataset, asset,
font, SDK, codec, provider or service has been legally cleared.

Until the canonical audit status reaches `PASS` with evidence-backed closure:

- `release_eligible = false`;
- global rights promotion remains forbidden;
- UNKNOWN required rights facts fail closed;
- third-party material remains under its original terms;
- historical evidence remains append-only.

## Phase 1 inventory

The inventory deterministically scans the tracked repository release surface
and creates a work queue for:

- release-included distribution subjects;
- source code and documentation provenance/tagging;
- dependencies and provider/service records;
- donor/reference material;
- models and model weights;
- datasets/data;
- fonts and creative media;
- SDKs and codecs.

REUSE/SPDX markers and embedded metadata are **evidence signals**, not automatic
legal clearance.

## Closure

The audit may be changed to `PASS` only after all requirements in
`canonical/license-rights-audit-plan.json` are satisfied and the final
ReleaseLicenseComplianceReceipt passes the existing License & Rights Authority.
