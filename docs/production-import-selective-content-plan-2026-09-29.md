# FA3 Production Import — user-selected content and multilingual derivative plan

Date: 2026-09-29
Status: **PROPOSED PLANNING EXTENSION**, not runtime implementation or current-host admission.
Parent: [Production Import & Migration Fabric plan](production-import-migration-plan-2026-09-29.md).
Capability baseline: **175 fixed**; provider count dynamic; new architectural authorities: **0**.

## User requirement: 17 composable selections

A source can produce **multiple requested outputs within one scoped plan**. The three source-family menus below are the baseline GUI labels. A choice does not promise that a third-party mixed recording can be separated perfectly or that a file is an editable project.

| Source | Stable output selector | Required GUI label (Hungarian) | Meaning |
|---|---|---|---|
| TEXT | `ORIGINAL_LANGUAGE` | Eredeti nyelven | Preserve original document/selected source passage and exact available language metadata. |
| TEXT | `ONE_TRANSLATION` | Egy kiválasztott nyelven | Produce one user-selected target-language derivative. |
| TEXT | `MULTI_TRANSLATION` | Több nyelvre lefordítva | Produce one derivative per explicitly chosen target language. |
| TEXT | `ORIGINAL_PLUS_TRANSLATIONS` | Eredeti és fordított változatok együtt | Retain source and individually versioned target-language derivatives in the same lineage bundle. |
| AUDIO | `FULL_AUDIO` | Teljes hang | Copy/link the original audio or authorized selected time range, no destructive stem mixing. |
| AUDIO | `TRANSCRIPT_ONLY` | Csak szöveges átirat | Deliver timestamped transcript, not the audio payload; original remains retained or referenced according to archive policy. |
| AUDIO | `SPEECH_OR_SINGING_SEPARATE` | Beszéd vagy ének külön | Request a named vocal subset; speaker and singer identity/take boundaries only when verified. |
| AUDIO | `INSTRUMENTAL_ONLY` | Csak zene, ének nélkül | Prefer original instrumental stem; otherwise generate estimated vocal-removed derivative and flag residual bleed. |
| AUDIO | `AMBIENCE_AND_SFX` | Környezeti hangok és hangeffektusok | Prefer original discrete SFX/ambience tracks; estimated separation from mixed audio is capability/quality gated. |
| AUDIO | `DENOISED_SPEECH` | Zajcsökkentett beszéd | Preserve untouched original; export processed speech with measured artifacts, processing lineage and user review. |
| VIDEO | `FULL_VIDEO` | Teljes videó | Preserve original timeline/project when editable import is admitted; flattened full video is delivery-only. |
| VIDEO | `VIDEO_WITHOUT_AUDIO` | Csak kép, hang nélkül | Export picture-only sequence or supported picture track retaining source timebase. |
| VIDEO | `FULL_AUDIO_ONLY` | Csak teljes hang | Extract linked full audio without picture; preserve channels, timecode offset and timebase metadata. |
| VIDEO | `TRANSCRIPT_ONLY` | Csak beszédátirat | Extract audio as ephemeral input for authorized STT and return only transcript derivative. |
| VIDEO | `MUSIC_OR_INSTRUMENTAL_ONLY` | Csak zene vagy instrumentális rész | Prefer available source music tracks; otherwise estimate and disclose contamination and missing vocals. |
| VIDEO | `AMBIENCE_AND_SFX_ONLY` | Csak környezeti hangok és effektek | Prefer original effects channels/stems; mixed-source isolation may be unsupported or experimental. |
| VIDEO | `FRAMES_OR_SCENES` | Képkockák vagy kiválasztott jelenetek | User-selected frames, scene/timecode intervals or editor-aligned clips, with still-image/sequence/project distinctions. |

Menus are multi-select, not radio groups. Each selected output has its own output type, target FA3 application, language settings where applicable, source range, destination and quality/admission receipt. Source-only and derivative-only delivery are explicitly distinct from transferring the entire editable project.

## Additional controls shared by selections

