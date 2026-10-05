# CFA3 Tile-AI core donor intake — 2026-10-05

## Scope

This donor/reference intake reconciles the three Tile-AI sources identified in the TileLang evaluation line:

- https://github.com/tile-ai/tilelang
- https://github.com/tile-ai/TileRT
- https://github.com/tile-ai/TileOPs

The owner previously issued an explicit donor instruction for TileLang and, in the current continuation, explicitly directed completion of the identified three-source donor-intake reconciliation. This change records reference intake only.

## Parent snapshot

- published main: `f0dec00e71ee04849afb16b974cd7cefdaa4c39d`
- donor registry blob: `03bd0b56a1c176efc224cdd1bc6a091562663390`
- donor registry entries: **1548**
- proposed entries after publication: **1551**
- capability baseline: **175**
- capability delta: **0**
- authority delta: **0**
- usage edges created: **0**

## Upstream observations

### TileLang

- repository: `tile-ai/tilelang`
- observed main revision: `d82101ff08acea8d3e3ca7d0ab40985a3ca2a781`
- root license: MIT
- license note: the root license includes a historical collaboration notice covering 2024-12-01 through 2025-03-14; any future material reuse still requires normal file/dependency provenance and License & Rights review.
- reference role: kernel/compiler DSL and hardware-specific accelerator optimization patterns.

### TileRT

- repository: `tile-ai/TileRT`
- observed main revision: `0ea19371f120977761bfa0cf6a2d08415d8fce0e`
- root license: MIT
- reference role: ultra-low-latency LLM inference runtime, compiler/runtime co-design, and hardware-specific serving patterns.
- boundary: TileRT is not treated as a universal CFA3 runtime.

### TileOPs

- repository: `tile-ai/TileOPs`
- observed main revision: `c644c61b939aebd5f9275fc289d87d78149b9d61`
- root license: MIT
- reference role: spec-driven operator contracts, generated/optimized kernels, correctness validation, roofline/benchmark discipline and backend-specific operator implementations.

## CFA3 applicability boundary

The donor intake intentionally does not freeze the earlier TileLang evaluation as the final architecture. It preserves only the current planning hypothesis:

1. discover the exact accelerator and runtime capabilities;
2. characterize the workload;
3. derive eligible execution/optimization candidates;
4. qualify candidates through compatibility, correctness, Hardware Safety, Software Coexistence and License & Rights gates;
5. use physical/current-host evidence where runtime promotion is involved;
6. select TileLang, TileRT, TileOPs-derived implementations or other admitted backends only when the exact hardware/workload combination justifies them.

CFA3 invariants remain unchanged:

- CPU-only viability remains mandatory where the capability itself supports CPU execution;
- accelerator cardinality remains `0..N`;
- HRB remains sole physical resource placement/reservation/lease authority;
- Model Router remains sole model/provider routing authority;
- no silent device/provider/runtime fallback;
- no display-GPU auto-enlistment outside the existing policy;
- no application-local duplicated accelerator optimization core when a shared placement applies.

## Donor and admission boundary

This intake:

- does not copy upstream code;
- does not install TileLang, TileRT or TileOPs;
- does not create a runtime/provider/model admission;
- does not create donor usage edges;
- does not change the 175 capability baseline;
- does not change architectural authority;
- does not claim Current Host PASS.

The three staged identities remain invisible to canonical planning until they are published into the canonical Donor & Reference Registry on protected `main`. Subsequent material adoption requires an explicit usage edge and all normal governance.

## Rolling batch state

This branch is a source-delta intake for the post-#705 rolling-batch mechanism. It does not directly mutate the central registry. The batch finalizer must re-check normalized source identities against the live published registry, append only non-duplicate identities, refresh derived counts, bind the exact source head, and pass the protected exact-head donor gates before publication.
