# FA3 Central Model Router runtime

`FA3-AUTH-MODEL-ROUTER-001` is the single model-routing authority. LiteLLM is its reference data plane; it is not a second authority.

Committed route policy contains logical route names only. Physical provider endpoints and model IDs are runtime state and MUST NOT be committed into `deployment/model-router/routes.json` or `deployment/litellm/config.yaml`.

The runtime provider registry is a user/current-host file, normally `~/.config/fa3/model-router/providers.json`:

```json
{
  "schema": "fa3.model-router-runtime-providers.v1",
  "providers": [
    {
      "provider_id": "FA3-PROVIDER-LM-STUDIO-MODEL-001",
      "runtime_id": "local-openai-compatible-runtime",
      "enabled": true,
      "api_base": "http://127.0.0.1:PORT/v1",
      "litellm_provider": "openai",
      "priority": 100,
      "admission_receipt": "evidence/receipts/model-manager-current-host.json"
    }
  ]
}
```

The provider ID must already have a canonical provider record delegating model routing to `FA3-AUTH-MODEL-ROUTER-001`. The admission receipt must prove that provider on the current host. The materializer probes the live `/models` catalog and selects the current physical model at service start. An optional runtime-only `preferred_models` array may express operator preference; it is not canonical policy and must never be copied into canonical route definitions.

Baseline routes are local-only. Non-loopback provider endpoints are rejected. External/cloud routing therefore requires a separate explicit policy materialization rather than a silent fallback.

The generated LiteLLM configuration and selection receipt live under the user runtime directory and are rebuilt on router restart. They are evidence, not canonical configuration.
