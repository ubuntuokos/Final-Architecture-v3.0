# 2D / 3D character-animation donor intake — 2026-10-02

**Authority:** owner-explicit `donornak` registration after deep-research review.

This intake reconciles **20 approved character-animation source identities** into the existing
`FA3-DONOR-REFERENCE-REGISTRY-001`:

- **16 new records**
- **3 existing records enriched/promoted in place**: Stretchy Studio, ozz-animation, Animation Compression Library (ACL)
- **1 historical project record normalized in place**: OpenSeeFace (`project:openseeface` → `github:emilianavt/openseeface`), preserving the donor ID and the legacy source key.

No duplicate registry is created.

## 2D coverage

The approved 2D set adds or strengthens:

- Tahoma2D — cut-out / Plastic-style mesh deformation, rigging and Xsheet workflow.
- Inochi2D — realtime parameter-driven layered-art puppet runtime.
- Inochi Creator — 2D mesh/morph rig authoring.
- Stretchy Studio — AI-assisted layer/PSD rigging, mesh deformation and shape-key-style animation.
- See-Through — single-image character layer decomposition and 2.5D preprocessing research.
- Rive Runtime — realtime vector animation, artboards and animation state-machine/runtime patterns.
- Animated Drawings — archived auto-rig / retarget research reference.

## 3D and shared skeletal coverage

The approved 3D/shared set adds or strengthens:

- ozz-animation — skeletal sampling, blending and runtime skeleton evaluation.
- Animation Compression Library — clip compression/decompression and error-control patterns.
- O3DE / EMotionFX — animation graph, blend tree, hierarchical state-machine and retargeting patterns.
- VRM Specification — humanoid mapping, expressions, look-at and VRM animation interchange reference.
- UniVRM — practical VRM / glTF / VRM-Animation implementation reference.
- SATA — topology-agnostic and cross-skeleton/cross-species motion research.

## Performance capture, face and motion reconstruction

- OpenSeeFace — CPU-oriented face/landmark/head-pose tracking.
- MediaPipe — body, hand and face tracking pipeline reference.
- MMPose — whole-body, hand, face, 3D mesh and animal-pose research.
- Pose2Sim — multi-camera markerless 2D→3D pose reconstruction patterns.
- MoCapAnything — monocular/arbitrary-skeleton motion reconstruction research.
- EasyMocap — multi-view human/body/hand/face capture reference.
- Ubisoft ZeroEGGS — speech-driven style-conditioned gesture-generation research.

## Rights and maturity boundaries

Registration is **reference metadata only**.

- Tahoma2D main code declares BSD-3-Clause; `thirdparty` and bundled brush assets keep separate terms.
- Inochi2D and Inochi Creator declare BSD-2-Clause.
- Stretchy Studio, Rive Runtime, ozz-animation, ACL, UniVRM, Animated Drawings and MoCapAnything declare MIT at repository level.
- See-Through, MediaPipe, MMPose and SATA declare Apache-2.0 at repository level.
- O3DE is dual Apache-2.0 / MIT at the engine level; bundled third-party packages retain separate licenses.
- OpenSeeFace declares BSD-2-Clause.
- Pose2Sim declares BSD-3-Clause.
- VRM specification repository has no root license file in this review; treat it as specification/reference only until rights are resolved.
- ZeroEGGS declares CC BY-NC-ND 4.0 and is kept **reference-only**; no FA3 source/model/dataset reuse is implied.
- EasyMocap currently uses Project Registration License v1.0 with organizational project-registration conditions; it is kept **reference-only**.
- MoCapAnything contains separately licensed/external model and motion-data dependencies; MIT on the repository does not clear those materials.
- AI model checkpoints, datasets and external assets for See-Through, MediaPipe, MMPose, SATA and related projects require their own rights/model admission.

## Architecture boundary

This intake does **not**:

- copy or import upstream source code;
- install any dependency;
- activate a runtime;
- admit a model, dataset, provider or engine;
- create a donor usage edge;
- replace Blender/Bforartists/OpenToonz/Godot or another existing FA3 authority;
- create a new application;
- change the capability baseline;
- change architectural authority.

Potential later adoption should be evaluated as shared capabilities first, under a prospective
**Shared Character Animation Fabric**, with application adapters for Character Studio, Animation Studio,
3D Fabric and Performance Capture. Actual adoption requires a separate owner-approved canonical decision
and usage edge.

## Invariants

- published parent main: `3db848db0018f13f422635cbdac4314f49ebda34`
- parent donor registry: **1317** entries / blob `c29638de9ac73f133a817cc239eba0d3837daac6`
- reconciled source identities: **20**
- new donor records: **16**
- in-place enrichments/normalizations: **4**
- proposed donor registry: **1333** entries
- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- provider count: dynamic / unchanged
- Current Host runtime promotion: **not claimed**
