# Open Dots donor/reuse hardening assessment

**Date:** 2026-10-02  
**Status:** PLANNING ONLY — CANONICAL DONOR CAPTURE BLOCKED PENDING EXPLICIT OWNER `donornak` MARKER  
**FA3 base:** `bf50877f64c41cfea49c69dc274812370dfcb77b` (merged PR #601)  
**Capability baseline:** 175, unchanged  
**Authority delta:** 0  
**Provider delta:** 0  
**Runtime admission:** none  
**Code import:** none

## 1. Upstream identity

Source: `https://github.com/Anil-matcha/open-dots`

Inspected immutable upstream commit:

`5abe1b3d65d5176af936ed92de1b731634d2bcb5`

Observed source metadata at that snapshot:

- repository: `Anil-matcha/open-dots`
- primary language: Python
- upstream status: prototype / active development
- root license declaration: MIT
- LICENSE blob SHA: `83c02287248c0e2e3e6b0618d86cd758e454bd27`
- README blob SHA: `23f69cc9dcab5c7922f5eb6b8b7a83cfa06f69c6`
- relevant upstream surfaces: action gateway, approval broker, governed connector actions, provider-neutral computer interface, Docker/remote computer adapters, local audit/state storage.

The upstream README explicitly says that multi-user hosting and hostile-web isolation are not production ready. Therefore no upstream computer/runtime security boundary is eligible for implicit FA3 admission.

## 2. Donor Registry status and blocker

Merged PR #601 advanced the published donor intake from 1307 to an expected 1316 canonical records. Repository search on the current main snapshot found no existing `Anil-matcha/open-dots` record.

FA3 reuse policy is fail-closed and contains the invariant:

`ONLY_EXPLICIT_OWNER_DONORNAK_MARKED_LINKS_ENTER_DONOR_REGISTRY`

The owner supplied the Open Dots URL and approved continuation of this assessment, but the URL was not explicitly preceded by the required `donornak` marker. Therefore this branch MUST NOT add the source to `FA3-DONOR-REFERENCE-REGISTRY-001` and MUST NOT create a donor usage edge.

This is a governance blocker, not a technical rejection of the source.

## 3. Existing FA3 coverage

Open Dots does not justify a new application, provider, shared capability, architectural authority or runtime dependency. Its major patterns are already covered by stronger FA3 primitives:

| Open Dots pattern | Existing FA3 owner | Disposition |
| --- | --- | --- |
| explicit action registry / unknown-action denial | `FA3-UNIFIED-ACTION-FABRIC-001` | already covered |
| typed action request | UAF ActionContract / ActionRequest | already covered |
| approval-gated effects | Security Governance + `AUTH-HUMAN` | FA3 stronger |
| single-use approval | UAF approval validation + consuming approval authority | already covered |
| action/version/argument binding | UAF digest-bound approval | FA3 stronger |
| connector mediation | Central MCP Gateway + UAF | FA3 stronger |
| secret handling | Secret Broker opaque references/leases | FA3 stronger |
| evidence/audit | Evidence authority + Journal | FA3 stronger |
| resource admission | HRB | FA3 stronger |
| computer provider abstraction | `FA3-COMPUTER-INTERACTION-RUNTIME-001` | already covered |
| blind mutation retry prevention | Computer Interaction Runtime | already covered |
| uncertain computer mutation verification | Computer Interaction Runtime reobserve/verify | already covered |

No capability-count change is warranted.

## 4. Selected hardening deltas

The following are the only Open Dots-derived patterns worth carrying forward for FA3 design review. They are refinements of existing authorities, not new authorities.

### OD-H1 — uniform UAF action lifecycle events

Define a provider-neutral lifecycle projection for all governed actions:

`REQUESTED -> AUTHORIZED/APPROVED | DENIED -> DISPATCHING -> DISPATCHED -> COMPLETED | FAILED | OUTCOME_UNKNOWN | EXPIRED | CANCELLED`

Requirements:

- lifecycle events are projections into existing Journal/Evidence, never a new state authority;
- every transition binds `request_id`, `trace_id`, action/version, principal, argument/context digests and provider identity when known;
- no UI or agent may infer success merely from DISPATCHED;
- terminal state remains evidence-backed;
- sensitive arguments/results stay outside lifecycle metadata.

### OD-H2 — generic remote side-effect uncertainty

Generalize the existing computer-interaction rule to arbitrary remote connector/API mutations.

If cancellation, timeout, transport failure or process failure occurs after dispatch and the remote effect cannot be proven absent:

`REMOTE_EFFECT_OUTCOME_UNKNOWN`

Policy:

- automatic replay is forbidden;
- approval replay is forbidden;
- the target state must be reconciled or independently verified before another mutation;
- a new mutation requires a fresh valid authorization/approval where policy requires it;
- idempotency keys may permit safe reconciliation but do not by themselves prove remote outcome;
- unresolved uncertainty must surface as BLOCKED/INDETERMINATE, never SUCCESS.

### OD-H3 — UAF action-attempt / dispatch replay ledger

Evaluate a durable, authority-compatible ledger binding:

- `request_id`
- execution attempt ID
- action/version
- argument/context digests
- authorization / approval receipt references
- provider selection
- dispatch state
- idempotency key when defined
- terminal outcome/evidence reference.

The ledger must prevent:

- concurrent duplicate dispatch;
- duplicate client submission from creating the same side effect twice;
- cancellation + retry races;
- crash/restart blind replay;
- late completion superseding a newer authorized revision.

Temporal remains the sole global durable workflow authority. The ledger may be implemented as UAF/Temporal state or an existing Journal-backed execution projection; it MUST NOT become a second scheduler, workflow engine or approval authority.

## 5. Explicit non-adoption

Do not adopt or promote:

- Open Dots as a separate FA3 application;
- the upstream ApprovalBroker as an FA3 authority;
- its SQLite store as a canonical state authority;
- its secret store in place of FA3 Secret Broker;
- its inference adapter in place of Model Router;
- its Next.js UI as an FA3 GUI foundation;
- Composio as an architectural authority;
- its Docker/Playwright runtime as a trusted FA3 computer security boundary;
- free-form `terminal_execute` semantics in the FA3 Computer Interaction Runtime.

Any future code reuse requires separate source-file/transitive dependency license and provenance review. MIT repository metadata alone is not sufficient for bundled assets, dependencies, remote services or external terms.

## 6. Target placement

If the owner later marks the source with the required donor marker and separately approves adoption, the three selected patterns should attach only to existing components:

- `FA3-SHARED-TOOL-ACTION-MEDIATION-001`
- `FA3-UNIFIED-ACTION-FABRIC-001`
- `FA3-CLOSED-LOOP-AGENT-OPERATIONS-001`
- existing Journal / Evidence projections
- Computer Interaction Runtime only where the generalized uncertainty contract is reused.

No new shared module is required.

## 7. Safety, coexistence and runtime boundaries

This assessment introduces no service, daemon, port, socket, dependency, model selection, provider activation, hardware mutation or current-host claim.

Any later implementation remains subject to:

- Security Governance;
- Central MCP Gateway;
- Secret Broker;
- HRB;
- Hardware Safety Envelope;
- Software Coexistence & Host Non-Interference;
- Temporal durable workflow authority;
- Model Router;
- Evidence/Gate;
- CPU-only valid path;
- no silent fallback;
- current-host promotion only from fresh physical evidence.

## 8. Gate to the next stage

Canonical donor capture is permitted only after an owner message explicitly marks the exact source as donor, e.g. by using the repository URL with the required `donornak` marker.

After that marker exists, the next stage may:

1. append one source-unique reference record to the central Donor Registry;
2. reconcile against the then-current published main registry snapshot;
3. create the owner-approved donor decision/usage edge only if actual pattern adoption is approved;
4. produce an exact-head ApplicationIntent/ReuseAssessment for OD-H1..H3;
5. prepare implementation changes without merging or promoting them until the next explicit approval.

