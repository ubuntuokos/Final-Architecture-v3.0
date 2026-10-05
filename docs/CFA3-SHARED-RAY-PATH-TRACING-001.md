# CFA3 Shared Ray/Path Tracing Fabric

## Status
Owner-approved static materialization. Capability baseline remains **175**. The fabric binds to existing **CAP-127** and creates no new architectural authority.

## Purpose
`FA3-SHARED-RAY-PATH-TRACING-001` is the single shared CFA3 semantic and compatibility layer for ray tracing and path tracing. Applications consume the shared core through capability-based adapters; application-local tracing cores are forbidden.

## Execution boundaries
- Engine preference/compatibility intent remains with `FA3-ENGINE-SELECTION-FABRIC-001`.
- Device placement, reservation and lease remain with HRB.
- Hardware Safety remains authoritative before accelerator execution.
- Neural denoise/model-provider routing remains with Model Router.
- Render job dispatch remains the existing CAP-161 Render Fabric responsibility.
- License/Rights, Security and Evidence remain existing authorities.
- This fabric returns candidates and typed plans; it **never authorizes execution**.

## Portability
The canonical surface supports:
- CPU software tracing path — mandatory baseline path.
- NVIDIA accelerator path.
- AMD accelerator path.
- Intel accelerator path.
- portable/open-standards backends when normally admitted.

There is no silent fallback. An explicit backend request that cannot be satisfied returns `UNAVAILABLE`.

## Donor-derived patterns
The implementation uses canonical donor patterns/reference bindings only, with no code copy and no runtime dependency:
- Project-10/OpenRT — provider-neutral API/backend separation.
- GPUOpen GPURT — acceleration-structure and hardware-traversal boundary.
- GPUOpen RRA — acceleration-structure diagnostics/evidence projection.
- Intel Level Zero ray-tracing support — Intel RT capability discovery and exact backend binding.
- Intel RealTimePathTracingResearchFramework — progressive path-tracing accumulation/quality pattern.
- Ancientkingg Rust raytracer — CPU software reference path.
- NVIDIA-RTX organization — reference-only NVIDIA native vendor path context.

All uses are registered through `FA3-APPLICATION-DONOR-LINKS-001`.

## Current Host
Repository-wide `CURRENT_HOST_STABILIZATION_FREEZE / CROSS_PR_PREREQUISITE` remains in force. This changeset has `NO_RUNTIME_IMPACT`: it installs no driver/package, activates no provider/model, binds no physical device and claims no Current Host PASS. Any future executable backend promotion requires a separate exact-head physical qualification.
