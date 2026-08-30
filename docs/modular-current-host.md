# FA3 Modular MAX/Mojo current-host production E2E

This harness materializes and verifies the optional `FA3-PROVIDER-MAX-001` and `FA3-PROVIDER-MOJO-001` runtime without granting either provider FA3 authority.

## Runtime materialization

The bootstrap uses an isolated `uv` virtual environment and deliberately refuses to install `uv` from a remote shell pipeline:

```bash
bash bin/fa3-modular-bootstrap.sh
```

The default stable package range is `max[all]>=26.5,<26.6`. Override the environment path with `FA3_MODULAR_VENV` and the admitted package spec with `FA3_MODULAR_MAX_SPEC`.

## Production E2E

The canonical smoke model is:

- `LiquidAI/LFM2.5-350M`
- revision `9e6c6ccf47cd318696e137d381a7ded8fe4df09f`
- `model.safetensors` SHA-256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`

Network model retrieval is denied by default. To perform the one-time admitted fetch:

```bash
bash bin/fa3-modular-current-host.sh \
  --model-revision 9e6c6ccf47cd318696e137d381a7ded8fe4df09f \
  --devices cpu \
  --allow-network-model-fetch
```

After the snapshot is cached, omit `--allow-network-model-fetch`.

For GPU execution use only an explicit broker-leased ordinal:

```bash
bash bin/fa3-modular-current-host.sh \
  --model-revision 9e6c6ccf47cd318696e137d381a7ded8fe4df09f \
  --devices gpu:0 \
  --hrb-lease /path/to/AcceleratorExecutionLease.json
```

GPU evidence fails closed unless the lease is issued by `FA3-HOST-RESOURCE-BROKER-001`, broker validation returns `VALID`, the current ordinal resolves to the leased GPU UUID, broker-side memory reservation is declared, and MAX receives a lease-derived `--device-memory-utilization` guard.

The collector proves both execution paths:

1. MAX: pinned local model artifact -> loopback `max serve` -> real `/v1/chat/completions` response -> response digest.
2. Mojo: source -> `mojo build` -> native executable -> expected stdout -> source/binary/compiled-artifact digests.

A successful run creates `evidence/receipts/modular-current-host.json` with evidence level `CURRENT_HOST_PRODUCTION_E2E_PASS`. GitHub-hosted CI cannot create this status. The optional workflow `.github/workflows/fa3-modular-current-host.yml` runs only on a self-hosted runner carrying the `fa3-current-host` label.
