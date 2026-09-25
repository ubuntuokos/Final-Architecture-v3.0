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

## Multidimensional resource admission current-host closure

`FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001` requires live Host Attestation, a measured Compute Profile, a non-empty workload envelope, a current scope-bound HRB admission authorization, and PASS for every declared resource dimension.

Every workload requires HRB admission authorization. The mechanism depends on the workload:

- **CPU-only / non-accelerator:** a short-lived `fa3.hrb-admission-authorization.v1` is issued by the existing HRB authority and bound to host, workload ID, exact workload-envelope SHA-256 and requested resource classes. It is not a lease.
- **Accelerator workload:** the existing `FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1` remains required and can serve as the HRB authorization source for that accelerated execution.

A CPU-only workload must not require accelerator discovery or an accelerator lease. `CU`/`TU` values remain diagnostic-only and are forbidden as admission requirements.

### HRB privilege separation

Use the combined one-time installer:

```bash
sudo ./bin/fa3-install-host-admission-bridge.sh --user "$USER"
```

It installs the generic admission client, accelerator acquire client and accelerator validator. Both HMAC secret domains remain root-only. The non-root runner can request only typed authorization/validation operations through narrow sudo helpers; collector, provider and orchestrator cannot mint their own authorization.

The default smoke now exercises the vendor-neutral CPU-only path:

```bash
./bin/fa3-resource-admission-current-host.sh smoke
```

For a custom CPU-only workload, the lower-level path is:

```bash
/usr/local/bin/fa3-host-resource-broker-admission authorize \
  --workload .fa3-current-host/input/resource-workload-envelope.json \
  --output .fa3-current-host/input/resource-hrb-authorization.json

./bin/fa3-resource-admission-current-host.sh collect \
  --workload-envelope .fa3-current-host/input/resource-workload-envelope.json \
  --hrb-authorization .fa3-current-host/input/resource-hrb-authorization.json

./bin/fa3-enforce resource-admission-current-host
```

Accelerator workflows continue to use `--hrb-lease` or the admitted acquire bridge and are not silently rerouted to CPU.

A successful receipt may claim only `CURRENT_HOST_RESOURCE_ADMISSION_PASS` and must keep `GLOBAL_FA3_PROMOTION` as a non-claim.

## FFmpeg neural-media current-host closure

The executable closure for `FA3-NEURAL-MEDIA-EXECUTION-001` is `FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001`. It is deliberately fail-closed and does not derive a PASS from CI, documentation, a static GPU ordinal, or the earlier HRB/CUDA component evidence alone.

A real run requires two attributed local inputs:

- an unexpired `fa3.hrb-placement-receipt.v1` from `FA3-AUTH-HOST-RESOURCE-BROKER-001`, workload `NEURAL_MEDIA`, bound to live GPU UUID + PCI BDF;
- a `fa3.ffmpeg-build-trust-receipt.v1` proving an immutable signed upstream release or signed distribution package and matching the installed FFmpeg binary SHA-256.

The collector performs no network model fetch. It generates a tiny deterministic ONNX Identity model and a synthetic BT.709 A/V golden clip locally, proves ONNX Runtime CUDA execution without CPU fallback, executes hardware decode → `scale_cuda` → NVENC → mux, then measures VMAF/SSIM/PSNR plus A/V duration, timestamp monotonicity and color/HDR expectations. Stable FFmpeg 9.0.1 DNN zero-copy is explicitly **not** claimed.

Run on the current admitted host:

```bash
bin/fa3-ffmpeg-ai-current-host.sh \
  .fa3-current-host/input/ffmpeg-ai-hrb-placement.json \
  .fa3-current-host/input/ffmpeg-ai-build-trust.json

./bin/fa3-enforce ffmpeg-ai-current-host
```

Or dispatch `FA3 FFmpeg Neural Media Current-Host E2E` with `execute_current_host=true`. A component PASS remains separate from the 143-capability Evidence Registry closure and the 19-point global promotion gate.
