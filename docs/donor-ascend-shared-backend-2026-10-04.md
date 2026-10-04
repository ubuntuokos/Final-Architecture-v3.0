# CFA3 Ascend shared-backend donor intake — 2026-10-04

## Scope

This intake stages the external references processed while preparing the owner-approved CFA3 Ascend shared accelerator backend plan.

The owner explicitly enabled the implementation-plan donor-analysis exception for the originating conversation and then approved the completed plan. Under that bounded exception, the exact processed source set must be registered before implementation execution. This branch does **not** start implementation and does **not** claim canonical donor publication while the rolling donor-intake window is full.

Published parent main:

- `b5052f6595a3fdad84ed7a06e6276f8af5a8dcd8`
- donor registry blob: `1362d75186c6da74e5cf947fdf0b8867d462636a`
- donor registry count: **1427**
- capability baseline: **175**

## Processed source set

| Source | Planned classification | Observed revision / version | Rights observation |
| --- | --- | --- | --- |
| https://github.com/Ascend/pytorch | ACCEPTED_REFERENCE / REFERENCE_IMPLEMENTATION | `9cd8d1f1483f8268944d80392d4aa91fd455339f` | GitHub reports NOASSERTION; root LICENSE is mixed/inherited. File-level License & Rights review required before copying. |
| https://github.com/Ascend/torchair | ACCEPTED_REFERENCE / REFERENCE_IMPLEMENTATION | `e1118e8b0fc1b95190ab53b732c0872989550e20` | GitHub reports NOASSERTION; root LICENSE is mixed/inherited. File-level License & Rights review required before copying. |
| https://github.com/triton-lang/triton-ascend | ACCEPTED_REFERENCE / REFERENCE_IMPLEMENTATION | `35c55ba0d2351a919fed8f9bdddcbb3acaae0ac9` | MIT at repository root. |
| https://github.com/Ascend/triton-ascend | SUPERSEDED / MIGRATION_PROVENANCE_ONLY | `865691e2e9b656bc58008170207b4108d92e8dd1` | MIT; observed head states that the repository moved to `triton-lang/triton-ascend`. Do not select it as primary upstream. |
| https://github.com/vllm-project/vllm-ascend | ACCEPTED_REFERENCE / REFERENCE_IMPLEMENTATION | `7df96048756856e4d30f29618129e9942ba6985c` | Apache-2.0 at repository root. |
| https://github.com/Ascend/samples | ACCEPTED_REFERENCE / API_USAGE_EXAMPLES | `fc2aea93e48be8f8cee51d0c6c1b13a08155f83a` | Apache-2.0 at repository root. |
| https://github.com/microsoft/onnxruntime | ACCEPTED_REFERENCE / INTEROPERABILITY_REFERENCE | `690e73121061595a6fc15f1f4b29afcda1d666dc` | MIT at repository root. |
| https://www.hiascend.com/document/detail/en/CANNCommunityEdition/910/index/index.html | ACCEPTED_REFERENCE / EXTERNAL_RUNTIME_DOCUMENTATION | CANN 9.1.X | Vendor documentation/reference only. CANN downloads/runtime packages are subject to Huawei terms/EULA; no bundling or redistribution is authorized by this intake. |

## Intended CFA3 use after canonical admission

These references support a single shared accelerator backend, not application-local ports:

```
CFA3 application
  -> capability layer
  -> Model Router / accelerator routing
  -> Shared Accelerator Fabric
  -> Ascend backend
       -> TorchNPU
       -> TorchAir / GE
       -> Triton-Ascend
       -> ONNX Runtime CANN EP
       -> vLLM-Ascend
       -> ACLNN / AscendCL / Ascend C
       -> CANN
       -> Ascend NPU
```

The existing CUDA portability rule remains authoritative: CUDA is a backend rather than a capability. Strongly CUDA-oriented functionality is assessed for target-hardware equivalence and may traverse at most five technical donor dependency layers. Shared-only placement, explicit limitation disclosure and fail-closed unavailable behavior remain mandatory.

## Rights and reuse disposition

### A — potentially reusable after normal review

- `triton-lang/triton-ascend` — MIT
- `vllm-project/vllm-ascend` — Apache-2.0
- `Ascend/samples` — Apache-2.0
- `microsoft/onnxruntime` — MIT

These licenses are permissive at the repository root, but actual material reuse still requires exact-file provenance, dependency/license review, Security, Software Coexistence and applicable Hardware Safety/runtime gates.

### B — reference-first pending file-level clearance

- `Ascend/pytorch`
- `Ascend/torchair`

GitHub metadata reports `NOASSERTION`, and the root LICENSE text contains inherited multi-project notices. These are useful technical references, but source copying/import is blocked until the License & Rights Authority clears the exact files/dependencies selected.

### C — external vendor runtime boundary

- CANN 9.1.X documentation

CANN is treated as an externally installed vendor runtime/toolkit. This intake does not authorize bundling, redistribution, automated installation, EULA acceptance, driver/firmware mutation or runtime promotion. Exact deployment requires a separate rights, hardware compatibility, driver/firmware/CANN version and Current Host/target-host qualification.

### D — superseded provenance only

- `Ascend/triton-ascend`

The observed head explicitly redirects development to `triton-lang/triton-ascend`. The legacy repository is retained only so provenance is not lost.

## Usage-edge boundary

This intake creates **zero** donor usage edges.

The approved plan may not consume these donors for implementation until:

1. the records are published in the canonical donor registry;
2. the implementation-plan exception is canonically enforceable on published main;
3. Reuse Discovery and License & Rights run against that published donor snapshot;
4. each actually adopted donor receives an explicit typed usage edge;
5. normal Security, Software Coexistence, Hardware Safety, HRB, Model Router and runtime gates pass.

## FIFO state

The currently observed active donor-intake window remains:

`#651, #657, #663, #664, #671`

Observed donor-intake requests waiting ahead include:

`#672, #673, #675, #676, #682, #683, #684, #686, #693, #699`

Therefore this branch is intentionally **FIFO waiting**. It does not mutate `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`.

In addition, the implementation-plan exception is represented by open PR **#701** but is not yet published on the verified parent main. Until the required policy is canonical and this intake reaches an available slot, these identities remain non-canonical planning references only.

## Invariants

- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- provider-count policy: dynamic / unchanged
- runtime activation: none
- package installation: none
- hardware mutation: none
- Current Host PASS: none
- implementation authorization: blocked until donor publication and subsequent approved stage
