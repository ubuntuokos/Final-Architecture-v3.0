# FA3 Native Anti-Slop Quality Fabric

## Decision

FA3 materializes the useful anti-slop methodology as the native canonical profile `FA3-QUALITY-ANTI-SLOP-001`. The upstream `miqdadbadjuber/anti-slop` project is provenance and design-method inspiration only; FA3 does not install its runtime, installer, plugins or agent-entry-file mutation mechanism.

The implementation introduces **no new capability and no new architectural authority**. The canonical capability count remains 143.

## Precedence

Quality filtering is not a design system:

1. canonical FA3 policy;
2. application-specific design contract;
3. FA3 native quality filter;
4. agent suggestion.

The filter may reject unsupported, fabricated, inaccessible or mechanically generated patterns. It may not invent brand direction, providers, models, tools, capabilities or execution authority.

## Rule model

The canonical registry is `canonical/quality/FA3-QUALITY-RULE-REGISTRY-001.json`.

- **HARD_GATE** — blocking and never waivable by a local justification.
- **PURPOSE_GATE** — blocking unless the artifact contains an explicit task-scoped reason using the canonical justification contract.
- **QUALITY_LOCK** — non-blocking consistency warning unless another canonical policy makes the issue blocking.

The initial native registry contains 29 rules spanning CORE, UI, COPY, HUMAN, RESPONSIVE, CODE and FA3-specific integrity concerns.

## Agent Native and Skill Fabric

Specialized concerns are represented by five FA3-native declarative skills:

- `fa3-quality-ui`
- `fa3-quality-copy`
- `fa3-quality-human`
- `fa3-quality-responsive`
- `fa3-quality-code`

They are admitted as `FA3_NATIVE`, task-scoped and authority-free. Task-class eligibility is deterministic before any Decision Fabric involvement. Decision Fabric may select only within the already eligible quality-skill candidate set and may not expand it.

## Enforcement

`src/fa3_quality_filter.py` performs the deterministic analysis. `src/fa3_quality_gate.py` validates canonical records, skill bindings, authority invariants, workflows and rule behavior.

Enforcement surfaces:

- standalone workflow: `FA3 Native Anti-Slop Quality Gate`;
- permanent enforcement: `./bin/fa3-enforce quality-anti-slop`;
- `static`, `all` and `promote` preflight through `bin/fa3-enforce`;
- GUI reconciliation: changed Control Center QML artifacts pass the native quality scan.

Existing untouched legacy artifacts are not mass-rewritten. New and changed in-scope artifacts are evaluated. This avoids a cosmetic repository-wide migration while making the rule mandatory for ongoing work.

## Upstream provenance

Observed on 2026-09-23:

- repository: `miqdadbadjuber/anti-slop`;
- observed package version: 3.2.15;
- immutable upstream commit: `0e384b7bff3301c8ec56dea300330772fed28e6a`;
- license: MIT;
- upstream code copied into the FA3 native implementation: none;
- required upstream runtime dependency: none.

The upstream installer and automatic agent-entry-file mutation paths are explicitly excluded from FA3.
