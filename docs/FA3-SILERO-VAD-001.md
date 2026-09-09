# FA3 Silero VAD materialization

`FA3-VOICE-ACTIVITY-DETECTION-001` defines the provider-neutral Voice Activity Detection boundary under `FA3-AUDIO-001`. `snakers4/silero-vad` is admitted only as `FA3-PROVIDER-SILERO-VAD-001`, an optional strong local reference provider.

## Canonical decisions

- VAD is `P0/MUST-IF-VAD-USED`; Silero itself is not P0/MUST.
- Capability count remains **143**; no new architectural authority is created.
- ONNX is the primary interchange/runtime candidate when supported.
- A portable CPU execution path is required; GPU/accelerator execution is optional.
- Accelerator use requires explicit Host Resource Broker admission and backend compatibility evidence.
- CUDA device selection is bound from `AcceleratorExecutionLease@1`; a remembered CUDA ordinal is not a portable configuration input.
- Accelerator sessions disable implicit CPU execution-provider fallback.
- Runtime `torch.hub` loading, runtime model auto-download and network acquisition are forbidden. Network acquisition is allowed only as explicit bootstrap/reference work that produces immutable artifact identity evidence.
- Current-host hardware facts are evidence only and never portable requirements.
- Concrete CPU vendor/model/ID, NUMA node, GPU SKU/VRAM, PCI BDF, CUDA ordinal and fixed device count are forbidden as provider portable requirements.
- Production promotion requires model SHA-256 admission plus real current-host 8 kHz and 16 kHz audio E2E, state continuity/reset, explicit quality regression thresholds, concurrency and soak receipts.
- A current-host collector can prove an evidence bundle; it cannot promote production by itself.

## Reference pin

- repository: `snakers4/silero-vad`
- release: `v6.2.1`
- revision: `7e30209a3e901f9842f81b225f3e93d8199902b1`
- license: MIT

## Executable surfaces

- provider adapter: `src/fa3_silero_vad_provider.py`
- static/reference gate: `src/fa3_silero_vad_gate.py`
- regression tests: `tests/test_silero_vad_registry.py`
- single-audio current-host collector: `evidence/collect-silero-vad-current-host.py`
- production-promotion evidence suite: `evidence/collect-silero-vad-promotion-current-host.py`
- reference CI: `.github/workflows/fa3-silero-vad-gate.yml`
- designated-host production E2E: `.github/workflows/fa3-silero-vad-current-host.yml`

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

For an accelerator route, `--provider CUDAExecutionProvider` also requires `--hrb-lease /path/to/AcceleratorExecutionLease.json`.

## Promotion corpus

The full current-host promotion collector accepts a `fa3.silero-vad-quality-corpus.v1` manifest. Each case names a real mono PCM16 8 kHz or 16 kHz WAV, timestamped speech/non-speech annotations, and either case-specific or manifest-level minimum precision/recall/F1 requirements. The corpus must exercise both admitted sample rates. Thresholds are explicit policy/evidence inputs rather than provider-chosen promotion criteria.

Minimal shape:

```json
{
  "schema": "fa3.silero-vad-quality-corpus.v1",
  "threshold": 0.5,
  "reset_probability_tolerance": 0.00001,
  "minimum_metrics": {"precision": 0.90, "recall": 0.90, "f1": 0.90},
  "cases": [
    {
      "id": "real-8k-example",
      "path": "/absolute/runner/path/example-8k.wav",
      "annotations": [
        {"start_s": 0.0, "end_s": 0.8, "speech": false},
        {"start_s": 0.8, "end_s": 2.5, "speech": true}
      ]
    }
  ]
}
```

The actual production corpus must contain suitable real 8 kHz and 16 kHz cases, including speech, silence, background-noise and non-speech/music regressions. The current-host workflow additionally exercises independent concurrent sessions and repeated full-corpus soak execution. Final promotion remains owned by the existing FA3 artifact/model admission, policy reconciliation and evidence authorities.
