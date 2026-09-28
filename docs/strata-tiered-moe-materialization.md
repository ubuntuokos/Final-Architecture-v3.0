# Strata -> FA3 tiered MoE materialization

Pinned upstream reference: `Niko1221/Strata@b742ff998704638903461a2d7d6c1e03b8032509` (observed release `v0.1.12`, 2026-09-28).

## Materialized outcome

Strata is represented as `FA3-PROVIDER-STRATA-001`, an optional disabled-by-default inference provider candidate. It does not own model routing, model trust admission, resource placement, security policy, secrets, or evidence promotion.

The reusable architectural result is `FA3-TIERED-MOE-EXECUTION-CONTRACTS-001`. It separates:

- authoritative expert residency in admitted NUMA host memory;
- rebuildable hot-expert cache in admitted accelerator memory;
- dense-weight placement across accelerator/host memory;
- explicit KV accelerator residency and optional host spill;
- persistent-storage placement for auxiliary indexes and cold artifacts.

`src/fa3_tiered_moe_plan.py` is an independent FA3 implementation of this contract. It is intentionally provider neutral and preserves the global CPU-only baseline and accelerator cardinality 0..N.

## Authority path

```text
FA3 application
  -> FA3-AUTH-MODEL-ROUTER-001
  -> admitted provider candidate
  -> FA3-AUTH-HOST-RESOURCE-BROKER-001 placement/lease
  -> Strata provider (when admitted)
```

Direct application -> Strata routing is forbidden. Fixed canonical model/provider routes and silent fallback are forbidden.

## Source reuse / license state

At the pinned upstream snapshot, no repository-root `LICENSE`, `COPYING`, or `NOTICE` file was present and GitHub exposed no repository-level license metadata. Therefore this materialization copies **no original Strata source code**. The implementation uses only independently expressed FA3 policy and architecture concepts.

If upstream later publishes a compatible license, code-level reuse requires a new per-file/repository reuse audit and immutable source pin before any copy is admitted.

## Hardware audit

The FA3 contract is vendor neutral and keeps CPU-only execution viable. Strata's observed upstream implementation is provider-specific (currently NVIDIA/CUDA and a single selected GPU at the pinned snapshot); those limits are admission constraints on Strata only and must not become global FA3 assumptions.

## Promotion state

Static materialization can pass in CI. Runtime promotion remains pending real physical current-host evidence: exact binary/source identity, API conformance, model identity, HRB lease/placement receipt, resource-pressure behavior, and Model Router selection provenance.
