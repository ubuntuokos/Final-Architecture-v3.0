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

## Current materialization and runtime-closure status

The repository-side materialization stage is complete: explicit registration coverage is **429/429 obligations** across all **143 capabilities**. Every capability has an explicit positive, negative and rollback qualification definition, qualification-constituent producer and capability-test executor.

The 117 capabilities that were still unmaterialized after MAT-004 are bound through `canonical/current-host-capability-proof-recipes.json` to explicit real-host proof primitives. Registration alone cannot produce PASS: missing required runtime dependencies causes the corresponding real current-host obligation to fail closed.

There is no remaining `MAT-*` batch. `next_materialization_batch` is `null`, and all 143 capabilities are materialized in deterministic `EXEC-*` batches.

Physical current-host runtime closure is also complete. `FA3 Global Current-Host Evidence Closure` run **#443** (run ID `35822104006`) succeeded on source main commit `4277829255fea114e3b082199e9736012445537e`. The verified result is **429/429 current-host obligations**, **143/143 bundles**, **143/143 attestations**, **143/143 qualified current-host receipts**, and **0 pending Evidence Registry runtime records**. The durable reference is `evidence/reference/current-host-143-audit-2026-09-23.json`.

Runtime closure does **not** imply global release promotion. Release acceptance remains a separate fail-closed boundary: static/release acceptance, all 19 acceptance criteria and every mandatory promotion gate must independently PASS before promotion is allowed.

## External RT3D engine scope

CAP-027 is provider-neutral `Realtime / Virtual Production Interchange`. Proprietary RT3D engines excluded by canonical policy are not discovered, installed, registered, launched, evidenced or promoted by FA3. Users may operate such software independently outside FA3.

## Fail-closed producer diagnostics

When a registered qualification constituent producer rejects execution, diagnostic propagation is limited to the schema-bound `fa3.qualification-producer-rejection.v1` envelope. The rejection must be bound to the registered producer/qualification/constituent/subject identities, use an allowlisted stage, use only allowlisted `reason_codes`, and contain only the bounded allowlisted `summary` fields and scalar/list types accepted by the orchestrator.

The orchestrator may preserve sanitized reason-code and bounded-summary diagnostics alongside the producer return code. Raw stdout/stderr, arbitrary free-text findings and unbound producer data are not promoted. Partial constituent/source-artifact trees are removed on any blocking producer failure, and diagnostic preservation never converts rejection into PASS or promotion evidence.

## Resource Fabric hardware-discovery evidence

CAP-006 current-host qualification must accept an empty accelerator inventory for a CPU-only host and enumerate 0..N typed accelerators without a vendor or runtime allowlist. Accelerator names, memory sizes, architecture values and runtime capabilities remain evidence inputs, not global eligibility floors. Only a workload that explicitly requires an accelerator may demand a compatible discovered device and current scope-bound HRB lease; provider-specific CUDA, ROCm, Level Zero/oneAPI or other runtime checks remain workload scoped.

For cgroup v2 cpuset evidence, an empty leaf effective value must not be interpreted as zero available CPU or memory nodes when the effective allowance is inherited. The collector records the nearest non-empty effective ancestor together with its cgroup source path. This is discovery evidence only; HRB remains the exclusive admission and placement authority.
