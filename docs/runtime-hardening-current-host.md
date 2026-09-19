# FA3 Runtime Hardening — Current-Host Closure

This closure materializes real current-host evidence collection for the cross-cutting runtime-hardening decision without changing the 143-capability baseline or any architectural authority.

## Required surfaces

The current-host gate is PASS only when all four surfaces are fresh, bound to the checked repository HEAD, non-synthetic, and individually PASS.

### 1. Runtime isolation + agent sandbox

- cgroup v2 must be present.
- The installed FA3 agent-sandbox Quadlet must be present, digest-pinned, network-deny, read-only, no-new-privileges, capability-drop-all and Pull=never.
- A preloaded image must execute under rootless Podman with the OCI runtime explicitly selected as runsc.
- The successful runsc container execution is the operational runtime proof; Podman inspect data is retained only as supplementary evidence because inspect field names may vary by Podman version.
- Wasmtime must execute a WASM module without filesystem preopens or a network lease.
- If a GPU is projected into the gVisor sandbox, nvproxy must accept the current NVIDIA driver ABI and unsupported-driver override is forbidden.

runsc --rootless do remains a compatibility smoke only. It cannot substitute the production Podman/runsc container execution.

### 2. PyNvVideoCodec zero-host-round-trip neural segment

- A validated FA3-EVIDENCE-ENVELOPE-001 CURRENT_HOST_ADMISSION PASS is mandatory; its HRB UUID + PCI BDF binding must map to the same live NVIDIA GPU.
- PyNvVideoCodec 2.2+ must decode with device memory.
- The decoded frame must export DLPack and the PyTorch tensor must have identical GPU pointer identity. This proves shared decode-to-tensor GPU memory, not full-pipeline Zero-Copy.
- A separate fa3.cuda-copy-trace.v1 from CUPTI, Nsight Systems or CUDA activity tracing must show zero HtoD frame copies, zero DtoH frame copies and zero host frame round-trips during the neural segment.
- PCIe Rx/Tx is sampled at 25 ms or faster (20 ms by default). The 5% budget is derived from the live negotiated PCIe generation and width rather than a GPU-SKU constant.
- PCIe telemetry is supporting copy-budget evidence only and can never by itself prove Zero-Copy.
- The typed media receipt is additionally bound into FA3-EVIDENCE-ENVELOPE-001 with a canonical payload SHA-256.
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

## Promotion boundary

A scoped runtime-hardening current-host PASS is component evidence only. It does not assign GLOBAL_FA3_PROMOTION, does not change the 143-capability release baseline and does not create a new architectural authority. Production promotion still requires the existing global current-host closure and all 19/19 acceptance criteria.
