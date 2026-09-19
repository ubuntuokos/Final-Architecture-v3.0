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

After MAT-001, explicit registration coverage is **33/429 obligations** across eleven fully materialized capabilities. MAT-001 contributes CAP-001 through CAP-005 (15 obligations) on top of the prior 18 obligations.

MAT-001 being materialized does **not** mean those capabilities have passed runtime closure. Their first real execution batch is `EXEC-001`, selected from the registry-derived planner and executed only by the self-hosted `fa3-current-host` runner. Until that physical execution produces valid qualification constituents, test results, bundles, attestations and capability receipts, their Evidence Registry state remains pending.

The next deterministic materialization batch is **MAT-002 = CAP-006, CAP-007, CAP-008, CAP-009, CAP-010**.
