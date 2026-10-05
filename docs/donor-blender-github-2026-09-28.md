# Blender GitHub donor curation — 2026-09-28

## Scope and upstream identity

Five **verified public Blender GitHub references** are captured as non-authoritative `CANDIDATE` records in `FA3-DONOR-REFERENCE-REGISTRY-001`. The [Blender Foundation GitHub organization](https://github.com/blender) is a **discovery index**, not blanket admission of all its repositories. GitHub mirrors are read-only; Blender's primary development host is [projects.blender.org](https://projects.blender.org/blender/blender).

| Verified upstream | Selective FA3 reuse target | License declaration / boundary | Lifecycle |
| --- | --- | --- | --- |
| [blender/blender](https://github.com/blender/blender) | Bforartists, 3D Fabric, Character Studio, World Generator, VFX/Gaffer, Creative Studio, FA3 Video Editor and Asset Graph: modeling, rigging, geometry-node workflow, animation, compositing and asset/interchange patterns | Whole application GPL-3.0; bundled components and individual files need separate review | Active mirror; candidate |
| [blender/cycles](https://github.com/blender/cycles) | Bforartists, 3D Fabric, VFX/Gaffer and World Generator: CPU-capable path-tracing, render/back-end abstraction and standalone / Hydra-delegate reference | Apache-2.0 repository declaration; inspect intended copied files and dependencies | Active mirror; candidate |
| [blender/blender-addons](https://github.com/blender/blender-addons) | Bforartists, 3D Fabric, Character Studio and Asset Graph: legacy Python extensions and scene/import/export patterns | Per-file licensing; no blanket license inference | Archived 2025-05-09; historical candidate |
| [blender/blender-addons-contrib](https://github.com/blender/blender-addons-contrib) | Bforartists, 3D Fabric and Asset Graph: older community extension and creative asset patterns | Per-file licensing and author/provenance review required | Archived 2025-05-09; historical candidate |
| [Blender GitHub organization](https://github.com/blender) | Cross-application discovery index for future source-specific research | No organization-wide license declaration | Discovery-index candidate |

## Planning integration

Before any new or materially modified FA3 3D / creative module, Reuse Discovery must query the canonical donor registry using the capability, domain, problem and target hints above. These entries complement the preexisting Bforartists and Creative Studio architecture: **Bforartists remains the primary DCC**. Do not create a second 3D scene authority or import Blender's full UI/editor/runtime just because a reference matches.

- **DCC and interchange:** use Blender's established scene, animation and geometry-node concepts as reference for the FA3 3D-ready schema, compatibility adapters, native project preservation and the existing Khronos/OpenUSD/glTF interchange design.
- **Render and VFX:** assess Cycles' standalone/Hydra and CPU-rendering reference patterns against existing FA3 render, color and hardware governance; source reuse and runtime admission are separate decisions.
- **Creative workflows:** consider animation, rig/pose/shot/camera, compositing, extension metadata and asset organization when the corresponding FA3 applications are built or revised. FA3 Video Editor retains its own timeline, MLT/FFmpeg and project format; Blender video/editor code is reference-only.
- **Historical add-ons:** archive is **not** a current maintenance signal. Prefer active canonical upstream implementation for new compatibility work; treat old scripts as provenance-checked historical examples.

## Source and license boundary

Blender's [official license statement](https://www.blender.org/about/license/) says the complete Blender binary is GPL-3.0-compatible; source files may carry different compatible licenses. The [Cycles mirror](https://github.com/blender/cycles) declares Apache-2.0. The archived add-on repositories contain per-file licenses and cannot be given a blanket declaration. Each selected source requires exact upstream revision, SPDX/file-level provenance, security/ABI/dependency/coexistence and redistribution review **before any code copy**. No code is imported by this donor change.

This registration does **not** fetch, install or activate Blender, Cycles, add-ons, Bforartists, a model or a new provider. It does not override the FA3 Model Router, HRB, evidence registry, Creative Studio architecture or the exclusion of Unreal Engine. No new FA3 capability or architectural authority is introduced.

## Hardware Audit — mandatory

Registry/query is metadata-only and supports **CPU-only** systems, zero or more accelerators (`0..N`), and vendor-neutral discovery. GPU-specific Cycles paths and Hydra integration are optional upstream references, **not** FA3 baseline requirements or guaranteed compatibility. The Host Resource Broker is the only execution-resource authority; no vendor/SKU/backend/session pin, silent fallback, current-host renderer PASS or runtime promotion is claimed. Future GUI work remains desktop-independent, Wayland-preferred and X11-compatible.

## Verification and concurrent PRs

The main baseline at `f270fe9eca20f8156851a58e75b4c4a6733e8e0a` has **290** entries; this scoped branch adds **five** unique normalized source keys to reach **295**. Dedicated test: `PYTHONPATH=src python3 -m unittest tests.test_donor_blender_github -v`. Existing donor PRs #448–#454 can change the same canonical JSON; reconcile **all** merged records by normalized source key before merge, regenerate the exact-head release projection, and confirm CI. Registry candidate capture is not current-host execution evidence.
