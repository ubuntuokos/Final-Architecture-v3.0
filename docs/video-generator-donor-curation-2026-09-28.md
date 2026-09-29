# Video generator GitHub topic: selective FA3 donor curation (2026-09-28)

Source index: https://github.com/topics/video-generator

Scope: metadata-only source discovery and selective workflow/model research. Eight new records were captured in `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json` (seven individual repositories and the topic index). The already-registered `github:ath-maas/pixelle-video` remains a single existing source, not a duplicate of the renamed `AIDC-AI/Pixelle-Video` link; the existing archival `project:opendirector` is distinct from the newly verified `github:seme-org/open-director` repository.

## Narrow reuse targets

| Source | Selective donor scope | Intended FA3 consumers | Explicit blockers / boundaries |
|---|---|---|---|
| [Helios](https://github.com/PKU-YuanGroup/Helios) | Long-video T2V/I2V/V2V, group offload and context-parallel research | Generative Media Studio, Video Fabric, FA3 Video Editor | Already related to FA3 Helios/Open-Sora work; model weights, performance claims, provider choice and runtime admission require independent review/current-host evidence. |
| [Short Video Maker](https://github.com/gyoridavid/short-video-maker) | MCP/REST composition pattern: TTS, captions, background media, music | QuickClip, FA3 Video Editor, Central MCP Gateway | This is clip assembly, not image-to-video generation. Do not import fixed upstream voice/model paths or their rendering architecture as FA3 authority. |
| [ConsisID](https://github.com/PKU-YuanGroup/ConsisID) | Consistent reference-conditioned identity across generated clips, evaluation recipes | Character Studio, Digital Actor, Performance, Generative Media Studio | Face-reference consent and provenance required. Hardware feasibility and model admission remain pending. |
| [Agnes Video Generator](https://github.com/lcy362/agnes-video-generator) | Multi-scene workflow, task checkpoints, continuation, reference-based transitions | Film Planning, Story/Screenplay, QuickClip, FA3 Video Editor | Its unknown-provider fallback to Agnes is not acceptable under FA3's fail-closed Model Router contract. |
| [OpenDirector](https://github.com/seme-org/open-director) | Nine-agent screenplay/storyboard/character/location research pipeline and batch short-video workflow | Director/Workforce, Film Planning, Story/Screenplay, QuickClip | Reuse only patterns compatible with existing FA3 Director/Workforce and Temporal orchestration. Upstream LGPL-3.0 needs distribution/linking review before source reuse. |
| [AI Short Video Engine](https://github.com/chenwr727/AI-Short-Video-Engine) | Article-to-video pipeline with narration and FFmpeg composition | Story/Screenplay, QuickClip, FA3 Video Editor | Upstream README says MIT, but no root LICENSE file was observed; code reuse requires independent licensing check. |
| [OmniTransfer](https://github.com/PangzeCheung/OmniTransfer) | Research: motion, visual effect, camera and style transfer | Character Studio, Choreography, VFX/Gaffer, FA3 Video Editor | Current root exposes paper/demo assets but no implementation source. Apache-2.0 LICENSE and academic/non-commercial README wording require rights clarification; research reference only. |
| [GitHub topic index](https://github.com/topics/video-generator) | Repeatable future discovery of upstream projects | Donor & Reference Registry / Reuse Discovery | Discovery index only, never a software or model runtime dependency. |

## Existing entries reconciled

- `Pixelle-Video` already exists under `github:ath-maas/pixelle-video`. Its prior scene-task and media-capability-routing work is relevant to Creative Studio, FA3 Video Editor and QuickClip. Do not create an `aidc-ai` duplicate after the GitHub owner redirect.
- `project:opendirector` is an older archival, project-level record; `github:seme-org/open-director` is a separately verifiable repository and should be related rather than silently merged across different normalized source keys.

## Proposed implementation boundary

1. Use Reuse Discovery against the existing Registry and application links before defining any implementation task.
2. Feed selected film-planning, shot/scene, checkpoint and delivery patterns into existing FA3 Director/Workforce and dynamic production graph. Only the canonical Central MCP Gateway exposes tools; Temporal stays under its existing authority.
3. Preserve human-approved Story/Screenplay and character decisions, per-scene provenance, separate edit/render visibility and FA3-native `.fa3video`/`.fa3clip` outputs. Keep native upstream creative projects on interchange.
4. Route **all** generative model calls through central Model Router, then HRB-governed runtime/provider. Never pin an upstream vendor, upstream default model, or silent fallback.
5. Admit video models independently, only after capability-specific tests; no candidate record authorizes downloads or runtime execution.

## Required Hardware Audit compliance

Donor capture is metadata-only, CPU-only viable, accelerator-neutral and supports 0..N GPUs/NPUs. Clip assembly can have a CPU-only implementation. Model inference requires per-model hardware audit and actual current-host evidence. The HRB is the sole resource and placement authority. A designated display GPU stays reserved for display except under the existing explicit FA3 exceptions; spare compute demand never implicitly enrolls it. Wayland is preferred; X11 must remain supported, and UI logic must not require a particular desktop environment.

## Admission / verification gates

A future implementation PR must independently check: source and model licensing, dependencies and distribution; provenance and consent for reference identities/media; network and secret boundaries; deterministic checkpoint/restart behavior; native project export/import and timeline validation; router/HRB placement with zero silent fallback; vendor-neutral CPU-only composition path; actual current-host evidence. No repository was installed, model downloaded or performance benchmark executed in this curation.
