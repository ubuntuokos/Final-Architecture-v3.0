# FA3 release-scoped capability baseline and host-scoped evidence

This materialization introduces two zero-delta canonical governance policies:

- `FA3-RELEASE-CAPABILITY-BASELINE-001`
- `FA3-EVIDENCE-SCOPE-001`

They do not add capabilities, authorities, providers, runtime receipts or promotion paths.

## Release-scoped capability baseline

The current FA3 release `2026-08-23/v3.0.11` retains exactly **143 canonical capabilities**. The important change is semantic: 143 is the declared baseline for this release, not a timeless global constant.

A future release must explicitly declare its own capability baseline. A capability-count change requires registry reconciliation, Evidence Registry reconciliation, unified release-projection reconciliation and a full permanent-enforcement PASS. Provider additions, projections or repository file growth do not imply a capability-count change.

The existing `canonical/enforcement-policy.json` count remains valid as a current-release mirror while it equals the active release baseline. A mismatch fails closed.

## Evidence scope

Evidence is evaluated against distinct observations rather than treating every canonical capability as if it were active on every host:

- `CANONICAL_SUPPORTED` — architecture support only; no host-runtime claim.
- `HOST_AVAILABLE` — discoverable/compatible on the host; not necessarily enabled.
- `HOST_ENABLED` — configured or enabled; positive current-host evidence is required.
- `HOST_ACTIVE` — executing or serving; positive current-host evidence is required.
- `PRODUCTION_PROMOTED` — admitted by the existing Acceptance and Promotion authorities; positive current-host evidence is mandatory.

These observations are not a linear shortcut. In particular, canonical support does not imply host availability, availability does not imply enablement, and activity does not imply production promotion.

## Disabled optional components

An optional or conditional component that is explicitly disabled may satisfy host disposition with `NEGATIVE_HOST_ASSURANCE` rather than fabricated positive runtime evidence. Negative assurance must prove at least:

- no unexpected process;
- no unexpected listening port;
- no unexpected accelerator/resource lease;
- no unexpected network egress;
- no unexpected authority claim;
- no unexpected secret use.

This path is non-blocking only when the component is genuinely optional/conditional, explicitly disabled, not active and not a production-promotion target. Unknown or partial disposition remains blocking/pending.

Negative assurance can never prove positive runtime conformance and can never promote production.

## Mandatory and active components

Positive current-host evidence remains mandatory for:

- mandatory/required capabilities whose activation policy is always-on or gate-critical;
- any component enabled on the host;
- any component active on the host;
- every production-promotion target.

The existing Evidence Registry, current-host runner, Acceptance Gate and Promotion Guard remain authoritative. Reference CI and documentation cannot substitute for current-host evidence.

## Relationship to governance tiering

`FA3-GOVERNANCE-TIERING-001` remains a read-only lifecycle projection. The release baseline and evidence-scope policies preserve:

- `authority_delta: 0`
- `capability_delta: 0`
- the v3.0.11 baseline of 143 capabilities
- `CANONICAL_CLOSED + PENDING_CURRENT_HOST` as a valid composition
- fail-closed production promotion

## Enforcement

`src/fa3_release_evidence_scope_gate.py` validates the two policies against the current enforcement policy, unified release projection, Evidence Registry, governance-tiering projection, current-host workflow and Promotion/Acceptance implementation.

The gate deliberately does not generate current-host PASS evidence. It validates scope and authority boundaries only.