- **Language overlay**: `source_language` explicit or approved-detection with confidence, `target_languages[]` explicit locale/BCP-47 identifiers, original+translated side-by-side option, versioned production-specific terminology, protected proper names and speaker labels; optional human review and per-language target application. For AUDIO/VIDEO `TRANSCRIPT_ONLY`, the same four TEXT language selections apply *after* transcription. Preserve original transcript even when only a translated delivery is requested, as authoritative/provenance data under existing retention policy; expose only requested outputs to destination apps.
- **Source range**: whole source, selected episodes/scenes, shots, frame/timecode ranges, page/paragraph ranges, named tracks/channels, and explicitly authorized speaker segments when identity is reliably known. Keep original rational timebase/sampling information, language/segment alignment and scene/shot IDs.
- **Stem specificity**: `speech`, `singing`, `instrumental`, `music`, `ambience`, `sfx`, `noise` are **different classes**. The user's “környezeti hangok és hangeffektusok” means desired ambience/SFX, not arbitrary unwanted noise. A denoiser's removed noise is not proof that source ambience/SFX were cleanly isolated. A model advertising vocals/instrumental cannot claim guaranteed speech-versus-singing or SFX-versus-music separation.
- **Output scope**: `LINK_ONLY`, `DERIVED_ONLY`, `COPY_EDITABLE` where proven, `HYBRID`, `ARCHIVAL_COPY`. A transcript, translation, vocal-reduced mix or extracted still is a **derived asset** linked to the original. It is never a round-tripped, full native editable source project.
- **Routing**: target Story/Screenplay, Subtitle Studio, Music Studio, Audio Fabric, Video Editor/QuickClip, Photo/Image Studio, Sound Design, Director or user-selected archive. Publish only explicit requested derivatives, no hidden default media import or cloud upload.

## Processing DAG — shared work, multiple outputs

1. Existing Tools `file.convert.inspect` discovers type, source app/version, channels, editable tracks, languages, media offsets, scene structure, protected source, rights and data classification; external scripts, macros and paths remain inert.
2. Build a typed **SelectiveImportRequest** child of the existing `ProductionImportPlan`: immutable `source_ref` + digest, `source_kind`, selected output IDs, named `target_languages`, source ranges, quality requirements, target applications, privacy/egress approvals, `original_retention_policy`, `output_policy`, `requested_execution_mode` and existing project/approval refs.
3. Compile an explicit DAG with deduplicated decode, audio extraction and STT nodes, source-channel inspection, optional admitted separation/denoising, segment/word timing alignment, translation fan-out per target language, media/frame/scene projection and per-output QC. A video-to-transcript request extracts audio internally without publishing that intermediate audio. Separate music/SFX requests must share appropriate demuxing but cannot silently infer an absent target stem.
4. Route through existing authorities only: Document Interchange and Story for text; Language Fabric / Language Bridge for translation and terminology; existing Whisper/STT for transcription; existing Audio Source Separation Fabric / Demucs for **admitted** stem schemas; Audio/Video/Photo/Fabric for processing; Subtitle Studio's canonical timed text model; existing Tools `file.convert.*`, UAF, Central MCP Gateway, Model Router, HRB, Temporal, Security Governance, Logistics, Asset Graph and Evidence.
5. Preview each output **independently**. Display `EXACT` for literal source track extraction only when verified; `ESTIMATED` for transcription/translation/model-separated audio; `LOSS_DECLARED`, `INSPECT_ONLY`, `UNSUPPORTED` or `BLOCKED` when relevant. Do not infer that a clean instrumental, singer-specific stem or isolated ambience exists merely because a mixed recording is readable.
6. Execute a user-approved bounded plan; persist immutable source snapshot or approved read-only link, per-output hashes, source offsets/scene IDs, language and glossary revision, provider/model identities when used, leases, quality confidence, provenance and optional review corrections. Downstream approval gates prevent a failed/contaminated output from being silently marked complete.
7. Existing Director maps produced assets to requested FA3 application inboxes and dependency graph; original media and unrelated source project edits remain unaffected. Re-execution invalidates only derived nodes affected by changed source segments, separation model, vocabulary or translated language.

## Existing authority and implementation reality

- `canonical/contracts/FA3-AUDIO-SEPARATION-CONTRACTS-001.json` specifies `StemOntologyDescriptor`, `StemSeparationRequest`, `StemContaminationEvidence` and provider-neutral results. Current Demucs allowlist's admitted four-stem `htdemucs` classes are **drums/bass/other/vocals**, and its six-stem guitar/piano paths are experimental. Therefore **speech-versus-singing**, **pure SFX/ambience** and **clean isolated music from arbitrary mixtures** must start `UNSUPPORTED`/experimental unless another independently admitted stem schema or genuine source tracks substantiate them; no invented physical PASS.
- `canonical/contracts/FA3-CAPTION-SUBTITLE-CONTRACTS-001.json` already keeps original caption text when translated and offers `caption.translate`; use its timed text, revisions and editable caption track rather than a new transcript authority. Its historical 143 count is not a proposal to change current global **175** or rewrite old evidence.
- `canonical/profiles/FA3-LANGUAGE-FABRIC-001.json` and `canonical/FA3-LANGUAGE-BRIDGE-001.json` already require original-language authority, translated derivative lineage, local-first policy, semantic validation, protected tokens, no external translation for SECRET material, and no silent model/provider fallback.
- Existing Whisper and Demucs profiles still require actual current-host and per-model performance/quality evidence for new selective-import combinations. An archived or externally supplied transcript is not the same as independently verified new STT execution.

