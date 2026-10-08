# FA3 Game-Creation Capability Integration — WP0

**Date:** 2026-10-01  
**Status:** OWNER-APPROVED WP0 MATERIALIZATION  
**Base main:** `7c320638f021fd2783975d13e42af993dfae40e0`  
**Capability baseline:** 175 (unchanged)  
**Provider count:** dynamic (unchanged)

## Purpose

Maximize reusable capabilities from game-creation and interactive-authoring systems without importing a mandatory game engine, upstream editor authority, duplicate donor registry, resource authority or model/provider route. WP0 is the source/reuse/rights/architecture lock only; it does not implement WP1 runtime code.

## Donor serialization boundary

At materialization time PR **#581** is open and changes the canonical Donor & Reference Registry, so it owns the exclusive donor-intake slot. In addition, the newly researched URLs in this conversation were not preceded by the repository-required literal user-authored `donornak` marker. Therefore this WP0 deliberately does **not** mutate `FA3-DONOR-REFERENCE-REGISTRY-001`, create donor IDs, or add donor usage edges.

Two already-published references are reused without duplication: the existing Godot curation and `FA3-DONOR-MATERIAL-MAKER-001`.

## Reuse policy

- **A** — potential direct source/component reuse, only after exact file/dependency License & Rights clearance, security review, Software Coexistence and technical fit.
- **B** — algorithm/schema/workflow semantics are implemented behind FA3-native contracts.
- **C** — clean FA3-native implementation from functional/architectural observations; no source copying.

No A route in this WP0 is permission to copy code.

## Source lock and License & Rights disposition

| Source | Exact review revision | Observed rights | Route |
|---|---|---|---|
| Godot Engine | `084a2caa05119b625a99b6b51d44b459a26362de` | MIT | **A+B** |
| O3DE | `28872cbb42b4a140f92bf42d75850065135267ff` | Apache-2.0 OR MIT; third-party components separate | **A+B** |
| Bevy | `52c3ec0d5ecec0cdf6f4d2fdfd0895267d64740f` | MIT OR Apache-2.0 | **A+B** |
| Fyrox | `a445c62352682747be85f17e2cda8331a544ad44` | MIT | **A+B** |
| Defold | `5b389dfdaf28ce76f0f828d29b6b7819cb12dcce` | Defold License 1.0; commercialisation restriction for Game Engine Product | **B+C** |
| Stride | `a7fa31ced680c7d4a919f1fe233051cf508f6060` | MIT | **A+B** |
| GDevelop | `2ff7e45b40f52fbb2f90968e2cf1a91b248e8fcc` | MIT for core/engine/new IDE/extensions; name/logo reserved | **A+B** |
| GDevelop Extensions | `a256a405e053ce3dbf75a0da723eba9cc7d7d1b3` | MIT | **A+B** |
| LDtk | `6d69bd1d6be92f01ac30778f6a934f0da8448b16` | MIT | **A+B** |
| Tiled | `221be2066c4b0ed4bbefbcdfe25d0ad952fc51bd` | Mixed: editor/plugins GPL; libtiled BSD-2-Clause; other components BSD-2/3-Clause | **A(partial)+B+C** |
| TrenchBroom | `90de03cd28af86658403758ed28e8ca156d34422` | GPL-3.0 | **B+C** |
| Material Maker | `04a932dbc0063f7067a514f4219d283e1b3363b2` | MIT | **A+B** |
| Godot Orchestrator | `e1fdcaac6f80ff68d1419868eedf85eae4bd2a1a` | Apache-2.0 | **A(partial)+B+C** |
| Ink | `35c63e52f1d36060930dc7ed3cfba38ea224b528` | MIT | **A+B** |
| Inky | `3d46aa92bf1572797f35d338bf75e37bb047f2e3` | MIT declared in README/package; bundled third-party files require scan | **A(partial)+B** |
| Yarn Spinner | `dd8d9b4f7b752364e3dce94961c00924e13f5d72` | MIT | **A+B** |
| Ren'Py | `e46bb291c86c87de1c3d853a632507381db7df64` | Core contributions MIT; distribution contains multiple MIT/LGPL/other third-party licenses | **A(partial)+B+C** |
| Go Flow | `7c387b2cda9dc9c469859c28ff6e09f8652c1adf` | AGPL-3.0 | **C** |
| Pixelorama | `07d9323a10fba1c6f8f2a8daae4e8ed45905c1fc` | MIT | **A+B** |
| Blockbench | `e2ede0809ee6bc91f374ac7e00d34cffbdf86a14` | GPL-3.0 | **B+C** |
| Crocotile 3D | N/A | Proprietary/commercial application; no reusable source license established | **C** |

