# FA3 current-host closure batches

The active global current-host closure has **175 capabilities** and three mandatory runtime obligations per capability: positive, negative and rollback. That produces **525 obligations**.

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

The repository-side active materialization stage is complete at the registry level: explicit registration coverage is **525/525 obligations** across all **175 capabilities**. Every capability has an explicit positive, negative and rollback qualification definition, qualification-constituent producer and capability-test executor.

`canonical/current-host-capability-proof-recipes.json` contains **149 shared real-host proof recipes**. The remaining **26 capabilities** use dedicated capability producers (`CAP-001..CAP-020`, `CAP-028`, `CAP-054`, `CAP-074`, `CAP-075`, `CAP-076`, `CAP-080`). The shared and dedicated sets are disjoint and together must equal the exact active 175-capability Evidence Registry. Registration alone cannot produce PASS: missing runtime dependencies or failed safety/coexistence preflight causes the corresponding real current-host obligation to fail closed.

There is no remaining `MAT-*` batch. `next_materialization_batch` is `null`, and all 175 capabilities are materialized in deterministic digest-bound `EXEC-*` batches. Each batch is bound to the exact executor/qualification/producer registry SHA-256 set and a selection SHA-256; duplicate obligation keys or cross-registry binding drift are fatal.

The earlier physical closure remains valid **only as historical evidence for the 143-capability release**. `FA3 Global Current-Host Evidence Closure` run **#443** (run ID `35822104006`) on source commit `4277829255fea114e3b082199e9736012445537e` proved **429/429** obligations for that historical release; the immutable reference remains `evidence/reference/current-host-143-audit-2026-09-23.json`. It does **not** satisfy the active 175/525 release. Fresh physical Current Host requalification on the active exact source is required before 175/525 runtime closure may be claimed.

Runtime closure does **not** imply global release promotion. Release acceptance remains a separate fail-closed boundary: static/release acceptance, all 19 acceptance criteria and every mandatory promotion gate must independently PASS before promotion is allowed.

## External RT3D engine scope

CAP-027 is provider-neutral `Realtime / Virtual Production Interchange`. Proprietary RT3D engines excluded by canonical policy are not discovered, installed, registered, launched, evidenced or promoted by FA3. Users may operate such software independently outside FA3.

## Fail-closed producer diagnostics

When a registered qualification constituent producer rejects execution, diagnostic propagation is limited to the schema-bound `fa3.qualification-producer-rejection.v1` envelope. The rejection must be bound to the registered producer/qualification/constituent/subject identities, use an allowlisted stage, use only allowlisted `reason_codes`, and contain only the bounded allowlisted `summary` fields and scalar/list types accepted by the orchestrator.

The orchestrator may preserve sanitized reason-code and bounded-summary diagnostics alongside the producer return code. Raw stdout/stderr, arbitrary free-text findings and unbound producer data are not promoted. Partial constituent/source-artifact trees are removed on any blocking producer failure, and diagnostic preservation never converts rejection into PASS or promotion evidence.

## Resource Fabric hardware-discovery evidence

CAP-006 current-host qualification must accept an empty accelerator inventory for a CPU-only host and enumerate 0..N typed accelerators without a vendor or runtime allowlist. Accelerator names, memory sizes, architecture values and runtime capabilities remain evidence inputs, not global eligibility floors. Only a workload that explicitly requires an accelerator may demand a compatible discovered device and current scope-bound HRB lease; provider-specific CUDA, ROCm, Level Zero/oneAPI or other runtime checks remain workload scoped.

For cgroup v2 cpuset evidence, an empty leaf effective value must not be interpreted as zero available CPU or memory nodes when the effective allowance is inherited. The collector records the nearest non-empty effective ancestor together with its cgroup source path. This is discovery evidence only; HRB remains the exclusive admission and placement authority.
