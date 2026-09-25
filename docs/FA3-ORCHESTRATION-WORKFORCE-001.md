# FA3 Orchestration Workforce — Canonical Reconciliation

Reconciled: **2026-09-23**. Capability delta: **0**. Authority delta: **0**.

The competency-driven Workforce and provider-neutral Director remain. Runtime execution now follows:

```text
deterministic eligibility -> optional bounded Decision Fabric advisory
-> typed UAF action -> policy/security -> provider discovery
-> provider-neutral hardware compatibility -> AgentWorkloadTask
-> FA3-AGENT-WORKLOAD-RUNTIME-001 task-local execution projection
-> HRB admission/lease as required -> admitted runner adapter
-> execution -> AI-COMMS validation -> Journal/Evidence
```

Key invariants:

- Temporal remains the sole global durable lifecycle authority.
- HRB is a horizontal resource authority, **not** a workforce specialist/provider.
- Hardware discovery is provider-neutral, accelerator cardinality is 0..N, and CPU-only hosts remain valid.
- Agent/GUI/CLI/MCP/A2A/automation direct provider bypass is forbidden; execution enters through `FA3-UNIFIED-ACTION-FABRIC-001`.
- Decision Fabric is advisory only after deterministic eligibility and cannot expand the candidate set.
- Model Router remains the sole model/provider/runtime routing authority.
- Model/agent communication must satisfy `FA3-AI-COMMS-001`; private model language, emergent codebooks and model-only slang are forbidden.
- Providers cannot expand the application's authorized AI participant set.
- External provider runtime admission requires a scope-bound `CURRENT_HOST_PRODUCTION_E2E_PASS` receipt with runtime identity. Static `runtime_promotion_status` is informational only.
- CrewAI, Conductor, Open Multi-Agent, LangGraph, Kestra, Pipecat, n8n and Haystack remain `PENDING_CURRENT_HOST`; this reconciliation makes no runtime promotion claim.

Canonical UAF actions: `orchestration.plan`, `orchestration.delegate`, `orchestration.execute`, `orchestration.cancel`, `orchestration.resume`, `orchestration.inspect`.

The media reference plan no longer routes a fake HRB specialist task; resource requirements are carried horizontally to Hardware Discovery/HRB.
## Distribution boundary

CrewAI, Conductor, Open Multi-Agent, LangGraph, Kestra, Pipecat, n8n and Haystack are classified `USER_LOCAL_EXTERNAL` and are excluded from the FA3 product bundle. This classification does not grant runtime admission; current-host admission remains a separate evidence-bound decision.



## Agent Workload Runtime reconciliation — 2026-09-24

The Orchestration Director still decomposes and routes work but does not execute providers directly. A ROUTED decision can be compiled into an immutable `fa3.agent-workload-task.v1` only through the Agent Workload Runtime contract. This runtime is task-local and non-authoritative; Temporal remains the sole global durable lifecycle authority. Workload runner selection cannot expand the already-eligible provider set and production execution requires runtime admission plus the existing Security/UAF/HRB boundaries.
