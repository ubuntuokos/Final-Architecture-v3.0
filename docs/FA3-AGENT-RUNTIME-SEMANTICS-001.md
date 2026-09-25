# FA3 Agent Runtime Semantics — ADK 2.x-derived

Canonical profile: `FA3-AGENT-RUNTIME-SEMANTICS-001`

This mandatory child profile adopts selected Google ADK 2.x execution patterns as **FA3-native semantics**. Google ADK is not an FA3 runtime dependency or architectural authority.

## Adopted mechanisms

1. Typed workflow graph: agent/function/sequential/parallel/loop/decision nodes and validated edges. YAML is import syntax only.
2. Explicit model capability descriptors from admitted provider declarations/probes; model-name heuristics are forbidden.
3. Hard execution budget ledger for model calls, tool calls, retries and transfer hops.
4. Digest-bound resume/retry: failed nodes rerun; completed nodes are reusable only with matching receipt/spec digest. Side-effecting retry/resume requires idempotency or compensation.
5. Strict tool confirmation: exact booleans plus approval receipt when confirmation is required.
6. Bounded agent transfer: pre-authorized target, mandatory reason, no self-transfer and a hop budget.
7. Relayed-output fencing: another agent's output is untrusted data, not instruction authority.
8. MCP result normalization: standard top-level fields; vendor extensions only under `_meta`.
9. Session/event integrity: existing active session, matching thread and event-id deduplication.
10. Artifact confinement: relative-path, max-size and atomic monotonic version checks.

## Runtime wiring

`src/fa3_agent_workload.py::compile_execution_plan` now compiles an admitted workload task, validated workflow graph, explicit Model Router capability descriptor and workload limits into `fa3.agent-execution-plan.v1`. The plan binds the task-spec digest and initializes the hard execution ledger. Both `agent.workload.start` and `agent.workload.resume` require an `execution_plan_ref`; a runner must not start or resume from the task specification alone.

## Not adopted

ADK runtime/orchestration authority, ADK memory/session backend authority, ADK deployment authority, automatic cross-provider model failover, LiveKit/voice integration, a parallel ADK skill registry, and a parallel ADK evidence/evaluation authority.

Temporal remains the durable workflow authority; Model Router, MCP Gateway, Security Governance, HRB, AI Comms, Journal and Evidence keep their existing authority boundaries.

## Upstream provenance

Pinned reference: Google ADK Python `v2.9.2`, commit `dafa8e952a57e8ee613008dc6b8a32acf69b853b`.
`FA3-GOOGLE-ADK2-UPSTREAM-REFERENCE-2026-09-24` is `REFERENCE_ONLY`, release-bundle `EXCLUDED`; no ADK source is vendored.

## Verification

```bash
PYTHONPATH=src python3 -m unittest tests.test_adk2_runtime_semantics -v
PYTHONPATH=src python3 src/fa3_adk2_runtime_gate.py --root .
./bin/fa3-enforce agent-workload-runtime
./bin/fa3-enforce distribution-compliance
```

Static PASS does not create a current-host runtime or global promotion claim.
