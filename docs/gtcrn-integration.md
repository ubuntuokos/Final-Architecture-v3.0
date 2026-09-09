# GTCRN integration — FA3

`FA3-PROVIDER-GTCRN-001` is an **optional, CPU-first, local real-time speech-enhancement provider** under `FA3-SPEECH-ENHANCEMENT-001`. It adds no capability and no authority; canonical capability count remains 143 and the projection is `CAP-017`.

## Runtime boundary

Canonical request/result/state semantics are provider neutral. GTCRN is admitted only behind existing Model Router, Host Resource Broker, Model Artifact Security, Inference Portability, Security Governance and Evidence authorities. The baseline route is ONNX Runtime `CPUExecutionProvider`; accelerator execution is optional and requires an explicit HRB receipt. Silent execution-provider fallback is forbidden.

Upstream is pinned to `502ebfab64da7c4a9af78dcb9c6ceef1ebb01c73`. Direct runtime loading of `.tar`, PyTorch/pickle-style checkpoints is forbidden. The two upstream ONNX artifacts are reference-identified by immutable revision + Git blob SHA-1, but **FA3 production admission additionally requires SHA-256 calculated in quarantine**. Runtime auto-download is forbidden.

## Audio contract

GTCRN baseline is 16 kHz mono, `n_fft=512`, `hop_length=256`, with explicit recurrent/convolution state. Other rates/layouts require an admitted upstream/downstream audio projection; they are never silently converted inside the provider. Current-host promotion requires real audio, measured RTF, finite/clipping metrics, clean-speech preservation and noisy-speech improvement evidence.

## PipeWire/LADSPA

The upstream LADSPA/PipeWire adapter is useful as a Linux virtual noise-cancelled microphone, but remains experimental, optional and non-authoritative. Enabling it requires a separate current-host PipeWire E2E receipt; disabling it has no effect on GTCRN ONNX admission.

## Gates

Reference gate:

```bash
PYTHONPATH=src python src/fa3_gtcrn_gate.py
PYTHONPATH=src python -m unittest tests.test_gtcrn_gate tests.test_gtcrn_provider_runtime -v
```

Current-host collector:

```bash
PYTHONPATH=src python evidence/collect-gtcrn-current-host.py \
  --model /path/to/admitted/gtcrn_simple.onnx \
  --input /path/to/16k-mono.wav \
  --output /tmp/gtcrn-enhanced.wav \
  --expected-sha256 <quarantine-sha256>
```

The collector performs real WAV → STFT → stateful ONNX → ISTFT → WAV execution and records model/input/output hashes plus measured RTF, but it still returns non-promotion status until clean/noisy golden-corpus quality and rollback/bypass receipts exist. A reference PASS is not production promotion.
