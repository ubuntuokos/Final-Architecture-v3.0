# FA3 Orchestration Workforce — Canonical Materialization

**Profile:** `FA3-ORCHESTRATION-WORKFORCE-001`  
**Decision:** `FA3-DEC-ORCHESTRATION-WORKFORCE-2026-09-15`  
**Priority:** P0 / MUST  
**Capability delta:** 0  
**Authority delta:** 0

## Decision

FA3 uses a **hierarchical, competency-driven orchestration workforce**, not a universal orchestrator. The FA3-owned Orchestration Director classifies and decomposes work, applies hard competency/authority filters, delegates each part to the best eligible specialist, and escalates ambiguity or consequential conflicts to the human decision authority.

The Director is deliberately **non-authorizing**. It cannot grant itself or a provider security, resource, model, tool, durable-workflow, evidence or registry authority.

## Authority invariants

- **Temporal remains the sole global durable workflow lifecycle authority.**
- **FA3 HRB + ACCEL-GUARD remain host-resource and accelerator-conflict authority.** ACCEL-GUARD remains recommendation-first unless an explicit prior user policy authorizes automatic action.
- Security/policy, MCP/tool mediation, model routing, human approval, evidence/provenance and canonical registry ownership remain existing horizontal FA3 authorities.
- External orchestration frameworks are specialist providers. A provider cannot expand its authority through routing.
- Provider-native workflow/agent schemas are not canonical FA3 IR.
- Current-host runtime promotion requires executable evidence. Design acceptance alone never enables a pending provider.

## Workforce

| Domain | Specialist | Provider / authority |
|---|---|---|
| Durable lifecycle | Durable Lifecycle Manager | Temporal |
| Role-based teams | Role Team Manager | CrewAI |
| Media creative coordination | Media Production Director | FA3-owned + CrewAI adapter |
| Adaptive/media batch jobs | Adaptive Job Graph Manager | Conductor |
| Governed agent teams | Governed Agent Team Manager | Open Multi-Agent |
| Stateful/cyclic agent graphs | Stateful Agent Graph Manager | LangGraph |
| Event/media ingest | Event & Ingest Pipeline Manager | Kestra |
| Realtime multimodal | Realtime Multimodal Manager | Pipecat |
| Integration/business automation | Integration Manager | n8n |
| Knowledge/RAG/context | Knowledge Manager | Haystack |
| CPU/GPU/NPU/RAM/VRAM/NUMA | Resource Governance | FA3 HRB + ACCEL-GUARD |
| Heavy ETL/data DAG reserve | Heavy Data Batch Reserve | Airflow, disabled reserve |

## Selection pipeline

```text
work request
  -> domain classification
  -> decomposition
  -> anti-capability filter
  -> authority-scope filter
  -> security/policy eligibility
  -> current-host/runtime eligibility
  -> deterministic competency ranking
  -> specialist + ordered fallbacks
  -> human escalation on ambiguity/no eligible specialist
```

Hard filters run before scoring. An LLM may propose classification or decomposition, but it cannot override a hard filter or create authority.

## Media split

```text
FA3 Director
  -> Media Production Director / CrewAI: creative planning and specialist team
  -> Conductor: bounded transcode/render job graph
  -> Kestra: file/event ingest and pipeline dispatch
  -> Pipecat: realtime voice/avatar stream
  -> HRB + ACCEL-GUARD: accelerator admission/conflict decision
  -> Temporal: durable lifecycle when required
```

The Media Production Director is intentionally prohibited from GPU placement, security policy, canonical registry ownership and global durable-workflow authority.

## Executable reference

```bash
PYTHONPATH=src python src/fa3_orchestration_workforce.py \
  --root . \
  --request examples/orchestration-workforce-media.json

./bin/fa3-enforce orchestration-workforce
```

Runtime routing is fail-closed for providers whose current-host evidence is pending:

```bash
PYTHONPATH=src python src/fa3_orchestration_workforce.py \
  --root . \
  --request examples/orchestration-workforce-media.json \
  --runtime
```

## Gate coverage

The canonical gate checks the 143-capability baseline, absence of new architectural authority, provider-neutral Director, Temporal durable-authority singularity, HRB/ACCEL-GUARD resource-authority singularity, provider anti-capabilities, deterministic routing, negative GPU-authority tests, pending-provider runtime fail-closed behavior, and the cross-domain media decomposition.

## Runtime status

This materialization establishes **design/canonical conformance only**. CrewAI, Conductor, Open Multi-Agent, LangGraph, Kestra, Pipecat, n8n and Haystack remain `PENDING_CURRENT_HOST` until their actual FA3 adapters and executable current-host conformance evidence are produced. No document or CI-only reference test promotes them.
