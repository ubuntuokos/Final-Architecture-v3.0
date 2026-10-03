# FA3 License & Rights Management

## Purpose

FA3 treats licensing as a release-safety property, not as a documentation-only
field. The License & Rights Authority is a P0, fail-closed specialization of
the existing Software Supply Chain / Security Governance layer.

It does **not** add a capability to the canonical capability model and does not
create a new top-level architectural authority. The canonical capability
baseline remains **175**.

## Repository license

FA3-original work is Apache-2.0 unless a narrower file/component marker says
otherwise. Third-party works are not relicensed by this repository.

Apache-2.0 permits commercial use of the covered open-core work. A separate
commercial agreement is relevant only to an explicitly separately licensed
module, service, support offering, provider entitlement or similar deliverable.

## Rights domains

The authority records separate decisions for:

- code and documentation;
- models and model weights;
- datasets and training/evaluation data;
- creative assets, media and fonts;
- SDKs and codecs;
- providers and external services;
- templates;
- generated-output usage rights.

A license on source code must not be treated as evidence for model, dataset,
asset, service or output rights.

## Canonical disposition

Every admitted subject receives one of:

- **ALLOW**
- **ALLOW_WITH_OBLIGATIONS**
- **REVIEW_REQUIRED**
- **REFERENCE_ONLY**
- **DENY**

UNKNOWN required facts fail closed.

## Donor relationship

A donor/reference registry entry is discovery evidence only. It never implies
that source code may be copied, that the donor may be bundled, or that a
runtime/provider is admitted. Reuse requires its own rights descriptor and
the applicable FA3 admission gates.

## Entitlements and secrets

Commercial license keys, service tokens and similar secrets are never stored
in canonical records or evidence. Canonical data carries only an opaque
entitlement reference resolved by the FA3 Secret Broker or another admitted
secret provider.

## Release rule

A releasable FA3 bundle requires a
`fa3.release-license-compliance-receipt.v1` PASS proving at least:

1. repository rights audit PASS;
2. SPDX SBOM generated;
3. CycloneDX SBOM generated;
4. third-party notices generated;
5. attribution obligations resolved;
6. source-offer obligations resolved;
7. entitlement obligations resolved;
8. zero unknown required license facts;
9. zero unresolved conflicts.

The current historical repository audit is deliberately recorded as
`PENDING_RETROACTIVE_AUDIT`. Therefore the new authority can be statically
materialized while release eligibility remains **false** until the audit is
completed. Historical evidence must not be overwritten during reconciliation.
\n## Universal Capability Access\n\nThe existing License & Rights Authority owns the P0 Universal Capability Access rule. Every current and future donor record is classified by the executable gate. Material reuse fails closed for unknown rights and for restricted donors without a global substitute. Upstream territorial or other restrictions must never be bypassed technically; FA3 preserves the user-facing capability through a globally usable donor path or an independent FA3-native implementation. See `docs/universal-capability-access.md`.\n