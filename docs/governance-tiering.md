# FA3 Governance Tiering Derived Projection

`FA3-GOVERNANCE-TIERING-001` is a **read-only derived projection**, not a new FA3 governance authority and not a new capability.

## Why this exists

FA3 already has authoritative mechanisms for canonical closure, Evidence Registry state, current-host conformance, the 19-point Acceptance Gate, and runtime promotion. Those mechanisms must remain the source of truth.

The missing usability layer was a single lifecycle view that can expose those existing states together while formalizing a lightweight assurance progression for implementation maturity.

The projection therefore has:

- `authority_delta: 0`
- `capability_delta: 0`
- canonical capability baseline before/after: `143`

It cannot promote runtime, canonicalize a component, mutate evidence, enable a provider, grant authority, override Acceptance, or create current-host receipts.

## Three orthogonal axes

### 1. Assurance

The projection owns only these non-authoritative implementation-maturity rings:

`LAB -> CANDIDATE -> STAGING`

- **LAB**: experimental/exploratory; conformance may be incomplete. No production or canonical claim follows from this ring.
- **CANDIDATE**: identity/provenance is resolved sufficiently for controlled conformance work. It is still not a production state.
- **STAGING**: applicable static/reference/provider prerequisites have passed and the implementation can be evaluated by the existing runtime admission/promotion mechanisms. STAGING is not PROMOTED.

Invalidation may demote assurance. If the inputs are insufficient, assurance is `UNKNOWN` rather than guessed.

### 2. Canonical

Canonical state is **not owned by this projection**. It is passed through from the existing canonical policy/release sources.

The projection must never infer that a canonical component is production-promoted. A state such as:

`Canonical: CANONICAL_CLOSED` + `Runtime: PENDING_CURRENT_HOST`

is valid and expected in FA3.

### 3. Runtime / production

Runtime state is **not owned by this projection**. It is read from the existing Evidence Registry, current-host closure, Acceptance output, and Promotion output.

Only the existing promotion authority may produce `PROMOTED`. Reference CI, documentation, a canonical decision, or a STAGING assurance ring cannot substitute for qualified current-host evidence.

## Fail-closed rules

The projection must report unknown or pending state when an authoritative source is missing or ambiguous. It may not infer PASS.

Explicitly forbidden inferences include:

- `STAGING -> PRODUCTION`
- `CANONICAL_CLOSED -> PROMOTED`
- reference/CI PASS -> current-host PASS
- documentation -> runtime PASS
- assurance ring -> bypass Acceptance
- assurance ring -> bypass Promotion Guard

## GUI use

A GUI may render the projection as separate read-only fields, for example:

```text
Assurance       STAGING
Canonical       CANONICAL_CLOSED
Current Host    PENDING_CURRENT_HOST
Production      NOT_PROMOTED
```

Unknown values must remain visible as unknown and must never be rendered as PASS.

## Enforcement

`src/fa3_governance_tiering_gate.py` verifies that:

- the projection remains zero-authority and zero-capability;
- the 143-capability baseline is unchanged;
- current-host evidence remains mandatory for runtime promotion;
- the assurance rings remain separate from canonical/runtime state;
- the projection is not registered as an Evidence Registry capability;
- Acceptance and Promotion remain owned by `src/fa3_enforce.py`;
- the real current-host runner boundary remains `[self-hosted, linux, x64, fa3-current-host]`.

The dedicated CI workflow is `.github/workflows/fa3-governance-tiering.yml`. It performs only static/structural validation and does **not** create or claim current-host evidence.
