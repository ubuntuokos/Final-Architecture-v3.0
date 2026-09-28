# Intel OSPRay / RenderKit ecosystem — FA3 donor curation (2026-09-28)

**Scope:** 22 individually GitHub-verified, source-unique candidates in the existing `FA3-DONOR-REFERENCE-REGISTRY-001`. This is metadata-only reference discovery, **not** renderer adoption or a new render authority. The upstream [OSPRay devel README](https://github.com/RenderKit/ospray/blob/devel/README.md) distinguishes core dependencies, optional features, examples/test/build tooling, and the beta Intel Xe GPU path. The upstream OSPRay observation used here is [d5d60d47fb07973168194b83b694481797621213](https://github.com/RenderKit/ospray/commit/d5d60d47fb07973168194b83b694481797621213), a provenance observation only, not an automatic dependency pin.

## Direct OSPRay dependencies and CPU rendering

| Verified source | Relationship | FA3 future targets |
|---|---|---|
| [RenderKit/ospray](https://github.com/RenderKit/ospray) | Candidate surface and volume ray-tracing implementation | 3D Fabric, World Generator, Creative Studio, VFX/Gaffer |
| [RenderKit/embree](https://github.com/RenderKit/embree) | OSPRay ray intersection dependency (README: >=4.3.3) | 3D Fabric, World Generator, VFX/Gaffer |
| [RenderKit/openvkl](https://github.com/RenderKit/openvkl) | Volume renderer dependency **only when** `OSPRAY_ENABLE_VOLUMES` is enabled (README: >=2.0.1) | 3D Fabric, World Generator, Asset Graph |
| [RenderKit/oidn](https://github.com/RenderKit/oidn) | **Optional** denoiser module dependency (README: >=2.3.0) | 3D Fabric, Creative Studio, Video Editor |
| [RenderKit/rkcommon](https://github.com/RenderKit/rkcommon) | Common tasking, aligned memory and vector math | 3D Fabric, World Generator |
| [ispc/ispc](https://github.com/ispc/ispc) | CPU SIMD/SPMD kernel compiler (README: >=1.23.0) | 3D Fabric, Developer Agent |

OSPRay's documented runtime minimum is **SSE4.1 on x86_64** or **NEON on ARM64**; its SIMD references additionally include SSE4, AVX, AVX2 and AVX-512. This is an **OSPRay-specific** compatibility condition, never an FA3 global CPU baseline. [Arm ACLE](https://github.com/ARM-software/acle) is separately captured as a NEON reference. A CPU-only host that cannot satisfy the OSPRay minimum must keep FA3's existing CPU-only functionality through other admitted implementations; do not pretend the renderer itself is universal.

## Tasking, compilers and optional Intel GPU stack

| Verified source | Relationship and limit |
|---|---|
| [oneTBB](https://github.com/uxlfoundation/oneTBB) | Optional/recommended rkcommon tasking; source identity preserves the pending Intel PR #450 key `github:oneapi-src/onetbb` (official old URL redirects). |
| [LLVM/Clang/OpenMP](https://github.com/llvm/llvm-project) | Clang is a supported C++ compiler; OpenMP is one optional rkcommon tasking alternative; rkcommon also offers `Internal`. |
| [Khronos SYCL specification](https://github.com/KhronosGroup/SYCL-Docs) | Portable API *specification*; OSPRay's Intel Xe GPU implementation remains upstream beta. |
| [Intel DPC++ / SYCL](https://github.com/intel/llvm) | Optional Intel GPU compiler/runtime implementation; not proof of NVIDIA or AMD GPU compatibility. |
| [oneAPI Level Zero](https://github.com/oneapi-src/level-zero) | Related optional Intel GPU API/interoperability reference; not asserted as a separately required OSPRay dependency. |
| [Intel Compute Runtime](https://github.com/intel/compute-runtime) | Related optional Intel GPU backend/runtime reference; independent runtime admission needed. |
| [GCC](https://github.com/gcc-mirror/gcc) | Supported C++ compiler reference; OSPRay requires a C++11-capable build toolchain. |
| [Microsoft MSVC documentation](https://github.com/MicrosoftDocs/cpp-docs) | Documentation-only reference for OSPRay's supported MSVC compiler. **No proprietary code donor rights.** |

The upstream OSPRay beta GPU implementation specifically lists Intel Arc (Linux/Windows), and Intel Data Center GPU Flex/Max (Linux). The candidate registry must **not** infer GPU interoperability beyond upstream documentation or bypass the HRB. Source selection should remain optional, explicit, version- and device-aware; no automatic failover or fixed provider pin. Khronos and Intel/oneAPI existing FA3 sources should be consulted first in Reuse Discovery.

## Optional MPI, samples, build and test ecosystem

| Verified source | Relationship |
|---|---|
| [Open MPI](https://github.com/open-mpi/ompi) | One possible implementation for optional `OSPRAY_MODULE_MPI` `mpiOffload` and `mpiDistributed`; MPI is not mandatory. |
| [Google Snappy](https://github.com/google/snappy) | Required only by optional upstream MPI modules. |
| [Kitware CMake](https://github.com/Kitware/CMake) | Upstream OSPRay build configuration reference; no new FA3 build authority. |
| [Khronos OpenGL Registry](https://github.com/KhronosGroup/OpenGL-Registry) | Standard reference for optional upstream examples/tests/benchmarks; not mandatory for headless CPU rendering. |
| [GLFW](https://github.com/glfw/glfw) | Optional window/context management for upstream examples and test tools. |
| [GoogleTest](https://github.com/google/googletest) | Optional upstream C++ test framework; reusable testing patterns only. |
| [Google Benchmark](https://github.com/google/benchmark) | Optional benchmarking patterns; no fabricated current-host performance evidence. |

## FA3 reuse boundaries and Hardware Audit

- **Registry:** all 22 records are `CANDIDATE`, `REFERENCE_ONLY` for planning, non-authoritative, source-copy-blocked pending per-source license, provenance, bundled dependency, security and coexistence review. OSPRay's upstream Apache-2.0 license was checked via its `LICENSE.txt`; other candidate records deliberately remain `UNKNOWN` until individually audited. Proprietary MSVC docs are only a documentation reference.
- **Hardware:** this change captures metadata only. FA3 remains vendor-neutral, CPU-only viable, with discovered accelerator count `0..N`. The Host Resource Broker is the **only** resource placement/lease authority, and no Intel GPU/SYCL/Level Zero/oneTBB/OSPRay global requirement is added.
- **Architecture:** existing native project formats and existing rendering/video/Khronos authorities persist; this does not add a renderer application or require Unreal Engine. Any later proposed OSPRay adapter must go through ApplicationIntent, Reuse Discovery, independent security/license admission, an exact hardware audit and **actual current-host execution evidence**. A CMake build or unit test does not establish host render/provider admission. The Model Router remains sole model route authority.
- **Cross-PR reconciliation:** other donor PRs (#447 NVIDIA, #448 AMD/ROCm, #449 Houdini, #450 Intel/oneAPI) may edit the same canonical registry. In particular, pending #450 uses exactly these source keys and IDs: `oneapi-src/onetbb`, `intel/llvm`, `oneapi-src/level-zero`, `intel/compute-runtime`. Merge equivalent observations **into one row by normalized source key**, preserve all existing Intel targets/metadata and never discard records from other PRs. Regenerate the exact-commit release projection and check full CI on the rebased eventual head.
