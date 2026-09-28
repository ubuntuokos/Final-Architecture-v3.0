# FA3 QuickClip: Short Video Factory selective integration plan (2026-09-28)

Status: **IMPLEMENTATION PLAN / NOT RUNTIME ADMISSION**. Source: [YILS-LIN/short-video-factory](https://github.com/YILS-LIN/short-video-factory), reviewed at upstream commit `f2aa5958b9a949b339e04d8aee9754223f07a18f` (2026-09-28), package v1.2.2. Registry ID: `FA3-DONOR-YILS-LIN-SHORT-VIDEO-FACTORY-001`. Parent FA3 donor-capture PR: #510. **No third-party source code, templates, generated media, or runtime dependency is adopted by this plan.**

## 1. Existing FA3 baseline, before adding anything

Use the canonical Donor & Reference Registry and Reuse Discovery **before** beginning each implementation PR. Consult related candidates `FA3-DONOR-PIXELLE-VIDEO-001` (scene-task pipeline), `FA3-DONOR-OPENCUT-001` (programmatic editor adapter; not production-admitted), `FA3-DONOR-KAOMEI-STICKMAN-VIDEO-DIRECTOR-001` (story/director pattern), `FA3-DONOR-NVIDIA-VIDEOPROCESSINGFRAMEWORK-001` (optional accelerator-specific reference only), and existing admitted FA3 capabilities. Their registry status is not source-code or runtime approval.

The FA3 repository currently declares `fa3.quickclip` and `fa3.video-editor` as **PLANNED internal applications**, rather than shipping either as an independently admitted native production runtime. Existing **implemented** building blocks include the native caption workflow (`src/fa3_caption_workflows.py`), `caption.editorial.project` UAF projection to QuickClip, the caption contract's editable QuickClip/OTIO handoff and the application/donor index. The video timeline and programmable-editing contracts specify typed mutation, dry-run/diff/approval, render cancellation, QC, provenance and OpenTimelineIO, but do **not** establish a working QuickClip application. Avoid treating contract presence or a source-level gate as a current-host PASS.

**Canonical reconciliation prerequisite:** the currently checked `canonical/profiles/FA3-VIDEO-001.json` still contains legacy `editorial_handoff: OTIO_KDENLIVE` and `FA3-PROGRAMMABLE-VIDEO-EDITING-001.json` still names Kdenlive as the human finishing NLE. Those older repository contracts **conflict with the later agreed single native FA3 Video Editor architecture**. The implementing P1 child PR must explicitly reconcile those canonical declarations, their dependent gates and compatibility tests through ordinary governance before claiming that the new editor boundary is implemented. Do not silently edit the old runtime contract, falsely claim that this planning PR fixed it, or revive Kdenlive as a second primary editor.

Non-negotiable existing design: FA3 Video Editor is the **only full editor**, with native `project.fa3video` and FA3-controlled timeline/command bus using MLT + FFmpeg; QuickClip is a **distinct, purpose-built short-form application** with native `.fa3clip`. A user-approved full QuickClip -> Video Editor import carries **timeline, clips, captions, reframe, audio, style and provenance**; neither native project is flattened or overwritten. Kdenlive/OpenShot/OpenCut are constrained reference/compatibility providers, not competing primary editors. Native Krita `.kra`, Ardour sessions and MIDI-as-audio-asset references are preserved.

## 2. Upstream-vs-FA3 capability gap assessment

| Upstream observed capability / exact source | FA3 present-state | QuickClip implementation decision | Acceptance evidence |
|---|---|---|---|
| Prompt -> script; provider/model/API fields in `src/views/Home/components/TextGenerate.vue` | FA3 has Story/Screenplay planning and Model Router contracts, but no QuickClip production script UI | Reuse *workflow idea* via approved Story/Screenplay document -> human-approved scene beats -> QuickClip; all LLM calls via central Model Router, never upstream direct provider settings | Deny fixed or unapproved provider/model, preserve human-edited text and separately attributed AI notes |
| Script -> EdgeTTS -> SRT in `electron/tts/index.ts` | Native Voice v2, narration and caption contracts exist; no complete QuickClip TTS job | Use existing FA3 Voice/Narration requests and admitted providers, optional offline-local mode; never hardwire EdgeTTS or silently switch online | Voice consent, explicit execution mode, route receipt, exact audio/caption linkage, failure BLOCKED rather than fallback |
| Audio-duration-driven segment assembly and cached media metadata in `VideoManage.vue` | FA3 media/timeline reference contracts exist, not QuickClip-specific selector | Implement a bounded, deterministic, seeded *shot-intent-aware* candidate selector over verified Asset Graph metadata; random mixing is opt-in, not the canonical editorial policy | Same inputs/seed/policy -> same EDL; reject unreadable/zero-duration assets and prohibited reuse |
| Multistep script/voice/media/render flow in `src/views/Home/index.vue` | Goal/Workforce planning baseline and UAF/Temporal boundaries exist; QuickClip production DAG absent | Map to existing Director/Workforce dynamic job graph: idea -> plan -> detail -> approved script -> assets -> narration -> captions -> edit -> preview -> QC -> delivery | Durable state/restart, bounded retries, all human approvals respected; no invented runtime PASS |
| Pixi-based per-frame subtitle PNG generation + FFmpeg overlay (`electron/effect-engine`, `electron/ffmpeg`) | Canonical Caption JSON, `caption.editorial.project`, Subtitle Studio and OTIO projection exist | Preserve *editable* canonical caption tracks; offer derived styled PNG/ASS overlay at export through admitted media/render path; never make raster frames canonical | Round-trip text, timing, style and provenance; Unicode/bidi and safe-zone QC; source captions unchanged |
| Video concat, trim, scale, pad, audio mixing/normalization via FFmpeg | Existing FA3 Video/Media Finish/programmable-edit contracts; no complete QuickClip exporter | Implement typed MLT/FFmpeg render plan backed by existing Render Fabric/HRB; timebase-aware VFR/AV sync, aspect profiles and loudness/true-peak QC | CPU-only synthetic E2E; inspect output frames/audio, compare expected durations, hash artifact |
| Continuous batch mode/presets in `VideoRender.vue` | Render Fabric/Temporal contracts exist; QuickClip batch UX absent | One immutable production recipe -> independently tracked variant jobs with per-job approval, seed and idempotency key; cancel/pause/resume supported | N-item batch has N separately addressable receipts; retry does not duplicate final artifacts |
| Per-stage render progress, abort and temp cleanup in `electron/ffmpeg`, `electron/effect-engine` | Typed render/job and evidence contracts exist | Integrate those *behavior patterns* into current FA3 worker lifecycle and artifact store, not Electron main process/IPC | Cancellation stops descendants, cleans uncommitted temp outputs, retains audited prior artifacts; restart uses durable checkpoint |
| Electron/Vue desktop UI (upstream) | FA3 Control Center Qt6/QML/KF6; Wayland primary, X11 supported | Build separate **FA3 QuickClip Qt6/QML** page/launcher, declarative UAF intents and project-owned workspace; no Electron requirement | Focus/keyboard/reduced-motion, GUI reconciliation, Wayland/X11 interactive smoke |
| Local-first description; upstream changelog v1.2.1 documents anonymous event reporting | FA3 explicit privacy/security/Secret Broker policy | **No inherited telemetry**. No network egress for an offline job; optional explicitly consented online services through existing authorities, never a hidden analytics channel | Negative egress test, secrets absent from logs and project files |
| Upstream AGPL-3.0 license | FA3 independent distribution-compliance admission | Reference only; independently implement generic ideas against existing FA3 contracts. Copying/embedding/bundling upstream code stays **blocked** until separate legal/distribution review | Source provenance attestation + license-review receipt before any change in reuse mode |

Upstream evidence is a **design observation**, not proof that the proposed FA3 behavior exists or that upstream passes FA3 gates. Inspect upstream license, lockfile and network/telemetry entry points independently before any proposed code reuse.

## 3. Proposed native QuickClip project and boundaries

Propose `fa3.quickclip-project.v1` as the **application-owned** schema to be introduced in a separate implementation PR, not as a second global timeline authority:

- Project envelope: stable `project_id`, `revision`, `parent_revision_sha256`, `recipe_version`, locale, approved intent, project/scene/shot metadata and explicit approval receipts.
- Reusable **layer-file** references: canonical Asset Graph IDs + digest, source project/native references, edit-visible and render-visible flags tracked **independently**, local scene overrides with explicit inheritance, and separate `user_notes` versus attributable AI-note sidecar references. Prohibit silent mutation of the human-approved script.
- `ShotSelectionPlan`: semantic beat/asset match, hard exclusions, content identity, in/out in exact rational media time, duration constraints, optional seed, filter policy, reuse budget, shot-by-shot explanation and deterministic recipe digest. Disallow unseeded randomness for repeatable production.
- Timeline: QuickClip's editable timeline/clip/caption/reframe/audio/style graph with loss-accounted **OTIO projection**, not OTIO as a replacement for the native `.fa3clip` file; per-shot edit decisions are explicit.
- Render variant: aspect profile (9:16, 1:1, 16:9, extensible), target fps/timebase, narration track, BGM/music stems including MIDI asset references, subtitle presentation projection, encoder capability constraints, expected duration, scope and project revision digest.
- Artifact lineage: script/caption/voice revisions, approved asset IDs, source licenses, selected route/provider/model receipt if used, HRB lease, render-job ID, input digests, FFmpeg/MLT provenance, QA result, final SHA-256, cancellation state, native-file round-trip receipt.

Treat large media as external, content-addressed referenced assets; `.fa3clip` is a portable manifest with explicit missing-asset reporting, never silently embeds or rewrites arbitrary source projects. Atomic project save with revision precondition; staging and rollback for mutating timeline operations.

## 4. Execution graph and interfaces (proposed, not activated)

```text
Human creative intent / Director
  -> existing Story/Screenplay: approved script + beats + shot intent
  -> existing UAF + Workspace/Asset Graph: authorized media references
  -> existing Voice/Narration -> central Model Router -> admitted provider/model
  -> existing Caption JSON: transcript / word timings / revisions
  -> QuickClip shot plan: semantics, durations, deterministic optional seed
  -> editable .fa3clip: timeline / reframe / sound / captions / style
  -> approved preview and explicit user revisions
  -> existing Temporal durable job graph + HRB media worker (CPU-only valid)
  -> MLT / FFmpeg capability-admitted headless export
  -> independent visual/audio QC + SHA-256 + Journal/Evidence
  -> approved output, or complete editable Video Editor import
```

Candidate QuickClip UAF action IDs for **later** canonical action registration: `quickclip.project.create`, `quickclip.recipe.validate`, `quickclip.shots.plan`, `quickclip.timeline.apply`, `quickclip.preview.request`, `quickclip.batch.submit`, `quickclip.batch.status`, `quickclip.batch.cancel`, `quickclip.export.approve`, `quickclip.editor.handoff`. Actions are **names proposed by this document**, not presently registered/runnable UAF APIs. Do not bypass the central MCP Gateway; all mutations need typed contracts, immutable revision preconditions, idempotency keys, dry-run/diff and policy-mediated approval where applicable. All new state updates go through existing UAF/Durable/Journal ownership; Temporal alone owns long-running job lifecycle.

For an approved bulk request, freeze recipe + input asset revision + locale + variant index + seed + output profile as idempotent job identity. Any change produces a new revision/variant. Jobs may run on a validated local host or authorized heterogeneous worker; worker takeover must re-admit via HRB and verify content-addressed inputs and selected route. Do not make an unavailable remote worker or GPU a hard requirement. Maintain central and scoped local project state, explicitly reconciling revisions.

## 5. Hardware Audit, Model Router and GUI requirements

**Mandatory Hardware Audit:** vendor-neutral detection of physical/logical CPU, 0..N GPUs, NPUs, supported APIs and per-device roles; **CPU-only render + approved local AI path must remain viable**. No fixed CUDA, NVIDIA SKU, GPU ordinal, NUMA node or desktop shell. The central HRB is the sole allocation/placement/lease authority. The sole model decision path is **FA3-AUTH-MODEL-ROUTER-001 -> admitted runtime/provider -> approved model -> LiteLLM when applicable**. No direct upstream OpenAI-style URL, fixed Ollama/LM Studio, new model participant, silent fallback, or automatic GPU fan-out.

Designated **display GPU AI policy:** it remains display-only by default. AI may use it when there is **no other GPU and no NPU**, subject to normal HRB policy; if another GPU and/or NPU exists, its AI use requires a **specific explicit in-app assignment to a concrete model and task**. Availability alone never grants access. Media rendering remains a separately declared HRB workload, not a pretext to add a GPU to AI.

QuickClip must be **separately launchable** from the existing FA3 Create/AI Studio navigation via a registered semantic route, native Qt6/QML/KF6. Proposed UI panels: Goal/Recipe, Story/Assets, Shot Map, Timeline, Voice/Music, Subtitle/Style, Preview, Batch Queue, Quality/Evidence, Video Editor handoff. Side-by-side user-approved and proposed AI content; explicit visibility toggles for editing vs rendering; unambiguous blocked/running/partial/verified status and cancellation. Do not register a GUI surface as a separate donor/application. Wayland preferred, X11 supported, no KDE-exclusive business logic. The reference Qt app is not claimed production-admitted until real host visual tests pass.

No incidental change to AdGuardHome ports, host driver/BIOS choices, secret storage policy, or excluded real-time engines (including Unreal Engine).

## 6. Application and donor impact

| FA3 consumer | Change and integration artifact | Authority preserved |
|---|---|---|
| **QuickClip** | Native recipe, seeded shot planner, `.fa3clip`, batch controls, preview and CPU-only final export | QuickClip local project, central HRB/Router/UAF |
| **Video Editor** | User-approved, **full editable** timeline/clips/captions/reframe/audio/style/provenance import into `project.fa3video` | Sole full video editor and its timeline/command bus |
| **Story/Screenplay** | Approved beats, reusable scene/shot metadata and approved script handoff | Story authority, human approval, revision provenance |
| **Voice/Vocal and Music Studio** | Voice assets, mixdown/stems, voice consent, timing, MIDI asset references | Existing Voice/Narration and Audio Fabric |
| **Subtitle Studio** | Canonical Caption JSON remains editable; output-specific style render is a derived artifact only | Existing caption-authoring and UAF contracts |
| **Marketing / admitted campaign provider** | Explicit **approved media package only**; optional later Mautic adapter; no automatic posting or telemetry | Existing Marketing campaign authority and separate provider admission |
| **Director/Workforce, Render Fabric, Asset Graph, Evidence** | Durable dynamic job graph, content-addressed asset lineage, HRB placement and independently checked completion | No new orchestration, resource, model, evidence or registry authority |

Proposed index edges (all `PROPOSED`, human-approved, no automatic activation): Story/Screenplay -> QuickClip, Music Studio -> QuickClip, QuickClip -> Mautic; preserve existing QuickClip <-> Video Editor links. The edge to Mautic is metadata only, **not** campaign-posting or runtime admission.

## 7. Phased implementation and concrete gates

**P0 — This planning PR (documentation and metadata).** Record selective assessment + upstream immutable commit, source/license/telemetry limitations, source-unique donor identity and exact FA3 cross-app proposals; repair donor `backfill.entry_count` to make `fa3-app-donor-index --check` valid. Required check: registry exactly once, candidate only, `automatic_* = false`, all proposed links remain human-approved. No actual QuickClip or current-host runtime claim.

**P1 — Native project / user-editable core.** Add `fa3.quickclip-project.v1` schema and validator, `.fa3clip` atomic revisioned save/load, deterministic shot-selector planning contract, immutable input asset references, separated edit/render visibility, separately attributed user/AI notes and OTIO loss receipt. Implement typed plan/diff/dry-run without activating providers. **Gate:** round-trip all timeline data; reject invalid timebase, stale revisions, duplicate shot ID, missing/corrupt media and unintended script rewriting; same seed + assets + policy yields identical EDL.

**P2 — Content, voice, caption and audio binding.** Bind approved Story assets via UAF, existing Voice v2/Router/Secret Broker and canonical Caption JSON. Preserve human approval and safe script edits, allow user to choose no narration, local/offline-eligible narration, or explicitly approved online service. Audio-overrun policy is explicit: bounded retiming with receipt or human edit; never silently rewrite/downgrade. **Gate:** voice/caption/shot timing reconciled for synthetic HU/EN/Unicode fixtures; consent, offline/no-network, stale-caption and unsupported-provider negative tests.

**P3 — Batch and media worker.** Add deterministic recipe/variant/idempotency and existing Temporal lifecycle integration; HRB-admitted CPU-first FFmpeg/MLT exporter with available hardware option only after admission. Asset metadata cache includes invalidation on identity/content change; per-frame styled subtitle outputs may be derived only. Include loudness/true-peak, clipping/silence, fade/ducking, VFR timing and aspect/reframe QC. **Gate:** synthetic CPU-only N-job batch + same-input replay + cancel/retry/resume + cross-worker lease takeover + separate output hashes/provenance. No unsupported "auto failover" of models or unauthorized display GPU.

**P4 — Separate Qt QuickClip GUI and full editable Video Editor interchange.** Register one semantic QuickClip route in the existing FA3 surface registry and a separate launcher, use Control Center design tokens and typed action intents. Implement `.fa3clip` -> `project.fa3video` full mapping and provenance-preserving user approval; keep `.kra` and Ardour session references. **Gate:** full editable round-trip and loss-report verification; focus/accessibility, Wayland reference build + interactive current-host smoke, X11 supported smoke; no phantom operational status.

**P5 — Distribution, privacy, evidence and rollout.** Independent security/license/supply-chain review; no copied AGPL source absent signed-off distribution plan, no inherited upstream telemetry, and no unsolicited network egress. After authentic Hardware Audit, per-app UAF/policy/HRB/model-route admission and current-host CPU-only E2E plus available authorized-accelerator test, attach real QC/evidence receipts to immutable exact-head CI. **Gate:** canonical policy and application gates PASS, adversarial negative suite PASS, successful cancellation/rollback, approved artifact SHA-256 and actual current-host GUI/export receipts. Until then mark `PLANNED` / `PENDING_CURRENT_HOST`, not production READY.

### Mandatory negative-suite cases

1. Upstream AGPL source copied without license receipt; direct EdgeTTS/provider call; unapproved model replacement -> BLOCK.
2. Second GPU/NPU present and display GPU implicitly assigned AI work, or renderer silently recruits it for AI -> BLOCK.
3. Offline intent causes external request or analytics event; secrets appear in project/FFmpeg arguments or logs -> BLOCK.
4. Unseeded batch advertised as reproducible, asset digest changes without cache invalidation, retry duplicates a completed variant -> BLOCK.
5. Cancel leaves or publishes an unverified partial final video; expired remote lease reused without new HRB approval -> BLOCK.
6. Lossy QuickClip -> Video Editor import discards captions, reframe, audio, style or provenance without explicit loss report and approval -> BLOCK.
7. Destructive timeline change without project revision precondition, dry-run/diff/required human approval -> BLOCK.
8. GUI displays READY/VERIFIED without real matching current-host evidence; reference/static gate mistaken for runtime promotion -> BLOCK.

## 8. Delivery boundary and referenced sources

This file is a **complete implementation backlog and architecture comparison**, not evidence of completed P1–P5 code. Create focused child PRs per phase, with exact-head tests and verified receipts. Update the canonical registry/reference assessment when the upstream immutable revision or actual admission disposition changes; never silently promote its donor status.

- [FA3 app/donor links](../canonical/FA3-APPLICATION-DONOR-LINKS-001.json)
- [FA3 canonical donor registry](../canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json)
- [FA3 native caption contract](../canonical/contracts/FA3-CAPTION-SUBTITLE-CONTRACTS-001.json)
- [FA3 Video Timeline Provider contract](../canonical/contracts/FA3-VIDEO-TIMELINE-PROVIDER-CONTRACTS-001.json)
- [FA3 Voice contract](../canonical/contracts/FA3-VOICE-CONTRACTS-001.json)
- [Upstream 2026-09-28 pinned tree](https://github.com/YILS-LIN/short-video-factory/tree/f2aa5958b9a949b339e04d8aee9754223f07a18f)
- [Upstream changelog](https://github.com/YILS-LIN/short-video-factory/blob/f2aa5958b9a949b339e04d8aee9754223f07a18f/CHANGELOG.md)
- [GNU AGPLv3 text](https://www.gnu.org/licenses/agpl-3.0.en.html)
