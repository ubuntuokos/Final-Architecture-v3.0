# FA3 Triton Inference Server provider deployment

This directory materializes `FA3-PROVIDER-TRITON-001` as an optional, disabled-by-default inference-serving provider under `FA3-INFERENCE-PORTABILITY-001`.

## Authority boundary

Triton is not an FA3 model registry, model manager, model router, host-resource broker, policy authority, observability/evidence authority, secrets authority, or workflow authority. Its model repository is a non-authoritative runtime projection.

## Hardened defaults

- Runtime: Triton `2.72.0`, NGC `26.08-py3` metadata, production execution by immutable container digest only.
- Model control: `none` by default. `explicit` is permitted only with Model Manager authorization. `poll` is forbidden for production.
- Model repository: admitted projection, read-only mount, no provider-owned canonical store.
- GPU visibility: exact HRB-granted GPU UUID set; `--gpus all` is forbidden.
- Placement: a PASS `FA3-PROVIDER-TRITON-001` placement receipt is required before launch; model `instance_group` placement must be a subset of the HRB grant.
- Networking: host HTTP `127.0.0.1:8000`, gRPC `127.0.0.1:8001`, metrics `127.0.0.1:8002` only. External access belongs behind the canonical gateway/security boundary.
- Config: auto-complete disabled, strict readiness enabled, exit-on-error enabled.
- Monitoring: Triton metrics are observability inputs only. This deployment does not create a Prometheus/DCGM/evidence authority.
- Host lifecycle: this materializer does not install Docker, NVIDIA drivers/toolkit, jq, curl, or other host runtime packages.

## Required admission inputs

Export all required inputs before running the materializer:

```bash
export FA3_TRITON_IMAGE='nvcr.io/nvidia/tritonserver:26.08-py3@sha256:<admitted-digest>'
export FA3_TRITON_GPU_UUIDS='GPU-<hrb-granted-uuid>'
export FA3_TRITON_HRB_RECEIPT='/var/lib/fa3/hrb/leases/triton.json'
export FA3_TRITON_PLACEMENT_RECEIPT='/var/lib/fa3/model-manager/receipts/triton-placement.json'
export FA3_TRITON_MODEL_REPOSITORY='/var/lib/fa3/model-projections/triton'
export FA3_TRITON_MODEL_CONTROL_MODE='none'
sudo -E ./deployment/triton/install-fa3-triton
```

The image digest must come from the existing FA3 supply-chain admission path; this repository deliberately does not fabricate or substitute a digest.

For dynamic Model Manager-controlled load/unload, set `FA3_TRITON_MODEL_CONTROL_MODE=explicit` and provide the corresponding authorization projection with `FA3_TRITON_EXPLICIT_MODEL_CONTROL_AUTHORIZED=1`. Direct public access to model-control APIs remains forbidden.

## Evidence and promotion

A successful materialization writes a non-authoritative deployment receipt to `/var/lib/fa3/evidence/outbox/triton-deployment-receipt.json` for ingestion by the existing evidence authority. Static CI proves canonical/gate conformance only. Production promotion requires a real current-host run with an admitted image digest, real HRB lease, placement receipt, loaded admitted model, readiness PASS, and successful inference E2E.

## Rollback

```bash
sudo ./deployment/triton/rollback-fa3-triton
```

Rollback restores the previous environment if one was backed up; otherwise it disables the service. Model identity remains in the canonical Model Registry and is unaffected by provider rollback.
