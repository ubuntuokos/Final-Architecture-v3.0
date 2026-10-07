# FA3 Agent/Application Blueprint Fabric

**Date:** 2026-10-02
**Status:** MATERIALIZED DESIGN + STATIC COMPILER
**Capability baseline:** 175 fixed
**Capability delta:** 0
**Architectural authority delta:** 0

## Purpose

The Agent/Application Blueprint Fabric adds a reusable, provider-neutral design and compilation layer on top of the existing FA3 task-group + Layer Guard + Temporal + optional Conductor + shared orchestration model.

It does **not** introduce a new orchestrator, scheduler, durable workflow engine, provider authority or capability registry. A blueprint is versioned configuration that describes how an agentic application or feature should decompose into FA3 work.

## Canonical flow

```text
Application / user objective
  -> Agent/Application Blueprint
  -> blueprint validation + digest
  -> explicit task-group binding
  -> task-scoped roles (planner/router/worker/reviewer/verifier/operator)
  -> structured handoffs + review bindings
  -> FA3 Orchestration Director
  -> deterministic specialist eligibility
  -> optional bounded Decision Fabric advisory
  -> Temporal durable lifecycle
  -> optional FA3 Adaptive Conductor / admitted Conductor task-local graph
  -> UAF + MCP/Security approvals
  -> HRB / ACCEL-GUARD resource admission
  -> Model Router
  -> Agent Workload Runtime
  -> output validation
  -> Evidence / Journal / release gates
```

## Design rules

1. **Task group first.** Every blueprint names one FA3 task group. The blueprint compiler emits existing Workforce work requests; it never creates a second task registry.
2. **Roles are context, not authority.** Planner, router, worker, reviewer, verifier and operator roles may constrain task intent and declared capabilities, but they cannot grant permissions or select providers.
3. **Independent review is explicit.** A review binding names both the target task and the review task. The review task must use a distinct REVIEWER or VERIFIER role.
4. **Handoffs are typed.** Handoffs use the existing orchestration dependency relation vocabulary and are validated by the existing governance graph validator.
5. **Temporal remains singular.** Durable execution always resolves to the existing Temporal authority.
6. **Conductor remains bounded.** FA3 Adaptive Conductor is the native task-local adaptive graph layer; external Conductor remains optional and subject to its existing runtime admission.
7. **No direct tool/provider calls.** Blueprint-derived effects still enter through UAF/MCP/Security and provider-specific execution remains behind the existing SPI.
8. **Model and hardware neutrality.** Logical needs may be declared, but physical model/provider selection stays with Model Router and physical resource admission stays with HRB.
9. **Digest-bound provenance.** Compilation emits a SHA-256 digest over the canonical blueprint payload and injects blueprint identity/revision/digest into every generated task.
10. **Compilation is not execution.** A READY design plan does not assert Current Host runtime admission or PASS evidence.

## Blueprint shape

A `fa3.agent-application-blueprint.v1` contains:

- `blueprint_id`, `revision`, `application_id`, `task_group_id`, `objective`
- `roles[]`: task-scoped role declarations with allowed capabilities and empty authority scope
- `tasks[]`: FA3 domains/capabilities plus role assignment and existing orchestration governance fields
- `handoffs[]`: typed task-to-task edges with artifact and digest requirements
- `reviews[]`: independent target/review-task bindings
- `execution_policy`: Temporal durable authority, bounded conductor mode, UAF execution, no direct provider invocation

## Integration with the seven orchestration profiles

- **P1 Director:** consumes the compiled provider-neutral work plan and performs decomposition/routing only.
- **P2 Adaptive Conductor:** may execute bounded local adaptive subgraphs after delegation.
- **P3 Agent Workforce:** resolves specialist eligibility and anti-capabilities.
- **P4 Production Conductor:** consumes the same blueprint form for production dependencies.
- **P5 Distributed Coordinator:** may distribute already-approved tasks; no authority expansion.
- **P6 Live Cue Coordinator:** uses blueprint constraints only where latency and operator policy allow.
- **P7 Event Coordinator:** may instantiate an approved blueprint from a governed event trigger.

## Layer Guard / testőr binding

The blueprint layer is guarded at entry and exit:

- input guard rejects malformed role/task/handoff/review structures;
- role guard rejects any non-empty role authority scope;
- capability guard rejects task requirements not declared by the assigned role;
- review guard rejects self-review when independent review is declared;
- lifecycle guard requires Temporal as durable authority;
- execution guard requires UAF and forbids direct provider invocation;
- downstream Workforce/HRB/Model Router/Security/Evidence guards remain unchanged.

## External reference boundary

The structural planner/worker/reviewer and structured-handoff ideas were re-evaluated against `cporter202/agentic-ai-starters`. That repository is **not** registered as a canonical donor by this change because it was not supplied with the required `donornak` marker. No source code, dependency, API service, provider or runtime is imported or admitted from it.

## Acceptance criteria

The implementation is valid only if:

1. capability baseline remains 175;
2. architectural authority delta remains zero;
3. Temporal remains sole global durable workflow authority;
4. blueprint roles cannot grant authority or expand the specialist/provider/model/tool set;
5. handoffs use existing typed dependency validation;
6. independent review cannot self-review;
7. every generated task carries blueprint ID/revision/digest provenance;
8. runtime promotion remains separate and evidence-bound;
9. compilation can produce an existing `fa3.cross-domain-work-plan.v2`;
10. existing Workforce tests and blueprint-specific tests pass.
