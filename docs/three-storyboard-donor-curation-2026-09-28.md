# Three storyboard donors — FA3 selective reuse review (2026-09-28)

## Scope and verified source identities

Review of three separately inspected upstream repositories as inputs to the existing FA3 Donor & Reference Registry and Reuse Discovery, **not** three additional FA3 applications:

| Upstream (verified default-branch commit) | Source licence / state | Selective contribution |
| --- | --- | --- |
| [yogendra-yatnalkar/storyboard-ai](https://github.com/yogendra-yatnalkar/storyboard-ai), `152d06025747a9c27c7b0c8cf59102300ab27a4b` (2026-07-01) | GPL-3.0 root LICENSE inspected; optional SAM 3 model/weights rights and external services separately assessed | Narration-first whiteboard animation; image threshold/contour drawing, optional mask-driven multi-pass drawing, multilingual script + TTS/subtitle pacing, research-to-scene workflow |
| [GaurAk495/ai-story-board](https://github.com/GaurAk495/ai-story-board), `bcd1b8ab5253885fde262016cf86be73b2ac1db7` (2026-03-22) | No root LICENSE found; README says open-source/free but does not grant an identifiable licence. **SOURCE COPY BLOCKED** | Panel-by-panel script/character/camera/prompt editor, per-shot reshoot, 16:9 reference layout and ZIP handoff as UX patterns |
| [dseditor/AI-storyboard-generator](https://github.com/dseditor/AI-storyboard-generator), `40ca3eaf723c8052f6e4761eaea7e03837aea6b4` (2025-11-22) | README claims MIT, but no root LICENSE file found in the inspected tree. **SOURCE COPY BLOCKED** pending author/rights verification | Separate image/video selection, selected/missing/all batch regeneration, cut rearrangement, imported initial frames, project ZIP/load/append, ComfyUI workflow-node mapping and FFmpeg.wasm comparison |

**Prior donor reconciliation:** FA3 registry already has RainLib/AI-Storyboard, 0xsline/StoryGen-Atelier and general beat/creative references in draft PR #518. RainLib is a narrative-beat and storyboard-planning pattern; StoryGen Atelier contributes adjacent-frame motion planning; the three projects above add **whiteboard vectorized draw animation**, **per-panel reshoot/editor UX**, and **separate image/video batch-control plus ComfyUI mapping**, respectively. Reconcile into the same FA3 Storyboard/Scene/Shot and Creative Studio workflows; do not create duplicate editors, routing stacks or unconnected data stores.

## Evidence-backed source-level observations

### 1. yogendra-yatnalkar/storyboard-ai — whiteboard animation

Inspected `genai-pipeline/tools/draw_animation.py`, `director.py`, `narration_refiner.py`, `video_subtitle.py`, `config.py`, README and root requirements. The drawing engine uses OpenCV adaptive thresholding, divides a frame into blocks containing dark pixels, traverses a nearest-neighbour order, simulates drawing-hand overlays, and optionally constrains drawing to an object mask. Director plans scene-level narration and visual setup; narration refinement tries to preserve existing facts while adjusting cadence to generated image/video duration; subtitles have an SRT generation and FFmpeg burn path. README claims optional SAM3 endpoint and standalone single-pass rendering.

Transfer **design concepts only** until GPL and separate model/asset distribution review. Do not transfer fixed Gemini/Veo/TTS/direct-research calls, rigid model pins, unmanaged .env secrets, provider autodiscovery or remote reference-image fetch. Research/reference sources require rights/provenance capture and explicit user-approved network scope. Avoid irreversible audio or caption burn-in; native FA3 project should retain editable subtitle/audio layers and original sources. A CPU-only OpenCV-style single-pass drawing concept must function without SAM 3; segmentation is optional and requires an independently admitted model + HRB resource lease.

### 2. GaurAk495/ai-story-board — editable scene/panel interaction

Inspected README, `AppDoc.md`, `src/components/SceneCard.tsx`, `src/lib/gemini.ts`, `src/lib/pollinations.ts`, package.json and app API directory. The implemented SceneCard exposes separate prompt generation, editable description/prompt and per-shot image generation or reshoot. The README describes independent story/character/scene phases, visual styles and browser ZIP export. Real code hardcodes `gemini-3.1-flash-lite-preview` and Pollinations Flux-style URL with 1280x720 default. README/install descriptions are not proof of full correctness, performance, export round-trip fidelity or production availability.

Reuse only UX and minimal typed entity patterns, adapted to FA3's production-type-aware screenplay schema, scene inheritance, narrative branches, change history, provenance and explicit human edit detection. Never expose a direct vendor API/model selection path in app code. No repository licence grant was identified; code copying is blocked pending provenance clearance. Do not import a separate web GUI as authoritative FA3 GUI.

### 3. dseditor/AI-storyboard-generator — selective multi-output processing

Inspected README, package.json, `index.tsx`, `ModelManagement.tsx`, ComfyUI workflow directory. README details six cut types, arbitrary cut count, 16:9/9:16, editable prompts, selected/missing/all image or clip generation, seed changes, single-end-frame final-cut handling, custom ComfyUI start/end/prompt/save node IDs, FFmpeg.wasm merge, and ZIP save/load/append. Source demonstrates separate sets of selected images/videos, project state, video versions, workflow node IDs and browser `localStorage` containing API keys and direct ComfyUI URL/model settings. The repository lacks an inspected root MIT grant notwithstanding its README assertion.

Use **separate selectable image/video batches, idempotent missing-only generation, image-first/version-aware invalidation, ComfyUI workflow manifest mapping and ZIP import/export UX** as patterns only. FA3 must not store secrets in browser localStorage, pin localhost:8188, give an application direct ComfyUI/model-provider authority, or auto-install models or plugins. ComfyUI may be an optional admitted downstream adapter with pinned workflow manifest, node types/IDs validation, model permissions, provenance and independent current-host tests.

## Native FA3 implementation proposal: single Storyboard-to-Production service

Existing application/fabric consumers, with no duplicate stand-alone project:

1. **Story/Screenplay**: typed scene/shot and approved story branch; production profile selects commercial/feature/TV/episode/live-specific fields. Script-to-shot proposals and visual continuity remain separately versioned. Source text (including imported/exported office-format families) and native application projects are preserved.
2. **Storyboard / Scene & Shot Designer**: edit a visual panel, character reference, camera/lens/shot framing, image prompt, visual style, source images, rendering visibility and narrative linkage independently. `Regenerate only this panel` never destroys its previous accepted version.
3. **Whiteboard Draw Animation mode**: optional 2D ink-mask/outline stroke planner -> human-editable drawing order, simulated drawing progress and per-object durations; deterministic CPU-only single-pass baseline first, optional admitted segmentation only if requested. Audio/narration lengths determine suggested stroke pacing, not irreversible final timing.
4. **Separate batch operations**: `GENERATE_MISSING_IMAGES`, `REGENERATE_SELECTED_IMAGES`, `GENERATE_MISSING_CLIPS`, `REGENERATE_SELECTED_CLIPS`, `REPLAN_TRANSITIONS`. Each is a typed UAF user intent; deduplicate jobs by accepted source digests, route and job revision; invalidate only provably affected downstream assets. Never silently re-render unchanged approved art.
5. **Storyboard-to-video transition bridge**: existing StoryGen pairwise `TransitionPlan` produces shot-bound motion candidates and editable start/end frame continuity, not a fixed-length or fixed-number frame chain. Closing shot is a separate optional plan. ComfyUI, admitted remote providers or deterministic CPU storyboard preview are delegated adapters, not FA3 authorities.
6. **Asset Graph and Review**: append-only asset provenance and immutable revision checks bind story branch, panel digest, approved image version, source image, generated clip, narration, subtitle and human-review receipt. Preserve previous candidate revisions and production handoff; never conflate story beat, musical beat and game beatmap events.
7. **FA3 Video Editor + QuickClip**: export into existing `project.fa3video` and `.fa3clip` full-import workflows, preserve native Krita `.kra`, Ardour projects and other project natives. FFmpeg/MLT editable clip/subtitle/audio tracks replace destructive standalone concat or burned-in-only caption outputs.

Proposed data additions are subordinate to the established canonical project model: `StoryBoardPanelRevision`, `DrawStrokePlan`, `TransitionPlan`, `BatchGenerationIntent`, `GeneratedMediaReceipt`; each carries parent `project_ref`, `story_branch_ref`, `scene_ref`, `shot_ref`, immutable source digests, approval and provenance references, original native project links, user override, optional model/provider admission and independent evidence refs. Extend existing contracts instead of defining second model/workflow/security authorities.

## Mandatory Hardware Audit and security boundaries

**This contribution: metadata/documentation-only; static constraints PASS.** No runtime, device, process or network service added. Vendor-neutral; deterministic drawing preview CPU-only; 0..N accelerators possible but no accelerator needed to read registry or plan a manual storyboard. Wayland preferred, X11 supported for later Qt6/QML GUI; no KDE-only requirements.

At a future implementation gate: UAF enters existing security/human approval, Temporal manages global durable job lifecycle, Central MCP Gateway mediates tools, Model Router routes pre-approved model participants, HRB admits CPU/GPU/NPU/memory workloads and leases, Secret Broker handles API keys. **No direct Gemini/Pollinations/ComfyUI/SAM 3 app calls**, no fixed models/ports, no automatic new model recruitment or silent fallback; no automatic display GPU use outside existing two-case explicit FA3 rule. External media/reference fetch must be consented, allowlisted, size-limited and audited.

## Testable gates for implementation (NOT yet implemented)

- Static source/licence/dependency/asset/model-weights review per repository, immutable upstream SHA pinned; do not label source-copy permission solely from README. Root GPL3 source cannot be assumed permissive for mixed distribution.
- CPU-only, no-segmentation whiteboard frame and audio-paced timing with deterministic fixtures. Validate zero-ink, transparency, edge contours, mask mismatch and non-Latin subtitles.
- Branch-aware invalidation: changing one shot updates only affected clips/stroke plan, preserves approved previous revisions and leaves alternative story branches intact.
- Separately selected image/video work: missing-only and selected-only operations are idempotent, retryable, bounded, resumable, cancellation-safe and never alter unselected accepted assets.
- ComfyUI workflow manifests must validate node IDs/types, pinned models and supported output before use; negative test for wrong ID, stale workflow, unauthorized direct endpoint and unapproved GPU.
- No raw API keys in browser/local storage, logs or project ZIP; verify secrets projected by Secret Broker at runtime only. Verify size/content/scheme/sandbox for external images to prevent SSRF and secret disclosure.
- Editable Video Editor/QuickClip imports preserve audio sync, captions, raw images, clip provenance and native files; no unconditional `-c copy` or destructive flatten.
- Independent current-host E2E, security/rights and distribution review required for any runtime activation. CI-only PASS and donor CANDIDATE are never promotion evidence.

**Disposition:** capture all three separately as non-authoritative `CANDIDATE`. For GPL-3.0 treat Yogendra as workflow/algorithm research pending reuse policy. For unlicensed/missing-license repositories GaurAk495 and dseditor treat as strictly UX/pattern references without source copying.
