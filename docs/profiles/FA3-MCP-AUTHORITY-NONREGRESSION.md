# FA3 MCP Authority Non-Regression Contract

This contract freezes the authority boundary established by `FA3-AUTH-MCP-GATEWAY-001`.

## The Central MCP/Capability Gateway owns

- tool/capability registration and exposure;
- typed tool/capability invocation;
- dispatch to admitted adapters/providers;
- provider/transport mediation;
- MCP compatibility adaptation;
- enforcement at the invocation boundary;
- execution receipt emission.

## The Central MCP/Capability Gateway does not own

- durable workflow orchestration;
- security-policy authorship;
- identity lifecycle;
- durable secret storage;
- CPU/NUMA/GPU/RAM scheduling or placement;
- model/provider routing for inference;
- canonical evidence retention;
- canonical architecture governance.

## Prohibited regressions

The following are architectural failures:

1. a provider exposes a production execution path directly to an agent that bypasses the gateway;
2. a client/agent host becomes a second tool-registration or dispatch authority;
3. an MCP daemon/registry imports external entries and makes them executable without canonical admission;
4. the gateway allocates governed compute resources without HRB authority;
5. the gateway stores durable secrets as its own source of truth;
6. the gateway becomes the model-router authority;
7. the gateway becomes the durable-workflow authority;
8. a GUI marks an adapter CONNECTED without runtime E2E evidence;
9. an adapter changes canonical caller schemas to provider-specific schemas;
10. missing policy/evidence/lease requirements are treated as permissive fallback.

All such cases must fail closed in canonical gates.
