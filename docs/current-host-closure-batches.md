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
