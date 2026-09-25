# FA3-CAPABILITY-COUNT-DEHARDCODE-001

## Purpose

Remove the current release capability cardinality from executable hardcoded constants while preserving historical release semantics across explicit capability-model changes.

The authoritative executable source for the active release and its capability count is:

`canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json`

The active `2026-09-26/v3.1.0` release resolves to **175** capabilities. The earlier de-hardcode migration remains a historical `143`-capability, `capability_delta: 0` decision; the later capability-model migration is declared separately with `capability_delta: 32` and `authority_delta: 0`.

## Rules

- Active enforcement, release-projection and governance gates load the active release baseline through `src/fa3_release_baseline.py`.
- Missing, ambiguous or internally inconsistent baseline data fails closed.
- `canonical/enforcement-policy.json`, the Evidence Registry, and the release projection may retain the current release count as validated mirrors, but executable code must not treat that mirror value as a timeless constant.
- Historical release records and capability identifiers such as `CAP-143` remain valid historical/current-release data.
- A future capability-count change requires an explicit new/updated release baseline plus registry, Evidence Registry, release projection and permanent-enforcement reconciliation.
- Provider/file additions do not imply a capability-count change.

## Anti-regression

`FA3-CAPABILITY-COUNT-DEHARDCODE-GATESET-001` scans active Python execution surfaces and blocks reintroduction of constructs such as:

- `CAPS = 143` / `CAPS = 175`
- `CAPABILITY_COUNT = 143` / `CAPABILITY_COUNT = 175`
- `EXPECTED_CAPABILITY_COUNT = 143` / `EXPECTED_CAPABILITY_COUNT = 175`
- `CURRENT_RELEASE_COUNT = 143` / `CURRENT_RELEASE_COUNT = 175`
- `range(1, 144)` / `range(1, 176)` when used as a global capability-cardinality boundary

The gate also verifies the enforcement-policy, Evidence Registry, governance projection and release projection mirrors against the active release baseline.

## Non-goals

The de-hardcode migration itself does not create a capability. The later `FA3-DEC-CAPABILITY-MODEL-175-2026-09-26` migration explicitly adds 32 capabilities. It does not create runtime evidence or relax Acceptance/Promotion/current-host requirements.
