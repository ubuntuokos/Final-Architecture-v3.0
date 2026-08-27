# Final Architecture v3.0

Canonical governance and runtime-promotion enforcement for **FINAL ARCHITECTURE v3.0**.

## Permanent gates

- `canonical-regression / P0` validates the exact 143-capability catalog, v3.0.11 source-graph attestation, 36/36 reconciliation, geometry closure, and scope invariants.
- `promotion-safety / fail-closed` proves that runtime `PROMOTED` cannot be set until the current-host Evidence Registry and all 19 acceptance criteria are PASS.

Runtime evidence starts at `PENDING_CURRENT_HOST`; documentation alone never promotes the runtime.

## Commands

```bash
./bin/fa3-enforce static
./bin/fa3-enforce runtime
./bin/fa3-enforce acceptance
./bin/fa3-enforce promote
```

Read-only host evidence collection:

```bash
./evidence/collect-current-host.sh
```

The removed **Linux Recovery/Rebuild Projection** remains explicitly `OUT-OF-SCOPE`.
