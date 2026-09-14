# FA3 FFmpeg + ONNX Runtime CUDA

This directory implements two deliberately separate claims.

## `FA3-FFMPEG-ONNX-CUDA-001`

The build profile pins FFmpeg 9.0.1 and nv-codec-headers n12.1.14.0 by immutable commit, enables `libonnxruntime` and CUDA, and selects CUDA architectures from the current host or `FA3_CUDA_ARCH_LIST`.

A successful build proves **build capability only**. It does not prove ONNX Runtime CUDA execution and never proves zero-copy. `FA3_FFMPEG_LICENSE_PROFILE` defaults to `lgpl`; `nonfree` is accepted only with explicit `FA3_ALLOW_NONFREE=YES`. The obsolete `--enable-libnpp` switch is intentionally absent.

## `FA3-FFMPEG-ONNX-ZEROCOPY-001`

Zero-copy remains experimental. Promotion requires current-host evidence for CUDA `AVHWFrames` interoperability, ONNX Runtime device-memory I/O Binding, same-GPU identity, CUDA stream synchronization, and profiler evidence with `host_transfer_bytes == 0`.

This is separate from `FA3-FFMPEG-ZEROCOPY-001`, which tracks the upstream Torch DNN CUDA frame-to-tensor candidate and likewise does not claim an end-to-end GPU-resident path.

## Build

```bash
export ONNXRUNTIME_PREFIX=/opt/onnxruntime
# Optional; otherwise current-host compute capabilities are detected.
export FA3_CUDA_ARCH_LIST="8.6 9.0"
tools/ffmpeg-ai/build_onnx_cuda_ffmpeg.sh
```

## Current-host acceptance

The JSON command must invoke the attested FFmpeg and exercise `dnn_processing` with `dnn_backend=onnx`.

```bash
python3 tools/ffmpeg-ai/current_host_acceptance.py \
  --ffmpeg /path/to/ffmpeg \
  --command-json /path/to/inference-command.json \
  --output /path/to/result.mkv \
  --host-attestation /path/to/host-attestation.json
```

Without `--profiler-evidence`, runtime success may establish `CURRENT_HOST_ONNX_CUDA_PASS`, while zero-copy stays `PENDING_PROFILER_EVIDENCE`. No portable CI result may be relabeled as current-host PASS.
