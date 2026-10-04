# FA3 Generative Media Capability Mesh — final materialization — 2026-10-04

## Decision

The owner approved the final HiDream/FA3 plan on 2026-10-04. The implementation is capability-centric rather than vendor-centric. HiDream-ai remains a published organization-level discovery/reference donor; no child repository, model, checkpoint, dataset, service or runtime is inherited from that organization registration.

The canonical shared profile is `FA3-GENERATIVE-MEDIA-MESH-001` and the provider-neutral contract set is `FA3-GENERATIVE-MEDIA-MESH-CONTRACTS-001`.

## Existing FA3 substrate reused

- `FA3-IMGGEN-CONTRACTS-001` for visual generation/edit semantics.
- `FA3-MMG-CONTEXT-IR-CONTRACTS-001` for provider-neutral multimodal generation context.
- `FA3-VIDEO-001`, CAP-159 and CAP-160 for shared motion/video execution.
- `FA3-VIDEO-REFINEMENT-CONTRACTS-001` for separate generator/refiner lifecycle.
- `FA3-ENGINE-SELECTION-FABRIC-001` for user preference/compatibility only.
- Model Router for provider/model routing, HRB for resource placement, Temporal for durable workflows.

## Material donor-pattern reuse

The materialization reuses already-published patterns from Diffusers, xDiT, VideoSys, NVlabs Sana/SoL-Refiner, AI Visual Prompt Cookbook, stickman-video-director, See-Through, HiRoute and SystemOneHarness. TobyFlow is used only as a reference-only workflow/UI pattern because no open-source license is verified in the canonical donor record. Google Antigravity was reviewed but is not materially adopted here because its existing donor-intake regression requires no application usage registration without a separate adoption decision.

No donor code is copied by this change. No donor runtime, model or provider is admitted.

## HiDream child waves

Wave A remains: HiDream-O1-Image, HiDream-E1, MotionPro, ReCo and PS-SR. They are represented as intended capability roles only. Each is fail-closed pending an explicit child-level donor marker plus exact provenance, License & Rights for code/weights/datasets/dependencies, security, Software Coexistence, Hardware Safety/runtime review, typed usage edge, provider/model admission and physical evidence where execution affects Current Host.

## GUI placement

The common FA3 AI Studio now exposes a Generative Media Mesh planning/control projection. Exact application placement is fixed as:

- Image / Photo Studio: Create > Generate; Edit > AI Edit; Edit > Constraints > Physical Consistency.
- Story / Screenplay: Visualize > Storyboard.
- Shot Designer: Motion > Trajectory; Camera > Generated Motion.
- Video Editor: AI > Generate; AI > Regional Edit; AI > Refine / Enhance.
- Quick Video: Generate > Visual; Generate > Motion.
- Character Studio: Animation > Motion Transfer; Appearance > Virtual Try-On, rights-gated.
- AI Module Factory: Experiments > Generative Media.
- Model Manager: Models > Generative Media.
- FA3 Control Center: Models > Engines.

These are FA3-native surfaces. Upstream donor UI is not imported.

## Runtime and hardware boundary

The shared fabric keeps a CPU reference or non-AI/manual path. Individual high-compute providers may be unavailable on a CPU-only host; that is an explicit ineligibility state, not a reason for silent fallback. GPU/NPU placement is HRB-only. The display GPU is never automatically enrolled for AI outside the established FA3 exceptions.

## Current Host

This change is a structural GUI/canonical materialization. It does not claim physical Current Host PASS. Runtime/global promotion remains blocked until exact-head physical positive, negative and rollback evidence is available for any actually executable provider path.

Capability baseline: **175 -> 175**. Architectural authority delta: **0**.
