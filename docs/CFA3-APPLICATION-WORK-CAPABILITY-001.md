# CFA3 Application, Work & Capability Operating Model

Status: **materialized static architecture / runtime-specific promotion separate**.

## Purpose

This package materializes the approved PhreshOS + Cloudflare OS + Operately + WebOS-derived design as CFA3-native extensions of existing canonical owners.

It does not introduce a new top-level Fabric authority.

## Canonical ownership

- effectful operations: Unified Action Fabric
- work truth: Work Management
- context projection: FA3 OS
- application lifecycle: existing provisioning lifecycle + runtime lifecycle extension
- authorization: Security Governance
- scoped agent grant: CapabilityGrant scope contract
- task-local execution: Agent Workload Runtime
- durable workflow: Temporal
- model/provider routing: Model Router
- host resources: HRB
- MCP/tool mediation: Central MCP Gateway
- evidence: Evidence Authority
- history/activity: Journal
- updates: Update Fabric

## Work Management v2

The existing provider-neutral work-item layer remains compatible.

New canonical semantic entities:

```text
Goal
  └─ Program / Production
       └─ Project
            └─ Workstream
                 └─ Milestone
                      └─ Task
```

Check-ins, Risks, Blockers, Decision Requests and Activity records attach to this hierarchy by canonical reference.

Provider object IDs remain projection metadata. Kaneo, Kanboard and GitHub Issues may not own canonical work identity.

## Check-ins

A check-in records:

- status
- completed since last check-in
- next actions
- blockers
- risks
- decisions needed
- actor identity
- timestamp
- provenance

AI may summarize a check-in but may not replace its source truth.

## Application Runtime Lifecycle v2

The existing first-use provisioning lifecycle remains unchanged.

After `INSTALLED`, the runtime extension supports:

```text
CONFIGURING
READY
STARTING
RUNNING
SUSPENDING
SUSPENDED
RESUMING
STOPPING
STOPPED
UPDATING
ROLLBACK_PENDING
ROLLING_BACK
REMOVING
REMOVED
FAILED
```

The lifecycle contract coordinates state only. It is not an execution authority.

Actual effects remain delegated to UAF, Security, Temporal, HRB, Update Fabric and Evidence.

## CapabilityGrant

Agent authority is explicitly delegated and bounded by:

- actor
- allowed operations
- allowed resources
- project/workspace scope
- delegator
- validity interval
- approval binding
- budget envelope
- provenance

An agent does not inherit the user's full authority.

Subagent scope must be a subset of its parent grant.

## Work Context

FA3 OS carries a reference-only Work Context:

- organization
- production
- goal
- project
- workstream
- milestone
- task
- workspace
- workflow
- actor/agent
- assets/artifacts/approvals

This context does not duplicate project/task truth. Canonical work truth remains in Work Management and canonical historical truth remains in Journal.

## Task Capsule

A Task Capsule is a composition of:

```text
Agent Workload Task
+ Workspace
+ CapabilityGrant
+ Blueprint
+ Work Context
```

It is not:

- an application authority
- a project/task authority
- a permission authority
- a second workflow engine

Speculative results never become canonical commits without the normal approval + UAF + target-authority path.

## Blueprint extension

Blueprints may declare:

- UI surfaces
- shared module requirements
- requested capabilities
- workspace requirements
- lifecycle profile
- plugin/extension requirements
- Work Context requirements
- promotion target

These are requirements, not grants or runtime admission.

## Promotion

A successful Task Capsule may become a reusable Blueprint, Plugin, Extension or Application only after:

- reuse review
- security review
- License & Rights review
- capability compatibility review
- GUI compatibility review
- application compatibility propagation review
- test and rollback review

There is no automatic promotion.

## Inter-application operation & handoff

`FA3-APPLICATION-OPERATION-HANDOFF-CONTRACTS-001` provides addressed application-to-application request/result/event/artifact/intermediate-result/cancellation envelopes.

The canonical application ID is the address. Transport endpoints are implementation details and do not become application identity.

Every effectful cross-application request carries:

- source and target application IDs
- correlation ID
- operation reference
- Work Context reference
- CapabilityGrant reference
- provenance
- optional workflow/task/artifact/result receipt references

A handoff is never authorization. The receiver re-validates scope and an effectful operation must resolve to a typed UAF action. Artifact handoff preserves provenance and native project/data formats.

## Application lifecycle GUI

The existing AI Studio Applications surface now understands the runtime lifecycle vocabulary but never fabricates runtime state.

When only provisioning state is available, the UI explicitly shows:

`Runtime control: ADAPTER-GATED`

A RUNNING/SUSPENDED/STOPPED state is displayed only when an admitted runtime adapter supplies it.

## Platform binding reconciliation

`FA3-PLATFORM-BINDING-RECONCILIATION-001` separates platform taxonomy from execution authority.

Collaboration remains a composition category; it does not become a new runtime authority.

Plugin/Extension binding is intentionally left attached to the already-existing owner line from PR #564 rather than creating a second implementation.

## Compatibility

The model must remain compatible with all affected existing and future CFA3 applications.

A shared capability increase is not complete until all affected consumers are classified as one of:

- NO_CHANGE
- GUI_PROJECTION
- CONTRACT_ADAPTER
- SHARED_CAPABILITY_BINDING
- LOCAL_TO_SHARED_MIGRATION
- RUNTIME_REQUALIFICATION

The enforcement for this forward/retroactive propagation is materialized separately in PR #715.

## Donor provenance

Materially used pattern sources:

- PhreshOS
- Cloudflare OS
- Operately
- webOS OSE

No donor code was copied and no donor runtime/provider/model was admitted.

Canonical usage edges are materialized in stacked donor PR #717 over donor baseline #714.

## Current Host

This package does not claim physical Current Host PASS.

Current Host remains the final stable-exact-head step after structural reconciliation. Synthetic or static PASS cannot substitute physical positive/negative/rollback evidence where runtime requalification is required.
