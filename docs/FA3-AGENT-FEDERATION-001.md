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
