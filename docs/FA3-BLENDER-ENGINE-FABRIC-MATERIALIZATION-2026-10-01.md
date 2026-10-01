# FA3 Blender Engine Fabric — static materialization

Date: 2026-10-01

## Decision

FA3 strengthens Blender compatibility through an **adapter-first Blender Engine Fabric**. Bforartists remains the primary DCC. Blender remains the upstream compatibility base, native `.blend` authoring/interchange target, headless compatibility target, and Cycles/EEVEE reference render target.

This materialization introduces **no new capability and no new architectural authority**. The canonical capability baseline remains **175** and the Current Host proof model remains **175 × positive/negative/rollback = 525**.

## Compatibility boundary

The following are mandatory invariants:

- no FA3 Blender fork;
- no Blender core patch is required by this stage;
- no `.fa3blend` or other competing project format;
- `.blend` stays Blender-native;
- bpy/RNA/operators, Geometry Nodes, animation, rigs, constraints, drivers, camera/scene semantics, Cycles and EEVEE remain compatibility surfaces;
- Bforartists remains the primary interactive DCC;
- FA3 adds replaceable adapters around Blender rather than taking ownership of Blender internals.

Three rings are used:

1. **UPSTREAM_PURE** — native Blender semantics and compatibility contracts.
2. **COMPATIBLE_ACCELERATION** — FA3 scene/render/geometry/cache/distributed/AI adapters that remain removable.
3. **EXPERIMENTAL** — experiments may never become the sole authoritative project representation.

## Existing FA3 reuse

The fabric reuses existing FA3 structures instead of duplicating them:

- `FA3-3D-GEOM-001` for geometry semantics;
- `FA3-KHRONOS-OPEN-STANDARDS-001` plus the existing OpenUSD/Khronos planning path for interchange;
- CAP-161 for Render Fabric & Job Dispatch;
- CAP-163 for Neural Rendering & Reconstruction Enhancement;
- CAP-166 for Scene / Shot / Camera / Rig Interchange;
- CAP-171 for native-project preservation and round-trip;
- CAP-175 for Software Coexistence & Host Non-Interference;
- `FA3-AUTH-HOST-RESOURCE-BROKER-001` as the only execution-resource authority;
- `FA3-AUTH-MODEL-ROUTER-001` as the only optional AI model/provider authority;
- existing evidence and Current Host structures.

The Blender donor curation, Metric 3D provider fabric, OpenUSD curation and Khronos materialization are planning/reuse inputs. This PR does not create or promote donor identities and does not copy third-party source.

## Render and device policy

Cycles and EEVEE remain available compatibility paths. CPU rendering remains mandatory. Future Hydra/render delegates are optional provider paths behind existing FA3 fabrics.

Device selection must pass through HRB and Hardware Safety Envelope. No silent GPU→CPU fallback, no silent provider fallback, no hardware mutation and no automatic recruitment of a display GPU for compute are permitted.

OpenDLSS-NR/neural rendering is not coupled directly into Blender core. It routes through the existing CAP-163 / Render Fabric boundary after separate runtime admission.

## Scene, material and geometry

The fabric does not create a second scene authority. Blender adapters project into existing FA3 scene/interchange structures. Material interchange may use existing MaterialX/OpenPBR paths; geometry may use existing geometry and cache infrastructure. Derived data must be regenerable and may not replace the authoritative native/canonical source.

Every conversion result is exactly one of:

- `LOSSLESS`
- `LOSSY_WITH_EXPLICIT_REPORT`
- `BLOCKED`

`SILENT_LOSS` is forbidden.

## Optional AI

AI is an optional service boundary only. It must be disableable at application/module/function level. Disabled state must not start models or providers. Model/provider routing remains owned by Model Router and execution resources by HRB.

## Current Host

This change is structural but static. The Current Host alignment record is materialized in the same change. No executable path, package, service, daemon, port, socket, Blender/Bforartists installation, GPU backend, provider or model is activated here, so no physical PASS is claimed.

Future executable materialization requires non-simulated positive, negative and rollback evidence for the applicable surfaces, including Blender GUI, Bforartists GUI, Blender headless, Cycles CPU, admitted accelerator backend, USD/interchange, Render Bridge and `.blend` round-trip.

## Compatibility gate set

The static profile defines the future gate names:

- BLEND-ROUNDTRIP
- BFORARTISTS-ROUNDTRIP
- BLENDER-BFORARTISTS-CROSSOPEN
- BPY-CONFORMANCE
- RNA-CONFORMANCE
- OPERATOR-CONFORMANCE
- SCENE-CONFORMANCE
- MATERIAL-CONFORMANCE
- GEOMETRY-NODES-CONFORMANCE
- ANIMATION-CONFORMANCE
- RIG-CONFORMANCE
- CAMERA-CONFORMANCE
- ASSET-CONFORMANCE
- CYCLES-CONFORMANCE
- EEVEE-CONFORMANCE
- USD-ROUNDTRIP
- GLTF-ROUNDTRIP
- HEADLESS-CONFORMANCE
- EXTENSION-CONFORMANCE
- ROLLBACK-CONFORMANCE

These names are contracts only in this stage; they are not physical runtime evidence.

## Concurrency and merge boundary

The branch was created from published main `7c320638f021fd2783975d13e42af993dfae40e0`. Before merge, reconcile with concurrent render/shared-fabric work, especially PR #550 and PR #580 if they remain open or have landed, regenerate any repository-wide derived release projection required by the then-current main, and run exact-head CI. No static document may self-promote runtime readiness.
