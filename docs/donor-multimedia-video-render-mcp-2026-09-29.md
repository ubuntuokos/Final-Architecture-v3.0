# FA3 multimedia/video/rendering/MCP donor curation — 2026-09-29

**Capture:** 19 user-supplied URLs and four separately verified upstream repositories, **23 new source-unique metadata-only CANDIDATE records**, 592 -> 615 against exact main base `cb3e5b34da3e0f4002f8fb82b4d1c0ae05375194`. This is not code/runtime/provider/model admission, license clearance, a new authority, CI PASS or current-host PASS.

## Curated source matrix

| Source | Class | Individually scoped observation | Potential FA3 targets |
|---|---|---|---|
| [Struktur AG GitHub organization](https://github.com/strukturag) | Organization discovery | Organizational source discovery; resolve individual codec/media repositories before reuse. | Photo/Image Studio, Video Editor, Production Import & Migration |
| [GitHub HEIF C topic filter](https://github.com/topics/heif?l=c&o=asc&s=updated) | Dynamic filtered topic | Dynamic HEIF C language/update-sort repository discovery; not a vetted dependency. | Photo/Image Studio, Production Import & Migration |
| [GitHub HEIF Objective-C topic filter](https://github.com/topics/heif?l=objective-c) | Dynamic filtered topic | Dynamic Objective-C HEIF interoperability discovery; no FA3 Apple-platform requirement. | Photo/Image Studio, Production Import & Migration |
| [GitHub AV1 Python topic filter](https://github.com/topics/av1?l=python) | Dynamic filtered topic | Dynamic AV1 tooling and Python workflow discovery. | Video Editor, Production Import & Migration |
| [GitHub MP4 topic](https://github.com/topics/mp4) | Dynamic filtered topic | Dynamic MP4 demux/remux, editing and metadata discovery. | Video Editor, Production Import & Migration |
| [GitHub MP4 video PHP topic filter](https://github.com/topics/mp4-video?l=php) | Dynamic filtered topic | Dynamic PHP web/API video-processing examples, no PHP host dependency. | Production Import & Migration, Video Editor |
| [GitHub MP4 files C-sharp topic filter](https://github.com/topics/mp4-files?l=c%23&o=asc&s=forks) | Dynamic filtered topic | Dynamic C# file-handling projects, no C# host dependency. | Production Import & Migration, Video Editor |
| [GitHub free-video-generator topic](https://github.com/topics/free-video-generator) | Dynamic filtered topic | Dynamic low/no-cost generation discovery; licensing and runtime must be verified per project. | Motion & Video Generation Fabric, QuickClip |
| [CharlieDreemur AI Video Converter](https://github.com/CharlieDreemur/AI-Video-Converter) | Verified upstream repository | Verified frame extraction, ControlNet-guided video-to-video style conversion and reassembly; model checkpoints not included in admission. | Video Editor, Motion & Video Generation Fabric |
| [GitHub image-to-video topic](https://github.com/topics/image-to-video) | Dynamic filtered topic | Dynamic image-to-video and temporal-consistency source discovery. | Motion & Video Generation Fabric, QuickClip |
| [benrugg AI Render](https://github.com/benrugg/AI-Render) | Verified upstream repository | Verified Blender add-on for scene-to-image Stable Diffusion and prompt animation; pattern only, no paid app dependency. | Bforartists, 3D Fabric, Motion & Video Generation Fabric |
| [Render AI Code GitHub organization](https://github.com/Render-AI-Code) | Organization discovery | Discovery of Cog wrappers and forks; identify true upstream origins before reuse. | Photo/Image Studio, Motion & Video Generation Fabric |
| [GitHub architectural visualization topic](https://github.com/topics/architectural-visualization) | Dynamic filtered topic | Dynamic architectural lighting/material/scene visualization discovery. | World Generator, 3D Fabric |
| [GitHub image-generation topic](https://github.com/topics/image-generation) | Dynamic filtered topic | Dynamic generation workflow research; central Model Router and HRB remain mandatory. | Photo/Image Studio, Creative Studio |
| [Render cloud deployment GitHub organization](https://github.com/renderinc) | Organization discovery | Render.com cloud deployment examples, not an image/video renderer; no paid runtime dependency. | Deployment Fabric, Optional External Deployment Providers |
| [GitHub render-deployment topic](https://github.com/topics/render-deployment) | Dynamic filtered topic | Dynamic Render cloud deployment patterns, not a required FA3 local runtime. | Deployment Fabric |
| [Official Model Context Protocol GitHub organization](https://github.com/modelcontextprotocol) | Organization discovery | Official protocol and SDK discovery; no second FA3 MCP Gateway. | MCP Gateway, Skill Fabric, Agent Federation |
| [GitHub MCP Registry catalog](https://github.com/mcp) | GitHub MCP catalogue | GitHub MCP server catalog UI, not the official MCP protocol organization; catalog entries need individual review. | MCP Gateway, Skill Fabric |
| [Microsoft MCP for Beginners](https://github.com/microsoft/mcp-for-beginners) | Verified upstream repository | Verified multilingual learning and sample repository, not production admission. | MCP Gateway, Skill Fabric, Developer Agent |
| [strukturag libheif](https://github.com/strukturag/libheif) | Verified upstream repository | Verified HEIF/AVIF, HDR, container metadata, image sequences and MP4 handling; optional codec plugins and patents require audit. | Photo/Image Studio, Production Import & Migration |
| [strukturag libde265](https://github.com/strukturag/libde265) | Verified upstream repository | Verified H.265 C decoder interoperability reference; license and patent review required. | Video Editor, Production Import & Migration |
| [Official MCP specification](https://github.com/modelcontextprotocol/specification) | Verified upstream repository | Official MCP specification for compatibility, versioning and security tests; no parallel gateway. | MCP Gateway, Skill Fabric |
| [Official MCP reference servers](https://github.com/modelcontextprotocol/servers) | Verified upstream repository | Official MCP reference servers are educational and not production-ready; selective sandbox/testing patterns only. | MCP Gateway, Skill Fabric, Agent Federation |

## Selective reuse and hard boundaries

**HEIF / AV1 / MP4:** `strukturag/libheif` supports the HEIF/AVIF container family, metadata, HDR, sequences and MP4; `strukturag/libde265` is a C HEVC decoding reference. Reuse only behind FA3's existing media/interchange adapters after individual codec, dependency, license, patent, security and Software Coexistence audit. Preserve FFmpeg/OpenImageIO and reciprocal-format import/export contracts. Filtered topic URLs are discovery queries, not reviewed code.

**Motion/video:** `CharlieDreemur/AI-Video-Converter` suggests frame extraction, ControlNet frame-level conditioning and reassembly. `benrugg/AI-Render` suggests Blender scene-to-prompt and prompt animation UX. Neither confers model-checkpoint rights, upstream runtime admission, paid rendering dependencies, or replacement of FA3-native Motion & Video Generation Fabric. Render-AI-Code contains forked/wrapped third-party sources: source-provenance must follow the original upstream.

**Cloud/graphics naming:** `renderinc` is Render.com's cloud deployment GitHub profile, **not** a visual renderer. Treat it and `render-deployment` as optional deployment-pattern indexes only; do not add paid cloud or rendering application requirements. Architectural visualization/image generation sources are individually vetted before use.

**MCP naming:** `modelcontextprotocol` is the official specification/SDK organization; its specification and educational reference servers were separately verified, and `microsoft/mcp-for-beginners` is a multilingual learning source. `github.com/mcp` points to GitHub's dynamic MCP Registry catalog, not an alternative protocol organization. Preserve the **existing** FA3 MCP Gateway, UAF, central Security/Secret Broker/Evidence, Skill Fabric and their fail-closed boundaries. No automatic catalog-server installation.

**Global FA3 policy:** The fixed **175-capability baseline** remains unchanged. Dynamic provider count, CPU-only route, host-vendor neutrality, HRB-only resource authority, central Model Router, explicit display-GPU task/model authorization, Hardware Safety Envelope and Software Coexistence remain mandatory. Topic results, transitive dependencies, licenses and other projects are never silently admitted.

## Concurrent changes and validation

Observed main cb3e5b34da3e0f4002f8fb82b4d1c0ae05375194 held 592 entries. Current registry PRs #528, #529 and #530 were cross-checked by source key and none contained this batch of 23 identities at inspection. These parallel branches mutate the same canonical file; reconcile by normalized source key against the actual exact head before merging, keeping their records and historical evidence. **Do not** blindly replace concurrent changes.

Metadata assertions during capture: 615 unique normalized source keys and 615 unique donor IDs, 23 candidate-only additions, all nine authority/automatic action flags false, capability_count=175. CI, final merge/reconciliation, source-copy rights and physical current-host runs remain PENDING and must be separately evidenced.
