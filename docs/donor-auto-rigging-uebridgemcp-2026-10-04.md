# FA3 auto-rigging topic and UEBridgeMCP donor intake — 2026-10-04

## Owner marker

The owner explicitly marked both submitted sources as **donornak** on 2026-10-04:

- https://github.com/topics/auto-rigging
- https://github.com/uuuuzz/UEBridgeMCP

## Canonical intake

Published parent main: `a3071208cf182857d4c49dad4f0d17bf9fe68a6a`

Parent donor registry blob: `1362d75186c6da74e5cf947fdf0b8867d462636a`

Registry count: **1427 → 1429**

Capability baseline: **175 unchanged**

Capability delta: **0**

Authority delta: **0**

Usage edges created: **0**

### Auto-rigging topic

- donor ID: `FA3-DONOR-AUTO-RIGGING-TOPIC-001`
- normalized key: `github:topics/auto-rigging`
- source kind: `GITHUB_TOPIC`
- status: `ACCEPTED_REFERENCE`
- role: metadata-only dynamic discovery index

The topic is useful for discovering automatic skeleton generation, skinning/weight prediction, template-free rigging, rig transfer/retargeting, skeleton repair and DCC integration patterns. Repositories surfaced by GitHub are **not recursively registered or admitted**. Any concrete child repository selected later requires its own donor/reuse, provenance, License & Rights, security, Software Coexistence, Hardware Safety/model-runtime and typed usage-edge review.

### uuuuzz/UEBridgeMCP

- donor ID: `FA3-DONOR-UEBRIDGEMCP-001`
- normalized key: `github:uuuuzz/uebridgemcp`
- source kind: `GITHUB`
- status: `ACCEPTED_REFERENCE`
- observed upstream head: `51c7a0c2288fc00a36aa6b11b73e2789a58ea68e`
- observed release: `v1.19.0`
- observed root license: **GPL-3.0**
- role: reference implementation / architecture pattern only

Observed high-value reference areas include a native C++ MCP server inside Unreal Editor, Streamable HTTP/JSON-RPC, dynamic `tools/list` capability discovery, resource and prompt registries, sticky MCP sessions/cancellation, game-thread marshaling for Unreal object APIs, workflow presets, editor-only lifecycle isolation, release-preflight checks and optional Control Rig / PCG / external-AI extension modules. The documented tool surface also covers Blueprint, level/world, UMG, animation, StateTree, gameplay, navigation, physics, PIE, Niagara and MetaSound workflows.

The upstream documentation explicitly states that UEBridgeMCP is **not a permission system**. FA3 must therefore keep any future Unreal MCP adapter behind existing task-group authority, Layer Guard/testőr, MCP/UAF authorization, Security, audit/provenance, rollback and Evidence boundaries.

## License and rights boundary

UEBridgeMCP's repository root declares GPL-3.0. This intake does not decide Unreal/Epic redistribution compatibility and does not authorize source-code copying, linking, bundling, redistribution or plugin/runtime adoption. Those actions remain fail-closed pending exact License & Rights and Unreal-license compatibility review.

Where legally permitted, independently understood architectural patterns may be re-expressed in an FA3-native implementation without creating a second MCP, Unreal, workflow, resource or security authority.

## Runtime and hardware boundary

This intake is metadata-only. It does not install UEBridgeMCP, Unreal Engine, Python tooling, models or dependencies; it starts no service or port and performs no GPU/CPU placement. The auto-rigging topic does not admit any child model or runtime. Model Router, HRB, Security, Software Coexistence, Hardware Safety and Current Host rules remain unchanged.

No physical Current Host PASS is claimed.

## Rolling donor-intake state

Earlier donor-intake requests already occupy the canonical rolling order and additional draft intakes are waiting. This two-source intake is therefore created as **draft / FIFO waiting** and must not be finalized ahead of earlier eligible donor-intake work.
