# FA3 Model Manager current-host provider E2E

The default smoke is local-only and CPU-first.

- Hugging Face: existing immutable Hub cache snapshot plus a real cached-file SHA-256.
- LM Studio: local LLM discovery, resource estimate, explicit `--gpu off` load, one-shot inference, unload.
- Ollama: isolated loopback service with accelerator visibility removed, local digest-addressed generation, `/api/ps.size_vram == 0`, unload and teardown.

No model download or model pull is allowed.

Run:

```bash
bash bin/fa3-model-manager-current-host.sh
./bin/fa3-enforce model-manager-current-host
```

The receipt is `evidence/receipts/model-manager-current-host.json`.

GPU evidence is separate and must be bound to Host Resource Broker admission or a lease. Provider-local GPU selection is not FA3 authorization. `CURRENT_HOST_MODEL_PROVIDER_E2E_PASS` is provider-specific evidence and does not itself promote the global FA3 release.
