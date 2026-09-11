# FA3 Triton Inference Server provider deployment

This directory materializes `FA3-PROVIDER-TRITON-001` as an optional, disabled-by-default inference-serving provider under `FA3-INFERENCE-PORTABILITY-001`.

## Authority boundary

Triton is not an FA3 model registry, model manager, model router, host-resource broker, policy authority, observability/evidence authority, secrets authority, or workflow authority. Its model repository is a non-authoritative runtime projection of already-admitted canonical model state.

## Admitted v1 runtime scope

The current FA3 runtime projection is deliberately narrow: `NVIDIA_GPU_HRB_SCOPED_V1`.

- Triton runtime metadata: `2.72.0` / NGC `26.08-py3`.
- Admitted backend provider projections in v1: `FA3-PROVIDER-TENSORRT-001` and `FA3-PROVIDER-ONNXRUNTIME-001`.
- Other upstream Triton backends (including OpenVINO, PyTorch, Python and custom backends) are capabilities of Triton upstream, not automatically FA3-admitted runtime paths.
- CPU execution is not part of this v1 deployment projection. A future CPU projection requires its own compatibility/admission evidence.

## Hardened defaults

- Production execution requires the exact Triton image reference pinned by immutable `sha256` digest.
- A PASS supply-chain image admission receipt must bind that exact image reference.
- A PASS backend compatibility receipt must bind Triton, an admitted backend provider and the exact HRB device scope.
- Model control is `none` by default. `explicit` is permitted only with Model Manager authorization. `poll` is forbidden for production.
- The model repository is an admitted, read-only provider projection; provider-owned canonical model storage is forbidden.
- Before launch the projection is hashed. The Model Manager placement receipt must bind the exact projection path, projection digest, device scope and a non-empty runtime ordinal map.
- GPU visibility is exactly the HRB-granted GPU UUID set; `--gpus all` is forbidden. Runtime GPU ordinals are not canonical identities.
- Host HTTP `127.0.0.1:8000`, gRPC `127.0.0.1:8001` and metrics `127.0.0.1:8002` are loopback-only. External access belongs behind the canonical gateway/security boundary.
- Auto-complete configuration is disabled, strict readiness is enabled and startup exits on model/configuration error.
- Triton metrics are observability inputs only. This deployment does not create a Prometheus, DCGM or evidence authority.
- The provider materializer does not install Docker, NVIDIA drivers/toolkit, `jq`, `curl` or other host runtime packages.

## Required admission inputs

```bash
export FA3_TRITON_IMAGE='nvcr.io/nvidia/tritonserver:26.08-py3@sha256:<admitted-digest>'
export FA3_TRITON_IMAGE_ADMISSION_RECEIPT='/var/lib/fa3/security/receipts/triton-image-admission.json'
export FA3_TRITON_BACKEND_COMPAT_RECEIPT='/var/lib/fa3/inference/receipts/triton-backend-compatibility.json'
export FA3_TRITON_GPU_UUIDS='GPU-<hrb-granted-uuid>'
export FA3_TRITON_HRB_RECEIPT='/var/lib/fa3/hrb/leases/triton.json'
export FA3_TRITON_PLACEMENT_RECEIPT='/var/lib/fa3/model-manager/receipts/triton-placement.json'
export FA3_TRITON_MODEL_REPOSITORY='/var/lib/fa3/model-projections/triton'
export FA3_TRITON_MODEL_CONTROL_MODE='none'
sudo -E ./deployment/triton/install-fa3-triton
```

The image digest and supply-chain receipt must come from the existing FA3 security/admission path. This provider materialization deliberately does not fabricate a digest or self-approve an image.

For dynamic Model Manager-controlled load/unload, set `FA3_TRITON_MODEL_CONTROL_MODE=explicit` and provide the corresponding authorization projection with `FA3_TRITON_EXPLICIT_MODEL_CONTROL_AUTHORIZED=1`. Direct public access to model-control APIs remains forbidden.

## Evidence and production promotion

A successful materialization writes a non-authoritative deployment receipt to `/var/lib/fa3/evidence/outbox/triton-deployment-receipt.json` for ingestion by the existing evidence authority. It records the image digest, admission/compatibility/HRB/placement receipt references, model-projection digest, device scope, model-control mode, loopback boundary and readiness result.

Static CI proves canonical and deployment-policy conformance only. It cannot claim real current-host production conformance.

For a real inference E2E after the provider has been admitted and materialized on the current host:

```bash
export FA3_TRITON_E2E_MODEL='<admitted-model-name>'
export FA3_TRITON_E2E_REQUEST='/absolute/path/to/inference-request.json'
sudo -E ./deployment/triton/fa3-triton-current-host-e2e
```

The same path is exposed as the manual GitHub Actions workflow `FA3 Triton Current-Host E2E`, which runs only on `[self-hosted, linux, x64, fa3-current-host]`. It verifies the active deployment receipt, server/model readiness and a real `/infer` request, then emits a hashed E2E receipt. The collector itself never self-promotes the provider: `production_promotion_claimed=false` remains explicit.

Until that real E2E succeeds, `current_host_production_evidence` remains `PENDING_REAL_CURRENT_HOST_E2E`.

## Rollback

```bash
sudo ./deployment/triton/rollback-fa3-triton
```

Rollback restores the previous environment, systemd unit and launcher as one runtime projection when a complete backup exists; otherwise it removes/disables the Triton projection. Canonical model identity remains in the FA3 Model Registry and is unaffected by provider rollback.
