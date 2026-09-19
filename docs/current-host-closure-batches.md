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

After MAT-004, explicit registration coverage is **78/429 obligations** across twenty-six fully materialized capabilities; **351 obligations remain pending materialization**. MAT-001 contributes CAP-001 through CAP-005, MAT-002 contributes CAP-006 through CAP-010, MAT-003 contributes CAP-011 through CAP-015, and MAT-004 contributes CAP-016 through CAP-020, each with explicit positive, negative and rollback obligations.

Materialization does **not** mean runtime closure. `EXEC-001` (CAP-001 through CAP-005), `EXEC-002` (CAP-006 through CAP-010), `EXEC-003` (CAP-011 through CAP-015), and `EXEC-004` (CAP-016 through CAP-020) are execution-ready from the registry-derived planner but remain pending physical execution on the non-root self-hosted `fa3-current-host` runner. Until a physical run produces valid qualification constituents, capability test results, bundles, attestations and capability receipts, the affected Evidence Registry records remain pending and global promotion remains fail-closed.

The next deterministic materialization batch is **MAT-005 = CAP-021, CAP-022, CAP-023, CAP-024, CAP-025**.
