# FA3 selective production import — verified donor research and executable implementation plan

Research date: **2026-09-29**. Parent proposal: [17-selector content plan](production-import-selective-content-plan-2026-09-29.md) and [production migration plan](production-import-migration-plan-2026-09-29.md). Earlier converter decision crosswalk: [historical reconciliation](production-import-historical-conversion-reconciliation-2026-09-29.md). Existing PR: **#528**, extending the merged **#459** donor baseline.

**State: RESEARCH + IMPLEMENTATION DESIGN + NON-AUTHORITATIVE REGISTRY CAPTURE ONLY.** This document does not assert released codecs, admitted models, actual translation/separation accuracy, a functioning GUI, independently verified editable project roundtrip, physical current-host PASS, or production deployment. Central canonical capability baseline **175 unchanged**; providers dynamic; new architectural authorities **0**.

## 1. Required user-facing behavior

Exactly **17 independently selectable** outputs exist in the already versioned parent 17-selector plan: TEXT 4, AUDIO 6, VIDEO 7. Their stable IDs and verbatim Hungarian GUI labels **must be read from that parent** rather than duplicated into a second inconsistent registry. All checkboxes are combinable. A single video request can yield silent picture, one or more language-specific timed transcripts, instrumental music and extracted ambience; an audio request can simultaneously produce full original sound, selected vocals, instrumental version and a denoised speech derivative.

Text translation is also a **cross-cutting transformation of audio/video transcripts**. The original-language transcript is kept as a source-linked, independently versioned intermediate under the existing retention policy; only explicitly selected destination derivatives may be delivered to applications. Whole-source/page/sentence/scene/shot/frame/timecode/track/channel/speaker-range selection is orthogonal to output type.

**Never conflate**: (1) original discrete audio track extraction, (2) deterministic demuxing of combined stream, (3) AI-estimated source separation, (4) noise suppression, (5) text transcription, (6) translation, (7) project-level reversible import. "Környezeti hangok és hangeffektusok" means desired ambience/SFX, **not** arbitrary residual denoiser noise. Speech and singing, instrumental/music, ambience/SFX, and generic noise have distinct semantic ontology IDs.

### 1.1 Output and provenance contract (subordinate schema, not new authority)

Extend existing `ProductionImportPlan` / `SelectiveImportRequest` under `FA3-CREATIVE-PROJECT-WORKFLOW-CONTRACTS-001`, CAP-171 and #195's `file.convert.inspect/plan/execute`. Every selected output has:

- `request_id`, stable `source_ref`, `source_sha256`, `source_app/version`, `source_rights`, `source_data_class`, immutable or read-only original reference, `production_id`, `shot_id/scene_id` where meaningful.
- `source_range` (rational media timebase / source frame IDs / source sample rate and channels / document offsets), `source_track_ids` and `track_kind`; no silent offset, frame-rate, channel or orientation conversions.
- `output_selector_id` (from the exact 17 enum), `target_application`, `target_format_version`, `destination`, delivery-only vs editable-project status, `source_stem_kind` where appropriate.
- `source_language`, each explicit `target_language` (BCP-47), `translation_strategy`, `glossary_revision`, protected names, original segment IDs, speaker or voice labels when independently supported. Code-switching stores language **per segment**, never a fabricated single-language certainty.
- `execution_class` = ORIGINAL_TRACK_EXTRACT / LOSSLESS_TRANSFORM / ESTIMATED_SEPARATION / ASR_ESTIMATE / TRANSLATED_DERIVATIVE / PROJECTION_ONLY; `fidelity_status` = EXACT_VERIFIED / ESTIMATED / DECLARED_LOSS / INSPECT_ONLY / UNSUPPORTED / BLOCKED. Avoid EXACT on generated audio or automatic language translation.
- Existing canonical Evidence receipt: input/intermediate/output digests, renderer/adapter/model IDs and versions, separately admitted model-weights digest, resource lease, authorized egress, rights/data-class decisions, failures and user-reviewed quality. `source_never_modified=true`; every delivered artifact has separately addressable destination and lineage.
- `requested_outputs` vs `produced_outputs` equality is checked. A skipped output requires an explicit decision and receipt. An internal decoded audio buffer for requested video transcription is short-lived; do **not** publish it as an unsolicited output.

Do not create another Registry, AST, translation service, audio separator, ffmpeg service, scheduler or evidence store. Store only typed extensions/references in the existing project/asset/subtitle/artifact structures.

### 1.2 Single-source multi-output DAG

