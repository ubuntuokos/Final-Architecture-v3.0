# FA3 Current Host Change & Delta Authority

## Purpose

The Current Host no longer needs a full new base release for every application runtime change.

The model is:

```text
immutable admitted Current Host base
  + admitted delta 001
  + admitted delta 002
  + ...
  = effective Current Host
```

A delta is not a weaker Current Host. It is a scope-bound physical requalification package.

## Admission classes

| Request | Result |
|---|---|
| no runtime effect | `NO_RUNTIME_IMPACT` |
| local runtime change | `CAPABILITY_DELTA_REQUALIFICATION` |
| shared/consumer impact | `IMPACT_REQUALIFICATION` |
| capability/proof/current-host/global authority change | `FULL_REQUALIFICATION` |

Every runtime delta automatically includes CAP-175 Software Coexistence & Host Non-Interference. Hardware Safety Envelope, License & Rights, Software Coexistence and structural-impact gates remain mandatory.

For shared-component changes, the request names the changed shared component IDs. The planner derives their capability scope and consuming applications from the canonical FA3 application/shared Capability Map bindings. A manually supplied smaller list cannot override that derived scope; unknown or unresolved shared bindings fail closed.

## Evidence rule

Unchanged base evidence is never copied to the new source commit.

Instead:

- the admitted base is immutable and retains its own physical proof;
- the change request is bound to a SHA-256 `change_digest`;
- the delta is bound to the current `parent_effective_digest`;
- each affected capability requires fresh physical positive, negative and rollback proof;
- hosted CI may validate schemas/planning but cannot create a physical PASS;
- global promotion is separate and is never implied by delta admission.

This keeps exact evidence provenance while avoiding a 175 × 3 replay when only a narrow runtime surface changed.

## CLI

Plan:

```bash
bash bin/fa3-current-host-delta plan \
  --request /path/to/change-request.json \
  --output reports/current-host-delta-plan.json
```

Verify a physical receipt produced on the Current Host:

```bash
bash bin/fa3-current-host-delta verify \
  --plan reports/current-host-delta-plan.json \
  --receipt evidence/receipts/current-host-delta.json \
  --output reports/current-host-delta-gate.json
```

Compose an effective host only after the full base has status `CURRENT_HOST_BASE_ADMITTED`:

```bash
bash bin/fa3-current-host-delta compose \
  --base evidence/receipts/current-host-base-state.json \
  --delta reports/current-host-delta-gate.json \
  --output reports/effective-current-host.json
```

Multiple `--delta` arguments are applied in order. Each delta must reference the immediately preceding effective-host digest.

## Current transition state

The active #559 175/525 reconciliation still requires its first fresh full physical Current Host closure. The delta channel is intentionally fail-closed until that base is admitted. After that initial closure, ordinary application-local changes can use the delta path instead of waiting for another complete base release.
