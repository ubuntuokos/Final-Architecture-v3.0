# FA3 Paperclip donor intake — 2026-10-02

**Authority:** owner-explicit `donornak` registration.
**Source:** https://github.com/paperclipai/paperclip
**Scope:** canonical donor/reference registration only; no runtime, code, provider, model or control-plane admission.

## Prior FA3 materialization

Paperclip was already analyzed for FA3 orchestration governance at upstream revision `b54b2dc35c1f41d367ff4d94615ebfd38bbbdad0`. The owner-approved functional plan was materialized FA3-native by PR #571 while the upstream URL was still analysis-only.

That materialization already covers objective ancestry, boundary-based decomposition, typed dependencies, responsibility-scope monotonicity, task-bound execution claims, revision/digest-bound approvals, bounded execution budgets, liveness projection, bounded recovery, versioned configuration/rollback and the non-authoritative Orchestration Control & Monitoring surface.

This intake therefore **does not rebuild or duplicate #571**.

## Current upstream observation

The Paperclip `master` branch was observed at `144083fd481464f4a328f0d184a82263de63228d` on 2026-10-02. The repository LICENSE declares MIT. The upstream revision has advanced since the #571 analysis, but new post-#571 features are not automatically adopted by this intake.

## Canonical use boundary

The exact repository is registered as `FA3-DONOR-PAPERCLIPAI-PAPERCLIP-001` with status `ACCEPTED_REFERENCE`.

This intake does not:

- install Paperclip or its dependencies;
- copy Paperclip source code;
- adopt Paperclip runtime, scheduler or control plane;
- admit a provider, model, service or secret-storage authority;
- create a second durable workflow authority;
- create a donor usage edge;
- change the fixed capability baseline of 175;
- claim Current Host PASS.

Temporal remains the sole global durable workflow lifecycle authority. HRB, Model Router, Security/UAF/MCP, Secret Broker and Evidence/Gate retain their existing boundaries.

## Required post-publication reconciliation

FA3 planning and finalization consume only the finalized published donor database. Therefore the canonical usage edge for the already materialized #571 Paperclip-derived architecture patterns must be created **after** this donor intake is published on `main`.

That follow-up must:

1. create a fresh Reuse Assessment bound to the published-main registry snapshot containing Paperclip;
2. record one canonical `ARCHITECTURE_PATTERN` donor-usage edge to `FA3-ORCHESTRATION-WORKFORCE-001`;
3. update the #571 analysis-only Paperclip boundary records to reflect canonical donor registration without changing runtime/authority semantics;
4. preserve capability baseline 175 and authority delta 0;
5. run the normal donor/application/reuse/release gates.

Parent published main: `536bacedbebcd25ce80fe29cead523c7e890bc82`
Parent registry blob: `67795f00d5f7d801978bd6d4f92006b5412fe9ee`
Parent donor count: **1354**
Proposed donor count: **1355**
Capability baseline: **175**
Capability delta: **0**
Authority delta: **0**
