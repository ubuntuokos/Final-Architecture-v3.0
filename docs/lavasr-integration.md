# FA3 LavaSR integration

## Canonical classification

`FA3-PROVIDER-LAVASR-001` is an optional, strongly recommended local reference provider for speech restoration, bandwidth extension and selected downstream audio-conditioning use cases under existing `CAP-017`.

It is **not** an audio, inference, model-registry, routing, workflow, security, resource or evidence authority. Capability count remains 143 and no architectural authority is added.

## Provider-neutral contract

`FA3-AUDIO-RESTORATION-BWE-CONTRACTS-001` defines restoration/BWE intent independently of LavaSR. It covers explicit sample-rate/channel projections, BWE target rate, denoise policy, execution-provider admission, model-artifact security, output integrity and evidence lineage.

GTCRN and LavaSR remain independently routable providers. GTCRN is suited primarily to real-time denoising/noise suppression; LavaSR's primary role is restoration/BWE. LavaSR denoising defaults to disabled. A second denoise stage on already-denoised audio requires an explicit cascaded-denoise policy and quality evidence.

## Immutable upstream identities

Method/reference source:

- repository: `ysharma3501/LavaSR`
- revision: `33ac040892519c1bb4aed7eb32e79af51cc29e2a`
- effective source license reference: Apache-2.0
- metadata issue: the repository LICENSE/README say Apache-2.0 while `pyproject.toml` contains an MIT classifier; the conflict is retained as provenance rather than silently normalized.

Preferred direct runtime reference:

- repository: `Topping1/LavaSR-ONNX`
- revision: `1a979b80d760f00d973b13d530fdd8da51be160b`
- release: `Alpha-v0.1`
- license: Apache-2.0

The release tag is not treated as immutable identity. The five ONNX/external-data assets are bound to their exact SHA-256 and byte size in `FA3-LAVASR-MODEL-ALLOWLIST-001`.

## Security policy

Direct runtime loading of upstream `.bin`, `.pt`, `.pth`, `.pkl`, `.pickle`, `.ckpt` and `.tar` serialized checkpoints is forbidden. Such artifacts may only participate as isolated quarantine/conversion sources under `FA3-MODEL-ARTIFACT-SECURITY-001`.

Runtime network model fetch is forbidden. `snapshot_download()` and floating Git dependencies in the upstream Python wrapper are not production runtime behavior in FA3.

## Runtime policy

The production candidate is ONNX-first and CPU-baseline:

- provider-native processing input: 16 kHz mono
- contract-level external input range: 8-48 kHz, only through explicit admitted projection when non-native
- output: 48 kHz mono
- default denoise: disabled
- `CPUExecutionProvider`: baseline
- accelerator provider: optional, requires Host Resource Broker receipt and proof that each ONNX session honors the requested provider without CPU fallback

The community ONNX CLI's CUDA provider list includes CPU fallback. FA3 therefore does not treat that CLI behavior as sufficient accelerator promotion evidence; the FA3 collector binds and verifies the provider sessions explicitly.

## Audio integrity

Current-host promotion requires evidence for:

- finite output
- output peak and clipping metrics
- input/output SHA-256
- duration/timebase preservation
- no batch-padding tail leakage
- 48 kHz output contract
- measured real-time factor
- denoise-off and explicit denoise-on paths
- double-denoise rejection
- clean-speech preservation
- degraded-speech/BWE quality improvement
- rollback/bypass

ASR preprocessing additionally needs measured WER/CER evidence before that projection is promoted. TTS postprocessing needs dedicated downstream quality evidence.

## Materialization

Quarantine source/model materialization:

```bash
bash bin/fa3-lavasr-bootstrap.sh
```

The bootstrap deliberately does not install Python dependencies and does not promote the provider. Run it only as an operator-driven networked acquisition step. The execution environment must be separately admitted and provide `onnxruntime`, `numpy`, `scipy`, `soundfile` and `PyYAML`.

Static/executable reference gate:

```bash
PYTHONPATH=src python src/fa3_lavasr_gate.py
```

Real current-host runtime receipt, native 16 kHz mono input:

```bash
PYTHONPATH=src python evidence/collect-lavasr-current-host.py \
  --runtime-dir ~/.local/share/fa3/lavasr/runtime \
  --model-dir ~/.local/share/fa3/lavasr/models/LAVASR-ONNX-ALPHA-V0.1-001 \
  --input input-16k-mono.wav \
  --output /tmp/lavasr-output.wav
```

For a non-16 kHz source, add `--allow-resample-projection`. For a non-mono source, add `--allow-channel-projection`. Denoising is enabled only with `--denoise`; already-denoised inputs additionally require explicit `--allow-cascaded-denoise` when a second denoise pass is intended.

## Promotion boundary

A reference CI PASS proves canonical closure and executable admission-policy behavior only. A runtime-integrity receipt likewise does not, by itself, prove quality. `FA3-LAVASR-RUNTIME-CONFORMANCE-001` remains `PENDING_CURRENT_HOST` / `production_admitted=false` until the required real-host quality and rollback evidence exists and is reconciled into the canonical evidence/release projection.