1. Inspect source inside existing Tools/File Conversion and quarantine untrusted project imports, macros, extra file references, non-local URLs and unknown archives. Discover project vs flattened delivery, discrete tracks, multichannel layout, VFR/drop-frame timecode, subtitle tracks and embedded language metadata.
2. Build a **non-executing** preview of the 17 allowed output choices, feasible original-track extraction vs experimental separation and quality/rights/HRB eligibility for every requested selector; verify format, per-source-version adapter, CPU path, license/weight admission and destination permission **before** any decoding.
3. Stage read-only source through FA3 Logistics with hash/path-map receipts. Deduplicate one bounded source decode and audio demux across all selected consumers; do not allow source text, metadata, annotations or embedded scripts to become executable instructions.
4. Branch processing:
   - **TEXT**: Document Fabric/Story or verified extracted transcript -> Language Fabric/Language Bridge -> locale-specific translation; protected terms/scene IDs and locked author text retained.
   - **AUDIO**: original typed track where present; or existing Audio Source Separation Fabric with *explicit admitted* provider/stem schema; Whisper/STT then Subtitle Studio for timed transcript; existing speech enhancement for denoise. Multi-speaker and singer split require separately admitted model capability, not inferred from Demucs four-stem vocals.
   - **VIDEO**: existing FFmpeg/Video Editor demux for picture-only or audio-only; editorial IR/OTIO only when genuine editable project import is admitted; audio sub-DAG for transcripts/music/SFX; PySceneDetect-style scene proposals plus human-adjustable in/out; selected still frames retain source `PTS`, rational timebase and image color metadata.
5. Word/cue/timecode alignment precedes optional locale translation fan-out. Every language output shares original segment IDs; subtitle fitting, hyphenation, transcription verification and long-text chunking are governed by existing Subtitle Studio/Language Fabric, not fresh per-import implementations.
6. Parallel processing is bounded by Director/Workforce typed tasks and **existing Temporal** durable workflow. Execution uses UAF/Central MCP Gateway. HRB alone leases CPU/memory and opt-in accelerator; Model Router selects only admitted models without automatic provider/model fallback. Designated display GPU rule and Hardware Safety Envelope always apply.
7. Independent output-specific QC -> one receipt per output -> user preview and accept/reject/retry *only* affected derivations -> authorized delivery to existing Story/Subtitle/Audio/Music/Video/Photo/Shot Designer inboxes. Preserve original native external project and supported FA3 native project; do not claim derivative MP4/WAV/SRT creates an editable migrated production.
8. Changed source segment, transcript corrections, glossary, adapter or model revision invalidates only dependent DAG nodes; frozen approved outputs cannot be silently rewritten. Multi-host jobs discover available app/role placement through existing FA3 machine registry; Logistics owns all LAN movement.

## 2. New donor research and selective reuse decisions

