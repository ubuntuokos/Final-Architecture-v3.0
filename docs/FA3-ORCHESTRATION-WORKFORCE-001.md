# FA3 Orchestration Workforce — Canonical Reconciliation

Reconciled: **2026-09-23**. Capability delta: **0**. Authority delta: **0**.

The competency-driven Workforce and provider-neutral Director remain. Runtime execution now follows:

```text
deterministic eligibility -> optional bounded Decision Fabric advisory
-> typed UAF action -> policy/security -> provider discovery
-> provider-neutral hardware compatibility -> HRB admission/lease as required
-> provider adapter -> execution -> AI-COMMS validation -> evidence
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

