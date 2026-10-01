# FA3 Universal Agent Harness & Interoperability — Phase A research and coverage

Date: 2026-10-01
Status: **RESEARCH_ONLY / OWNER_REVIEW_REQUIRED**
FA3 comparison base: `dfb9ab7d8a3e192908bc2fb0f57c6aefed1d7bee` on `main`
Capability baseline: **175 fixed**
Capability delta: **0**
Architectural authority delta: **0**

## 1. Approved scope

This file materializes only the approved **PHASE A / WP0–WP2** work:

1. upstream source freeze;
2. deep capability extraction;
3. reconciliation against the current FA3 architecture.

This change does **not**:

- modify a canonical authority;
- add a top-level capability;
- register a donor;
- import upstream code;
- add a runtime dependency;
- admit a provider/model/harness;
- activate Omnigent;
- modify Current Host runtime semantics;
- claim physical Current Host PASS.

Repository policy requires a user-supplied source link preceded by the literal owner marker `donornak` before canonical Donor & Reference Registry registration. The sources below are therefore **analysis-only research inputs** in Phase A.

Machine-readable extraction:
`research/universal-agent-harness-phase-a-coverage-2026-10-01.json`

## 2. Architecture decision retained

Omnigent is **not** proposed as an FA3 core runtime or authority.

The intended future architecture remains:

```text
FA3 Orchestrator
      |
   Conductor
      |
   Temporal                 <- sole global durable lifecycle authority
      |
Agent Workload Runtime
      |
Universal Agent Harness Contract
      |
+-----+--------+-----------+-----------+
|              |           |           |
Native         ACP      Omnigent    OpenHands / future
|              |           |           |
+--------------+-----------+-----------+
               |
              UAF
               |
Security / Scope & Authority Guard
               |
MCP Gateway / Model Router / HRB / Secret Broker
               |
Journal / Evidence
```

Protocol roles remain intentionally distinct:

```text
ACP = client <-> agent
A2A = agent  <-> agent
MCP = agent  <-> tool/resource
```

None of these protocols becomes an authorization, resource, routing, secret, evidence or durable-workflow authority.

## 3. Frozen upstream research sources

| Source | Exact researched HEAD | Upstream licence declaration | Phase A role |
|---|---|---|---|
| `omnigent-ai/omnigent` | `8a71f9003e0dbedb1eaada37a39be827f44174e1` | Apache-2.0 | meta-harness, policy, session and sandbox patterns |
| `agentclientprotocol/agent-client-protocol` | `9e032156545412be9bba5e092f12d0080c499b6d` | Apache-2.0 | client-agent interoperability |
| `a2aproject/A2A` | `c0e13ef67ec386ab304acbf60952f09cdc70bd66` | Apache-2.0 | agent-agent interoperability |
| `pydantic/pydantic-ai` | `dac0464672d09272a11065bbe84201e9ae67167e` | MIT | deferred actions, typed tools, durability patterns |
| `langchain-ai/langgraph` | `b36b1d58a8b408455b512cfad3b1b26e02927282` | MIT | interrupt/checkpoint graph patterns |
| `microsoft/agent-framework` | `f1fb145c4d80191aa86b3480d12112d828233763` | MIT | workflow checkpoint, approval and session persistence |
| `cedar-policy/cedar` | `2cfa86bab4776d587e96e8da43a37fc44622411a` | Apache-2.0 | typed authorization pattern |
| `open-telemetry/semantic-conventions` | `70550277d98a01ca3fe83bcfc3a2dac18a0d98b7` | Apache-2.0 | GenAI observability interchange |
| `letta-ai/letta` | `5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a` | Apache-2.0 | agent/conversation/memory separation |
| `OpenHands/software-agent-sdk` | `0a9abc87641ad7ffe02e2dadf5e2cb3976b35217` | MIT | existing developer-agent + ACP-related reference |
| `temporalio/sdk-python` | `65fecc416588151b65e62495d76015778124dd8d` | MIT | existing durable workflow authority implementation reference |

The licence column records only the repository's upstream declaration at the frozen identity. It is **not** FA3 License & Rights clearance for source reuse, dependency adoption, bundled code, model/data use, hosted services or redistribution.

## 4. Research findings

### 4.1 Omnigent

The strongest reusable pattern is the separation of **agent configuration from harness runtime**. A harness can be switched while tools, policies, prompts and model intent remain largely stable.

Useful concepts:

- runtime/harness switching;
- declarative agent configuration;
- contextual policy composition;
- persistent sessions;
- sub-agent execution;
- harness registration;
- direct versus native execution modes;
- separate cloud/placement sandbox from OS access policy;
- per-harness capability/conformance expectations.

Important FA3 rejection:

Omnigent's OS sandbox documentation explicitly states that MCP subprocesses are outside that sandbox. FA3 must **not** inherit that boundary. MCP/tool subprocess execution must remain canonically mediated and, where agent-controlled code executes, covered by the FA3 containment contract.

### 4.2 ACP

ACP v2 supplies a useful client-agent protocol surface including:

