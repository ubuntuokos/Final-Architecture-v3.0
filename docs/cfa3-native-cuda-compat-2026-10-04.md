# CFA3 Native CUDA Compatibility Fabric

## Decision

CFA3 implements CUDA-oriented compatibility as one **CFA3-owned shared platform service** available to every current and future CFA3 application. Spectral Compute SCALE remains a functional reference target only and is **not** a build dependency, runtime dependency, binary-loading dependency, installer dependency, or activation requirement.

CUDA remains a backend interface, not a CFA3 capability. The capability baseline remains 175 and no new architectural authority is introduced.

The owner-approved implementation plan is `docs/cfa3-native-cuda-compat-final-plan-2026-10-04.md`.

## Central application access

Every application uses the same shared interfaces:

- `resolve_cuda_compatibility` — target/device compatibility candidates;
- `prepare_cuda_compat_translation` — content-addressed translation preparation;
- `prepare_cuda_compat_build` — fail-closed nvcc-style build-plan normalization;
- `inspect_cuda_runtime_compatibility` — declarative CUDA Runtime API compatibility inspection.

All are exposed by `src/fa3_cuda_compat_shared.py`. There is no per-application allowlist. Application/workload identity is provenance and audit context only. Application-local CUDA compatibility cores are forbidden.

Candidate resolution, translation artifacts, build plans and runtime maps **do not authorize execution**.

## V2 structured implementation

V2 separates the compatibility pipeline into:

- `fa3_cuda_compat_frontend.py` — bounded structured CUDA frontend;
- `fa3_cuda_compat_ir.py` — typed CUDA compatibility IR;
- `fa3_cuda_compat_backends.py` — target lowerers;
- `fa3_cuda_compat_runtime.py` — bounded Runtime API compatibility map;
- `fa3_cuda_compat_build.py` — fail-closed nvcc option/build planning;
- `fa3_cuda_compat_native.py` — target analysis/translation coordination;
- `fa3_cuda_compat_shared.py` — application-wide shared API.

The frontend extracts balanced kernel signatures and bodies, typed parameters, runtime/driver/math calls and supported semantic features. It is intentionally bounded and **does not claim to be a complete C++ or CUDA compiler frontend**.

## Target matrix

### NVIDIA

Native CUDA remains independent and primary when admitted. The CFA3 translation backend does not silently replace it.

### AMD

The supported V2 subset lowers to HIP C++ over the admitted ROCm path.

For the precisely admitted subset, successful translation is classified `FULL_EQUIVALENCE`. This classification is not a full-CUDA claim; unsupported features or runtime symbols are `UNAVAILABLE` and fail closed.

The bounded runtime map covers selected device, allocation/copy/set, synchronization, stream/event and error-query calls where an explicit HIP equivalent is declared.

### Intel

Primary translation target: SYCL C++ over an admitted Level Zero/SYCL execution path.

Secondary target: OpenCL C when explicitly requested and admitted.

The current Intel V2 source path is classified `FUNCTIONALLY_REDUCED`: host queue/launch integration remains a governed adapter responsibility and CUDA stream/event semantics are not silently inferred. The limitation is returned as structured data for user-visible disclosure.

## Compatibility classifications

Every assessed target is one of:

- `FULL_EQUIVALENCE`
- `FUNCTIONALLY_REDUCED`
- `UNAVAILABLE`

A reduced result must disclose the relevant limitations. An unavailable result fails closed. Device presence or a compiler/runtime claim alone never establishes equivalence.

## Build compatibility

The shared build planner accepts a bounded set of nvcc-style source, include/define, language, optimization, relocatable-device-code and architecture-request arguments.

Unknown options are rejected. They are never silently dropped.

A build plan is not compiler execution authorization and does not grant accelerator access.

## Runtime compatibility

The runtime compatibility service reports explicit CUDA→target symbol mappings and their classification. AMD mappings target the admitted HIP API surface; Intel mappings are explicitly reduced SYCL host-adapter semantics.

Unknown symbols are `UNAVAILABLE`.

## Donor-informed implementation

Two already-published canonical donors are adopted only as architecture/test patterns:

- `FA3-DONOR-GPUOPEN-OROCHI-001` — provider-neutral CUDA/HIP runtime-dispatch boundary pattern;
- `FA3-DONOR-ROCM-EXAMPLES-001` — CUDA/HIP portability smoke-test and explicit backend-comparison pattern.

No donor source code is copied and neither donor becomes a runtime dependency or authority. Pending donor PRs are excluded.

## Fail-closed exclusions

This implementation does **not** claim:

- full CUDA C++ language parity;
- complete nvcc CLI parity;
- complete CUDA Driver API parity;
- complete CUDA-X library parity;
- dynamic parallelism, texture/surface or cooperative-group parity where not explicitly admitted;
- arbitrary inline PTX translation;
- PTX, CUBIN or FATBIN input compatibility;
- closed CUDA binary compatibility;
- arbitrary CUDA application binary compatibility.

Unsupported semantics return structured findings instead of silently running on CPU, another GPU, another provider or cloud.

## Hardware and authority boundary

Hardware Discovery observes devices and backends. HRB remains the exclusive placement/reservation/lease authority. Hardware Safety remains mandatory. Model Router remains model/provider routing authority. The Evidence authority remains responsible for promotion evidence.

The display-GPU policy and CPU-only global baseline are unchanged.

## Current Host and target-host evidence

No physical PASS is claimed by this implementation.

AMD and Intel target promotion each require fresh exact-head physical positive, negative and rollback evidence on supported target hardware. Static CI proves only deterministic structure and regression behavior.

## Distribution and coexistence

The compatibility implementation is CFA3-native source and may be included in the CFA3 bundle. External ROCm, SYCL/Level Zero, OpenCL, CUDA or other toolchains/drivers remain separately governed and are not implicitly bundled or installed.

No daemon, socket, port, global PATH mutation, loader replacement, driver mutation, package mutation or host-wide environment mutation is introduced.
