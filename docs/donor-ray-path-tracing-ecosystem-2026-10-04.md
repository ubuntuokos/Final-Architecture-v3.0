# CFA3 ray/path-tracing ecosystem donor intake — 2026-10-04

## Owner instruction

The owner explicitly requested that the ray/path-tracing source batch from this conversation be added **donornak**, and separately requested an implementation plan.

This PR is donor/reference intake only. The implementation plan remains a separate design artifact in the conversation and does not authorize implementation, runtime adoption or donor usage edges.

## Parent snapshot

- published main: `b5052f6595a3fdad84ed7a06e6276f8af5a8dcd8`
- canonical donor registry blob: `1362d75186c6da74e5cf947fdf0b8867d462636a`
- published donor count: **1427**
- capability baseline: **175**

## Intake normalization

The owner supplied **29 exact URLs**. They normalize to **24 source identities**.

Five URL aliases collapse without losing provenance:

- three filtered `topics/ray-tracing` URLs -> `github:topics/ray-tracing`;
- two `topics/ray-tracing-in-one-weekend` URLs -> `github:topics/ray-tracing-in-one-weekend`;
- two `topics/ray-tracer` URLs -> `github:topics/ray-tracer`;
- the Level Zero ray-tracing releases page and repository root -> `github:intel/level-zero-raytracing-support`.

Two normalized identities are already present on published main and are therefore **reconciled in place, not duplicated**. Because the owner has now explicitly marked them `donornak`, their existing records are to be promoted or preserved as `ACCEPTED_REFERENCE` when this intake is materialized:

- `github:gpuopen-librariesandsdks`;
- `github:intel/intel-graphics-compiler`.

Result: **22 new staged identities + 2 in-place existing-identity reconciliations**, parent-relative proposed count **1449** once this intake is materialized.

## Source families

### Discovery indexes

Organization/topic sources cover the RayTracing, NVIDIA-RTX and RenderKit organizations plus the ray-tracing, raytracing, raytracer, RTX, CPU-raytracing and related GitHub topic indexes. These records do not recursively admit child repositories.

### Portable and CPU reference implementations

OpenRT, worldveil/ray-tracing, Ancientkingg/rust-raytracer, bicknyers/raytracer-cpp and the Ray Tracing in One Weekend-derived references are useful for algorithm decomposition, CPU reference behavior, intersection/material/sampling baselines and deterministic correctness comparison.

### CUDA / NVIDIA-oriented reference

Ancientkingg/cuda-raytracer and the NVIDIA-RTX discovery index are constrained by `FA3-CUDA-PORTABILITY-SHARED-FUNCTION-POLICY-001`. CUDA/RTX-specific behavior may inform a shared CFA3 implementation, but an application-local CUDA functional core or silent CUDA fallback is forbidden.

### AMD reference

- `GPUOpen-Tools/radeon_raytracing_analyzer`: BVH/acceleration-structure visualization, traversal analysis and performance diagnostics.
- `GPUOpen-Drivers/gpurt`: acceleration-structure build/traversal design reference. The upstream repository is archived and therefore remains historical/reference-only unless independently re-admitted later.
- the already-published `GPUOpen-LibrariesAndSDKs` donor identity is reused.

### Intel reference

- `intel/level-zero-raytracing-support`: Level Zero RTAS construction/interface reference;
- `intel/RealTimePathTracingResearchFramework`: Vulkan path-tracing, validation and profiling patterns;
- the already-published `intel/intel-graphics-compiler` identity is reused;
- Canonical's Kobuk Intel compute-runtime/package repositories are packaging/runtime provenance references; the compute-runtime mirror is archived and cannot become the execution authority.

## CFA3 architecture target

This source set does **not** justify a new capability. CFA3 already contains:

- **CAP-127 — GPU Ray Tracing, Hardware Traversal, Render Acceleration & Denoising Compatibility**;
- **CAP-161 — Render Fabric & Job Dispatch**;
- the existing **FA3-KHRONOS-OPEN-STANDARDS-001** Vulkan/SPIR-V/ANARI integration;
- the shared-only CUDA portability policy;
- HRB as the sole hardware/resource authority.

Any later material reuse must strengthen those existing surfaces rather than create a parallel renderer authority, hardware router or vendor-local application implementation.

## Rights, safety and runtime boundary

This intake does not authorize:

- source copying or bundling;
- build/runtime dependencies;
- driver, loader, ICD or system-package replacement;
- model/provider admission;
- hardware mutation;
- direct application device placement;
- cloud fallback;
- Current Host PASS.

Exact License & Rights, provenance, Security, Software Coexistence, Hardware Safety and Current Host qualification remain separate for every materially adopted source or pattern.

## FIFO state

The observed five active donor-intake slots are:

`#651, #657, #663, #664, #671`

Earlier waiting donor intakes are:

`#672, #673, #675, #676, #682, #683, #684, #686, #693, #699, #704`

This intake is therefore staged as **draft / FIFO waiting**. The central donor registry is intentionally unchanged on this branch. Before eventual finalization the branch must be reconciled against then-current published main, duplicate detection repeated, identities materialized only for still-new sources, and exact-head donor gates rerun.
