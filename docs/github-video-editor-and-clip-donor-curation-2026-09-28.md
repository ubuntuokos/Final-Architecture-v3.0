# FA3 selective donor curation: AI video editors, open-source video and clip generation

Research snapshot: **2026-09-28**. Scope: [AI video editors (recently updated)](https://github.com/topics/ai-video-editor?o=desc&s=updated), [open-source video](https://github.com/topics/open-source-video), and [AI clip generator](https://github.com/topics/ai-clip-generator).

This is **source discovery and metadata capture only** under the existing `FA3-DONOR-REFERENCE-REGISTRY-001`. It changes no runtime, authoritative model/provider routes, application project format, or capacity claims. The reviewed GitHub topic pages also contain commercial unlocking/keygen/download-bait repositories; those are **excluded from the curated set**, regardless of update recency or stars.

## Reuse discovery: existing authorities and nonduplication

- Queried the canonical donor registry and application/donor links before selecting these entries. The initial main snapshot had 306 unique donor entries; 13 new repositories and 3 topic discovery indexes are captured here (322 total on this branch).
- Keep the existing OpenCut donor and the existing FA3 Video Editor / QuickClip application records; this PR neither creates a competing editor nor registers GUI panes as applications.
- **Concurrent draft PR #512** captures `lcy362/agnes-video-generator` and the separate `video-generator` topic, among other records. Reuse that record; do **not** create a second Agnes entry here. **PR #510** separately covers `yils-lin/short-video-factory` and plans QuickClip integration. **PR #459** reconciles other donor changes. This PR must undergo field-level union/rebase against the merged registry before merging; never replace its entries with a historical main snapshot.
- No upstream may assign itself as an FA3 editor authority, Model Router provider/model authority, independent MCP gateway, or Host Resource Broker.

## Individually checked repository candidates

Each `sha` is the GitHub branch-head commit observed 2026-09-28, not a claim that the entire dependency tree or shipped binaries have passed an audit. License labels are upstream GitHub API/README declarations, **not** a complete redistribution review.

| Upstream | Snapshot SHA | Declared license / caveat | Narrow reuse target |
| --- | --- | --- | --- |
| [OpenChatCut](https://github.com/0xsline/OpenChatCut) | `bb2a4f7e1bb587aa55f3816583ec180d58eb1432` | AGPL-3.0; patterns only pending counsel/distribution analysis | Proposal/draft editing sessions, typed undoable timeline commands, transcript-linked edits -> Video Editor + central MCP Gateway |
| [OpenShorts](https://github.com/mutonby/openshorts) | `29c54fa04c42621310f768adf40c81a1f3436bf2` | MIT declaration; audit bundled models, fonts, ffmpeg and optional cloud terms | Speaker/face-aware vertical reframing, highlight generation, subtitle/dub workflow -> QuickClip |
| [AutoClip (zhouxiaoka)](https://github.com/zhouxiaoka/autoclip) | `609e3fb31c4db3621712d7443fa33be8df94fbb0` | MIT declaration | Highlight candidate finding and human-review UX -> QuickClip |
| [Forge Film](https://github.com/F-R-L/forge-film) | `f67f0a003aee58b3afe1b4f48b39ba8db5ed30f0` | MIT declaration; README includes roadmap items, not demonstrated full runtimes | Scene DAG and critical-path scheduling reference -> existing Director/Workforce + production workgraph |
| [AI YouTube Shorts Generator](https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator) | `de07f3a94a9ef0c4c55376cfa118141de62a3d43` | MIT declaration; respect source media rights | Transcript-based clip candidates + vertical cropping -> QuickClip |
| [HotClip](https://github.com/xixihhhh/hotclip) | `62aef3919fdd7d8a974f80a9b721e0177eb408c2` | AGPL-3.0; patterns only pending legal review | VOD-to-clip workflow; long transcript search, resumable transcription/corrections -> QuickClip + Subtitle Studio |
| [Recut](https://github.com/6174/recut) | `adc8b2583c872d78539ef87f8b179e9fde877113` | GitHub API license NOASSERTION: source-copy blocked | Persistent reusable world/character/scene/style canvas -> Story/Screenplay + Asset Graph |
| [CaroCut](https://github.com/bilibili/carocut) | `2f8dc102012036a20b1645c2183e680b3e4a8fd4` | README says MIT; GitHub API license NOASSERTION; **Remotion has independent commercial terms** | Separation of planner/media/builder/reviewer roles + resumable production stages -> Director/Workforce |
| [AutoClip (artbyjazi)](https://github.com/artbyjazi/autoclip) | `5d0eac36fa615b79dd2104083bf273a96f8d68bb` | MIT declaration | Offline face/speaker-aware crop, captions and review/export pipeline -> QuickClip |
| [dawn-cut](https://github.com/kwakseongjae/dawn-cut) | `7de68fce41505d8092ec227806b8d4bea4127675` | MIT declaration; README marks conversational AI/MCP experimental | Deterministic EDL and text/silence/subtitle-based local editing -> Video Editor / QuickClip |
| [MakeMyClip Editor](https://github.com/MakeMyClip/editor) | `867333981a5bfa4fead1b12f5c96f9cdc34fb68b` | Editor MIT; README states bundled FFmpeg binary GPL, independently audit deployment | Typed agent-tool catalog, edit session history, snapshots/undo -> central MCP Gateway + Video Editor |
| [Monet AI Editor](https://github.com/Monet-AI-Editor/Monet) | `74fcb1646a2329dfa35acfe7b3726491544fca18` | MIT declaration | Cross-media video/image agent UX and semantic search patterns -> Creative Studio |
| [ClipTalk](https://github.com/GML-MMGroup/ClipTalk) | `c2870c289a8471f142fc90fd9dbe576c7be5250d` | GitHub API license NOASSERTION; source-copy blocked | Conversational editing intent and skills reference -> Video Editor / central MCP Gateway |

Topic discovery entries are `github:topics/ai-video-editor`, `github:topics/open-source-video`, `github:topics/ai-clip-generator`; they are indexes, never approved code.

## Selective implementation wiring (proposals, not work performed)

1. **FA3 Video Editor** stays the one authoritative full editor: `project.fa3video`, Qt6/QML/KF6 GUI, FA3-owned Timeline/Command Bus and MLT/FFmpeg rendering. Feed agent-generated *typed* timeline operations to dry-run + visual diff + explicit approval, undo and provenance. Treat OpenChatCut, dawn-cut and MakeMyClip only as donor designs; no Electron or Remotion editor takeover.
2. **FA3 QuickClip** stays a separate `.fa3clip` application. Combine *ideas* from OpenShorts, the two AutoClip implementations, HotClip and AI YouTube Shorts Generator: asset ingest -> transcription -> scored segment candidates -> speaker framing -> caption/voice/style -> human preview -> export or **complete editable** Video Editor import preserving timeline, clips, captions, reframe, audio, style and provenance. Ranking confidence is evidence, not publication authorization.
3. **Director/Workforce + existing dynamic production workgraph:** assess Forge Film CPM scheduling under Temporal and the central resource broker, preserving per-machine responsibilities, dependencies, checkpoints, backup machine plans, rescheduling and deterministic stage evidence. CaroCut contributes separate planner/media/builder/reviewer responsibilities and checkpoint ideas; agents cannot bypass the normal orchestration, permission or gate path.
4. **Story/Screenplay + Asset Graph:** assess Recut's persistent world/scene/style relationships without importing a second project authority. Keep layer-based common production project and DCC/native project preservation. Reusable references must be versioned, have rights provenance, support scene-level inheritance and explicit human override.
5. **Central MCP Gateway / UAF:** expose only FA3-defined typed, allowlisted, auditable edit and production tools. All AI model choices follow the one central FA3 Model Router and live admitted routes; do not retain upstream direct Ollama, proprietary API, arbitrary CLI, or static model pin as an alternative authority. No silently triggered generation, remote upload or public distribution.
6. **Subtitle / voice services:** expose local transcript and speech providers through existing contracts, avoid duplicated provider stacks, and preserve editable transcript-to-timecode provenance across QuickClip and Video Editor.

### Hardware Audit / host admission block

Metadata curation needs **CPU-only and 0 accelerators**. Any future candidate runtime must independently prove CPU-only support and dynamically discover 0..N GPU/NPU/accelerators and admissible backends without vendor pins. HRB is the **only resource authority**, Model Router the **only model-route authority**. The selected display GPU remains display-first: AI use is eligible automatically only when there is no other GPU **and** no NPU; otherwise only with explicit in-app designation of the **specific model and task**. No automatic expansion, silent fallback or parallel display-GPU enlistment. Prefer Wayland, support X11, and never tie the GUI to one desktop environment. Perform safety and full current-host evidence before admission.

### Rights, security, licensing and acceptance gates

- MIT source-code labels do **not** license embedded models, stock assets, fonts, downloaded media, ffmpeg builds or commercial video frameworks. Verify SPDX file at exact SHA, all included assets and transitive dependencies, attribution and distribution plan **before** copying any source.
- AGPL-3.0 donors remain architecture/UX references until separate distribution and network-service obligations are approved; unknown licenses and Remotion-related builds remain source-copy blocked.
- Treat ingested video, media links, captions, prompts, web content, media metadata and package hooks as untrusted. Sandbox parsing and execution, restrict read roots, validate archive/path boundaries, redact credentials and block automatic telemetry/cloud submissions.
- Future gate matrix: deterministic timecode/EDL diff, visual/audio QC and subtitle alignment, render hashes/provenance, human approval on destructive edits, local-only/no-upload test, CPU-only E2E, optional admitted hardware profile, separate Wayland and X11 GUI probes and exact QuickClip-to-Video-Editor preservation.
- This PR performs **no executable donor integration, no upstream install, no native host benchmark, no current-host PASS, no new capability, no new authority**, and no automatic registry promotion. Resolve donor registry concurrent PR overlap and regenerate exact-head projections and impacted application indexes before any merge.
