# FA3 Orchestrator–Conductor–Temporal — governance-strengthened final plan

**Date:** 2026-09-30
**Status:** OWNER-APPROVED IMPLEMENTATION PLAN / MATERIALIZATION BASIS
**Capability baseline:** 175 fixed
**Provider count:** dynamic
**Capability delta:** 0
**Architectural authority delta:** 0

## 1. Architecture

FA3 keeps one global durable workflow authority: **Temporal**. The FA3 Orchestration Director decomposes and routes work but does not authorize its own security, resources, models, tools, durable lifecycle or evidence. Specialized Orchestrator/Conductor profiles remain task-group specialists, selected after deterministic eligibility. The shared FA3-native Adaptive Conductor handles delegated adaptive graphs; Conductor OSS remains optional and cannot become a second durable control plane.

The accepted functional structure remains:

- 31 first-level FA3 task groups;
- 7 logical control profiles (P1 Director, P2 Adaptive Conductor, P3 Agent Workforce, P4 Production Conductor, P5 Distributed Coordinator, P6 Live Cue Coordinator, P7 Event Coordinator);
- one central Temporal durable lifecycle;
- independent Security, UAF/MCP, HRB, Model Router, Secret Broker and Evidence/Gate authorities;
- Control & Monitoring projection for observability and governed operator changes.

## 2. Governance strengthening

This revision adds one shared **Orchestration Work Governance** contract used by all seven profiles.

### 2.1 Goal ancestry
Every governed task can carry an objective ancestry from user/project objective to work package, task and graph node. The ancestry explains why the work exists but does not grant execution authority.

### 2.2 Boundary-based work decomposition
The Director creates a separate task only when a real execution boundary exists: specialist/owner boundary, permission boundary, independently parallelizable deliverable, hard dependency/handoff, independent review/approval, or independent retry/recovery lifecycle. Micro-task creation without a qualifying boundary is rejected by the governance validator.

### 2.3 Typed dependency relations
Structure and execution dependency are distinct. Supported relation types are:
- STRUCTURAL_PARENT
- BLOCKED_BY
- DATA_REQUIRES
- APPROVAL_REQUIRES
- RESOURCE_REQUIRES
- VERIFY_REQUIRES
- HANDOFF_TO
- SUPERSEDES

Hard dependency cycles fail closed.

### 2.4 Responsibility and authority chain
Delegation carries a responsible-principal chain. Child/delegated authority scope must be a subset of the parent scope. A replan, retry, recovery or fallback cannot expand permissions.

### 2.5 Atomic execution claim
Runtime work uses task-bound execution claims with claimant, generation, idempotency key, expiry and authority scope. A successor cannot take over a live claim only because a heartbeat is stale. Takeover requires terminal/released/expired predecessor state and a strictly newer generation.

### 2.6 Version-bound approval
Approval binds to object ID, revision, SHA-256 digest, scope and allowed operation set. A new plan/config/artifact revision invalidates the previous approval for execution unless explicitly re-approved.

### 2.7 Execution budget envelope
Tasks may carry bounded time, CPU, GPU/NPU, memory, storage, network, provider-cost, token, retry and parallelism budgets. These are coordination limits only; physical resource placement remains HRB-only.

### 2.8 Liveness model
The common liveness states are READY, CLAIMED, RUNNING, WAITING_INPUT, WAITING_APPROVAL, WAITING_RESOURCE, BLOCKED, RECOVERING, STALLED, CANCELLING, FINISHED, FAILED and UNKNOWN. Monitoring must distinguish liveness from durable Temporal status and from independent Evidence/Gate verification.

### 2.9 Monitoring and governed reconfiguration
The Orchestration Control & Monitoring Center projects:
- objective/work hierarchy;
- Temporal workflow state;
- task graph and blockers;
- specialist/agent responsibility;
- authority chain and approvals;
- execution claims;
- HRB/resource and Model Router references;
- liveness, recovery, alerts and evidence status;
- versioned configuration changes and rollback references.

The monitor is not an authority. Changes are requests to the owning authority. Runtime engine/specialist switching is never silent.

## 3. External reference analysis

Paperclip was analyzed as an external reference because the owner explicitly requested this redesign after reviewing it. Under the repository donor-marker rule, the submitted URL was not introduced with `donornak`, so this materialization does **not** add Paperclip to the canonical donor registry and does not copy, install or depend on Paperclip code/runtime.

The FA3-native design adopts only owner-approved functional requirements that are independently justified by FA3 needs: goal ancestry, ownership/dependency/execution separation, atomic claim semantics, version-bound approvals, bounded recovery, responsibility attribution, budget envelopes and operator observability.

Published-main Reuse Discovery remains bound to donor registry blob `7e900cac93936d2f319e132def4c172b2a415d4d` with 1233 entries. Existing published donors relevant to this design include Temporal SDK patterns, Dagger, SkyPilot, OpenShell and Langfuse references; no external runtime is promoted by this plan.

## 4. Stability and recovery

- Temporal owns durable workflow history and global resume/cancel.
- Delegated graphs may keep local execution state only.
- Duplicate commands/effects require idempotency identities.
- Unknown remote execution outcome is not blindly replayed.
- Recovery is bounded by retry/time/storage budgets.
- Claims, approvals, HRB leases, model route and security authorization are revalidated at the point of effect.
- STOP prevents new delegation and new graph branches; continuation requires fresh admissibility.
- A worker result is a claim, not VERIFIED evidence.

## 5. Parallelism and productivity

Parallelism is allowed only after dependency, mutation-conflict, authority and resource checks. The Director minimizes unnecessary task fragmentation, while the Conductor exposes safe parallel branches. Incremental reprocessing targets only affected descendants. The Monitoring Center reports queue wait, critical path, retry cost, reused results, blocked time and verified-output throughput.

## 6. Current Host alignment

This is a structural orchestration change, therefore Current Host projection is updated. Static/unit evidence may prove contract behavior only. Runtime promotion of provider/Conductor execution still requires real scope-bound Current Host evidence; no synthetic PASS is created.

## 7. Acceptance

The materialization is accepted only if:
1. active capability baseline remains 175;
2. Temporal remains the sole global durable lifecycle authority;
3. responsibility scope cannot grow through delegation;
4. hard dependency cycles fail closed;
5. live claims cannot be stolen by stale-heartbeat inference;
6. stale approval revisions/digests cannot authorize execution;
7. budget/liveness/config projections are non-authoritative;
8. existing routing and provider-admission rules remain compatible;
9. Monitoring projection cannot bypass Security/UAF/HRB/Model Router/Evidence;
10. Current Host physical promotion remains pending until real evidence exists.