All exact GitHub sources below were checked as public upstream repositories on 2026-09-29; **repository-level license metadata is not validation of bundled weights/datasets**, runtime ABI, network behavior or source-copy rights. Each source was captured source-uniquely as `CANDIDATE` into `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. Reference-only means not a mandatory packaged application or second authority.

| Upstream GitHub source | License from repository metadata; state | Selectively reusable FA3 pattern | First-use gate or exclusion |
|---|---|---|---|
| [Argos Translate](https://github.com/argosopentech/argos-translate) | MIT; active | Offline translation and explicit language-pair packages | Independent package/weight provenance, source/target and terminology QA. |
| [LibreTranslate](https://github.com/LibreTranslate/LibreTranslate) | AGPL-3.0; active | API and GUI ideas for multi-target offline translation | Reference-only optional; no mandatory server/network or license-obligating embedded backend. |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT; active | CPU-capable local translation/STT inference patterns | Adapter under Model Router/HRB; no independent model admission. |
| [OpenNMT-py](https://github.com/OpenNMT/OpenNMT-py) | MIT; active | NLP translation/tokenization and model assessment | Model/dataset/license and output semantic validation separate. |
| [WhisperX](https://github.com/m-bain/whisperX) | BSD-2-Clause; active | Word-level alignment, VAD, speaker diarization | Alignment weights, pyannote model agreements, code-switch, silence/overlap QA; no assumed real speaker identity. |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT; active | Batch STT with CTranslate2, source time offsets | STT architecture adapter only; benchmark verified CPU path. |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | MIT; active | Offline CPU GGML STT reference | Separately admitted model assets, no automatic download/fallback. |
| [pyannote-audio](https://github.com/pyannote/pyannote-audio) | MIT code; active | Overlap/VAD/diarization | Model cards, gated HF terms and speaker errors checked separately. |
| [Silero VAD](https://github.com/snakers4/silero-vad) | MIT; active | Source-aware VAD segmentation | Short utterances, multilingual audio, overlapping singing and voice false positives. |
| [Audio Separator](https://github.com/nomadkaraoke/python-audio-separator) | MIT code; active | VR/MDX/RoFormer separation adapter designs | Check **every** downloaded model/checkpoint's license and stem schema; no blind internet retrieval. |
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | BSD-3-Clause; active | Cut detection, still-frame and scene-range previews | Detector outputs are candidates, not original editorial decisions; VFR/timebase QC. |
| [AudioSep](https://github.com/Audio-AGI/AudioSep) | MIT code; active, latest research repo updates older | Text-queried target sound extraction for ambience/SFX research | **EXPERIMENTAL/RESEARCH_ONLY**; isolated language-conditioned SFX from mixed masters is not guaranteed; pretrained weights separate. |
| [Facebook Denoiser](https://github.com/facebookresearch/denoiser) | unknown repo assertion; archived | Historical causal denoiser reference | Historical research only; no auto-fetch/install. |
| [Microsoft DNS Challenge](https://github.com/microsoft/DNS-Challenge) | CC-BY-4.0 repo metadata | Noise suppression evaluation cases and speech-quality research | Dataset/model asset rights and distribution review separately; not a universal SFX extraction dataset. |
| [Asteroid](https://github.com/asteroid-team/asteroid) | MIT; active | Multi-talker source-separation research | Speaker counting and voice/artifact QC; no singer identity guarantees. |
| [Music Source Separation Training](https://github.com/ZFTurbo/Music-Source-Separation-Training) | MIT code; active | Stem training/evaluation and model capability metadata | No pretrained model licensing inherited from trainer. |
| [OpenAI Whisper](https://github.com/openai/whisper) | MIT; active | Reference multilingual speech transcription | Transcription is not arbitrary target-language MT; follow with Language Fabric. |
| [adefossez/demucs](https://github.com/adefossez/demucs) | MIT; active upstream fork, original Facebook repo archived | **Existing FA3 optional Demucs provider** source reference; four-stem vocals/other/bass/drums | Enrich existing provider source lineage only; no independent audio authority or claim of speech/singing/SFX separation. |
| [pysubs2](https://github.com/tkarabela/pysubs2) | MIT; active | Timed subtitle parsing, export and retiming test fixtures | Existing Subtitle Studio remains canonical; verify each exact import+export subset, style and timebase. |
| [RNNoise](https://github.com/xiph/rnnoise) | BSD-3-Clause; active | Lightweight CPU speech noise suppression | **Upstream example builds fetch model assets**: FA3 must pin/verify bundled admitted assets and use offline build, not automatic network. |
| [SVoice](https://github.com/facebookresearch/svoice) | unknown repo assertion; archived | Historical unknown-speaker-count separation research | **REFERENCE_ONLY**; no runtime or blind pretrained weights admission. |

**Pre-existing shared donors reused, not duplicated:** `github:ffmpeg/ffmpeg` is enriched for demuxing/audio-only/picture-only/frame extraction. Existing OTIO format adapters, AYON/OpenAssetIO, MediaInfo/MediaConch, BagIt/OCFL and C2PA references from the parent production import plan remain available through Reuse Discovery. The Demucs provider in the canonical provider registry remains independent of donor metadata; candidate capture does not change its optional state.

### 2.1 Explicit donor dispositions

- **P0 pattern study**: FFmpeg existing, Argos offline language packages, WhisperX timing, whisper.cpp CPU STT, PySceneDetect scene preview, pysubs2 retiming, RNNoise CPU denoise; each is **candidate reference**, not a runtime dependency.
- **P1 bounded optional adapter research**: CTranslate2, faster-whisper, Silero VAD, pyannote, Audio Separator, Demucs's already existing provider, Asteroid.
- **Research only pending model fidelity and rights**: AudioSep, SVoice, Facebook Denoiser, Microsoft DNS Challenge, stem training recipes. AGPL LibreTranslate is optional reference-only, no default embedded service or required web API.
- Every new provider/weights variant requires source/license/SBOM/security/Model Router/HRB/real current-host review. Mixed-song instrumental quality cannot be inferred from generic separation benchmark labels.

## 3. Mandatory existing FA3 ownership map

| Need | Existing owner; required boundary |
|---|---|
| Shared file conversion, format-pair allowlist, WASM/native worker choice | #195 `FA3-FILE-CONVERSION-001`, Tools Fabric and `file.convert.*`; reconcile historical VERT patterns; ConvertX stays **QUARANTINED**, never automatic fallback. |
| Story and document types | Document Fabric/STARc *research* and #520's verified bounded Fountain/FDX subset; no fictitious symmetric Office/WPS/PDF editability. |
| Source production, scene, asset and edit graph | `FA3-CREATIVE-PROJECT-WORKFLOW-CONTRACTS-001`, CAP-171, Story/Screenplay, native .fa3video/.fa3clip preservation. |
| Text translation | `FA3-LANGUAGE-FABRIC-001`, `FA3-LANGUAGE-BRIDGE-001`; original is authoritative, SECRET never leaves host. |
| Speech-to-text and subtitle timing | Existing STT route, `FA3-CAPTION-SUBTITLE-CONTRACTS-001`, `caption.translate`; subtitles are not a new translation authority. |
| Original tracks, demux, denoise, stem extraction | Existing FFmpeg, Audio Fabric, `FA3-AUDIO-SEPARATION-CONTRACTS-001`, optional Demucs; missing stem schema = fail closed. |
| Selected scenes/frame extraction | Video Editor/QuickClip/Shot Designer with OTIO editorial interchange and original source frame mapping. |
| Job workflow / device / models / data movement / evidence | Existing Director/Workforce + Temporal, UAF/MCP Gateway, HRB, Model Router, Security Governance/Secret Broker, FA3 Logistics and canonical Evidence/Gate authorities. |

The proposed separate `FA3-CONVERSION-FABRIC-001` from the 2026-09-19 historical VERT assessment is an execution **pattern** folded into existing #195, never a second converter. Hardware Safety Envelope and Software Coexistence apply retroactively; keep Linux-generic venv, CPU-only, Wayland-first/X11 fallback, no Conda/Mamba, and no fixed CUDA assumption. A display GPU may execute AI only under the existing explicit task/model-specific rule where another GPU/NPU exists.

## 4. Implementation work packages and dependencies

| Stage | Concrete deliverable | Gate before continuation |
|---|---|---|
| **S0 / registry** | Research this donor list against canonical 592 baseline; add metadata-only 21 normalized sources, enrich FFmpeg, preserve #459 histories; link this plan in #528. | Unique normalized source keys and donor IDs, 175 invariance, donor/static tests. |
| **S1 / contract** | Add `SelectiveImportRequest`/child output schema and per-output `SelectiveImportReceipt` to existing ProductionImportPlan/CreativeProjectGraph; freeze exactly 17 selector IDs; privacy/rights/roles and typed-source constraints. | Schema validation, 17 selector positive and invalid-selector negative fixtures, no second authority. |
| **S2 / secure scanner** | Non-executing local media/document sniff, source-app/version detection, track and language inventory, original immutable link/hash, source-range map, preflight compatibility/loss/quality preview and model/weight availability. | Symlink/path-escape, decompression bomb, URL, macro, untrusted prompt and hidden external media blocked; missing-model selectors marked unavailable. |
| **S3 / deterministic extraction** | Text original, exact discrete track music/SFX, full audio, picture-only video, video audio-only, explicit frames and validated scene-boundary preview; share FFmpeg decode and original timebase. | Byte/frame/sample/PTS offsets and channel mapping QC, legal source/supported codec fixtures, no publishing of unrequested intermediate. |
| **S4 / transcription and multilingual fan-out** | Existing approved STT -> Subtitle Studio timed track -> Language Fabric 0/1/N requested translations; glossary/protected terms, word/cue and source scene anchors. | Positive + adversarial multilingual/code-switch/overlap tests; per-language semantic QA, timebase drift checks, no external SECRET payload. |
| **S5 / audio-derived branches** | Existing optional Demucs for **supported** stems; optional admitted denoiser/MDX/VR/RoFormer task capability; separate speech/singer, requested ambience/SFX routed to `UNSUPPORTED`/experimental when reliable provider/source is missing. | Label schema must match provider; blind vocals!=speech, residual noise!=ambience; contamination/QC receipt, source immutable. |
| **S6 / cross-app + GUI** | Add source-aware 17 checkbox workspace and languages/timeline/track/range/quality badges to existing Production Studio; previews, user approval, multi-output fan-out into target inboxes and incremental stale invalidation; accessible keyboard UI. | User can separately accept/decline estimates; cancel/retry/restart/rollback work; no silent omission or external source overwrite; Wayland physical GUI. |
| **S7 / physical end-to-end** | Real CPU-only and optionally HRB-authorized accelerator examples on current host; test roundtrip **only for exact admitted editable source format subsets** and negative availability paths; regenerate release projection on exact PR head. | Independent Canonical/Promotion, Reuse Discovery, reference/static, current-host batch orchestration, source/license and co-existence gates + evidence receipts. |

**Blocking dependencies:** #195's shared conversion authority/formats must first be reconciled for runtime use; #520's Story subset is the only cited bounded story import/export work, not universal document compatibility; existing Demucs and Caption/STT routes require their own current-host proofs for the new combinations. Metadata/design commits **do not** unblock experimental SFX-only extraction or global production admission.

## 5. Required acceptance matrix

- **17/17 exact selectors**: each has one GUI label, one stable selector, valid standalone request, valid combined request and invalid option negative test. Existing parent is source of truth.
- **Text**: original-only, one explicit target, 2+ targets, original+translations; reject missing target, unauthorized remote SECRET translation, protected names/IDs mutation and falsely labeled original language.
- **Audio**: full track, timestamped transcript-only with no destination audio payload, vocal subset, source-vs-estimated instrumental, discrete original SFX/ambience vs unsupported mixed-audio class, denoised speech with original retained. Test vocal bleed, overlapping speakers, sung lyrics, sample/channel preservation.
- **Video**: full media/project distinction, picture-only no audio, complete audio-only no pictures, STT-only no published intermediate audio, music/instrumental selected, ambience/SFX selected, chosen frames/scenes; test VFR, 23.976/29.97 drop-frame, multilingual subtitles, shot source PTS and embedded 5.1 layouts.
- **Combined fan-out**: one test video produces original timed transcript + two explicit translations + approved instrumental + selected silent scene; exactly requested deliverables arrive in each app with matched source digest/shot IDs and independent quality receipts.
- **Operational gates**: duplicate event and retry idempotence, output hash mismatch, mid-run cancel, source changed during import, insufficient HRB lease, offline unavailable model, unauthorized provider fallback, accidental source mutation, leak of unrequested media, stale glossary version, unknown model license, GUI inaccessible approval and missing current-host receipt must **fail closed**.

## 6. Immediate status and non-claims

Registry capture and plan curation are documentation/metadata work. No new model/provider automatically becomes available; no physical current-host runtime, QT build, source-application reopen, mixed SFX/music separation, or bidirectional source-project compatibility is claimed. Report the exact PR head and gate outcomes **after** publishing this plan and running available checks; use `PENDING` for any gate not independently run. No historical evidence is overwritten.

## 7. Follow-up translation and audio QC donor annex (2026-09-29)

The [subsequent 11-source quality-research extension](production-import-selective-quality-extension-2026-09-29.md) covers Marian/Bergamot local translation, COMET optional human-reviewed quality analysis, DeepFilterNet speech denoising, Spleeter/Open-Unmix musical separation alternatives, AudioSet-tagging/CLAP *classification only*, SpeechBrain overlap processing, noncommercial Seamless reference-only patterns, and Sonic Visualiser operator review UX. These are source-key-unique CANDIDATE records; this section updates the branch's donor total from the prior **613** snapshot to **624** without modifying the older 21-source study or inferring production admission. The addendum requires independent rights/model-weight/HRB/current-host gates and preserves all 17 original selectors.


## Research round 2 — acoustic segment proposals, language alignment and source-separation QC (2026-09-29)

[The follow-up analysis and nine additional GitHub donors plus existing CLAP enrichment](production-import-selective-quality-curation-round2-2026-09-29.md) are REQUIRED by this implementation plan. The static registry regression is `tests/test_donor_production_import_selective_quality_round2.py`. On the follow-up commit the branch baseline is **633 source-key-unique records**, including nine new candidates; CLAP was already a 624-record baseline candidate, so it was enriched **in place**, not duplicated. All new entries are CANDIDATE metadata, not approved runtime or model providers.

Gate the workflow into three separable proofs: (1) speech/music/noise *detection* produces imperfect, human-reviewable intervals, never isolated signals; (2) verified original tracks or independently admitted exact-schema Audio Source Separation workers produce actual/estimated stems, with no false speech-vs-singing or ambience-vs-noise promise; (3) existing Subtitle/Language Fabric owns transcript corrections, timed forced alignment and 0/1/N translation branches, while ground-truth-backed metrics and human QA remain separately reportable. Never use unlicensed openSMILE commercially, require Conda/Mamba for MFA, bundle AGPL Essentia by default, or mistake SONAR/CLAP embedding scores for authoritative accuracy or clean separation.
