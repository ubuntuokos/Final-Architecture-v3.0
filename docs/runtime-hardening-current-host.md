# FA3 Runtime Hardening — Current-Host Closure

This closure materializes real current-host evidence collection for the cross-cutting runtime-hardening decision without changing the 143-capability baseline or any architectural authority.

## Required surfaces

The current-host gate is PASS only when every applicable surface is fresh, bound to the checked repository HEAD, non-synthetic, and individually PASS. The media-residency surface is conditional: CPU-only and non-claiming workloads do not require an accelerator or an accelerator provider.

### 1. Runtime isolation + agent sandbox

- cgroup v2 must be present.
- A preloaded image must execute under rootless Podman with network disabled, read-only root, all capabilities dropped, no-new-privileges and image pulling disabled.
- Wasmtime must execute a WASM module without filesystem preopens or a network lease.
- gVisor needs both a rootless compatibility smoke and a separate production OCI isolation proof.

runsc --rootless do is deliberately not accepted as production isolation proof because it exposes the host filesystem read-only by default. A production proof must demonstrate an explicit mount allowlist, default-deny network behavior and ephemeral writable state.

### 2. Conditional accelerator memory-residency claim

- The selected provider must bind to a compatible accelerator through a fresh HRB lease.
- A provider-specific trace must prove memory-domain and shared-buffer identity.
- No frame may be converted to CPU memory.
- Transfer telemetry is advisory and no universal PCIe percentage threshold is an admission decision.
- No claim is made that demux, compressed-input transport, decoding, encoding, or the complete media pipeline is literally copy-free.

PyNvVideoCodec remains an optional NVIDIA adapter for this proof. It is not a global runtime-hardening dependency.

### 3. Hungarian AQC

- PCM16 WAV signal integrity is recomputed locally.
- CER/WER is recomputed locally from reference text and ASR back-transcription.
- Language, grammar/register, toxicity, perceptual quality and optional speaker-identity scorers must carry model digests, versions, admitted licenses and current-host provenance.
- All required dimensions must pass independently.

### 4. Shadow execution

- It depends on a passed current-host sandbox receipt.
- Input is synthetic or sanitized.
- Output stays quarantined and non-authoritative.
- The ephemeral workspace is destroyed.
- The run cannot set PROMOTED or acquire promotion authority.


## Real-execution preflight

Before any of the four collectors run, the self-hosted workflow now executes `src/fa3_runtime_hardening_current_host_preflight.py`. It fails closed unless all execution prerequisites are already present on the current host.

The preflight requires:

- a PASS runner-doctor receipt proving the labeled runner is online;
- rootless execution;
- local `podman`, `wasmtime` and `runsc`;
- `nvidia-smi`, `pynvml`, `PyNvVideoCodec` and `torch` only when the optional NVIDIA media claim is explicitly requested;
- an installed digest-pinned agent Quadlet with `Network=none`, read-only root, no-new-privileges, drop-all capabilities, `Pull=never` and `runsc`;
- a running agent container whose actual Podman inspection resolves to `runsc`;
- an immutable, already preloaded OCI image. Network pulling remains forbidden;
- an exact host-attestation reference;
- a valid PASS `CURRENT_HOST_ADMISSION` Evidence Envelope with provider-compatible HRB accelerator binding only when the media claim is requested;
- when an explicit zero-host-round-trip claim is requested, a PASS `fa3.accelerator-copy-trace.v1` produced by the selected provider trace adapter, with zero frame H2D/D2H transfers and zero host frame round-trips;
- the approved local media input only when the media claim is requested;
- the Hungarian PCM16 AQC audio and JSON scorer bundle;
- nvproxy driver compatibility when GPU projection into the gVisor sandbox is explicitly requested.

The result is written to `.fa3-current-host/runtime-hardening/preflight.json`.

A preflight PASS means only `READY_FOR_REAL_EXECUTION`. It is not a runtime-hardening surface PASS receipt, does not promote the component, and cannot claim global FA3 promotion.

## Operator execution

Use the FA3 Runtime Hardening Current-Host Closure workflow with execute_current_host=true on the runner carrying all labels: self-hosted, linux, x64, fa3-current-host.

The workflow does not install packages, pull container images, download models, or create credentials. All prerequisites and test artifacts must already be locally admitted.

The expected status before the real run is EXECUTABLE_CLOSURE_MATERIALIZED_REAL_EXECUTION_PENDING.

A failed real-execution job means at least one required surface remains unproven. It must not be converted to PASS by substituting hosted CI, a synthetic receipt, a provider-only receipt or documentation.
