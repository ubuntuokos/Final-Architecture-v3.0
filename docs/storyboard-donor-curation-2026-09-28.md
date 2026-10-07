# FA3 storyboard upstream donor curation — 2026-09-28

Status: **metadata-only donor candidates; proposed selective reuse; no code/runtime admission**.

## Input and scope

Research was initiated from these ten topic views (query variants intentionally preserved as discovery provenance):
- https://github.com/topics/storyboard?o=desc&s=forks
- https://github.com/topics/storyboard-generation
- https://github.com/topics/storyboards?l=css
- https://github.com/topics/ai-storyboard
- https://github.com/topics/storyboards?o=asc&s=stars
- https://github.com/topics/storyboard-application
- https://github.com/topics/storyboard?l=php
- https://github.com/topics/video-storyboard
- https://github.com/topics/storyboards?l=html&o=asc&s=stars
- https://github.com/topics/storyboard-tools

Topic pages are **discovery indices, not trustworthy adoption evidence**. CSS/HTML/PHP and the general storyboard pages mix film storyboards with unrelated Apple UI storyboards, webpage sliders, prototypes, and potentially questionable repositories. Do not automatically capture every listed repository. Seven distinct canonical topic URLs and eleven source-unique, manually reviewed initial project candidates were added to the existing canonical registry.

## Existing FA3 authority and reuse discovery

- Query `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json` and the existing `FA3-REUSE-DISCOVERY-001` before a storyboard module or related application is designed or materially changed.
- Existing application identities: `fa3.story-screenplay`, `fa3.video-editor`, `fa3.quickclip`, and `fa3.character-studio` in `canonical/FA3-APPLICATION-DONOR-LINKS-001.json`. No replacement applications or new architectural authorities are created by this research.
- Already-recorded related donors include Krita, OpenToonz, Pixar OpenUSD, and other existing creative/production references. Reuse those entries rather than duplicating them.
- FA3-natively authored storyboard/production data, linked native assets, and approved project states are authoritative for this proposed workflow; upstream project formats are optional import/export adapters, not the new FA3 source of truth.

## Source-specific candidate review

