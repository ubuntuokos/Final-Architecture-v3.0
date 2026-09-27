# Hungarian speech → editable video project reference journey

`FA3-HU-SPEECH-EDITABLE-VIDEO-REFERENCE-001` is the canonical zero-authority reference journey for:

`media → FFmpeg audio normalization → Whisper hu STT → validated timestamps → FA3 Caption document → explicit human edit → SRT/VTT re-export → OTIO → project.fa3video → Kdenlive subtitle/import compatibility`.

It composes existing FA3 authorities and adds neither a capability nor an architectural authority. The active capability baseline remains **175**.

## Evidence levels

The deterministic reference gate proves composition, editability, hash lineage, checkpoint/retry/resume, controlled failure injection, rollback semantics, OTIO projection, Kdenlive sidecar compatibility and final `project.fa3video` hashing. It deliberately reports `current_host_claim=false`.

A physical current-host PASS requires the separate collector:

```bash
python3 evidence/collect-hu-speech-editable-video-current-host.py \
  --media /absolute/path/to/hungarian-source.mp4 \
  --output-dir /absolute/path/to/fa3-hu-reference-run \
  --model-cache /absolute/path/to/offline-whisper-cache \
  --model turbo \
  --device cpu \
  --human-edit-text "Ember által javított feliratszöveg."
```

Accelerated execution is optional. A CUDA route requires an explicit HRB lease. The collector refuses GitHub Actions evidence, requires an offline model cache, measures wall time, process CPU, peak RSS and process CUDA VRAM when applicable, and writes a 30-day-expiring receipt bound to repository commit, host, run ID and final project SHA-256.

A reference-CI PASS MUST NOT be interpreted as physical `hu-HU` recognition, current-host PASS, Acceptance PASS or production promotion.

## Failure/recovery proof

The journey checkpoints the canonical caption document before the human edit. The required failure injection occurs after that checkpoint; the retry resumes from the hash-validated checkpoint. Rollback restores the pre-edit caption revision and verifies its digest while preserving the separately materialized final editable project artifact.

## Interchange boundary

OpenTimelineIO remains the canonical timeline IR. Kdenlive remains the human finishing/compatibility surface. Direct external mutation of `.kdenlive` project XML is forbidden; the reference journey emits only typed OTIO and subtitle sidecar/import projections.

## Hardware Audit

The reference is vendor-neutral, supports CPU-only execution, permits 0..N accelerators, requires HRB admission for accelerator execution, performs no hardware mutation or unsafe tuning, and keeps CPU/RAM/VRAM evidence separate from deterministic CI reference conformance.
