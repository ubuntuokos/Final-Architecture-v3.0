# FA3 Task Group & Guard Policy Plane

**Date:** 2026-10-02
**Status:** MATERIALIZED STATIC POLICY PLANE / RUNTIME CONDUCTOR DELEGATION NOT INCLUDED
**Capability baseline:** 175 fixed
**Capability delta:** 0
**Architectural authority delta:** 0

## Purpose

This change materializes the first-class policy layer that sits between Agent/Application Blueprint classification and the existing FA3 Orchestration Workforce. It does not add a scheduler, task manager, workflow engine, resource authority, model authority or evidence authority.

The canonical path is:

```text
Goal Contract
  -> Agent/Application Blueprint
  -> Task Group Registry
  -> Task Group Policy Snapshot
  -> ordered Guard Chain
  -> Director / Workforce
  -> Temporal durable lifecycle
  -> existing runtime admission boundaries
```

Runtime Conductor delegation is intentionally excluded from this static policy-plane change and remains a separate Current Host evidence-gated follow-up.

## Canonical task groups

`FA3-TASK-GROUP-REGISTRY-001` contains exactly 31 first-level groups, F01 through F31.

Special handling:

- F07 Durable Workflow Lifecycle is Temporal-exclusive.
- F09-F13 are horizontal authority/service domains and are not specialist-owned task groups.
- F17 Verification & Evidence remains independent from the executor.
- F23/F24/F27 and other workload-heavy groups may declare Workload Mode domains as intent only; HRB remains physical resource authority.

Compatibility aliases are allowed only as registry-owned aliases. Compilation resolves aliases to the canonical Fxx identity and binds task-group revision and digest.

## Guard chain

`FA3-ORCHESTRATION-GUARD-CHAIN-CONTRACTS-001` defines:

- G0 Goal / Intent
- G1 Task Group
- G2 Role / Responsibility Scope
- G3 Dependency / Handoff
- G4 Identity / Security
- G5 Capability / Specialist Eligibility
- G6 Provider / Runtime Admission
- G7 Workload Mode / HRB / Resource
- G8 Model Router
- G9 UAF / Effect Authorization
- G10 Evidence / Verification

The chain is a non-authoritative validation projection. It checks existing authority decisions and cannot mint them.

## Workload Mode integration

The mandatory `FA3-WORKLOAD-MODE-FRAMEWORK-001` is reused rather than duplicated.

Task groups may declare workload intent such as `AGENT_BACKGROUND`, `VIDEO_GENERATION` or `RENDER_ANIMATION_BATCH`. They cannot choose physical GPU/CPU/NUMA placement or create resource leases.

With FA3 present:

```text
Task Group workload intent
  -> Workload Mode state/policy
  -> HRB admission/placement/lease
```

CPU-only remains valid. Automatic display-GPU recruitment remains forbidden by existing policy.

## Existing layers reused

- Goal Execution remains the source of goal scope and acceptance policy.
- Work Management remains the provider-neutral work-item/operator projection.
- Temporal remains the sole global durable lifecycle authority.
- Orchestration Governance owns typed dependencies, claims, approvals, handoff and recovery semantics.
- Workload Mode owns shared workload intent/effective mode state.
- HRB owns physical resources.
- Model Router owns physical model/provider/runtime routing.
- UAF/MCP/Security own effect authorization and mediation.
- Evidence/Gate owns verification.

## Governance extensions

The existing Orchestration Governance contract now includes:

- typed handoff lifecycle;
- ACK-is-not-completion invariant;
- explicit recovery classes: RETRYABLE, RECOVERABLE, REPLAN_REQUIRED, HUMAN_REQUIRED, UNKNOWN_EFFECT;
- no blind retry for UNKNOWN_EFFECT;
- task-group revision/digest binding.

## Donor/reuse boundary

The orchestration Reuse Assessment is refreshed to the latest finalized published donor snapshot used by current main lineage: 1354 entries, registry blob `804786e96c66ef6c4397b1471e52a6594473bb20`.

Pending donor PR records are not consumed.

`cporter202/agentic-ai-starters` remains analysis-only and is not registered or adopted by this change.

The finalized Google Antigravity donor intake on current main was re-assessed for Shared Orchestration / Layer Guard relevance. No additional material adoption or usage edge is required because the relevant policy-hook, tool-dispatch, session, MCP and adapter patterns are already covered by existing Temporal, UAF/Security/MCP, Blueprint and orchestration-governance boundaries.

## Current Host boundary

This materialization is static policy/governance work. It does not claim physical Current Host runtime promotion.

The later bounded Conductor runtime delegation work must remain separate and requires real scope-bound Current Host evidence for any external runtime execution path.