| Candidate | Selected capability or reusable pattern | Intended FA3 target | Upstream license declaration / guard |
| --- | --- | --- | --- |
| [Wonder Unit Storyboarder](https://github.com/wonderunit/storyboarder) | Fast manual board editing, Fountain import, onion skin, animatics and rapid shot iteration | Story/Screenplay, Animation, Video Editor | Full repository license file not confirmed in this review: treat source copying as blocked pending legal/provenance audit |
| [ZenStory Drama Skills](https://github.com/zenstory-ai/drama-skills) | Explicit screenplay / visual bible / storyboard / prompt deliverables; continuity-lock validation; preview-before-cost approval | Story/Screenplay, Director | README declares MIT; verify exact checked-in license, version and dependencies before code reuse |
| [Open Film Skills](https://github.com/62656456/ai-film-skills) | Structured directing, composition and shot breakdown, research-backed skill boundaries, experimental playable 3D whitebox previs | Director, Animation, Bforartists | Apache-2.0 declaration; separate verification required |
| [AICON](https://github.com/869413421/ai-moive-studio) | Editable infinite canvas connecting screenplay, images, shot/video tasks, graph review and manual triggering | Director, Creative Studio | Apache-2.0 declaration; no adoption of its provider/broker authority |
| [ArcReel](https://github.com/ArcReel/ArcReel) | Script-to-shot chain, cross-shot asset identity, regenerable media versions, cost tracking, editable video handoff | Asset Graph, Director, QuickClip, Video Editor | AGPL-3.0 with upstream NOTICE/additional terms; architectural reference until distribution audit |
| [DramaClaw](https://github.com/dramaclaw/dramaclaw) | Episode-aware node graph, series asset library, approved canvas agent changes, spatially repeatable set/previs references | Director, Bforartists, Creative Studio | Elastic License 2.0; source-available, **not** OSI open source; code reuse blocked pending constraints review |
| [InkOS](https://github.com/Narcooo/inkos) | Persistent character/story state, long-form context, safely staged revisions, script/shot skill decomposition | Story/Screenplay, Director | AGPL-3.0; reference only until copyleft/distribution review |
| [waoowaoo](https://github.com/waooAI/waoowaoo) | Visual reference roles, first/last-frame options, version-preserving media refinement, durable workflow reference | Creative Studio, Asset Graph | Elastic License 2.0 from v0.5.0-beta.1 per README; source-available, not OSI open source |
| [StoryForge](https://github.com/zhiyuzi/StoryForge) | Human-approved synopsis gates, separate generator/evaluator roles, explicit storyboard acceptance and traces | Story/Screenplay, Director | License not verified; small experimental reference |
| [ShotTessera](https://github.com/ixiehao/ShotTessera) | Reverse storyboard from existing footage, cut detection, representative frames, blur/duplicate rejection, contact sheet and manual correction | Video Editor, QuickClip, Review | MIT source declaration; native macOS implementation is a **pattern**, not a Linux/Qt runtime dependency |
| [VidBoard](https://github.com/LyAhn/VidBoard) | Paired start/end-frame planning and shot/reference consistency for music video | Music Studio, QuickClip, Director | License not verified; its hardwired sample models/providers must **not** become FA3 defaults |

This is a curated starting set, not a completeness claim about the GitHub topic search results. A candidate entry does not approve use of its source code.

## Proposed cross-application storyboard design (not admitted implementation)

1. **Single FA3 production project and shot data model.** Story/Screenplay owns the authoring entry point for story beats, episode/scene/shot identity, dialogue and user annotations. A stable scene/shot/board reference model links camera, lens intention, blocking, duration, frame ratio, audio cues, characters, props, environments, continuity requirements and provenance to the existing shared production asset graph.
2. **Three interchangeable board production paths.** (a) Lightweight hand-drawn and Krita-linked boards with original `.kra` preserved, (b) explicitly user-authorized AI-generated draft/keyframe variants routed through the central Model Router and HRB, (c) Bforartists-led 3D whitebox/previs with OpenUSD-compatible interchange and native DCC project preservation. No assumption that all paths exist or pass runtime admission.
3. **Versioned acceptance at shot granularity.** Generated or imported alternatives never silently replace user-approved boards. Distinguish scratch/edit visibility, review visibility and final render visibility; record accepted shot variants and continuity evidence. Require consent before costly generation or asset promotion.
4. **Animatics and editorial integration.** Feed accepted boards, timing and optional dialogue/music cues through FA3 Video Editor’s own `project.fa3video` timeline/command bus; MLT/FFmpeg implement previews and final editorial outputs. QuickClip may receive an approved selection and keep the complete `.fa3clip` interchange path. OTIO is optional interchange; it does not replace FA3-native projects.
5. **Reverse storyboard.** Offer video-to-shot extraction, shot boundary detection, representative keyframe sampling, deduplication and contact-sheet review inspired by ShotTessera; implement Linux-native backend using already accepted image/video facilities instead of a Swift/macOS dependency.
6. **Director/Workforce governance.** A goal-driven task graph may propose `Idea → Outline → Script → Scene → Shot → Board → Animatic → Production → Review`, but never execute unapproved model/provider changes, expensive media generation or publication. Temporal provides durable workflow semantics where already admitted; Central MCP Gateway and UAF remain integration boundaries.
7. **FA3 GUI placement.** Add an embedded **Storyboard / Previs** workspace in Story/Screenplay and surface the same approved shot sequence in Director and Video Editor. Avoid making a second overlapping video editor. Hand drawing can open/link Krita; previsualization can link Bforartists. Expose shot status, variants, inherited scene constraints and a diff/acceptance panel.

## Explicit Hardware Audit / execution boundary

- Metadata capture and planning are vendor-neutral, CPU-only viable, accelerator-cardinality `0..N`, make **no** hardware changes and require **no** GPU or model.
- Any future runtime implementation must perform a fresh Hardware Audit. HRB is the **sole** runtime resource authority and the Model Router is the **sole** model-route authority; providers/models are never pinned from donor documentation. Live route/provider/model availability is required. No silent fallback.
- Display GPU is display-only by default. An AI task may use it by the established FA3 exception when no other GPU **and** no NPU exists, or by explicit in-app assignment to a named model and task if additional GPU/NPU resources exist. The latter case never triggers automatic participation.
- GUI remains Wayland-preferred, X11-compatible and not KDE-exclusive despite the planned Qt6/QML/KF6 implementation. CPU-only functional paths remain valid.
- All external code/license/provenance/security/coexistence/distribution audits and independent current-host evidence are **pending**. Do not represent this documentation PR as implemented software or a successful runtime gate.

## Proposed verification before implementation

- Check donor registry normalized-key uniqueness, stable donor IDs, accurate candidate counts and all no-auto-install/activation/model flags; run existing donor-index check and associated CI.
- For each shortlisted code-level reuse, pin reviewed upstream commit plus SPDX and exact LICENSE/NOTICE/dependency tree; reject if obligations conflict with planned FA3 distribution.
- Define and exercise machine-readable shot/board inheritance, edit-vs-render visibility, native project preservation, approved-only graph promotion, CPU-only preview and no-silent-fallback negative tests.
- Add real current-host evidence **only when code, adapters, GUI and runtime have actually been executed and verified**.
