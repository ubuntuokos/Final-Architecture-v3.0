# FA3 Supercool GitHub organization donor intake — 2026-10-03

## Owner marker

The owner explicitly marked the exact source `https://github.com/supercool` as **donornak** on 2026-10-03 and requested donor-list registration plus an FA3 usability plan.

## Source classification

- canonical source key: `github:supercool`
- donor id: `FA3-DONOR-SUPERCOOL-ORG-001`
- source kind: `GITHUB_ORGANIZATION`
- status: `ACCEPTED_REFERENCE`
- mode: metadata-only `DISCOVERY_INDEX`
- capability delta: **0**
- authority delta: **0**
- capability baseline: **175**
- runtime impact: **NO_RUNTIME_IMPACT**

The inspected organization currently exposes a mixed-provenance Craft CMS ecosystem containing Supercool-authored repositories and forks of external upstream projects. Organization-level admission therefore cannot be treated as code, dependency, license or ownership admission for any child repository.

## High-value FA3 discovery areas

The organization provides useful patterns for:

- scheduled jobs and application-level timed actions;
- XML/RSS/ATOM/CSV/JSON import and field mapping;
- remote multimedia/oEmbed ingestion;
- search/index synchronization;
- cache invalidation and warming;
- image transformation, optimization and watermarking;
- security scanner/control-panel interaction patterns;
- large relationship editors and nested data UX;
- dynamic forms and submission workflows;
- external entity/provider linking.

## Provenance boundary

Examples observed during analysis include forks whose upstreams are outside Supercool, including Verbb, Craft CMS/Pixel & Tonic, CraftPulse, PutYourLightsOn, Værsågod, Flipbox and others. Any child repository selected for material use must bind to its actual upstream and exact license independently.

The organization record therefore does **not** recursively register child repositories. It is a discovery index only.

## FA3 architecture disposition

Reusable workflow, data-model, admin-UX and adapter patterns should normally be re-expressed as FA3-native shared services rather than embedding a Craft/PHP/Yii runtime island.

Likely FA3 targets include Capture & Inbox, Source Manager, shared Import/Export, Temporal adapters, Search/Indexing Fabric, image/media transform services, Security Inspection/Control Center, File/Project/Asset/Contact managers, the Shared Plugin & Extension Fabric and business workflow applications.

## Admission boundaries

No code is copied and no package is installed. No provider, model, runtime, dependency, service or child repository is admitted. No usage edge is created by this intake.

Repository-level material adoption requires:

1. explicit repository eligibility under donor policy;
2. exact upstream provenance;
3. License & Rights clearance;
4. security review;
5. Software Coexistence review;
6. Hardware Safety/runtime review where applicable;
7. capability/layer placement and non-regression review;
8. canonical usage-edge registration;
9. Current Host requalification only if runtime behavior is actually affected.

The fixed FA3 capability baseline remains **175**.
