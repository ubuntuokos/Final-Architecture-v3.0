# Browser source discovery donor intake — 2026-10-02

**Authority:** owner-explicit `donornak` registration only.

This intake adds exactly six owner-marked GitHub URLs to `FA3-DONOR-REFERENCE-REGISTRY-001` as metadata-only reference/discovery identities:

- https://github.com/mozilla
- https://github.com/topics/firefox-based
- https://github.com/googlechrome
- https://github.com/operasoftware
- https://github.com/topics/opera?o=asc&s=stars
- https://github.com/topics/opera?l=c%2B%2B&o=asc&s=forks

## Classification

The three organization URLs are `GITHUB_ORGANIZATION` discovery indexes. The Firefox/Opera URLs are `GITHUB_TOPIC` discovery indexes. The two filtered Opera URLs remain distinct source identities because the canonical registry preserves owner-marked filtered topic views as separate discovery viewpoints.

This registration does **not** recursively register any repository listed by those pages and does not admit Mozilla, Firefox, Chromium/Chrome, Opera, WebDriver, extension, developer-tooling or other runtimes into FA3.

## Mandatory boundary for child repositories

Any repository later selected from one of these indexes requires its own donor/reuse assessment and, before material use, license/provenance and rights review, security review, Software Coexistence & Host Non-Interference, Hardware Safety Envelope review, shared-capability/layer placement review and an actual donor usage edge where adopted.

No organization-level or topic-level license assertion is made. Collection indexes use `NOT_APPLICABLE / COLLECTION_INDEX`; source copy stays blocked until the selected repository is reviewed.

## Invariants

- canonical capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- provider count: dynamic; no provider is admitted here
- no automatic fetch/install/activation/dependency/code import
- no model/provider selection
- no Current Host PASS or runtime-promotion claim
- no child-repository auto-registration

## Registry effect

This batch extends the serialized donor-maintenance PR #601 registry snapshot from **1310 to 1316** entries. It is intentionally capture-only; browser capability analysis and any FA3-native materialization are separate approval-gated work.
