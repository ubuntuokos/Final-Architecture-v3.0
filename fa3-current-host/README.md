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

`verify` checks the current-host projection against the canonical policy, the exact `CAP-001..CAP-143` conformance surface, the 143-record Evidence Registry, registered collectors/gates, and the unified release manifest.

`collect` runs the existing read-only host fingerprint collector. Successful collection remains `COLLECTED_UNVALIDATED`; it is never converted to `PASS` merely because collection succeeded.

`gate` runs the global static, runtime, and 19-point acceptance gates. Exit code `2` means fail-closed blocking, not a successful promotion.

`all` performs `verify → collect → gate`. It deliberately does **not** promote.

`promote` is explicit and delegates to the existing FA3 promotion guard. It succeeds only when current-host evidence and all 19 acceptance criteria are already PASS.

## Current-host execution

CI validates only the projection structure. Real host execution is opt-in through `.github/workflows/fa3-current-host.yml` on a self-hosted runner labeled:

```text
self-hosted, linux, x64, fa3-current-host
```

No GitHub-hosted runner may claim current-host production evidence for the workstation.

## FFmpeg neural-media current-host closure

The executable closure for `FA3-NEURAL-MEDIA-EXECUTION-001` is `FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001`. It is deliberately fail-closed and does not derive a PASS from CI, documentation, a static GPU ordinal, a reference workstation model, or earlier component evidence alone.

The Dell Precision Tower 7910 / 2× Xeon E5-2696 v4 / observed 44C-88T / two-NUMA tuple is retained only as **non-normative current-host evidence**. It is not an admission requirement. Live CPU/NUMA/GPU topology is rediscovered for every execution; accelerator placement remains exclusively owned by the Host Resource Broker.

A production run requires three attributed local inputs plus the admitted binaries:

- a non-synthetic real H.264 A/V SDR BT.709 golden media file and matching `fa3.real-media-input-provenance.v1` receipt; this format/color profile is an evidence-fixture constraint, not a provider capability limit;
- a canonical `FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1`, signed, unexpired, purpose-scoped to FA3 FFmpeg, and accepted by `fa3-host-resource-broker validate-lease`; GPU UUID + PCI BDF are canonical identity and the CUDA ordinal is derived only after validation;
- a `fa3.ffmpeg-build-trust-receipt.v2` proving an immutable signed upstream release or signed distribution package and binding **both** installed `ffmpeg` and `ffprobe` SHA-256 values.

The collector performs no network model fetch. It generates only the tiny deterministic ONNX Identity test model locally. Production PASS then proves:

1. real-media CPU-vs-CUDA ONNX identity-frame equivalence and observed ONNX Runtime CUDA provider with no silent CPU fallback;
2. real-media decode → filter → neural processing → NVENC encode → mux;
3. a separate CUDA-hwframes → `scale_cuda` → NVENC GPU-resident media path;
4. VMAF/SSIM/PSNR, A/V duration, timestamp monotonicity and fixture-scoped color/HDR validation;
5. explicit copy-boundary accounting. Stable FFmpeg 9.0.1 DNN zero-copy is still **not** claimed.

Run on any FA3-qualified Linux/NVIDIA current host with the required authority/evidence inputs:

```bash
bin/fa3-ffmpeg-ai-current-host.sh \
  .fa3-current-host/input/ffmpeg-ai-real-golden.mp4 \
  .fa3-current-host/input/ffmpeg-ai-real-golden-provenance.json \
  .fa3-current-host/input/ffmpeg-ai-accelerator-lease.json \
  .fa3-current-host/input/ffmpeg-ai-build-trust.json

./bin/fa3-enforce ffmpeg-ai-current-host
```

Or dispatch `FA3 FFmpeg Neural Media Current-Host E2E` with `execute_current_host=true`. A component PASS remains separate from the 143-capability Evidence Registry closure and the 19-point global promotion gate.
