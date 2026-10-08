# FA3 inference portability: admission and evidence delta (2026-09-28)

Status: implementation specification; no production promotion or new authority.
Governing baseline: FA3-INFERENCE-PORTABILITY-001 v1.2.0, FA3-INFERENCE-PORTABILITY-CACHE-HARDENING-001, FA3-INFERENCE-PORTABILITY-RECONCILIATION-001, FA3-DEC-INFERENCE-PORTABILITY-RECONCILIATION-2026-09-23.

## Verified repository delta

The September 23 canonical decision **already** records OpenVINO 2026.4.0, ONNX Runtime 1.30.0, TensorRT 11.3.0.99 / CUDA 13.4, TensorRT-RTX 1.6.1.120 and TensorRT-RTX EP ABI 0.4.2 as **reference only**. Do not duplicate those releases as a new capability, new authority or production pin. The existing contract already requires GPU SKU, exact TensorRT-RTX version, CUDA-context CiG state and cache-origin driver, cache/JIT evidence, and cold-vs-steady-state benchmarking. Focus on enforceable missing evidence and negative tests rather than renaming established contracts.

## Required implementation work

1. **Support-matrix admission**: each provider scope records exact installed version, package origin and digest, resolved executable/interpreter/library paths and SHA-256, loader environment, driver version/channel separately from CUDA compatibility, provider-specific runtime ABI and device/backend binding. Validate OpenVINO Intel CPU/GPU/NPU dependencies, ONNX Runtime shared-EP ABI and CUDA/cuDNN pairing, TensorRT engine/plugin ABI and compatibility mode, and TensorRT-RTX standalone EP ABI dependency closure. Missing providers are NOT_PRESENT_IN_PROBE_ENVIRONMENT, not a host-wide absence claim. Never auto-install or fetch a model.
2. **EP lifecycle**: for shared providers, prove load, ABI handshake, session create, execute, session teardown and library unloading or documented process-isolation requirement. Record module identity, dependency resolution and failure reasons. Never rely on unpinned global loader-path discovery for production admission.
3. **TensorRT-RTX runtime cache**: retain existing four-field fingerprint. Validate exact/evidenced-equivalent GPU SKU, exact runtime version, exact CiG state and runtime driver >= cache-origin driver. An evidence string of PASS alone must not establish SKU equivalence: require evidence identifying both SKUs, the compatibility rule and source. An incompatible cache must not be reported as a hit; capture observed reject/miss, JIT start/finish, rebuilt artifact hash, and a clear observability source. Do not claim JIT occurred solely because a static compatibility check failed; if upstream rebuild is transparent and unobservable, mark production admission INSUFFICIENT_EVIDENCE.
4. **Benchmark receipts**: record cold first-inference latency, warmup/JIT timing when observable, warmup count, steady-state sample count/distribution, cache state and model/device/driver/runtime pin. A cache-miss/JIT run cannot be labeled a cache-hit benchmark. Retain deprecated ITimingCache prohibition for new integrations; add a source/dependency scan and negative fixture.
5. **Hardware and authority**: zero-to-N accelerators and CPU-only hosts conform. Accelerator requires discovered DEVICE-bound available compatible backend plus exact HRB device/execution-path lease. Backend loss invalidates lease and affected derived-cache reuse pending readmission. Model Router is sole logical model/provider/runtime router; inference portability handles eligibility/build/execute/evidence; LiteLLM is data plane only. Agent Native must use typed UAF and cannot bypass Router, HRB, security or adapters. Providers do not expand AI participant topology. Jev only reranks a deterministic eligible set. No silent CPU/device/backend/cloud substitution. Respect display-GPU explicit assignment policy.
6. **Provider priority**: retain canonical priority and explicit policy; do not infer a new global provider ranking from upstream release numbers or benchmarks. Change only via an explicit canonical decision and admitted workload-specific evidence.

## Tests / closure

- Positive and negative fixtures for CPU-only, multiple GPUs, absent DEVICE-bound backend, lost backend and stale lease.
- ABI mismatches, loader-path collision, missing dependency, incompatible CUDA/cuDNN, unsupported device/runtime and unsupported opset/shape/precision.
- TensorRT-RTX same-SKU hit; evidenced-equivalent-SKU hit; unsupported equivalence reject; version/CiG/older-driver reject; newer-driver compatibility; cache reject with observed JIT; cache reject without JIT observability must block production promotion.
- Warmup versus steady-state benchmark receipts, forbidden ITimingCache integration, no silent fallback, UAF bypass, AI participant expansion and Jev candidate injection.
- Run existing portability, cache-hardening, reconciliation and current-host admission gates. Publish immutable receipt digests, exact tested scope and negative-test outcomes. Do not claim hardware E2E from synthetic CI fixtures.
- A new upstream version stays reference-only until scope-bound support-matrix admission, real current-host E2E, correctness/performance evidence and all mandatory gates PASS. Do not reopen historical 429/429 closure solely because a reference changed.

## Delivery sequence

A. Baseline/donor-registry reconciliation and provider-record diff.
B. EP ABI/package support-matrix receipts and tests.
C. Cache/JIT observability and benchmark regression tests.
D. Hardware/HRB/Router/UAF/Jev negative tests.
E. Current-host provider-specific execution, evidence and gate review.
F. Promote only explicitly admitted scopes in a separate reviewed decision; retain existing production pins otherwise.

The current document is an implementation plan and does **not** attest that E2E, CI or current-host admission has passed.
