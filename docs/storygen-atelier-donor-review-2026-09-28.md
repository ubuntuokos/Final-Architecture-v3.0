# StoryGen Atelier — selective FA3 donor review (2026-09-28)

Upstream: [0xsline/StoryGen-Atelier](https://github.com/0xsline/StoryGen-Atelier) at inspected commit `033e0c6ea2e54be23209cbaf29875b401e8a2010` (2026-09-17). Repository declares **Apache-2.0** in its root LICENSE; `backend/package.json` separately declares **ISC**, which requires provenance/licence reconciliation before copying any source. GitHub's default branch was inspected. This note is a design/reference review, **not** an upstream runtime acceptance or FA3 current-host test.

## Selective disposition

**CANDIDATE for workflow/algorithm patterns** in existing FA3 Story/Screenplay, Storyboard / Scene-Shot Designer, Director/Workforce, Creative Studio, Video Editor, QuickClip, Asset Graph and Review. Do not embed the entire upstream application or introduce a second project format, editing timeline, provider/router, scheduler, asset database or authority.

The upstream README documents (1) flexible prompt-to-storyboard frame creation, (2) pairwise visual transition analysis for every adjacent shot via a sliding window, (3) parallel external video-clip generation using start/end frames, (4) a separately prompted final-shot closing clip, (5) `ffmpeg` concat stream-copy, (6) SQLite logs and a gallery. Upstream code confirms a sequential shot loop with 2–12 images and hard-coded 4/6/8-second transition choices. This is useful as a reference for a **typed keyframe-to-motion handoff**, not a fixed FA3 timeline/shot-count model.

## Mandatory donor and architecture reconciliation

The existing central Donor & Reference Registry / Reuse Discovery already identifies RainLib/AI-Storyboard and other Story/Screenplay / video references. RainLib's narrative beat → storyboard → sequence → motion concept and StoryGen's pairwise frame-interpolation concept are complementary, but must be reconciled in **one FA3-owned canonical scene/shot/asset graph**, rather than duplicating agent chains.

```text
Story/Screenplay Fabric (production profile + branch + approved scene revision)
  -> existing canonical project / Asset Graph (Scene, Shot, keyframes, style, references)
  -> Storyboard / Scene-Shot Designer (human-approved frames + shot intentions)
  -> typed TransitionPlan (start/end frame digests, motion, timings, continuity policy)
  -> Director/Workforce + Temporal (durable work graph, delegated execution)
  -> UAF -> Security + approval -> Central MCP Gateway + Model Router + HRB
  -> admitted image/video provider or CPU-only manual/reference workflow
  -> evidence-bound generated clip assets -> FA3 Video Editor / QuickClip
  -> independent continuity review / correction / production handoff
```

**Production-type aware:** advertising, feature film, TV movie, episodic TV and live broadcasts must choose different shot metadata, pacing, approval and deliverable profiles. Story branch version, scene inheritance and user corrections remain independent: changing a master scene may invalidate affected downstream transitions but never silently overwrite accepted branch outputs.

**Scene/Shot contract sketch** (FA3-owned, subordinate to existing canonical project schema):
- `project_ref`, `production_profile_ref`, `story_branch_ref`, `scene_ref`, `shot_ref`, `shot_revision`
- `start_frame_asset_ref`, `end_frame_asset_ref`, their immutable hashes, visual/character/style inheritance refs and explicitly approved source branch
- `transition_intent`, `camera_move`, `subject_motion`, `duration_range`, `target_fps`, `timebase`, `continuity_constraints`, `approval_state`
- `provider_admission_ref`, `router_model_route_ref`, `resource_lease_ref`, `execution_receipt_ref`, `output_asset_ref`, `independent_review_ref`
- `manual_override`, `supersedes_revision`, `native_project_links`, `AI_provenance`

The keyframe-to-motion planner may suggest several approved alternatives per transition and keep all candidate prompts separate from the artist's editable instructions. AI notes and user notes remain separate and AI-originated text must be marked. No auto-approval of generated script, frame, motion prompt, clip or final edit.

## App boundaries

| FA3 application | Reuse surface | Boundary |
| --- | --- | --- |
| Story/Screenplay | Script-to-shot handoff, narrative and visual continuity | Branch aware, production-profile specific; original Office/Fountain/FDX/other admitted round-trip obligations unchanged |
| Storyboard and Scene/Shot Designer | Editable visual keyframes, adjacent-shot transition proposals, consistency | Dynamic number of shots; no mandatory 2–12 limit or fixed grid |
| Character, Animation and Bforartists/Blender | Asset- and camera-linked frame descriptions, optional previs/animation handoff | 3D-ready scene graph; preserve native .kra, DCC and motion sources |
| Director/Workforce / Temporal | Explicit job DAG for approved shot-pairs, gated parallelism, failed-task recovery | Temporal sole durable workflow owner; existing UAF/MCP/HRB/Model Router authorities |
| Asset Graph and Review | Immutable input frames, generated clips, provenance, SQLite-inspired searchable gallery UX | Existing authoritative Journal/Evidence and canonical project asset records; do not copy parallel SQLite authority |
| FA3 Video Editor / QuickClip | Editable transition clips, closing-shot option, MLT/FFmpeg timeline handoff | Keep `project.fa3video` and `.fa3clip` formats and their full import; no final destructive concat replacing timeline |

## Upstream implementation risks and FA3 negative rules

- `backend/src/controllers/storyboardController.js` clamps generated shots to [2,12]; `backend/src/services/llmService.js` and `videoService.js` fix transition duration to 4/6/8 seconds. FA3 must accept arbitrary approved shot counts and production-specific timings.
- `videoService.js` switches to MiniMax automatically if a key is set and `IMAGE_PROVIDER` does likewise; it otherwise pins Veo and calls vendor APIs directly. FA3 **forbids** implicit provider selection, fixed model/provider pins, silent fallback and direct vendor calls from applications. Model admission and routing remain central; cloud calls only through separately authorized provider backend. Do not assume any external video model is approved.
- Transition failure/JSON-parse failure can inject generic `Cinematic transition` output, which conceals loss of semantic fidelity. FA3 must emit typed `BLOCKED/NEEDS_REVIEW` with original error provenance and require explicit user approval of deterministic alternatives.
- `videoService.js` launches all clip jobs via unbounded `Promise.all`. Introduce HRB/Temporal-authorized bounded concurrency, provider rate limits, retry budgets, idempotency keys and cancellation; late/duplicate completions must not supersede approved outputs.
- The service fetches shot image URLs; validate allowed schemes/domains/content types/size and prevent SSRF or leaking local images without approval. Secrets must use FA3 Secret Broker, never project `.env` in managed production.
- `-c copy` concat can fail for incompatible frame rate, codec, timestamps, audio layouts and stream settings. Probe media, normalize when required through existing FFmpeg/MLT pipeline, verify duration and A/V sync; treat each generated clip as an editable native FA3 timeline asset.
- Upstream project root Apache-2.0 vs nested backend `package.json` ISC discrepancy, plus vendor APIs, fonts, model terms, example images and npm dependencies require separate full provenance review before any code or media incorporation. Default disposition: architectural/pattern reference only.

## Mandatory Hardware Audit and activation path

**This registry/documentation PR:** metadata only; vendor neutral, CPU-only viable; no GPU/NPU requirement, supported accelerator count 0..N; no new process, runtime, provider, network port or model. This is **not** current-host runtime evidence.

**Later execution:** existing hardware audit must precede provider/resource selection; approved model participants only, central Model Router and HRB authority, no automatic display-GPU enlistment or automatic silent fallback. CPU-only design path supports manual storyboards and deterministic prompt/shot planning without admitted generative image/video models. All actual provider execution must pass scope-bound independent security/licence/current-host E2E; UAF and Central MCP Gateway remain exclusive action/tool boundaries. Wayland-preferred Qt6/QML GUI with X11 support; choose service ports dynamically if required and do not disturb AdGuardHome.

## Implementation milestones (proposal, NOT delivered in this PR)

1. Query and reconcile central donor registry, existing Creative Studio/Storyboard/Video/QuickClip project contracts and RainLib storyboard patterns; register design intent and reuse assessment.
2. Define typed `TransitionPlan` / `GeneratedClipReceipt` additive interchange, branch-aware inheritance and deterministic invalidation; store original prompt, source hashes and human approvals.
3. Implement CPU-only deterministic planning + media preflight/probe and editable GUI previews, then test variable duration, one-shot closing, missing frames, branch changes and manually adjusted storyboards.
4. Add optional admitted provider SPI via Model Router + HRB + UAF/MCP, Secret Broker-projected secrets and bounded Temporal jobs; negative tests for unauthorized cloud calls, secret-driven auto-switch, unapproved display GPU and masked failure.
5. Wire Asset Graph to existing MLT/FFmpeg Video Editor and QuickClip full interchange; regression-check scene edits, image/video/native project provenance, variable codecs, media sync, cancellation and crash/resume.
6. Independent evidence gate on a real current host; no `ACTIVE`/release promotion from README claims, registry metadata or CI-only passes.

**Overall scope:** research + candidate capture only. Do not claim production capability or source-code transplantation.
