# FA3 Reuse Discovery

`FA3-REUSE-DISCOVERY-001` makes reuse discovery mandatory before a new FA3 application, provider, profile, derived implementation, GUI module, Agent Native component or material extension is implemented.

## Lifecycle

`ApplicationIntent -> deterministic discovery -> reuse assessment -> gap analysis -> authority collision -> coexistence -> Hardware Audit -> proposal -> normal FA3 admission -> implementation`

The reuse catalog is derived and rebuildable. Canonical records remain the source of truth. No reuse record, agent recommendation or Decision Fabric result grants capability, authority, permission, provider admission, resource access or runtime promotion.

## Deterministic first

The resolver searches existing capabilities, profiles, contracts, providers, actions, GUI projections, reusable patterns and references. License/distribution, authority collision, coexistence and hardware rules filter the set first. Decision Fabric may only rank the already eligible set and may not add a candidate.

## Reusable patterns

Patterns are not capabilities. They capture architecture that can be applied in multiple domains without growing the 143-capability baseline. Pattern metadata preserves provenance and does not imply source-code reuse.

## Third-party sources

External Project Radar and `FA3-JEV-CODE-REUSE-001` feed reference and provenance information into discovery. `REFERENCE_ONLY` and `PATTERN_SOURCE` never imply code copying or product-bundle inclusion. Unknown/problematic licenses forbid source copy.

## New-project adoption

Every post-adoption new profile or provider must have a `fa3.application-intent.v1` record and a PASS `fa3.reuse-assessment.v1` record covering the new canonical ID. The executable gate derives the adoption marker from the first commit containing the canonical reuse decision and checks later additions.

## Software coexistence

Every intent declares namespaced package/service/config/cache/runtime/socket/data/desktop identities and explicitly denies upstream uninstall, host-global environment mutation and default-port hijacking.

## Hardware Audit

Reuse discovery itself is CPU-only and vendor-neutral. Candidate projects must preserve the portable `FA3-HARDWARE-BASELINE-001`: CPU-only viability and 0..N accelerators. Provider-specific hardware requirements may narrow only the selected provider scope.

## CLI

```bash
./bin/fa3-reuse-assess --intent canonical/intents/FA3-EMBEDDING-FABRIC-APPLICATION-INTENT-001.json
./bin/fa3-enforce reuse-discovery
```

The committed Embedding Fabric intent/assessment is the golden design example. It deliberately remains `PLANNED_NOT_MATERIALIZED_BY_THIS_CHANGE`; reuse discovery does not fabricate implementation or runtime evidence.
