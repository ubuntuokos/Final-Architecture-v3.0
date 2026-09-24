# FA3 Credential-Aware Provider Execution

This materialization adds no capability and no architectural authority. `FA3-AUTH-MODEL-ROUTER-001` remains the only provider/model routing authority and `FA3-LLM-GATEWAY-001`/LiteLLM remains the single data plane.

## Clean-room source boundary

The architecture review used `lbjlaq/Antigravity-Manager` at commit `6af75a4aa3de192a0916385a4a6398124e7e8cc1` as a reference source. Its CC BY-NC-SA 4.0 licensing is incompatible with the intended commercial FA3 distribution for direct code/asset/runtime integration. No upstream source, test, asset or runtime dependency is imported. FA3 independently implements the derived requirements.

## Execution boundary

The Model Router first forms the admitted provider/model candidate set. This projection may then choose only among opaque `SecretReference` handles already eligible for that selected provider. Session affinity may retain an eligible credential. Rate limit, quota, auth and transient provider failure can trigger an intra-provider rebind. When no same-provider credential remains eligible, the only permitted result is `MODEL_ROUTER_REEVALUATION_REQUIRED`; this projection never silently selects another provider.

## Protocol compatibility

`FA3-LLM-PROTOCOL-COMPAT-001` normalizes OpenAI, Anthropic and Gemini protocol semantics behind the existing LLM gateway. Silent tool-schema stripping is forbidden. Security-relevant or tool-semantic loss fails closed unless an existing caller policy explicitly authorizes a declared non-security degradation.

## Secrets

Raw provider credentials remain exclusively under `FA3-SECRET-BROKER-001`. Canonical state, logs, Decision Fabric inputs, GUI state and evidence may contain only opaque references or SHA-256 identifiers of those references.

## Evidence

The repository gate provides deterministic positive/negative reference regressions and a fail-closed current-host producer. It does not claim real current-host provider execution by itself.

The real current-host producer is `bin/fa3-model-router-provider-execution-current-host.py`. It accepts only a loopback provider instance already proven by an existing current-host provider-admission receipt, requires existing admitted Secret Broker current-host evidence, plus live broker health and live `SecretReference` projection, and requires at least two distinct `SecretReference` credentials projected directly through the policy-bound Secret Broker Unix socket. The provider probe does not rerun the full Secret Broker LUKS/systemd/rekey qualification; that subsystem is already current-host admitted and its durable evidence is reused fail-closed. Before a PASS is possible, an intentionally invalid bearer credential must be rejected with HTTP 401 or 403; an endpoint that ignores credentials (for example an unauthenticated local provider) cannot prove credential failover. It performs real provider requests before and after a deterministic rate-limit state-machine injection so the intra-provider rebind is exercised without fabricating a provider failure. Direct provider access in this script is evidence-harness-only and is not an application routing path.

The workflow may consume an externally staged live-probe receipt or create one from `FA3_PROVIDER_EXECUTION_CURRENT_HOST_CONFIG`. If neither is available it fails closed. Raw credentials are never written to canonical state or evidence; temporary Secret Broker projections are removed before `rollback_pass` can be asserted.

Production promotion still requires a real current-host PASS plus the normal FA3 acceptance/promotion receipts. A repository/reference PASS never upgrades current-host or global production status.

## Physical credential provisioning

Credential-bearing closure is intentionally not auto-provisioned from CI. The generic harness remains available for any already-admitted loopback Bearer-authenticated provider, but OpenAI now has an explicit bounded current-host evidence adapter.

For OpenAI, the operator runs only:

```bash
sudo bash bin/fa3-openai-provider-execution-current-host-close.sh
```

The wrapper starts a transient loopback-only adapter for `FA3-PROVIDER-OPENAI-API-001`, verifies that a deliberately invalid Bearer token is rejected by the real OpenAI upstream, writes a current-host adapter admission receipt, and then invokes the generic provider-execution provisioning harness. By default no model is hard-coded: after Credential A is projected, the probe resolves relative endpoint paths against the admitted `/v1` API base, reads that API project's live `/v1/models` catalog, and tries bounded chat candidates until the fixed FA3 Chat Completions probe succeeds. The selected physical model is then reused unchanged with Credential B for the rebind proof. `FA3_OPENAI_PROBE_MODEL` remains an optional operator override and fails closed if that model is not visible to the project.

The adapter is evidence-scope only. It does not enable normal application routing, does not alter baseline local routes, and does not create a local-to-cloud fallback. External egress is bounded by `FA3-OPENAI-API-EXTERNAL-POLICY-001` to `https://api.openai.com/v1` for `GET /v1/models` and `POST /v1/chat/completions`. The bridge accepts only fixed FA3 provider-execution probe content.

Before asking for credentials, the generic harness starts the already-installed production Secret Broker lifecycle if needed and validates the durable admitted current-host Secret Broker reference. It does not invoke the heavyweight Secret Broker current-host qualification helper.
The Secret Broker prerequisite was requalified on 2026-09-24 and is active through `evidence/reference/secret-broker-current-host-2026-09-24.json`. The historical `2026-09-21` reference remains provenance only and is explicitly denied as an active prerequisite. Provider execution is therefore unblocked at the secrets prerequisite boundary, but real OpenAI provider-execution PASS is still withheld until the two-credential physical E2E and cleanup-bound gate complete.

Before the live Secret Broker lifecycle is started, the provisioning harness also requires the production vault artifacts `/var/lib/fa3/state/fa3-machine-state.img` and `/etc/credstore.encrypted/fa3-machine-state-key.cred`. Durable current-host admission proves that the Secret Broker implementation can run on this host; it does not initialize the operator's persistent production vault. If those artifacts are absent, provisioning fails immediately with the one-time initializer command instead of waiting on a systemd dependency timeout.

The generic harness reads both credential values only from `/dev/tty`, stores them temporarily under the Secret Broker as distinct `SecretReference` objects, restricts projection to a dedicated transient probe identity/unit, and preflights both credentials independently against the admitted provider before model discovery. A failed HTTP preflight reports only the credential label, HTTP status, and strictly sanitized provider `error.type` / `error.code`; provider `error.message`, response bodies, headers, and credential material are never logged. OpenAI-style terminal billing/quota blockers such as `credit_balance_exhausted`, organization/project spend-limit exhaustion, or organization usage-limit exhaustion stop chat-model probing immediately rather than retrying other models. Only if both preflights pass and provider execution is not externally billing-blocked does the harness perform the real before/after-rebind provider calls and write the secret-free live probe to `/run/fa3/model-router-provider-execution/current-host-source.json`. Temporary credential objects, policies, probe identity/runtime files, and any Secret Broker lifecycle started by the harness must be cleaned before collection/gating. `FA3 PROVIDER EXECUTION CURRENT-HOST: PASS` is withheld unless `provisioning_cleanup_pass` is proven. An unauthenticated provider endpoint cannot satisfy the gate.
