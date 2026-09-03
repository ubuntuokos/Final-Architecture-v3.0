# FA3 Current Host

`fa3-current-host` is the executable current-host runtime and evidence projection for FINAL ARCHITECTURE v3.0.

It is **not** a new canonical profile, capability, provider authority, or architectural authority. Canonical identity and policy remain in `canonical/` under `FA3-REGISTRY-001`; this directory only coordinates current-host collection, validation, admission evidence, and fail-closed promotion checks.

## Invariants

- canonical capability count: **143**
- new capabilities: **0**
- new architectural authorities: **0**
- document-only promotion: **forbidden**
- automatic promotion: **disabled**
- secret collection: **prohibited**
- Linux Recovery/Rebuild projection: **out of scope**
- raw current-host state: stored under `/.fa3-current-host/` and ignored by Git

## Commands

```bash
./bin/fa3-current-host verify
./bin/fa3-current-host collect
./bin/fa3-current-host gate
./bin/fa3-current-host status
./bin/fa3-current-host all
./bin/fa3-current-host promote
```

`verify` checks the current-host projection against canonical policy, the exact `CAP-001..CAP-143` conformance surface, the 143-record Evidence Registry, registered collectors/gates, and the unified release manifest.

`collect` runs the existing read-only host fingerprint collector. Successful collection remains `COLLECTED_UNVALIDATED`; it is never converted to `PASS` merely because collection succeeded.

`gate` runs the global static, runtime, and 19-point acceptance gates. Exit code `2` means fail-closed blocking, not a successful promotion.

`all` performs `verify → collect → gate`. It deliberately does **not** promote.

`promote` is explicit and delegates to the existing FA3 promotion guard. It succeeds only when current-host evidence and all 19 acceptance criteria are already PASS.

## Current-host execution

CI validates only projection structure and executable regressions. Real host execution is opt-in through self-hosted workflows on a runner labeled:

```text
self-hosted, linux, x64, fa3-current-host
```

No GitHub-hosted runner may claim current-host production evidence for a workstation.

## FFmpeg neural-media current-host closure

`FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001` is a **portable execution-conformance prerequisite**, not production neural-media E2E evidence. The 2026-09-03 audit correction is recorded in `FA3-DEC-FFMPEG-AI-CURRENT-HOST-AUDIT-2026-09-03`.

The collector follows `FA3-HARDWARE-BASELINE-001` and `FA3-HARDWARE-DISCOVERY-CONTRACTS-001`: CPU affinity/cgroup/NUMA and accelerator topology are discovered live. A Dell T7910, E5-2696 v4, a concrete GPU SKU, fixed PCI BDF, or a CUDA ordinal may appear in evidence as a non-normative current-host fact, but none is a portable production admission constant.

A real execution-conformance run requires:

- an active canonical `FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1`, issued by `FA3-HOST-RESOURCE-BROKER-001`, validated by the canonical broker, and revalidated against live GPU UUID + PCI BDF;
- a `fa3.ffmpeg-build-trust-receipt.v2` proving stable immutable version identity, installed binary hash match, signature verification with verifier identity, SBOM hash, and provenance-attestation hash.

The smoke collector performs no network model fetch. It generates a deterministic ONNX Identity model and synthetic BT.709 A/V clip locally. Those fixtures can prove only:

- observed ONNX Runtime CUDA execution with no silent CPU fallback;
- observed H.264 CUVID decode → `scale_cuda` → NVENC execution from verbose FFmpeg evidence;
- mux/container/codec/stream validation;
- fixture-scoped VMAF/SSIM/PSNR, A/V, timestamp, color/HDR checks;
- rollback, negative tests and an execution-evidence hash chain.

Stable FFmpeg 9.0.1 DNN zero-copy is explicitly **not** claimed.

Run on any hardware admitted by the portable FA3 baseline:

```bash
bin/fa3-ffmpeg-ai-current-host.sh \
  .fa3-current-host/input/ffmpeg-ai-accelerator-lease.json \
  .fa3-current-host/input/ffmpeg-ai-build-trust-v2.json

./bin/fa3-enforce ffmpeg-ai-current-host
```

A PASS from this gate means `CURRENT_HOST_FFMPEG_EXECUTION_CONFORMANCE_PASS` only. It does **not** satisfy `CURRENT_HOST_FFMPEG_NEURAL_MEDIA_PRODUCTION_E2E_PASS`.

Production runtime admission separately requires real or curated admitted media, a real admitted neural model from `FA3-MODEL-REGISTRY-001` with identity/hash/license/provenance, an actual neural transform, task-specific production QA, artifact provenance and rollback. Only after that separate evidence exists may the FFmpeg profile become runtime-promotion eligible; global FA3 promotion still remains behind the 143-capability Evidence Registry and 19-point acceptance gate.
