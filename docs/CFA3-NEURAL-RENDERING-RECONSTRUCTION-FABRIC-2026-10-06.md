# CFA3 Neural Rendering & Reconstruction Fabric

Status: OWNER-APPROVED STATIC MATERIALIZATION
Date: 2026-10-06
Capability baseline: 175; capability delta: 0; architectural authority delta: 0.

## Purpose

CFA3 uses one shared, provider-neutral Neural Rendering & Reconstruction Fabric. Applications do not integrate NVIDIA DLSS, AMD FSR, Intel XeSS, OpenDLSS-NR or future providers directly. They emit and consume the canonical Neural Frame Surface and request feature classes through the shared fabric.

## Feature contract

The shared feature classes are NEURAL_RENDER, SUPER_RESOLUTION, NATIVE_RESOLUTION_AA, RAY_RECONSTRUCTION, DENOISE, TEMPORAL_RECONSTRUCTION, FRAME_GENERATION and LOW_LATENCY_PRESENTATION.

The common frame surface preserves frame identity, dimensions, colour-space and transfer semantics, timecode, source artifact and provenance. Temporal features additionally require motion vectors, depth, temporal history, camera state and jitter. Ray reconstruction additionally requires normals. Super resolution requires explicit target dimensions.

Frame Generation is presentation-only. It may be used for interactive preview, viewport, previs, virtual-production monitoring and playback but it is forbidden for FINAL_MASTER, ARCHIVAL_MASTER, EXR_SEQUENCE and VFX_HANDOFF. Generated presentation frames never enter the canonical production timeline.

## Execution classes

- CPU_SOFTWARE: explicit, admitted CPU execution. Model-backed execution requires Model Router and HRB receipts. It is the mandatory vendor-neutral CPU path; it is not a silent substitute for a specifically requested vendor provider.
- HOST_NATIVE_ACCELERATED: exact device binding and HRB lease are required; Hardware Safety and display-GPU rules remain binding.
- BROWSER_WEBGPU: remains inside FA3-WEB-AI and may not silently egress or switch to remote execution.

No execution class can silently substitute provider, backend, device, precision, CPU, GPU, browser or cloud execution.

## Provider model

OpenDLSS-NR remains the existing conditional neural-render/temporal-reconstruction provider and is explicitly not advertised as Super Resolution or Frame Generation. CFA3-native CPU, NVIDIA DLSS, AMD FSR, Intel XeSS and browser/WebGPU are provider slots. A slot grants no donor, code, model, license, runtime, hardware or Current Host admission.

## Interoperability

Engine Selection chooses the requested engine/compatibility intent; it is not provider execution authority. Shared Ray/Path Tracing hands neural denoise/reconstruction data to this fabric. CAP-161 owns render dispatch semantics and CAP-162 covers admitted external render services. HRB remains the exclusive resource placement/lease authority and Model Router the exclusive model/provider route when a model route is used.

Application projects remain authoritative. The Neural Fabric never creates a competing project/scene/timeline format and never rewrites geometry semantics.

## Application projection

Current canonical consumers are FA3 Video Editor, QuickClip, Story/Screenplay (indirect previs request), Character Studio, AI Module Factory (evidence/artifact consumer), ComfyUI, InvokeAI, Kdenlive, Bforartists, Natron, Gaffer and the Krita reference surface.

Future applications in IMAGE, VIDEO, DIGITAL_HUMAN, ANIMATION, SHOT_DESIGN, VIRTUAL_PRODUCTION, LOCATION_SET, RENDER and EDITING domains must bind to this shared fabric rather than implement application-local neural rendering cores. Provider activation remains explicit and separately admitted.

## Donor and reuse boundary

This materialization consumes the verified published-main donor snapshot and reuses already canonical shared components and their existing donor provenance. It creates no new donor identity or donor usage edge and consumes no pending/unmerged donor. New FSR/Streamline/XeSS donor/provider admission remains separate.

## Current Host

This change is static and structural only. It installs no package or driver, activates no provider/model, mutates no hardware and claims no physical Current Host PASS. Any production provider activation requires the normal License & Rights, provenance, supply-chain, security, Software Coexistence, Hardware Safety and physical Current Host E2E gates.
