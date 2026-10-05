# FA3 Unified Action & Capability Fabric

`FA3-UNIFIED-ACTION-FABRIC-001` is the provider-neutral execution-contract layer used to converge FA3 GUI, agent, CLI, MCP, A2A and automation invocation semantics without creating a new resource, secret, identity, policy, evidence or MCP authority.

## Boundary

The canonical flow is `surface -> Action Contract -> authorization/approval -> provider compatibility -> HRB admission when required -> Secret Broker projection when required -> provider -> output validation -> evidence -> release`.

The Central MCP Gateway remains the external MCP protocol/trust boundary. Hardware Discovery remains non-authoritative. HRB remains the exclusive host resource admission, placement, reservation and lease authority. Secret Broker remains the credential projection boundary. UAF does not replace Temporal or another durable workflow authority.

## Hardware Audit compliance

Action contracts describe workload capabilities, never a global accelerator vendor or runtime. Accelerator cardinality is `0..N`; CPU-only actions require no accelerator. Physical-core requirements are distinct from logical processors. Translation backends require explicit workload/provider policy and cannot be silent fallback.

## Security

Authorization is externally owned and mandatory. Mutating/privileged approval grants are bound to principal, action/version, argument digest, context digest and expiry; a consuming approval authority must still confirm single-use consumption. Raw password/token/API-key/credential fields are rejected at the action boundary. Secret Broker projections enter providers only as ephemeral leases, and UAF evidence records only opaque lease identifiers.

## Migration

Migration is incremental. Existing providers may be wrapped with a thin `CallableProvider`/adapter while their implementation remains unchanged. Direct GUI/agent/MCP/automation execution paths are removed only after equivalent UAF routing and evidence exist. A static UAF PASS does not constitute current-host runtime promotion.

The first materialization deliberately does **not** rewrite the existing Central MCP Gateway, HRB or Secret Broker. Their authority boundaries remain unchanged while subsequent provider/surface migrations can attach to the UAF dispatcher through explicit adapters.

## Reference commands

`./bin/fa3-enforce uaf` validates the canonical UAF records and bootstrap actions.

`./bin/fa3-action list` and `./bin/fa3-action show <action>` inspect the action surface. `run` requires an explicit policy decision issued under `SECURITY_GOVERNANCE_POLICY_PLANE`; missing or mismatched authorization fails closed.

The bootstrap action set is intentionally small: `system.capabilities.list`, `system.providers.list`, and `hardware.describe`. They validate common contracts and the existing Hardware Discovery bridge without introducing a new capability or architectural authority.