Crocotile is retained only as a workflow/reference observation. Tiled direct reuse is limited to separately cleared components (for example libtiled BSD-2-Clause); the GPL editor is not copied by this decision. Defold, TrenchBroom, Go Flow and Blockbench default to B/C or C because their observed licenses are not suitable for automatic in-tree source reuse. Ren'Py and Inky require file/dependency-level review because bundled third-party materials have separate rights.

## FA3-native shared target architecture

1. **Shared Asset Processing Fabric** — extend the existing Media Asset pattern with source/product assets, dependency graph, deterministic jobs, cache/invalidation and hot reload.
2. **Creative Object & Scene Fabric** — provider-neutral object composition, stable IDs, hierarchy, components and references.
3. **Smart Asset / Prefab & Variant Fabric** — reusable nested assets, parameters, variants, instance overrides, rights and provenance.
4. **Universal Workflow Graph Fabric** — materialize the existing typed workflow graph pattern as shared data/execution/procedural graph infrastructure.
5. **Live Preview & Incremental Rebuild Fabric** — affected-subgraph rebuild and state-preserving preview.
6. **Transactional Creative History** — checkpoint/restore/branch/compare semantics integrated with Stateful Workflow and Creative Provenance.
7. **Validation & Creative Diagnostics Fabric** — issue model, locate/explain/preview-fix/apply/verify flow, profiler and dependency inspection.
8. **Spatial & Procedural Authoring Fabric** — typed layers/entities/spatial references/rule-driven placement/procedural graphs.
9. **Extension / Codec / Authoring Toolkit** — capability/permission-scoped plugin lifecycle, import/export codec contracts and shared authoring primitives.

Narrative semantics from Ink/Yarn/Ren'Py remain subordinate to Story/Screenplay and Stateful Workflow rather than creating a second story authority.

## Application impact target

Canonical internal applications to review retroactively: Video Editor, QuickClip, Story/Screenplay, Music Studio, Character Studio and AI Module Factory. Curated creative providers receive adapters only where approved; native projects remain authoritative. Planned World/Location, Texture/Material, VFX, Shot, Choreography, Credits/Titles, Photo/RAW, 2D Vector, Rendering and Presentation surfaces are included in future impact projection when their canonical application records exist.

## Work packages

- **WP0 — complete in this change:** source lock, rights disposition, A/B/C route, donor serialization boundary, implementation decision, Current Host structural-impact record.
- **WP1:** Asset Processing + stable IDs + dependency schema.
- **WP2:** Creative Object/Scene + Smart Asset/Prefab.
- **WP3:** Universal Workflow Graph + Event/Behavior model.
- **WP4:** Transactional History + Provenance + Validation.
- **WP5:** Live Preview + incremental rebuild + diagnostics/profiling.
- **WP6:** World/Material/Narrative/Animation domain adapters.
- **WP7:** retroactive application/provider migration without capability loss.
- **WP8:** physical Current Host requalification, manuals and release projection.

## Mandatory gates for WP1+

175 remains fixed unless separately reconciled. Shared-first and retroactive impact are mandatory. No capability regression, silent fallback, forced AI dependency, hardware mutation, upstream uninstall or authority duplication. HRB remains sole live resource authority; Model Router remains sole model/provider routing authority; Secret Broker, Layer Guard, Evidence, Hardware Safety Envelope and Software Coexistence remain mandatory.

Any executable/runtime materialization must update Current Host in the same change and later produce physical positive/negative/rollback proof before promotion.

## WP0 completion result

**PASS_WITH_SERIALIZED_DONOR_INTAKE_DEFERRED.**

WP0 does not authorize WP1 implementation.
