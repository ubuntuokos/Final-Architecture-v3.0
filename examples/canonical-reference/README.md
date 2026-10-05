# FA3 Canonical Reference Scenario

This is an executable miniature of the FA3 proof chain. It is **reference conformance only** and never creates current-host production or global promotion evidence.

Run:

```bash
PYTHONPATH=src python examples/canonical-reference/run.py
```

The four mandatory cases are:

1. `REFERENCE_VALID` — a typed reference Evidence Envelope passes its declared reference scope.
2. `CURRENT_HOST_MISSING` — missing current-host evidence remains `PENDING` and maps to exit code `2`.
3. `TAMPERED_EVIDENCE` — a payload SHA-256 mismatch is detected and fails closed.
4. `SCOPED_CURRENT_HOST` — a valid component-scoped current-host fixture may pass component admission only and explicitly lists `GLOBAL_FA3_PROMOTION` as a non-claim.

No example uses `|| true`; expected negative outcomes are asserted as part of the executable regression semantics.
