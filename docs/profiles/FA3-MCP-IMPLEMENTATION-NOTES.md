# FA3 MCP implementation sequencing

1. Preserve `FA3-AUTH-MCP-GATEWAY-001` as the only MCP/tool mediation authority.
2. Implement the loopback current-host service and health/readiness contract.
3. Load only admitted capability manifests.
4. Wire Policy Plane decisions as enforcement inputs.
5. Wire Secret Broker handles without durable credential duplication.
6. Wire HRB lease request/validation for governed execution.
7. Emit Evidence/Observability receipts for every invocation decision.
8. Connect MCP Control Chat only through the gateway.
9. Admit one low-risk current-host adapter for first E2E proof.
10. Run positive and negative regression gates before marking any adapter CONNECTED.

No step may be skipped by treating documentation, discovery or GUI presence as runtime evidence.
