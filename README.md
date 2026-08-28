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


## Terax reference-provider enforcement

`FA3-PROVIDER-TERAX-001` is an optional terminal-first native Developer/ADE provider and security/interaction pattern source. It creates no new capability or architectural authority; the canonical capability count remains 143.

CI executes the immutable reference and all 17 Terax-derived invariants:

```bash
./bin/fa3-enforce --ci-only terax
PYTHONPATH=src python -m unittest discover -s tests -v
```

The five P0 implementation invariants are read-before-edit, diff-before-apply, typed authenticated local control, executable security regression evidence, and effectively zero runtime cost when disabled.

Current-host evidence is deliberately separate from CI. On the actual FA3 workstation, with Terax kept disabled/reference-only:

```bash
python3 evidence/collect-terax-current-host.py --state disabled-reference
./bin/fa3-enforce terax
```

The collector is read-only, performs no network access, and does not read credentials. A PASS proves the disabled Terax provider has zero observed process/RAM/VRAM/polling/background-inference cost on that collecting host. It does not by itself promote the full 143-capability runtime.

Reference evidence is pinned to Terax v0.8.6 / commit `1fdbc50e53b3ac53db3ba80057805a2d54258545`. The later local-control pattern is separately pinned to exact commit `e9b489c5d50cb9e654fc9a61f901c0eb9f341be3`; floating `main` is forbidden as promotion evidence.
