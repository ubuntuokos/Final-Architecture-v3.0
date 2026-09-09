# FA3 Silero VAD materialization

`FA3-VOICE-ACTIVITY-DETECTION-001` defines the provider-neutral Voice Activity Detection boundary under `FA3-AUDIO-001`. `snakers4/silero-vad` is admitted only as `FA3-PROVIDER-SILERO-VAD-001`, an optional strong local reference provider.

## Canonical decisions

- VAD is `P0/MUST-IF-VAD-USED`; Silero itself is not P0/MUST.
- Capability count remains **143**; no new architectural authority is created.
- ONNX is the primary interchange/runtime candidate when supported.
- A portable CPU execution path is required; GPU/accelerator execution is optional.
- Accelerator use requires explicit Host Resource Broker admission and backend compatibility evidence.
- Silent execution-provider fallback is forbidden.
- Runtime `torch.hub` loading, runtime model auto-download and network acquisition are forbidden.
- Current-host hardware facts are evidence only and never portable requirements.
- Concrete CPU vendor/model/ID, NUMA node, GPU SKU/VRAM, PCI BDF, CUDA ordinal and fixed device count are forbidden as provider portable requirements.
- Production promotion requires model SHA-256 admission plus real current-host 8 kHz and 16 kHz audio E2E, state continuity/reset, quality regression, concurrency and soak receipts.

## Reference pin

- repository: `snakers4/silero-vad`
- release: `v6.2.1`
- revision: `7e30209a3e901f9842f81b225f3e93d8199902b1`
- license: MIT

## Commands

Reference/static gate:

```bash
PYTHONPATH=src python src/fa3_silero_vad_gate.py
pytest -q tests/test_silero_vad_registry.py
```

Current-host single-file evidence collection (necessary but not sufficient for promotion):

```bash
python evidence/collect-silero-vad-current-host.py \
  --model /path/to/admitted/silero_vad.onnx \
  --input /path/to/real-16k-mono-pcm16.wav \
  --expected-sha256 <sha256> \
  --provider CPUExecutionProvider
```

The collector fails closed on missing model/audio, SHA mismatch, unsupported sample rate, missing requested execution provider, unexpected model signature or runtime inference failure. It does not claim provider promotion from a single successful receipt.
