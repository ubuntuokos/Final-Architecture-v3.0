# FA3 selective AI video editor & generation donor curation (2026-09-28)

**Scope:** metadata-only donor capture, selective code/workflow review and phased FA3 integration proposal. This document creates no new FA3 application, architectural authority, deployment requirement, provider admission, model approval or verified runtime evidence.

## Discovery and deduplication

Four user-supplied sources: [ai-video-editor topic](https://github.com/topics/ai-video-editor), [HKUDS/ViMax](https://github.com/HKUDS/ViMax), [video-generation topic](https://github.com/topics/video-generation), and [lcy362/agnes-video-generator](https://github.com/lcy362/agnes-video-generator).

The two **topic URLs are evolving discovery indexes**, not licenses, repositories, model catalogs or permission to import everything they contain. The 2026-09-28 review identified candidate editor projects [OpenChatCut](https://github.com/0xsline/OpenChatCut) and [OpenShorts](https://github.com/mutonby/openshorts) for source-specific capture. The project [Agnes Video Generator](https://github.com/lcy362/agnes-video-generator) is **already captured on open draft [PR #512](https://github.com/ubuntuokos/Final-Architecture-v3.0/pull/512)**, alongside the distinct video-generator topic. Do not duplicate its source key; reconcile that PR before merging this branch if the base changes. The earlier [QuickClip Short Video Factory PR #510](https://github.com/ubuntuokos/Final-Architecture-v3.0/pull/510) is also a neighboring source of editing patterns. The existing canonical Pixelle-Video record and existing project-only Wan2.2/LivePortrait records must be reconciled with verified upstream links before adding duplicates.

| Source; upstream revision checked | Selective FA3 reuse | Code/license boundary |
|---|---|---|
| [ViMax](https://github.com/HKUDS/ViMax), `b596ca7793c7ec6346ddcc408a9ed1bc97998152` | Idea2Video, Script2Video, Novel2Video, per-shot continuity/reference planning, interactive agent loop, project/session and render checkpoints | MIT repository LICENSE observed. Its provider-specific API/YAML configuration and CUDA-index package setup **must not be adopted as FA3 architectural defaults**. Review dependencies and included assets independently. |
| [Agnes Video Generator](https://github.com/lcy362/agnes-video-generator), `9e2522d3e9c7ab5d2b398b98f0547180ef51213a` | Multi-scene manuscript production, per-shot first/end-frame chaining, narration/SRT, resumable task/checkpoint and progress patterns | MIT repository LICENSE observed, captured separately in draft PR #512. Its self-hosted orchestration still uses remote Agnes image/video APIs by default; cloud compute is not a CPU-only local AI implementation. Its documented unknown-text-provider fallback to Agnes conflicts with FA3 fail-closed routing; its file-based provider secrets conflict with Secret Broker policy. |
| [OpenChatCut](https://github.com/0xsline/OpenChatCut), `bb2a4f7e1bb587aa55f3816583ec180d58eb1432` | Agent proposes inspectable timeline changes, a shared editor-tool surface, transcript edits, manual review/undo and MCP interaction | AGPL-3.0 repository LICENSE observed: **clean, independent architecture/UI pattern reference only**. Do not copy source or integrate as an FA3 server/library absent independent legal review. Keep FA3's native Qt6/QML editor, Command Bus and MLT/FFmpeg path. |
| [OpenShorts](https://github.com/mutonby/openshorts), `29c54fa04c42621310f768adf40c81a1f3436bf2` | Transcript-based highlight proposals, speaker-aware split/reframe layouts, subtitles and short-form jobs | MIT repository LICENSE observed; independently verify NOTICE, models, media, pretrained weights and third-party services. Its upload/publishing, public gallery, direct provider/API-key and model defaults are not FA3 permissions. |
| [ai-video-editor topic](https://github.com/topics/ai-video-editor), [video-generation topic](https://github.com/topics/video-generation) | Recurring discovery for source-specific comparison | Metadata-only dynamic indexes; individual upstream licenses, revisions and security reviews mandatory. |

All newly captured records remain `CANDIDATE`; do not infer admission or completed implementation.

## Architectural fit: FA3, not separate editors

### Director / Workforce and Story / Screenplay

Use ViMax-style **idea -> accepted screenplay -> scene plan -> shot plan -> asset/shot work graph -> reviewed assembly** with stable `scene_id`, `shot_id`, `character_id`, immutable approved requirements and explicit revision lineage. Long text is chunked into story beats and continuity constraints, not automatically rewritten as approved canon. The **existing** Director/Workforce, Temporal, UAF and Decision Fabric own execution, approvals, bounded repair and compensation; ViMax's agent loop is a reference, not a second scheduler or permissions authority. Generated shot tasks declare dependency edges, proposed model capabilities and per-scene checkpoint/artifact receipts. Changing an ancestor scene invalidates only proven descendants; unrelated approved shots remain usable. User notes and AI notes are stored separately.

### FA3 Video Editor

OpenChatCut's most useful pattern is an **agent editing a real project**, not an immutable final clip. Generate typed, previewable `EditProposal` items against the **existing FA3 timeline/Command Bus** (insert/trim/move/ripple/caption/effect/transition/audio/reframe); make approval, conflict detection, undo/redo and provenance mandatory. Bind every edit to an exact native project revision and fail closed on stale commands. Do not replace `project.fa3video`, authoritative timeline, MLT/FFmpeg, QT6/QML GUI, OTIO interchange gate, Krita `.kra`, Ardour sessions, or Bforartists native files. Explicitly distinguish editing visibility from render visibility and use the existing layer-file project inheritance rules.

### QuickClip

Combine OpenShorts highlight selection, speaker-tracked layouts and word-aligned captions with Agnes manuscript segmentation and checkpointed narration. Emit editable `.fa3clip` containing **clip list, timebase/timeline, captions, reframe motion, audio, style, source/provenance and consent metadata**. A fully specified human-approved import maps the entire QuickClip project back to `project.fa3video`; MP4-only output is not acceptance. Preserve any accepted source clip independently of later output regenerations.

### Character, Generative Media, audio and reference continuity

ViMax per-character portraits/reference frames, Agnes first/end frames and OpenShorts face-aware composition are **candidate** inputs to existing Character Studio, Asset Graph and scene-aware inheritance. Only designated, admitted models may receive tasks; explicit image/video-generation provider contracts and rights checks are prerequisites. TTS and word-level SRT are typed Music/Voice and subtitle assets; audio mixes and MIDI remain separate media assets. Exported footage is an artifact derived from editable source, never the new project authority.

## Hardware Audit / security / licensing gate

- Vendor-neutral accelerator inventory `0..N`; dynamic AMD/Intel/NVIDIA/other GPU, CPU and NPU discovery, with physical and logical CPU counts distinguished. **CPU-only orchestration, non-generative editing and rendering must be viable**. A specific generative model may report `UNAVAILABLE` with an explicit explanation instead of silently switching providers.
- The HRB exclusively grants device reservations/leases; the Model Router exclusively resolves approved route -> provider/runtime -> designated model -> existing data plane. No ViMax/Agnes/OpenShorts direct model configuration, direct API credentials, fixed provider pin, unapproved new model, automatic parallel accelerator enrollment or silent fallback.
- A display GPU normally stays display-only. If there is no other GPU **and no NPU**, its approved AI use may be allowed; when another GPU and/or NPU exists, a display GPU can be allocated only upon explicit in-app assignment to a **specified model and task**, never automatically for spare capacity.
- Explicit Wayland preference with X11 support, no KDE-session-specific assumption; Qt6/QML/KF6 may be the application GUI technology. Avoid fixed ports and do not change AdGuardHome's ports. No Unreal installation, use, MCP or workflow path.
- Maintain LUKS state-image / Secret Broker boundary; never copy provider keys into vendor configuration files. Network/media/identity uploads need explicit user consent, source rights and destination/provenance records. No default autonomous social publishing. Supply-chain/license review covers upstream, subdependencies, fonts, model weights and bundled binaries.
- No current-host runtime PASS or benchmark is claimed by repository/README inspection.

## Phased implementation proposal and evidence

| Phase | Deliverable | Independent exit evidence |
|---|---|---|
| P0: registry and contracts | Source-unique capture; audited license/reference notes; reconcile related PR #512 and #510 and source-less Wan2.2/LivePortrait mentions | Registry uniqueness, exact 2026-09-28 source revision/provenance; no inherited provider approval |
| P1: production graph | Typed goal, story, scene, shot, character/ref, lineage, checkpoint and regeneration contracts using existing Director/Temporal/Asset Graph | Deterministic three-scene fixture; only dependent shots invalidated; approved human decisions remain immutable |
| P2: real editor integration | Native Command Bus `EditProposal`/review/undo/redo API via existing MCP/UAF; no duplicate editor | Positive and negative exact-revision edit tests, human approval and rollback; untouched `project.fa3video` parses |
| P3: QuickClip/audio | Highlight and speaker-safe crop suggestions, aligned captions, user-approved voice narration and complete editable QuickClip -> Video Editor exchange | Offline/CPU-only two-speaker 16:9 -> 9:16 fixture; timing/caption/reframe/audio/provenance round-trip with no lost tracks |
| P4: generation adapters | Separately admitted, reversible image/video model capability routes and rights-aware reference images; explicit unavailable state | HRB lease/Router binding tests for 0/1/N accelerators and display-GPU restrictions; revoked provider/network failures have **no silent fallback** |
| P5: physical/current-host gate | Independently checked end-to-end project on admitted host(s), restart-resume, provider refusal, no unintended upload/publish, visual/audio QC | Exact commit-linked receipts, Gate/Evidence Registry checks, reviewable resulting native files; any unsatisfied condition remains PENDING |

**Merge sequencing:** This curation branch only establishes five new metadata-only donor records plus this plan. The Agnes candidate lives on open draft PR #512; avoid duplicating it in another donor-registry patch. Rebase/reconcile overlapping donor-registry PRs before merge and independently run the canonical registry integrity/reuse-index checks on the final combined commit.