## GUI in the existing Production Studio, not a new app shell

**Production Studio → Open / Import Production → Select Content**, with three source-aware panels (Szöveg / Hang / Videó). Display exactly the 17 Hungarian checkbox labels from the table, plus optional shared controls for selected languages (single or chips/multi-select), scene ranges, stem source/quality (original / estimated / unavailable), destination apps, preview, loss/admission, original preservation and consent/approval. Include a single **“Import all selected”** action only when every requested output has a proven or explicitly approved quality/loss mode; otherwise offer **“Import supported subset”** with a human-reviewed skipped-output receipt, never silent drops.

**Example**: One 42-minute French-language documentary video yields (a) muted selected shots for Video Editor, (b) original French timed dialogue and explicitly requested Hungarian and English versions for Story/Subtitle Studio, (c) source music without vocals for Music Studio only if a clean source stem exists or the user explicitly accepts a documented estimated derivative, and (d) scene-bound ambience/SFX if supplied as original stems or independently validated by an admitted separator. All outputs retain exact shared source lineage/timecode and independent quality reports.

## Security, governance and acceptance

- **No network assumption**: offline-first/local processing, explicit opt-in for remote/billable translation/STT/separation; private source rights and data classification gate prior to any provider selection. Models chosen only through FA3 Model Router; CPU-only route remains mandatory and optional acceleration is task/model-scoped via HRB. Designated display GPU cannot be enrolled implicitly when another GPU or NPU exists.
- **No unauthorized extra data**: intermediate decodes and extracted audio are bounded and cleaned under retention policy; user-requested transcript-only import must not send unrequested media into Story/Subtitle Studio. Preserve source originals and provenance independently of selected delivered outputs.
- **No invented guarantees**: no exact stem separation, word-level accuracy, perfect translation, authorizing original project writeback, derived-asset symmetry or source-app roundtrip without independent evidence. Mixed singing/speech, vocal bleed, multilingual/code-switch speech, overlapping speakers, high-noise ambience, 5.1/ADM/object audio, variable frame rate and subtitle timing drift must have negative/quality fixtures.
- **Verification**: test all 17 selectors, combined fan-out, one/multi/parallel source+translations, no output of unrequested media, range/timebase alignment, duplicates in generated names, rollback/restart, unchanged source digests, data-class rejection, unavailable stem fail-closed, and exact-head canonical/reuse/projection gates. Do not claim physical current-host PASS or software release from proposal documents.

## Source-verified donor research and implementation work packages

The [2026-09-29 selective-content research annex](production-import-selective-donor-research-2026-09-29.md) records **21 additional** source-unique non-authoritative donor candidates, official repository source/licensing metadata, exact existing-owner mappings, seven-stage implementation dependencies, output-specific acceptance criteria and release gates. It augments, rather than overrides, the **17 exact selectable options** and cross-cutting text language modes in this parent document. The 592-record migration baseline increases to **613** only on this design branch until PR #528 is merged. No automatic runtime, provider, model or weight admission or physical current-host PASS is implied.

## Follow-up quality/translation research (same 17 selectors)

The [11-source translation/audio quality extension](production-import-selective-quality-extension-2026-09-29.md) adds offline local-MT and review patterns, distinct original-versus-estimated audio semantics, an operator QC model, source/revision-aware derivative cache rules and exact-head physical admission requirements. It adds **no new selector, capability ID or runtime authority**. The preceding 613 count is the historical pre-extension snapshot; the #528 proposal branch now has 624 source-unique donor records. License/weight gate and user-approved source preservation remain mandatory.


## Follow-up audio-language quality and segment controls (2026-09-29)

The [second-round segmentation / forced-alignment / QC research and candidate registry capture](production-import-selective-quality-curation-round2-2026-09-29.md) extends this plan, **without changing any of the exact 17 selector labels or IDs**. It adds human-editable interval previews for speech/music/noise and candidate events, evidence-typed original-versus-estimated track badges, optional corrected-text-to-original-audio word alignment, and independent per-output quality decisions. Detection/classification cannot be sold as source separation; word alignment of already-corrected text does not prove that the original transcription or translation is correct. Version, selected language, BCP-47 target, source samples/PTS and original IDs remain attached to each output. Existing Audio/Subtitle/Language/HRB/Model Router and canonical Evidence remain authoritative.

