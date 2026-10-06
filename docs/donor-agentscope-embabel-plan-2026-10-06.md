# CFA3 AgentScope + Embabel donor intake — 2026-10-06

## Scope

This source-intake records the exact 14 external sources substantively processed by the owner-approved CFA3 AgentScope–Embabel integration plan. The plan, donor assessment and owner approval binding are already canonical on protected main through PR #725.

This PR is donor/reference intake only. It does not implement the application, copy upstream code, install dependencies, activate AgentScope or Embabel runtimes, admit providers/models, create usage edges, change hardware, or claim Current Host PASS.

## Exact parent

- main: `5c6333e48fd992df9dcd225c1a52dba0eb5c827b`
- registry blob: `2bb6a74dd415b6374e4a6d5adce1bc9265229b63`
- registry count: **1792**
- proposed count after finalizer publication: **1806**
- capability baseline: **175**
- authority delta: **0**
- usage-edge delta: **0**

## Authorization

Registration is bounded by:

- `canonical/decisions/FA3-DEC-IMPLEMENTATION-PLAN-DONOR-EXCEPTION-2026-10-04.json`
- `canonical/decisions/CFA3-DEC-AGENTSCOPE-EMBABEL-PLAN-APPROVAL-2026-10-06.json`
- `canonical/assessments/CFA3-AGENTSCOPE-EMBABEL-DONOR-REUSE-ASSESSMENT-2026-10-06.json`
- `docs/CFA3-AGENTSCOPE-EMBABEL-INTEGRATION-PLAN-2026-10-06.md`

Only the exact approved processed donor-key set may be registered.

## Boundaries

AgentScope and Embabel remain references/providers/pattern sources, never CFA3 authorities. Temporal, UAF, Security Governance, HRB, Model Router, Central MCP Gateway, Secret Broker, Journal and Evidence/Gate retain their canonical authority. Organization records are discovery indexes only. The legacy `agentscope-runtime` source is retained as migration/history reference; the active upstream direction remains AgentScope 2.0.

Application execution remains blocked until the donor set is published in the canonical registry and fresh reuse/adoption/overlap gates pass.