- session creation;
- session resume/replay;
- cancellation;
- permission requests;
- client/agent capabilities;
- streaming session updates.

FA3 already owns execution, approval and durable lifecycle semantics. ACP therefore fits only as a **wire/projection adapter**.

### 4.3 A2A 1.0

A2A contributes a useful interoperable data model:

- AgentCard;
- Task;
- Message;
- Artifact;
- Part;
- streaming status/artifact events;
- long-running asynchronous task continuation.

The strongest semantic improvement for FA3 is explicit:

```text
Message != Artifact
```

Communication must not be confused with produced output/evidence.

The existing UAF already names A2A as an adapter surface, so Phase A does **not** propose a second A2A business-logic layer.

### 4.4 Pydantic AI

The most valuable new pattern is **Deferred Action**:

```text
REQUESTED
 -> DEFERRED
      -> WAITING_APPROVAL
      -> WAITING_EXTERNAL
      -> WAITING_RESOURCE
      -> WAITING_DEPENDENCY
      -> WAITING_USER_INPUT
 -> RESUMED
 -> COMPLETED / FAILED / CANCELLED
```

Pydantic AI also emphasizes stable tool identity through wrappers/deferred/durable execution. Its pluggable durable backends are not adopted as architecture: FA3 already assigns durable lifecycle ownership to Temporal.

### 4.5 LangGraph

Interrupt/resume and checkpointing are already substantially covered by FA3. The remaining research value is narrower:

- nested/subgraph checkpoint behavior;
- explicit distinction between inherited and disabled persistence;
- controlled state-fork/time-travel concepts if they can be represented without creating a second durable lifecycle authority.

### 4.6 Microsoft Agent Framework

Two useful patterns are not yet fully explicit in FA3:

1. checkpoint persistence that retains pending approval/session state;
2. strict session-scope isolation on resume, including nested/pending request correlation.

These should strengthen existing FA3 contracts rather than create another workflow engine.

### 4.7 Cedar

The useful authorization abstraction is:

```text
Principal + Action + Resource + Context
```

For FA3 this should be extended with capability, delegator, scope, revision/digest, budget, expiry and approval receipt.

FA3 remains fail-closed. The proposed Phase B semantics are:

```text
DENY > ASK > ALLOW
ERROR / UNKNOWN / MALFORMED / UNRESOLVED => DENY
```

Cedar itself is only a pattern source at this stage.

### 4.8 OpenTelemetry GenAI semantic conventions

FA3 currently has internal Journal/Evidence semantics but no explicit GenAI semantic-convention exporter.

Future direction:

```text
FA3 Journal / trace
        |
privacy + redaction
        |
OpenTelemetry GenAI projection
```

Observability remains non-authoritative:

```text
telemetry != canonical evidence
```

### 4.9 Letta

Letta gives a useful state-separation pattern:

- persistent agent identity;
- multiple conversations per agent;
- long-term memory;
- run/step identity.

FA3 should **not** adopt Letta as memory authority. The useful result is a canonical ownership distinction:

```text
Run      -> Temporal/execution state
Session  -> interaction/session state
Memory   -> existing Memory Governance
Evidence -> canonical Evidence Authority
```

### 4.10 OpenHands and Temporal

These are primarily **reuse**, not new work.

Existing FA3 OpenHands enforcement already covers append-only execution trajectories, crash-safe resume and no side-effect replay.

Temporal is already the sole FA3 global durable lifecycle authority. No alternate durability authority is proposed.

## 5. Coverage result

39 extracted capability candidates were reconciled.

| Disposition | Count | Meaning |
|---|---:|---|
| `ALREADY_COVERED` | 8 | existing FA3 semantics can be mapped without reopening the closed component |
| `PARTIALLY_COVERED` | 21 | existing foundation exists; only a contract/adapter/invariant delta is required |
| `MISSING` | 8 | useful capability surface is not currently explicit |
| `CONFLICT` | 1 | upstream pattern conflicts with an exclusive FA3 authority |
| `REJECT` | 1 | upstream behavior is unsuitable and becomes a negative-test lesson |

### 5.1 Main missing surfaces

The eight currently classified `MISSING` items are:

1. universal harness capability descriptor;
2. per-harness assurance/conformance layer;
3. explicit ACP custom-harness compatibility contract;
4. ACP client-agent capability negotiation mapping;
5. A2A AgentCard projection;
6. generic FA3 Deferred Action Contract;
7. OpenTelemetry GenAI exporter;
8. GenAI standard attribute projection.

These are **not eight new top-level FA3 capabilities**. Phase A finds that they can be implemented as contracts/adapters/sub-capability semantics under the existing 175 model.

### 5.2 Conflict

Pydantic AI's general multi-backend durability abstraction is useful as implementation research but conflicts with FA3 if interpreted as allowing multiple global durable lifecycle authorities.

Disposition:

`REFERENCE_ONLY / TEMPORAL_REMAINS_SOLE_GLOBAL_DURABLE_LIFECYCLE_AUTHORITY`.

### 5.3 Rejected upstream behavior

