# FA3 Blackhole production runtime

This directory contains the **production hardening projection** for the existing FA3 Blackhole/Kdenlive integration. `podman-compose.yaml` is development/integration only. Production uses rootless Podman Quadlet materialized from an authenticated Host Resource Broker (HRB) placement receipt.

## Fail-closed production sequence

1. Build/approve the Blackhole API, LiteLLM, ComfyUI and egress-gateway OCI images. Record each approved image as `repository@sha256:<digest>` in a private runtime image manifest. Mutable tags are not admitted.
2. Verify signatures, SBOMs and vulnerability admission for every image before deployment. The current-host collector requires operator-provided verification commands and will not infer PASS from a manifest.
3. Create the Podman secrets `fa3-litellm-master-key`, `fa3-audit-hmac-key` and `fa3-egress-allowlist` from the approved FA3 secret/vault source. Secrets are not stored in this repository.
4. Obtain an authenticated HRB `PlacementReceipt` for holder `fa3-blackhole-comfyui-worker`. The receipt must identify the accelerator by NVIDIA UUID and PCI BDF, contain an active lease and pass the HRB-owned verifier.
5. Materialize the Quadlet application with `src/fa3_hrb_cdi.py`. It converts the admitted UUID to the CDI selector and refuses `all`, numeric CUDA ordinals, expired leases and non-digest image references.
6. Install the materialized directory with `podman quadlet install --replace --application=fa3-blackhole <directory>`, reload the user systemd manager and start the four services.
7. Keep Blackhole API, LiteLLM and ComfyUI on `fa3-internal.network`. Only `fa3-egress-gateway` also joins `fa3-egress.network`. LiteLLM reaches external providers through the gateway proxy only.
8. `canonical/blackhole-egress-policy.json` defaults `ALLOW_EXTERNAL_PAID_PROVIDERS` to `false`. Enabling it only permits approved domains in the secret allowlist; it never grants unrestricted egress.
9. The audit ledger stores only opaque references/digests. Personal consent data belongs in the erasable encrypted Consent Vault. Production truncation detection additionally requires an external asymmetric/TPM-backed anchor receipt.
10. Run `evidence/collect-blackhole-production-current-host.py` and then `src/fa3_blackhole_production_gate.py --current-host-receipt ...`. Production admission stays `PENDING_CURRENT_HOST` until every executable check is PASS.

## Static regression

```bash
PYTHONPATH="$PWD/src" python3 -m unittest discover -s tests -p 'test_fa3_*.py' -v
PYTHONPATH="$PWD/src" python3 src/fa3_blackhole_production_gate.py --root "$PWD" --static-only
```

## Required current-host operator inputs

The self-hosted workflow `.github/workflows/fa3-blackhole-production-current-host.yml` intentionally requires runtime-owned paths/commands for the image manifest, HRB receipt/verifier, Cosign verification, SBOM verification, vulnerability admission, and external/TPM audit-anchor verification. Missing inputs fail closed.
