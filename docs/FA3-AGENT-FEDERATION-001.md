# FA3-AGENT-FEDERATION-001

This profile materializes the existing CAP-070 Hybrid Orchestration Federation capability as an FA3-native secure cross-host coordination layer.

## Architectural decision

Ruflo is a reference-pattern source only. Its runtime, daemon, memory authority, swarm authority and plugin marketplace are not imported into FA3. The immutable reference used for this derivation is ruvnet/ruflo commit 0a96fb8857dabd343d71d76c3ca703100a2923bc, observed at release v3.44.0 under the MIT license.

The capability count remains 143 and no architectural authority is added.

## Federation boundary

Federation transports typed agent delegation and coordination between authenticated peers. It does not authorize models, tools, secrets, host resources, durable workflows or provider runtimes.

Remote execution requires all existing FA3 decisions to succeed: peer identity verification, Security Governance authorization, Agent Execution runtime admission, a Unified Action Fabric route, remote HRB resource admission and provider runtime admission.

Peer trust, reputation and successful interaction history are advisory signals only. They can never expand authorization automatically.

## Coordination claims

A CoordinationClaim expresses logical ownership of a work item such as a task, file, artifact or integration unit. Claims have TTLs and support acquire, acknowledge, renew, handoff, release and expiry.

A CoordinationClaim is never an HRB resource lease. It cannot reserve CPU, GPU, NPU, RAM, VRAM, NUMA placement or any other host resource.

## Signed envelopes

Every federation envelope is versioned, signed, replay-protected, time-bounded and hop-bounded. Its payload remains subject to FA3-AI-COMMS-001 and therefore has an authoritative human-readable semantic representation.

The canonical signature algorithm for the v1 envelope is Ed25519. Signature verification itself remains an Identity/Security boundary; the reference runtime accepts a verifier callback and does not become a cryptographic-key authority.

## Delegation budgets

Delegations carry bounded hops, tokens, wall time, children, remote delegations, model cost and CPU/GPU time. Child budgets must be component-wise less than or equal to the parent's remaining budget.

## Circuit breaker

Peer state is ACTIVE, SUSPENDED, QUARANTINED or REVOKED. A revoked peer cannot automatically reactivate. Reactivation from suspended or quarantined state requires Security Governance authorization.

## Evidence truth boundary

CAP-070 has two distinct evidence levels.

LOCAL_MULTI_NODE_PROTOCOL_PASS may exercise independent peers, identities and sockets on one physical host using loopback. It proves protocol mechanics only.

CROSS_HOST_PRODUCTION_E2E_PASS requires at least two distinct host identities and real cross-host authenticated transport. A local protocol PASS must never promote CAP-070 to cross-host production status.

The Evidence Registry remains PENDING_CURRENT_HOST until the cross-host obligation is actually satisfied.

## Adaptive coordination

Ruflo-style hook, trajectory and background-worker ideas are normalized into existing FA3 authorities rather than becoming a new hook daemon.

Federation lifecycle events are non-authoritative projections into the existing FA3 Journal and Closed-Loop Agent Operations run ledger. The canonical lifecycle projection covers task, delegation, claim and action transitions and preserves human-readable semantics and evidence provenance.

Execution trajectories are derived, append-only lineage objects. They do not become evidence or memory authority. An outcome evaluation may create a PatternCandidate only when source trajectory and evidence lineage are preserved.

A PatternCandidate cannot grant authority or capability and cannot promote itself. Promotion requires explicit review plus evidence; HIGH/CRITICAL patterns additionally require human approval. Persistent patterns use existing Agent Memory Asset Governance, while Decision Fabric may rank candidates only as advisory input.

Adaptive/background workers remain ordinary bounded FA3 work. Event-driven or change-watch triggers are preferred. Polling requires an early-exit path, budget gate and no-op path. Durable lifecycle remains Temporal, execution enters through UAF, and resource admission remains HRB. Hidden resident worker authority and unbounded polling are forbidden.
