# FA3 current-host closure batches

The global current-host closure has 143 capabilities and three mandatory runtime obligations per capability: positive, negative and rollback. That produces 429 obligations.

This planner deliberately separates two states:

1. **Executor materialization** — an obligation has an explicit executor, qualification definition and qualification-constituent producer.
2. **Real current-host execution** — those materialized obligations have actually run on the non-root self-hosted `fa3-current-host` runner and produced attestable evidence.

A materialized executor is not a runtime PASS. A completed batch is not global promotion. Synthetic fixtures, provider-only receipts and generic host evidence cannot satisfy capability-level current-host closure.

Run:

```bash
PYTHONPATH=src python3 src/fa3_current_host_batch_planner.py --root .
```

The report is written to `reports/current-host-closure-batch-plan.json`. `EXEC-*` batches contain capabilities whose positive/negative/rollback obligations are fully materialized across all three registration layers. `MAT-*` batches identify the deterministic remaining capability materialization order.

## Current materialization frontier

The repository-side materialization stage is complete: explicit registration coverage is **429/429 obligations** across all **143 capabilities**. Every capability has an explicit positive, negative and rollback qualification definition, qualification-constituent producer and capability-test executor.

The 117 capabilities that were still unmaterialized after MAT-004 are bound through `canonical/current-host-capability-proof-recipes.json` to explicit real-host proof primitives. Registration alone cannot produce PASS: missing Bforartists/Blender, PyTorch3D, CUDA, FFmpeg, KDE/Wayland or other recipe dependencies causes the corresponding real current-host obligation to fail closed.

There is no remaining `MAT-*` batch. `next_materialization_batch` is `null`, and all 143 capabilities are now execution-ready in deterministic `EXEC-*` batches.

Materialization still does **not** mean runtime closure. The next stage is physical execution of all execution batches on the non-root self-hosted `fa3-current-host` runner, followed by qualification bundles, attestations, handoff and the existing promotion-safety chain. Until those real executions succeed, Evidence Registry runtime records remain pending and global promotion remains fail-closed.


## External RT3D engine scope

CAP-027 is provider-neutral `Realtime / Virtual Production Interchange`. Proprietary RT3D engines excluded by canonical policy are not discovered, installed, registered, launched, evidenced or promoted by FA3. Users may operate such software independently outside FA3.

## Fail-closed producer diagnostics

When a registered qualification constituent producer rejects execution, the orchestrator preserves only the producer's bounded structured `REJECTED/findings` payload alongside the return code. Raw stdout/stderr is not promoted. Partial constituent/source-artifact trees are still removed on any blocking producer failure, and diagnostic preservation never converts rejection into PASS or promotion evidence.

## Resource Fabric hardware-discovery evidence

CAP-006 current-host qualification must accept an empty accelerator inventory for a CPU-only host and enumerate 0..N typed accelerators without a vendor or runtime allowlist. Accelerator names, memory sizes, architecture values and runtime capabilities remain evidence inputs, not global eligibility floors. Only a workload that explicitly requires an accelerator may demand a compatible discovered device and current scope-bound HRB lease; provider-specific CUDA, ROCm, Level Zero/oneAPI or other runtime checks remain workload scoped.

For cgroup v2 cpuset evidence, an empty leaf effective value must not be interpreted as zero available CPU or memory nodes when the effective allowance is inherited. The collector records the nearest non-empty effective ancestor together with its cgroup source path. This is discovery evidence only; HRB remains the exclusive admission and placement authority.
