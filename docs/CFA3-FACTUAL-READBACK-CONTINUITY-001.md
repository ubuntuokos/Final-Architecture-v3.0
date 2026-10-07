# CFA3 Factual Readback Continuity

**Policy:** `CFA3-FACTUAL-READBACK-CONTINUITY-POLICY-001`
**Parent governance:** `CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001`
**Capability delta:** 0
**Architectural-authority delta:** 0

## Purpose

CFA3 must never reconstruct, continue, verify or fill gaps in prior work from memory alone.

When a task depends on earlier work, the mandatory sequence is:

`TASK SCOPE -> SOURCE DISCOVERY -> FACTUAL READBACK -> STATE RECONSTRUCTION -> CONTRADICTION CHECK -> CURRENT STATE VERIFICATION -> RE-ANALYSIS -> SCOPE GUARD -> EXECUTION -> SELF VERIFICATION -> AUTHORITATIVE VERIFICATION`

Memory may only help locate the source that must then be re-read. It is never proof.

## Development enforcement

The policy is composed into the existing CFA3 Development and AI Behavior Governance layer.

Implementation:

- canonical policy: `canonical/CFA3-FACTUAL-READBACK-CONTINUITY-POLICY-001.json`
- fail-closed guard: `src/cfa3_factual_readback_guard.py`
- development-gate integration: `src/cfa3_development_ai_behavior_gate.py`
- regression tests: `tests/test_cfa3_factual_readback_guard.py`

The guard allows continuation only when:

1. the task declares whether prior state is required;
2. factual source references exist when prior state is required;
3. readback is complete;
4. re-analysis is complete;
5. current state is verified;
6. all contradictions are resolved;
7. no unknown facts remain;
8. Scope Guard passes.

Otherwise the result is `BLOCKER_STOP`.

An allow result is only a governance preflight. It does not grant effect, security, workflow, model, resource, merge or release authority.

## State reconstruction

Recovered prior information is classified explicitly:

- `REQUESTED`
- `PROPOSED`
- `APPROVED`
- `IN_PROGRESS`
- `VERIFIED`
- `BLOCKED`
- `PENDING`
- `SUPERSEDED`
- `REJECTED`
- `UNKNOWN`

A plan or approval is not automatically execution evidence.

## Source priority

When sources disagree, use the following order:

1. live deterministic system state;
2. current canonical repository state;
3. current explicit owner directive;
4. factually retrieved prior conversation or artifact;
5. prior AI statement;
6. memory.

Prior AI statements and memory cannot independently establish a CFA3 fact.

## Repository exact-state rule

Repository work that depends on prior state requires fresh verification of all directly relevant facts before mutation, including default-branch head, target head, relevant PR state, required checks, review threads, canonical files and overlapping open work.

Material drift produces `BLOCKER_STOP`.

## Gap reconstruction

Questions such as “what was missed?”, “what is still missing?” or “continue from where we stopped” trigger full factual reconstruction of the relevant source range.

Required method:

1. read the relevant primary-source range;
2. extract commitments, decisions and open items;
3. compare them with verified delivered state;
4. report only the verified delta.

Memory-based reconstruction is forbidden.

## CFA3 application projection

The Control Center surface is defined by:

- binding: `canonical/FA3-FACTUAL-READBACK-CONTROL-CENTER-BINDING-001.json`
- QML component: `apps/fa3-control-center/qml/FactualReadbackPage.qml`
- target route: `governance.factual-readback`

The page exposes:

- task scope;
- factual source set and source priority;
- readback state;
- re-analysis state;
- current-state verification;
- contradictions;
- unknown facts;
- Scope Guard result;
- continuation decision.

The GUI is a projection only. It cannot convert memory into fact, auto-resolve contradictions, bypass Scope Guard, or bypass security/effect authority.

## Current Control Center binding state

The page component and canonical binding contract are materialized, but direct edits to the shared Control Center `Main.qml` and CMake resource list are intentionally not made in this branch because currently open GUI work overlaps those files.

Per `DEV-05`, overlapping modification is a blocker and may not be bypassed by a parallel overwrite.

The binding must be applied only after the Control Center shared GUI head is reconciled and exact-state checked.

## Completion semantics

For this rule, “complete” means:

- policy exists and is composed into existing governance;
- fail-closed guard exists;
- regression coverage exists;
- development gate checks policy composition and guard behavior;
- Control Center page exists;
- application binding contract exists;
- no unknown fact is silently promoted;
- no overlapping GUI file is overwritten.

Activation of the Control Center route remains pending the overlap blocker and is not claimed as complete until that exact-state condition is cleared.
