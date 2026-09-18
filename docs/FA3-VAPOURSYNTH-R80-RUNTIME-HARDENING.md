# VapourSynth R80 runtime-hardening integration

VapourSynth R80 is the portable Vulkan 1.4 GPU-resident frame-fabric reference inside the existing `FA3-MEDIA-GPU-ZEROCOPY-001` profile. It does not create a new resource, routing, security or evidence authority.

## Provider roles

- **VapourSynth R80**: portable GPU-resident frame fabric and VSVulkan4 foreign-API interop reference.
- **PyNvVideoCodec**: NVIDIA-specific fast path for NVDEC/DLPack/NVENC workloads.
- **vs-mlrt**: separate neural-runtime adapter. GPU residency is backend-specific and must be demonstrated.
- **FFmpeg**: retained deterministic media core for demux/mux/audio/metadata/native filters/packaging and compatibility.

The compatibility route `vspipe --y4m | ffmpeg` is not accepted as end-to-end zero-host-round-trip proof because VSScript/vspipe consumption introduces a GPU-to-host boundary for GPU-resident output.

## CRIT-020..022

**CRIT-020** requires a rootless provider runtime materialized from an immutable canonical Quadlet template by a valid HRB lease. The canonical template cannot be rewritten per lease.

**CRIT-021** requires bounded host-impact agent execution. gVisor/runsc is the default when current-host compatible; direct host project writes and container-runtime sockets are denied, and the default tool channel is the authenticated Central MCP Gateway UNIX socket.

**CRIT-022** requires a residency/transfer trace demonstrating no host pixel materialization within the declared accelerator-resident neural segment. Foreign-API zero-copy claims require device identity matching plus external-memory and device-side semaphore evidence. PCIe/NVML telemetry is supporting evidence, not a fixed-threshold proof.

Reference/static PASS does not promote any current-host runtime. Production remains blocked until signed current-host receipts for all 22 acceptance criteria are present.
