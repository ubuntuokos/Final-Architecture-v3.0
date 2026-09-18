# FA3 Runtime Hardening — Current-Host Closure

This closure materializes real current-host evidence collection for the cross-cutting runtime-hardening decision without changing the 143-capability baseline or any architectural authority.

## Required surfaces

The current-host gate is PASS only when all four surfaces are fresh, bound to the checked repository HEAD, non-synthetic, and individually PASS.

### 1. Runtime isolation + agent sandbox

- cgroup v2 must be present.
- A preloaded image must execute under rootless Podman with network disabled, read-only root, all capabilities dropped, no-new-privileges and image pulling disabled.
- Wasmtime must execute a WASM module without filesystem preopens or a network lease.
- gVisor needs both a rootless compatibility smoke and a separate production OCI isolation proof.

runsc --rootless do is deliberately not accepted as production isolation proof because it exposes the host filesystem read-only by default. A production proof must demonstrate an explicit mount allowlist, default-deny network behavior and ephemeral writable state.

### 2. PyNvVideoCodec zero-host-round-trip neural segment

- A fresh HRB UUID + PCI BDF binding must map to the same live NVIDIA GPU.
- PyNvVideoCodec 2.2+ must decode with device memory.
- The decoded frame must export DLPack and the PyTorch tensor must have identical GPU pointer identity.
- No frame may be converted to CPU memory.
- PCIe Rx/Tx telemetry is captured around a GPU-only neural-segment exercise.
- No claim is made that demux, compressed-input transport, decoding, encoding, or the complete media pipeline is literally copy-free.

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

## Operator execution

Use the FA3 Runtime Hardening Current-Host Closure workflow with execute_current_host=true on the runner carrying all labels: self-hosted, linux, x64, fa3-current-host.

The workflow does not install packages, pull container images, download models, or create credentials. All prerequisites and test artifacts must already be locally admitted.

The expected status before the real run is EXECUTABLE_CLOSURE_MATERIALIZED_REAL_EXECUTION_PENDING.

A failed real-execution job means at least one required surface remains unproven. It must not be converted to PASS by substituting hosted CI, a synthetic receipt, a provider-only receipt or documentation.
