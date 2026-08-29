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


## Kaneo optional-provider canonical enforcement

`FA3-PROVIDER-KANEO-001` registers `usekaneo/kaneo` strictly as an optional self-hosted work-management / human-agent coordination provider and architectural pattern source. It creates no new capability and no new architectural authority; the canonical capability count remains **143**.

Four Kaneo-derived rules are mandatory P0 canonical invariants and are executable in CI through `FA3-KANEO-GATESET-001`:

1. human and agent operations share the same authoritative authorization boundary;
2. equivalent API/MCP/SDK capability projections fail closed on surface drift;
3. changes cannot close until every declared applicable surface has PASS evidence;
4. security-relevant state that crosses replicas must be shared, expiring, atomically consumed, and replay-protected.

Run the gate directly with:

```bash
./bin/fa3-enforce kaneo
```

The provider runtime itself is **not** required for global FA3 promotion while Kaneo is disabled. The canonical rules remain mandatory regardless of whether the optional provider is deployed. Reference evidence is pinned to Kaneo `v2.22.0` / commit `4faa14858913801cfc62991cb326f35fe5fcae00`; floating `main` is forbidden as promotion evidence.


## Demucs optional-provider canonical enforcement

`FA3-PROVIDER-DEMUCS-001` registers `adefossez/demucs` strictly as an optional local audio source-separation / stem-decomposition provider, reference implementation and architectural pattern source under `FA3-AUDIO-SEPARATION-001`. The profile is a non-root `SUBPROFILE-OF FA3-AUDIO-001` projection over existing `CAP-017` and `CAP-066`; it creates no new capability and no new architectural authority, so the canonical capability count remains **143**.

The executable `FA3-DEMUCS-GATESET-001` enforces 18 audio-separation invariants plus two cross-cutting model-loading trust rules. In particular: unsupported/experimental stem handling is fail-closed; accelerator execution requires a Host Resource Broker lease; model variants, quantized weights, bags and separated stems are typed first-class artifacts with lineage; chunk/overlap/normalization/clipping policies are explicit; and safe model containers do not by themselves authorize execution.

Two global model-loading rules are canonicalized:

- `FA3-MODEL-LOAD-TRUST`: container safety is not execution authorization; provenance, admission, implementation identity and execution policy must also PASS.
- `FA3-MODEL-CLASS-ALLOWLIST`: external model metadata cannot select arbitrary local classes/modules; resolution must use an allowlisted registry implementation mapping.

Run directly with:

```bash
./bin/fa3-enforce demucs
```

The provider runtime is **not** required for global FA3 promotion while Demucs is disabled. Reference evidence is pinned to Demucs `v4.1.0` / commit `6a604bb002d12c4fbabb303ba64db40b5c5743f0`; floating `main` is forbidden as promotion evidence.
