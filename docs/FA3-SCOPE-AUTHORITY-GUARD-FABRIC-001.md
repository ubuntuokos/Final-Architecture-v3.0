# FA3 Scope & Authority Guard Fabric (Testőr)

Status: **STATIC MATERIALIZATION / P0 / MUST**. Capability delta **0**, architectural-authority delta **0**. Current-host or production promotion is **not** claimed.

## Purpose

Every governed FA3 actor must remain inside an explicit contract. Technical ability never implies permission. Unknown actor, unknown intent, scope expansion, forbidden delegation and unauthorized side effects fail closed.

The guard is not a scheduler, model router, resource broker, security authority, tool gateway or evidence authority. It enforces the already-canonical boundaries of Temporal, UAF/MCP, Security Governance, HRB, Model Router and Evidence/Gate.

## Runtime chain

```text
objective/task
  -> orchestrator scope guard
  -> workforce hard filters
  -> delegation guard
  -> provider/conductor projection
  -> layer/action guard
  -> UAF + Security + domain authority
  -> executor
  -> independent Evidence/Gate
```

The Orchestration Director may plan, route, split, delegate, aggregate and boundedly replan. It cannot self-authorize security, allocate/lease host resources, route models/providers, directly execute tools or verify its own result.

A provider or Conductor projection is rechecked against the selected specialist's domain, capabilities, anti-capabilities and authority scope. Provider capability does not expand FA3 authority.

## Task Authority Envelope

The executable guard accepts `fa3.task-authority-envelope.v1` with actor, intent, requested authorities, target actor when delegating, parent scope and side-effect class. The returned decision is only an enforcement result; `execution_authority=false` always. Real effects still require UAF/Security and the relevant canonical domain authority.

## State transition rule

Replan, retry, recovery and fallback may preserve or reduce scope but cannot expand it. A new larger scope requires a new upstream authorization path; it cannot be manufactured by an orchestrator or provider.

## Reuse and donor binding

The approved Reuse Assessment is tied to published donor registry blob `7e900cac93936d2f319e132def4c172b2a415d4d` (1233 entries). This materialization imports no external donor code; it reuses native FA3 contracts and already-admitted architectural patterns.

## Verification

```bash
PYTHONPATH=src python3 -m unittest tests.test_scope_authority_guard -v
./bin/fa3-enforce scope-authority-guard
```

Static PASS does not claim current-host runtime promotion or independent final evidence closure.
