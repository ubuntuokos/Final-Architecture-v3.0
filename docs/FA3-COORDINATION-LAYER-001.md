# FA3 Objective Coordination Layer

Date: **2026-09-25**
Profile: `FA3-COORDINATION-LAYER-001`
Capability delta: **0**
Authority delta: **0**
Current-host promotion claim: **none**

## Purpose

The Objective Coordination Layer provides a provider-neutral view across existing FA3 work items, workflows, agent workloads, application operations, approvals and artifact handoffs. It answers:

- which existing activities belong to the same high-level Objective;
- which prerequisites and handoffs connect them;
- which nodes are ready, running or blocked;
- why a node is blocked;
- which artifact/provenance references cross an application boundary;
- which correlation/causation chain explains the observed state.

It deliberately does **not** execute workflows, authorize actions, acquire resources, route models, grant secrets, move artifacts, admit providers or own evidence.

## Hardware Audit

Design-level Hardware Audit: **PASS**.

- vendor-neutral;
- CPU-only viable;
- accelerator cardinality 0..N;
- no accelerator required by default;
- no resident daemon, active polling or network dependency in the reference runtime;
- all resource admission remains with `FA3-AUTH-HOST-RESOURCE-BROKER-001`.

This is not current-host evidence.

## Authority boundaries

| Concern | Existing authority |
| --- | --- |
| authorization | `FA3-AUTH-SECURITY-GOV-001` |
| tool mediation | `FA3-AUTH-MCP-GATEWAY-001` |
| workflow execution | existing FA3 workflow authority |
| decision support | `FA3-DECISION-FABRIC-001` (bounded advisory only) |
| resource admission | `FA3-AUTH-HOST-RESOURCE-BROKER-001` |
| model routing | `FA3-AUTH-MODEL-ROUTER-001` |
| evidence | `FA3-AUTH-OBS-EVIDENCE-001` |
| secrets | existing FA3 secret authority |
| artifact transfer | existing FA3 artifact/logistics authority |

## Reused FA3 surfaces

The implementation reuses `FA3-WORK-MANAGEMENT-PROJECTION-001`, `FA3-WORK-ITEM-PROJECTION-CONTRACTS-001`, UAF, Decision Fabric, HRB and Journal/provenance references. The existing Developer Agent Coordination runtime remains scoped to developer-agent worktrees and patch integration and is not promoted into a system-wide coordinator.

## External application patterns

No external runtime is imported. The following are architectural pattern sources only:

- **Temporal** — durable history and idempotent replay semantics;
- **Dagster** — dependency/lineage graph concepts;
- **Prefect** — event/absence signals as trigger inputs, not authorization;
- **Kestra** — typed dependency relations and sequential/parallel planning;
- **Backstage** — canonical entity references and directional relations;
- **OpenTelemetry** — correlation and causation context.

No code is copied by this materialization. Any future direct code reuse still requires pinned provenance, license, security, supply-chain and admission review.

## Objective model

An Objective contains typed references to existing work. Nodes have observed states; dependencies are directional; handoffs must carry both artifact and provenance references; blockers may be explicit or derived. Required dependency cycles fail closed.

The reference runtime derives:

```text
Objective
├─ ready_node_ids
├─ running_node_ids
├─ blocked_node_ids
├─ blockers
├─ handoffs
├─ dependency_batches
└─ trace_context
```

Derived readiness is a projection. It is not authorization to run a node.

## GUI

The Control Center keeps one top-level **Work Management** surface. A child tab named **Coordination** projects Objective / Dependency / Handoff / Blocker state. It is read-only; mutating operations must continue through typed UAF intent and the existing approval/authority chain.

## Materialization plan

### Phase 1 — Reuse Discovery and architecture boundary — MATERIALIZED

- Application Intent;
- Reuse Assessment;
- explicit zero-authority decision;
- hardware/coexistence constraints;
- external pattern-source classification.

### Phase 2 — Contracts and reference core — MATERIALIZED

- Objective/node/dependency/handoff/blocker/event contracts;
- cycle rejection;
- ready-set and dependency-batch derivation;
- handoff provenance enforcement;
- replay-safe event correlation;
- fail-closed authority claims.

### Phase 3 — Work Management projection — MATERIALIZED

- Coordination child view;
- no duplicate top-level task manager;
- objective/blocker/handoff lists;
- provider-neutral projection.

### Phase 4 — Live adapters — PENDING

Adapters may be added for:

1. Work Management canonical work-item snapshots;
2. Orchestration/UAF workflow status;
3. Agent Workload status/evidence;
4. Journal/evidence event projection;
5. artifact/logistics handoff observations.

Each adapter must be read-only toward the source authority unless a separately authorized typed UAF action is submitted.

A future dedicated FA3 Task Manager and FA3 Logistics component may bind here only after their own canonical materialization/admission. The reference runtime must remain valid without them.

### Phase 5 — Current-host evidence — PENDING

Required before any production/current-host closure claim:

- real multi-component Objective scenario;
- event replay and restart recovery;
- blocker creation/resolution;
- handoff provenance round trip;
- provider disconnect/reconnect reconciliation;
- no-authority negative tests;
- CPU-only run;
- GUI projection evidence;
- rollback/cleanup evidence.

## Gate

```bash
./bin/fa3-enforce coordination
PYTHONPATH=src python -m unittest tests.test_objective_coordination -v
```

The mandatory gate is `FA3-COORDINATION-GATESET-001`.