The follow-up registry research added **nine** previously absent source-unique records and enriched the already-existing CLAP donor on draft #528 (624 → **633** at this documented snapshot), with all nine CANDIDATE and no automatic dependencies or current-host PASS. Earlier historical 613 snapshots remain historical rather than rewritten evidence.

## Live contribution source profiles: video, audio/podcast and subtitles only (2026-09-29)

The original **17 output selectors remain unchanged**. Live versus stored media is a separate source dimension. For authorized real-time video/audio and truly standalone caption-only EBU-TT Live/independent WebVTT feeds, see [Live Production Intake](production-import-live-source-intake-2026-09-29.md). Live source-provided captions differ from ASR-estimated transcripts; language fan-out reuses the same four text choices, while an embedded-only 608/708 caption request may require receiving video bytes for demux. A strict NO_AV_FETCH request never silently falls back to embedded video. No new server/daemon or default rebroadcast is admitted.

## Further source-specific audiovisual research (2026-09-29)

The [round-4 audiovisual source research and acceptance plan](production-import-selective-audiovisual-research-round4-2026-09-29.md) registers Sony MMAudioSep, openmirlab BS-RoFormer inference, the BS-RoFormer architecture, Traduko's staged multilingual UX and an AV quality benchmark as **five metadata-only donor candidates** (plus in-place enrichment of the official Blender reference). The selector interface remains exactly **4 text + 6 audio + 7 video** checkboxes. Recognizing an event is not separating its waveform; requested original source tracks are distinguished from independently admitted, operator-reviewed estimated outputs. Snapshot after this batch: **654 unique source keys**, 175 capabilities, no provider/runtime admission or physical PASS.

## S4 original-first audio-stem strategy (2026-09-29)

The [S4 source-attestation / requested-stem strategy preview](production-import-s4-stem-strategy-2026-09-29.md) adds a metadata-only decision plan for original discrete speech/singing/instrumental/ambience/SFX tracks versus optional **estimated** source-separation candidates. It keeps the exact 17 selectors and all 4 text overlays unchanged. S4 cannot execute source extraction or models, self-approve a supplied provider/weight digest, use the display GPU automatically, treat denoiser noise as ambience, claim editable project symmetry or publish derived media. Two separately source-checked official Meta references were captured as non-authoritative, license-gated candidates. Source-level reference tests and independent signed real-host/model-specific quality gates remain separate.

## S4.2 selective audio QC research and fail-closed implementation (2026-09-29)

[Three new source-checked, metadata-only audio QC/relink donor candidates, plus the S4.2 checklist contract and implementation](production-import-selective-audio-qc-round5-2026-09-29.md) extend the existing S4 stem-strategy preview. The common registry increases 656 → **659** source-unique donor records at this batch (historical earlier counts remain prior snapshots). The new typed `selective-audio-qc-plan.v1.json`, pure `fa3_selective_import_audio_qc.py` and seven synthetic regression tests separate external original-stem claims, estimated model stem candidates, denoised-speech derivatives and unavailable stems. All resulting QC checklists keep `publish_audio=false`, `execution_authorized=false`, verified-evidence flags false and the **175** capability baseline; independent Audio/Evidence/HRB/Model Router/rights review, exact-head gates and physical current-host execution are still pending. No third-party source code or weights are incorporated.


## S5 integrated delivery manifest preview (2026-09-29)

[S5 per-deliverable, cross-application planning contract and next executable gate sequence](production-import-s5-delivery-preview-2026-09-29.md) integrates the *existing* S1–S4.2 pure metadata previews. New files: `src/fa3_selective_import_delivery_preview.py`, `canonical/schemas/selective-delivery-preview.v1.json`, and `tests/test_selective_import_delivery_preview.py`. One stored-source request retains the **unchanged 17 family-scoped selections**, optionally fans out original and requested translations, and attaches per-output rights/inspection/target/evidence/human-approval requirements plus editable same-format roundtrip when requested. No unrequested audio/video from transcript-only paths. Distinguish requested publication *intent* from all-false actual publication and execution flags. This is not a converter worker, target application receiver, model license approval, trusted source receipt or physical current-host PASS. Reconcile the final exact PR head's release projection, then run hosted gates; actual Source→File Conversion→UAF/Temporal→target-app implementation and physical evidence remain separate.
