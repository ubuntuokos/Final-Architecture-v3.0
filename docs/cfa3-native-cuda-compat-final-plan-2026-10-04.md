# CFA3 Native CUDA Compatibility Fabric — final implementation plan

Date: 2026-10-04
PR: #700
Capability baseline: 175
Capability delta: 0
Authority delta: 0

## Owner-approved goal

Materialize one CFA3-owned, centrally shared CUDA compatibility fabric that every current and future CFA3 application can use through the same governed API. CUDA remains a backend interface rather than a capability. Application-local compatibility cores are forbidden.

Spectral Compute SCALE is a functional reference target only. It is not a build dependency, runtime dependency, installer dependency, binary-loading dependency, or activation requirement.

## Canonical boundaries

- Hardware Discovery observes devices and backend availability.
- Host Resource Broker remains the sole placement, reservation and lease authority.
- Hardware Safety retains precedence.
- Model Router remains the sole model/provider routing authority.
- Translation/build/runtime-compatibility artifacts never authorize execution.
- No silent backend, device, provider, CPU, cloud or reduced-function fallback.
- CPU-only remains a valid global platform baseline.
- Physical target-host PASS cannot be derived from static CI.

## Donor use

The implementation uses only donor records already published in the protected-main donor registry.

1. `FA3-DONOR-GPUOPEN-OROCHI-001`
   - architecture pattern for provider-neutral CUDA/HIP runtime-dispatch separation;
   - no source copy, runtime dependency, loader adoption or resource authority.

2. `FA3-DONOR-ROCM-EXAMPLES-001`
   - architecture/test pattern for CUDA/HIP portability smoke tests and explicit backend comparison;
   - no source copy, runtime dependency or current-host evidence inheritance.

Intel LLVM, SYCLomatic, Level Zero, Compute Runtime, LLVM/Clang and Khronos materials remain analysis/reuse-discovery references unless separately admitted for donor adoption. Unmerged donor PRs are excluded.

## Implementation architecture

### 1. Shared API
`src/fa3_cuda_compat_shared.py` remains the only application-facing functional core. It exposes compatibility candidate resolution, source translation preparation, build-plan preparation and runtime API compatibility inspection. Application/workload identity is provenance only, never an allowlist.

### 2. Structured CUDA frontend and IR
Replace direct V1 rewrite architecture with a structured frontend that masks comments/string bodies, extracts balanced CUDA kernel signatures/bodies, materializes typed parameter/kernel records, records runtime/driver/math calls and CUDA semantic features, and emits `fa3.cuda-compat-ir.v1`. This is bounded; it is not full C++/CUDA language parity.

### 3. AMD lowering
For the admitted V2 subset: CUDA kernel source → HIP C++; supported CUDA Runtime symbols → HIP equivalents; successful supported-subset translation is `FULL_EQUIVALENCE`; unsupported semantics fail closed. Physical execution still requires admitted ROCm + HRB lease.

### 4. Intel lowering
Primary: SYCL C++ over admitted Intel/Level Zero. Secondary: OpenCL C when explicitly requested/admitted. Current Intel lowering is `FUNCTIONALLY_REDUCED` because a governed host queue/launch adapter is required and CUDA stream/event semantics are not implicitly reproduced. Unsupported semantics fail closed.

### 5. Runtime compatibility map
Declarative runtime-API compatibility inspection: AMD CUDA Runtime → HIP mappings; Intel/SYCL mappings are explicitly reduced and require host-adapter/context semantics; unknown symbols are `UNAVAILABLE`. No execution authority.

### 6. Build compatibility
Fail-closed nvcc option normalizer/build-plan API. Known options are preserved; unknown options are rejected, never silently dropped. Architecture flags are request metadata, not resource authority. Compiler execution remains separately authorized.

### 7. Hardware discovery
NVIDIA native CUDA remains primary/independent. AMD uses ROCm/HIP. Intel uses Level Zero/SYCL primary with OpenCL secondary. Ambiguous host-only probes remain unavailable until exact device binding exists.

### 8. Compatibility classification
Every target result is `FULL_EQUIVALENCE`, `FUNCTIONALLY_REDUCED`, or `UNAVAILABLE`, with structured limitation disclosure.

### 9. Governance
The CUDA compatibility gate becomes a canonical mandatory reference gate executed by global static enforcement. It checks shared-only placement, capability/authority invariants, absence of SCALE dependency, donor decisions/usage edges, approved-plan binding, classification behavior, fail-closed source/build/runtime paths and pending physical Current Host requalification.

### 10. Tests
Static CI covers structured IR extraction, AMD HIP translation/runtime mapping, Intel SYCL/OpenCL lowering, classification semantics, unsupported-source failure, unknown-nvcc-option failure, universal shared access, hardware binding and mandatory gate integration.

## Current Host and promotion
No physical runtime PASS is claimed. AMD and Intel runtime promotion each require fresh exact-head physical positive, negative and rollback evidence on supported target hardware. NVIDIA native CUDA regression must remain unaffected.

## Explicit non-claims
No claim of full CUDA C++ parity, complete nvcc CLI parity, complete CUDA Driver/CUDA-X parity, PTX/CUBIN/FATBIN compatibility, closed CUDA binary compatibility, or arbitrary CUDA-application binary compatibility.

## Finalization rule
The owner approved this plan and implementation in conversation. Finalization/merge remains subject to exact-head owner approval and all mandatory gates. No owner exception is inferred.
