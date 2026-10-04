# CFA3 Native CUDA Compatibility Core

## Decision

CFA3 implements the CUDA-oriented compatibility function as one **CFA3-owned shared platform service**. Spectral Compute SCALE is **not** a build dependency, runtime dependency, binary-loading dependency, installer dependency, or activation requirement.

CUDA remains a backend interface, not a CFA3 capability. The capability baseline remains 175 and no new architectural authority is introduced.

## Central application access

Every current and future CFA3 application uses the same interfaces:

- `src/fa3_cuda_compat_shared.py:resolve_cuda_compatibility`
- `src/fa3_cuda_compat_shared.py:prepare_cuda_compat_translation`

There is no per-application allowlist. `application_id` and `workload_id` are provenance/audit context only. An application may request a compatible candidate or translation artifact, but it cannot authorize accelerator execution or select a hidden fallback.

Application-local copies of the CUDA compatibility/translation core are forbidden.

## Native implementation

The implementation core is `src/fa3_cuda_compat_native.py`.

The first materialized source scope is deliberately narrow and explicit:

- input: CUDA **kernel source** subset;
- AMD lowering: HIP C++;
- Intel lowering: OpenCL C over the existing Intel/Level Zero/OpenCL hardware-execution path;
- NVIDIA: native CUDA remains independent and primary.

The implementation produces content-addressed source analysis and translation artifacts. A translation artifact is **not** an execution permit.

### V1 supported semantics

The V1 analyzer recognizes CUDA kernel entries, device helpers, shared memory, block barriers, and thread/block/grid index builtins. AMD/HIP lowering retains compatible kernel syntax and moves the runtime include to HIP. Intel/OpenCL lowering maps kernel entry syntax, pointer address spaces, CUDA index builtins, block dimensions, grid dimensions, shared memory and block barriers to their OpenCL equivalents.

### V1 fail-closed exclusions

The initial implementation does not claim complete CUDA parity. It rejects or marks unavailable, as applicable:

- CUDA host launch syntax and CUDA Runtime API host code;
- CUDA Driver API host code;
- dynamic parallelism;
- texture/surface APIs;
- cooperative groups;
- inline PTX;
- closed CUDA binaries, PTX, CUBIN and FATBIN input;
- on the Intel/OpenCL V1 target: CUDA warp intrinsics, CUDA atomics, CUDA half/BF16-specific types and CUDA constant-memory syntax.

A limitation is returned to the caller as structured compatibility findings. Unsupported functionality must not silently execute on CPU, another GPU, another provider or a cloud service.

## Hardware binding

The shared compatibility backend is named `cfa3-cuda-compat` and has backend class `translation`.

It is derived only from already discovered device-bound execution paths:

- AMD: device-bound ROCm/HIP;
- Intel: device-bound Level Zero, with OpenCL as the V1 translation target where admitted.

Physical device presence alone does not authorize execution. If exact binding cannot be established—for example, multiple same-vendor devices with only host-scoped discovery—the compatibility backend remains `HOST_UNBOUND` and unavailable.

## Authority boundary

Existing authorities remain unchanged:

- Hardware Discovery observes devices/backends;
- source analysis decides only whether the materialized translator subset can represent the requested CUDA kernel;
- HRB remains accelerator admission, placement, reservation and lease authority;
- Hardware Safety remains mandatory;
- Model Router remains model/provider routing authority;
- Evidence remains required for correctness, performance and promotion.

Neither the compatibility core nor any application becomes an architectural authority.

## Current Host and target-host evidence

No physical PASS is claimed by this implementation. Runtime promotion requires fresh exact-head physical positive, negative and rollback evidence.

Because AMD and Intel are separate physical execution targets, each target family requires its own supported physical host evidence before that target is promoted. Hosted CI proves only static structure and deterministic translator regressions.

## Distribution and coexistence

The compatibility source is CFA3-native and may be included in the CFA3 product bundle. External target toolchains and drivers remain separately governed; this change does not bundle or install ROCm, Intel runtimes, OpenCL ICDs, drivers, SCALE, or any unrelated host package.

No daemon, port, global PATH change, system loader replacement, driver mutation, package mutation or host-wide environment mutation is introduced.
