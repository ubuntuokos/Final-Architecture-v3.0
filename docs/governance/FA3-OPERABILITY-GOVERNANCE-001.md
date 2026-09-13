# FA3-OPERABILITY-GOVERNANCE-001

Status: CANONICAL_CANDIDATE
Scope: Final Architecture v3.0 governance criteria revision

## Purpose

This profile consolidates the FA3 operability changes agreed during the 2026-09-13 governance review. The purpose is to keep FA3 fail-closed in production while removing unnecessary administrative cost from experimentation, provider evaluation and host-specific activation.

## Canonical principles

1. Experimentation MUST be cheap; production promotion MUST be strict.
2. Assurance requirements MUST increase monotonically across promotion stages.
3. A release capability count is a release baseline, not a permanent architectural constant.
4. Host evidence MUST be scoped to capabilities that are required, enabled or production-active on that host.
5. Production artifacts MUST remain pinned, reproducible and provenance-bearing.
6. LAB experimentation MAY follow floating upstreams when isolated from production and canonical state.
7. Human approval MUST be risk-based rather than universally required.
8. Execution governance MUST support LOCAL, LAN, CLUSTER, CLOUD and HYBRID targets through a common lease model.
9. FA3 MUST NOT depend on external meta-launchers/application managers for canonical application lifecycle management.
10. Paid external providers MUST be disabled by default and require explicit global and provider-level opt-in.

## Assurance stages

`LAB -> CANDIDATE -> STAGING -> PRODUCTION -> CANONICAL`

### LAB
- isolated experimentation
- floating upstream MAY be used
- no canonical or production claim
- minimal evidence

### CANDIDATE
- source revision MUST be resolved
- basic security and functional checks
- candidate is reproducible enough for evaluation

### STAGING
- immutable source/digest
- FA3 conformance checks
- dependency, permission and authority boundaries validated

### PRODUCTION
- immutable artifacts
- provenance/SBOM where applicable
- scoped current-host runtime evidence
- fail-closed policy enforcement

### CANONICAL
- release reconciliation
- registry/evidence consistency
- policy and capability baseline update
- canonical admission is intentionally expensive

## Related profiles

- FA3-RELEASE-CAPABILITY-BASELINE-001
- FA3-EVIDENCE-SCOPE-001
- FA3-UPDATE-RINGS-001
- FA3-RISK-BASED-HITL-001
- FA3-EXECUTION-FABRIC-001
- FA3-APPLICATION-FABRIC-001
- FA3-PAID-PROVIDER-POLICY-001
- FA3-EXTERNAL-SERVICE-LEASE-001
- FA3-PROVIDER-COST-GOVERNANCE-001

## Transitional rule

This change modifies FA3 criteria themselves. Existing rules MUST NOT be used to reject the migration solely because the migration changes those rules. Security invariants, authority boundaries and production fail-closed behavior remain mandatory throughout the transition.
