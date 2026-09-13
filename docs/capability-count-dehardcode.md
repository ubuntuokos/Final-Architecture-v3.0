# FA3-CAPABILITY-COUNT-DEHARDCODE-001

## Purpose

Remove the current release capability cardinality from executable hardcoded constants without changing the v3.0.11 capability set.

The authoritative executable source for the active release and its capability count is:

`canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json`

For the current release this still resolves to **143** capabilities. The migration therefore has `capability_delta: 0` and `authority_delta: 0`.

## Rules

- Active enforcement, release-projection and governance gates load the active release baseline through `src/fa3_release_baseline.py`.
- Missing, ambiguous or internally inconsistent baseline data fails closed.
- `canonical/enforcement-policy.json`, the Evidence Registry, and the release projection may retain the current release count as validated mirrors, but executable code must not treat that mirror value as a timeless constant.
- Historical release records and capability identifiers such as `CAP-143` remain valid historical/current-release data.
- A future capability-count change requires an explicit new/updated release baseline plus registry, Evidence Registry, release projection and permanent-enforcement reconciliation.
- Provider/file additions do not imply a capability-count change.

## Anti-regression

`FA3-CAPABILITY-COUNT-DEHARDCODE-GATESET-001` scans active Python execution surfaces and blocks reintroduction of constructs such as:

- `CAPS = 143`
- `CAPABILITY_COUNT = 143`
- `EXPECTED_CAPABILITY_COUNT = 143`
- `CURRENT_RELEASE_COUNT = 143`
- `range(1, 144)` when used as the global capability-cardinality boundary

The gate also verifies the enforcement-policy, Evidence Registry, governance projection and release projection mirrors against the active release baseline.

## Non-goals

This migration does not create a capability, change the current 143-capability v3.0.11 baseline, create runtime evidence, or relax Acceptance/Promotion/current-host requirements.
