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

After MAT-002, explicit registration coverage is **48/429 obligations** across sixteen fully materialized capabilities; **381 obligations remain pending materialization**. MAT-001 contributes CAP-001 through CAP-005 and MAT-002 contributes CAP-006 through CAP-010, each with explicit positive, negative and rollback obligations.

Materialization does **not** mean runtime closure. `EXEC-001` (CAP-001 through CAP-005) is execution-ready but remains pending physical execution on the non-root self-hosted `fa3-current-host` runner. `EXEC-002` (CAP-006 through CAP-010) becomes execution-ready from the same registry-derived planner after MAT-002. Until a physical run produces valid qualification constituents, capability test results, bundles, attestations and capability receipts, the affected Evidence Registry records remain pending and global promotion remains fail-closed.

The next deterministic materialization batch is **MAT-003 = CAP-011, CAP-012, CAP-013, CAP-014, CAP-015**.
