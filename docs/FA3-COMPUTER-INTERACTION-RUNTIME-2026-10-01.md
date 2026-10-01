# FA3 Native Computer Interaction Runtime

**Status:** canonical static materialization; physical CAP-013 Current Host requalification remains pending.

## Layer decision

The native computer-use execution path belongs under **FA3 Unified Action Fabric**, composed through **Shared Tool & Action Mediation**. It is not an application, orchestrator, scheduler, MCP authority, model router, evidence store, permission authority or sandbox authority.

The canonical flow is:

```text
Application / Agent
  -> Orchestrator / Conductor
  -> bounded intent / Decision Fabric advisory
  -> Shared Tool & Action Mediation
  -> Unified Action Fabric
  -> Computer Interaction Runtime
  -> separately admitted native desktop adapter
  -> physical application/window
  -> effect observation
  -> independent Evidence / Current Host verification
```

Browser automation remains the separate `FA3-BROWSER-ACTION-RUNTIME-001` specialization. The new runtime covers native desktop/window/application interaction and projects existing CAP-013 semantics without creating a capability.

## Why this layer

The repository already makes UAF the provider-neutral action execution contract layer and forbids direct agent/provider bypass. The merged Shared Tool & Action Mediation profile already binds CAP-013 to typed intent, security policy, approval, MCP/UAF, workload isolation, HRB and evidence. A second desktop automation authority would therefore be architectural duplication.

## Bounded interaction contract

Every executable action is bound to a specific:

- current user session;
- application identity;
- window identity and fingerprint;
- observation revision;
- capture identity;
- bounded action-space digest;
- observed target;
- authorization reference for mutations.

Any mismatch fails closed with `STALE_OBSERVATION`. Raw coordinate-only actions and arbitrary scripts are denied by default. Visual-region targets remain valid only for the same capture identity.

The Decision Fabric may select only from the runtime-created candidate set. It cannot add targets or actions. Control outcomes include `REOBSERVE`, `ABSTAIN` and `BLOCKED`; none counts as successful execution.

## Mutation and verification

Mutating actions cannot be blindly retried. A mutation requires:

1. fresh observation and capture binding;
2. deterministic revalidation;
3. security/authorization reference;
4. execution through an admitted UAF adapter;
5. post-mutation reobservation;
6. independent postcondition verification;
7. evidence export.

An execution receipt by itself is never success.

## Privacy

Telemetry is disabled by default. The default trajectory is metadata-minimal and excludes screenshot bytes, typed text, clipboard contents, raw tool arguments/results, window titles and URLs. External telemetry requires a separate explicit opt-in policy.

## CUA research input and boundary

`trycua/cua` was reviewed at upstream commit `9545a3d17b44b587b593d59090dc140740876a6e` (Cua Driver 0.31.0 observed). Its useful patterns include driver/decision separation, capture-bound action delivery, bounded permission concepts, reobserve/abstain outcomes, privacy-minimal action history and benchmark-style verification.

The owner-provided URL was **not preceded by the canonical `donornak` intake marker**, so this work does not create a donor record, donor usage edge, code import, runtime dependency, provider admission or model admission for CUA. The implementation is FA3-native and uses existing canonical authorities.

The upstream root is source-declared MIT, while optional perception/SOM areas have separate AGPL-related terms. Those components are not bundled or admitted here.

## CUA component disposition

| Upstream concept | FA3 placement | Disposition |
|---|---|---|
| Driver observation/action boundary | UAF -> Computer Interaction Runtime | FA3-native pattern |
| Bounded permission manifest | Security Governance + Shared Tool/Action Mediation | pattern only |
| CUA-S1 specialist decisions | Model Router + Decision Fabric | separate future admission only |
| Cua Bench step/evaluate | Current Host + Evidence | verification pattern |
| Trajectories | CAP-079 Observability | metadata-minimal pattern |
| Sandbox SDK | Agent Workload Runtime | lifecycle/isolation pattern |
| Fleets | optional provider layer | not admitted; never mandatory |
| Lume | virtualization reference | not generic Linux authority |
| MCP endpoint | Central MCP Gateway | no direct agent bypass |
| Computer History | Observability/Memory | privacy pattern only |
| Perception / OmniParser / SOM | optional perception adapter | blocked pending separate rights/security admission |

## Current Host

This changes a structural execution path for CAP-013, so Current Host alignment is mandatory. Static CI validates the contract, security boundaries and deterministic negative cases, but **does not** promote runtime status.

Fresh physical evidence must demonstrate a real current user session, real native application/window, positive effect, stale-capture denial, unauthorized-mutation denial, post-mutation reobservation, independent verification, rollback and privacy checks. Until that evidence exists, the runtime status remains `PENDING_PHYSICAL_REQUALIFICATION`.

## Invariants

- capability baseline remains **175**;
- provider count remains dynamic;
- capability delta **0**;
- authority delta **0**;
- CPU-only control path remains valid;
- accelerators remain optional `0..N`;
- HRB remains the sole resource authority;
- Model Router remains the sole model/provider routing authority;
- Central MCP Gateway remains the tool/MCP boundary;
- UAF remains the action execution boundary;
- Evidence remains independently owned;
- no silent fallback;
- no upstream uninstall or host-global mutation.
