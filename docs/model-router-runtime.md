# FA3 Central Model Router runtime

`FA3-AUTH-MODEL-ROUTER-001` is the single model-routing authority. Clients request stable **logical routes**; they do not select Ollama, LM Studio, llama.cpp, an OpenAI-compatible server, a concrete model name, or a model file path.

## Authority split

- **Model Manager / admitted provider adapters:** publish the current-host provider catalog: what runtime/model projections exist, are admitted, and are currently available.
- **Model Router:** filters the catalog against route requirements and policy, selects the current provider/runtime/model, and emits the route-resolution receipt.
- **Host Resource Broker:** remains the placement/admission/lease authority whenever accelerator or bounded resource execution requires it.
- **LiteLLM:** is the reference **data plane**. It provides authenticated OpenAI-compatible transport/normalization, but its running configuration is generated from the Model Router resolution. It is not a second routing authority.
- **Clients such as PageIndex:** submit only `fa3-pageindex-index`, `fa3-pageindex-reason`, or another admitted logical route.

## No fixed backend/model

The canonical route manifest is `deployment/model-router/routes.json`. It intentionally contains no provider ID, endpoint, runtime, or physical model name. Physical bindings exist only in the current-host provider catalog and the generated runtime resolution/configuration.

A provider catalog uses schema `fa3.model-router.provider-catalog.v1`. Example shape:

```json
{
  "schema": "fa3.model-router.provider-catalog.v1",
  "provider_neutral": true,
  "producer": "FA3-MODEL-MANAGER-001",
  "candidates": [
    {
      "candidate_id": "runtime-instance-1",
      "provider_id": "an-admitted-provider-id",
      "runtime": "OPENAI_COMPATIBLE",
      "model_id": "runtime-visible-model-id",
      "litellm_model": "provider-prefix/runtime-visible-model-id",
      "api_base": "http://127.0.0.1:<runtime-port>/v1",
      "locality": "LOCAL",
      "admitted": true,
      "available": true,
      "capabilities": ["text", "reasoning", "long_context"],
      "priority": 100
    }
  ]
}
```

The example is structural only; the repository does not commit a concrete provider, port, or model binding.

## Materialize runtime config

```bash
export FA3_MODEL_ROUTER_PROVIDER_CATALOG=/path/to/current-host-provider-catalog.json
./bin/fa3-model-router-materialize
```

The generated LiteLLM configuration and resolution are written under `$XDG_RUNTIME_DIR/fa3-model-router/` by default. They are runtime artifacts and are not canonical source.

## User service

The installer can bootstrap the pinned LiteLLM data plane (`1.102.0`) into an isolated venv, or use an already installed executable through `FA3_LITELLM_BIN`.

A production user service also requires a credential file supplied by the existing FA3 secret/session-vault authority. The installer refuses a group/world-readable credential file.

```bash
./bin/fa3-model-router-install \
  --catalog /path/to/current-host-provider-catalog.json \
  --credential-file /run/user/$UID/fa3/credentials/model-router-master-key \
  --bootstrap-litellm \
  --start
```

The service is loopback-only and its systemd sandbox denies non-loopback networking in the baseline local-only profile.

## Current-host evidence

```bash
export FA3_MODEL_ROUTER_PROVIDER_CATALOG=/path/to/current-host-provider-catalog.json
bash bin/fa3-model-router-current-host.sh
```

The collector generates an ephemeral authenticated LiteLLM data plane from the current provider catalog, executes real calls through `fa3-pageindex-index` and `fa3-pageindex-reason`, and writes `evidence/receipts/model-router-current-host.json`.

The receipt is compatible with the PageIndex current-host collector: it proves the central authority, logical routes, provider-neutral selection semantics, the runtime-selected backend/model, and absence of a canonical physical pin. It does **not** promote the global FA3 release.

## PR #186 reconciliation

The LiteLLM work from PR #186 is retained as the provider-neutral API/data-plane implementation. Its committed LiteLLM baseline must not contain independent physical model selection. The central Model Router owns route resolution and generates the effective LiteLLM `model_list` at runtime.