Omnigent's MCP-process-outside-primary-OS-sandbox boundary is rejected for FA3.

The useful outcome is a future negative requirement:

`AGENT_SANDBOX_CANNOT_BE_CLAIMED_COMPLETE_WHILE_AGENT_CONTROLLED_MCP_CHILD_EXECUTION_ESCAPES_REQUIRED_CONTAINMENT`.

## 6. Existing FA3 coverage that must not be rebuilt

### Agent Workload Runtime

Already provides:

- typed workload/task/workspace;
- runner SPI;
- execution network envelope;
- checkpoint modes;
- fresh HRB admission on resume;
- provider-neutral execution plan;
- direct model/provider/tool bypass prohibition.

Default action: **extend, do not reopen**.

### Agent Runtime Semantics

Already provides:

- typed workflow graph;
- model capability descriptor;
- hard execution budgets;
- digest-bound resume/retry;
- strict tool confirmation;
- bounded agent transfer;
- relayed-output fencing;
- MCP normalization;
- session/event integrity;
- artifact confinement.

Default action: **ALREADY_COVERED mapping or narrow extension**.

### UAF

Already exposes GUI/agent/CLI/MCP/**A2A**/automation as adapters and preserves existing authority boundaries.

Default action: use UAF as the action semantics layer; ACP/A2A are protocol projections only.

### Agent Federation

Already provides:

- signed, time/replay/hop-bounded envelopes;
- delegation budget narrowing;
- coordination claims;
- remote admission chain;
- local versus true cross-host evidence distinction.

Default action: A2A must be an interoperability binding on top, not a replacement.

### Agent Sandbox

Already separates resource/placement authority from security confinement and is fail-closed.

Default action: preserve this stronger boundary and use Omnigent's sandbox gaps only as negative-test input.

## 7. Near-closure/open-PR protection

### PR #557 — Scope & Authority Guard

Current status at research time: **OPEN / DRAFT**.

Recommended Phase B insertion point:

- typed authorization envelope;
- DENY/ASK/ALLOW precedence;
- malformed/error/unresolved => DENY;
- nested approval propagation;
- monotonic delegated scope narrowing.

No second policy authority.

### PR #556 — Objective Coordination & Dependency Intelligence

Current status: **OPEN / DRAFT**.

Recommended Phase B insertion point:

- `DEFERRED`;
- `WAITING_EXTERNAL`;
- `WAITING_APPROVAL`;
- `WAITING_RESOURCE`;
- resumability awareness.

It remains zero-authority coordination intelligence.

### PR #573 — Provider / Model / Gateway Assurance

Current status: **OPEN / non-draft**.

Do not destabilize it with the entire harness work.

Recommended action: separate follow-up **Harness Assurance Extension** after Phase B/C approval.

### PR #559 — Current Host 175/525

Current status: **OPEN**.

Phase A creates no runtime delta.

Do not add Omnigent, ACP, A2A or new harness runtime qualification to #559 before its current 175/525 physical reconciliation is complete. Later runtime adapters receive delta-scoped Current Host qualification.

## 8. Proposed Phase B input

If the owner approves Phase A findings, the next approved scope should be limited to:

### B1 — Donor capability processing contract

Extend the existing donor lifecycle concept so every *registered/adopted* donor capability eventually receives one of:

- `ADOPT_FA3_NATIVE`;
- `ADAPT`;
- `ALREADY_COVERED`;
- `REFERENCE_ONLY`;
- `REJECT`.

No `IGNORE` terminal state.

This Phase A research set itself remains outside the canonical donor graph until the repository's explicit owner-marker requirement is satisfied.

### B2 — #557-compatible authority semantics

Design only:

- authorization envelope;
- verdict composition;
- nested approval propagation.

### B3 — #556-compatible deferred coordination semantics

Design only:

- deferred/waiting states;
- no execution authority.

### B4 — Universal Harness contract design

Prepare the contract schema and assurance requirements, but runtime adapters stay for a later approved phase.

## 9. Closure protection rule

For every affected merged component:

```text
ALREADY_COVERED
    -> evidence mapping, no reopen

PARTIAL + interface only
    -> follow-up extension

runtime compatibility only
    -> adapter

missing canonical invariant
    -> REOPEN_REQUIRED, owner decision
```

A merged component is never reopened merely because an upstream donor uses different terminology or packaging.

## 10. Phase A conclusion

The research supports the planned direction:

**Do not integrate Omnigent as an FA3 core runtime.**

Instead, use the researched projects to define an FA3-native **Universal Agent Harness & Interoperability** layer above the already-materialized Agent Workload Runtime/UAF authorities.

The largest architectural gain can be obtained with a relatively small set of missing contracts:

- universal harness descriptor + assurance;
- ACP compatibility;
- A2A AgentCard/output mapping;
- deferred action state;
- explicit Run/Session/Memory/Evidence ownership;
- versioned OpenTelemetry GenAI projection.

No evidence found in Phase A requires changing the fixed 175 capability baseline.

**STOP:** Phase B implementation/design changes require explicit owner approval.
