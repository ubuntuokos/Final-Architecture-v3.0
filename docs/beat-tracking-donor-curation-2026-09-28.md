# Beat-tracking donor curation for FA3 — 2026-09-28

Source discovery index: [GitHub `beat-tracking` topic](https://github.com/topics/beat-tracking). This note extends existing [beat / storyboard donor candidates](donor-reference-registry.md) rather than creating a new architectural authority or unrelated application. Current PR branch already includes `adamstark/BTrack` and `github:topics/beat-detection`; do not duplicate them.

## Individually examined repositories

| Repo | Selective value | Upstream licence declaration | FA3 consumer and disposition |
| --- | --- | --- | --- |
| [CPJKU/beat_this](https://github.com/CPJKU/beat_this) | Research-backed offline beat/downbeat inference; PyTorch; compact/full checkpoints; TS-V format | MIT for code and published weights according to README; training corpora have separate rights | Audio Fabric offline inference / Video Editor, QuickClip. Candidate only; pin weights and require Router-admitted model rather than auto-downloading or directly assigning first GPU. |
| [mjhydri/BeatNet](https://github.com/mjhydri/BeatNet) | Four modes (stream, real-time, online, offline), joint beat/downbeat/tempo/meter; causal particle filtering | CC-BY-4.0 repository licence | Research and algorithm reference only pending **software-licence suitability**, dataset, and model checks. No code copying as a default assumption. |
| [mir-aidj/all-in-one](https://github.com/mir-aidj/all-in-one) | Tempo, beats, downbeats and functional song sections (intro/verse/chorus/bridge/outro) | MIT code declaration | Song-structure IR and offline candidate for music-to-edit alignment; Linux NATTEN/madmom/Python compatibility and weight rights are separate gates. |
| [groupmm/real_time_plp](https://github.com/groupmm/real_time_plp) | Real-time Predominant Local Pulse and controllable beat-synchronous effects; research examples | MIT (LICENSE checked) | Live/Broadcast and Audio Fabric research/algorithm reference; benchmark end-to-end latency and transient robustness independently. |
| [olilarkin/librosa.cpp](https://github.com/olilarkin/librosa.cpp) | C++17 STFT/onsets/tempo/beat analysis; CPU-first DSP; upstream parity harness | ISC (LICENSE checked) | CPU baseline / native DSP; agent-ported implementation must pass independent numerical parity testing. FFTW may trigger GPL obligations: assess pocketfft and every linked/bundled dependency. |
| [danigb/beat-this-rs](https://github.com/danigb/beat-this-rs) | Rust Beat This! port; default pure-Rust rten, optional ONNX Runtime; CLI JSON and .beats outputs | MIT declared in Cargo.toml; repository API SPDX unclear | Optional CPU-only external adapter, not a new model/provider authority. Pin and hash-check converted ONNX weights separately; the port says generated with AI and needs independent correctness audit. |
| [Music-and-Culture-Technology-Lab/omnizart](https://github.com/Music-and-Culture-Technology-Lab/omnizart) | Cross-task transcription (drums, vocals, pitch, chord, beats) with research provenance | MIT (LICENSE checked) | Music Studio / MIDI and Audio Fabric multi-event analysis; transitive dependencies, checkpoint rights and source-data rights must be checked. |
| [aubio/vamp-aubio-plugins](https://github.com/aubio/vamp-aubio-plugins) | Existing Vamp plugin API and CPU beat/onset/pitch feature extraction | GPL-3.0-or-later README declaration; GitHub SPDX GPL-3.0 | Research / compatibility adapter reference only pending distribution analysis. Upstream repository has not been pushed since 2017: freshness and build checks required. |

All candidates are **non-authoritative metadata** in `FA3-DONOR-REFERENCE-REGISTRY-001`, recorded with exact GitHub source keys. The topic itself is a discovery index, not a source-code dependency or proof of quality. Marketing/performance claims from upstream README are not independently verified.

## Proposed native FA3 design (no new capability or architectural authority)

```text
FA3 Audio Fabric: immutable audio / native-session asset
  -> channel/rate normalization and provenance (CPU-first)
  -> candidate DSP onset / tempo baseline
  -> optional external inference provider, only after admission
  -> FA3 typed rhythm events with confidence, timebase and evidence
  -> Music Studio / QuickClip / FA3 Video Editor / Live-Broadcast
```

Keep four independent domain types: `MusicalBeatEvent` (onset/beat/downbeat/bar/tempo/meter), `MusicalStructureSegment` (intro/verse/chorus etc.), `NarrativeBeat` (story point) and optional `GameBeatmapEvent` (Beat Saber beatmap parser). Never silently coerce between them.

Candidate normalized `MusicalBeatEvent` fields: `source_asset_ref`, `source_digest`, `stream_id`, `sample_index`, `sample_rate`, `presentation_time_ns`, `event_kind`, `bar_position`, `tempo_bpm`, `meter`, `confidence`, `detector_ref`, `model_ref`, `analysis_receipt_ref`, `manual_override`, and `revision_id`. Time alignment must handle resampling, audio latency and video frame-rate conversion without erasing sample-accurate origins. Preserve tempo drift and manual beat-grid revisions, never pretend one constant BPM fits every recording.

- **Audio Fabric** owns typed event interchange and normalization. Keep raw audio and native Ardour/LMMS sessions intact.
- **Music Studio** displays beat/downbeat/bar grids, tempo changes, rhythmic markers, audition and manual correction.
- **QuickClip / FA3 Video Editor** consume time-aligned suggestion markers for cuts, effects, captions, montage and transitions; no automatic destructive edit without user authorization. Preserve `.fa3clip`, `project.fa3video`, MLT/FFmpeg and OTIO obligations.
- **Live/Broadcast** consumes causal/streaming events only after bounded measured latency, clock drift, underrun and reconnect gates.
- **Storyboard / Story** may link musical cues to narrative beats and shots by explicit graph edges, not shared overloaded beat IDs.

## Hardware Audit — explicitly scoped

**Registry change: metadata-only and PASS against static constraints**. No runtime or hardware resource is acquired; vendor-neutral and CPU-only capable with 0..N accelerators. This note does **not** assert current-host runtime evidence.

Before any provider executes: independent current-host security / dependency / licence gate, CPU-only baseline test, HRB resource admission and active lease, Model Router selection of an already authorized model, Central MCP Gateway mediated tool access, UAF entry and evidence receipt. Disable upstream assumptions such as "choose first GPU", implicit checkpoint download, or silent CPU/GPU fallback. The display GPU can be used only under FA3's existing strict two-case policy; mere availability never authorizes its recruitment. Optional CPU DSP needs no model, but still requires dependency and runtime provenance validation. Use project-local Python venvs when Python is needed.

## Acceptance gate for a future implementation

1. Explicitly query existing Reuse Discovery and do not reimplement an already admitted function.
2. Verify each selected repository at immutable commit, exact licences, transitively linked libraries, separate model weight provenance and dataset rights.
3. Deterministic CPU-reference correctness against hand-annotated onset/beat/downbeat and variable-tempo samples, including silence, speech, syncopation, irregular metre and noise.
4. Timestamp accuracy and clock drift measured across 44.1/48/96kHz, audio resampling, 23.976/24/25/29.97/50/60fps and dropped frames, including versioned manual overrides.
5. Real-time latency, CPU load, underruns, stale-device handling and reconnection measured on a current host; streaming and offline results compared without claiming identical algorithms.
6. Negative tests for non-admitted model/provider, auto-checkpoint downloads, direct provider calls, silent GPU/fallback or unapproved display-GPU use.
7. Native audio/video project round-trip and CPU-only Wayland and X11 GUI tests; user edits survive re-analysis.
8. Promotion is forbidden without independent current-host E2E receipts, applicable licence and security approval. Static documentation or registry admission does not qualify.
