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

The repository gate provides deterministic positive/negative reference regressions only. It does not claim real current-host provider execution. Production promotion requires separate current-host route execution evidence and normal FA3 acceptance/promotion receipts.
