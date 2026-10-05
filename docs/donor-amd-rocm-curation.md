# AMD, ROCm and GPUOpen donor curation — 2026-09-28

Canonical records: `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. These are **CANDIDATE** donor/reference notes, not provider approvals or dependencies.

## Official discovery indexes

- [AMD](https://github.com/amd) — official AMD projects, AI/agent, Ryzen AI and XDNA references.
- [ROCm](https://github.com/ROCm) — current HIP/ROCm runtime, SDK, math and profiling references.
- [GPUOpen Libraries & SDKs](https://github.com/GPUOpen-LibrariesAndSDKs) — portable GPU APIs, graphics and media SDKs.

## Curated candidate repositories

| Source | Selective FA3 planning targets |
| --- | --- |
| [amd/skills](https://github.com/amd/skills) | Agent Runtime, hardware diagnostics, federated skill provenance/evaluation; do not install vendor skills automatically. |
| [amd/gaia](https://github.com/amd/gaia) | Local-first agent workflow and UI patterns; FA3 Model Router remains the only model routing authority. |
| [amd/RyzenAI-SW](https://github.com/amd/RyzenAI-SW) | Optional Ryzen AI/NPU discovery and provider compatibility; no NPU requirement. |
| [amd/xdna-driver](https://github.com/amd/xdna-driver) | Optional XDNA device discovery/reference; no driver installation. |
| [ROCm/TheRock](https://github.com/ROCm/TheRock) | Modular HIP/ROCm build and packaging patterns; never force ROCm onto CPU-only or non-AMD hosts. |
| [ROCm/rocm-systems](https://github.com/ROCm/rocm-systems) | HIP, AMD SMI, rocminfo, rocprofiler-sdk, rocdecode/rocjpeg patterns. Prefer this current super-repository to migrated standalone upstreams. |
| [ROCm/rocm-libraries](https://github.com/ROCm/rocm-libraries) | rocBLAS, hipBLASLt, MIOpen, Composable Kernel, rocFFT, RPP. Inspect subcomponent licenses individually. |
| [ROCm/rocm-examples](https://github.com/ROCm/rocm-examples) | HIP/CUDA portable CMake/sample tests, not current-host hardware evidence. |
| [ROCm/AMDMIGraphX](https://github.com/ROCm/AMDMIGraphX) | Graph/ONNX inference engine patterns, optional AMD provider behind FA3 Model Router. |
| [GPUOpen/Orochi](https://github.com/GPUOpen-LibrariesAndSDKs/Orochi) | Runtime HIP/CUDA API loading/interop, with existing HRB admission intact. |
| [GPUOpen/AMF](https://github.com/GPUOpen-LibrariesAndSDKs/AMF) | Optional FFmpeg/MLT AMD media provider for FA3 Video Editor, QuickClip and Live/Broadcast. |

The official `rocm-systems` and `rocm-libraries` repositories document migrated components and supersede those standalone source locations for current development where migration is complete. Each component's source-of-truth/migration state must be checked again during adoption.

## Mandatory hardware audit compliance

- Registry addition is **metadata-only**: vendor-neutral and CPU-only viable; 0..N discovered accelerators.
- No global AMD, NVIDIA, ROCm, CUDA, NPU or GPU requirement.
- Hardware discovery is not permission to schedule work: `FA3-AUTH-HOST-RESOURCE-BROKER-001` is the only resource admission/lease authority.
- The central Model Router remains the only model route authority. No fixed provider pinning or silent fallback.
- The actual target host must produce fresh hardware/runtime and functionality evidence before enabling an optional accelerated provider.
- These candidate records do not approve cloning, installation, code copying, dependency changes, build integration, vendor driver installation or runtime promotion.

Licensing: the current ROCm super-repositories contain components with independent licenses; verify each selected file or component before copying. Other license declarations are discovery metadata and do not substitute for per-version legal/provenance/security review.
