# Pixar GitHub donor curation — 2026-09-28

**Status:** selective, metadata-only source capture into `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. This document is a human-readable discovery index, **not** a code-reuse, dependency, provider, architectural or runtime admission decision.

**Scope:** all 10 public repositories returned by the official [Pixar Animation Studios GitHub organization](https://github.com/PixarAnimationStudios) on 2026-09-28 were inventoried. Five repositories and the organization index were captured as six *distinct* FA3 donor candidates. The other five appear below to make the scope and non-selection visible. An upstream source commit was observed for each captured repository, but has not been security-audited, compiled or promoted.

## Hardware Audit and safety boundary

- The donor registry and its discovery path are metadata-only: vendor-neutral, CPU-only viable, accelerator count `0..N`. No new accelerator, GPU, CUDA or OpenGL requirement is introduced.
- **OpenSubdiv:** CPU evaluation must remain a viable path; any optional acceleration (e.g., CUDA/OpenCL/OpenGL) is backend-specific and needs independent evidence and admission. Bforartists/Blender/OpenUSD may already provide OpenSubdiv, so avoid duplicate bundling.
- **OpenUSD:** USD schemas, stage composition, asset resolution and the bundled Hydra/Storm renderer are *possible* interoperability or architecture references, not a replacement for existing FA3 native projects, authoritative scene data, Khronos integration or rendering paths. Choose backends via the existing hardware/runtime authorities, not this registry.
- **Xolo/Chook:** Jamf/macOS/Ruby-specific components remain research or architectural-pattern references only, with no Jamf dependency, global system changes or Linux deployment assumption.
- Each source requires its own license/third-party provenance, security, coexistence, vendor-neutral alternatives and current-host evidence before any code copy, installation, provider admission or runtime use. FA3 HRB retains exclusive runtime resource authority. The Model Router remains the sole model-routing authority.

## Captured donor candidates

| Source | Intended selective use | FA3 targets | Upstream license declaration | State |
|---|---|---|---|---|
| [Pixar GitHub organization](https://github.com/PixarAnimationStudios) | Cross-application discovery index only | Donor Registry; Reuse Discovery | Per-repository; no blanket license | CANDIDATE |
| [OpenUSD](https://github.com/PixarAnimationStudios/OpenUSD) | Layered scene composition, USD interchange, ArResolver, bundled Hydra/Storm render delegates | 3D Fabric; Asset Graph; Creative Studio; FA3 Video Editor; World Generator; Virtual Production | Tomorrow Open Source Technology License 1.0 | CANDIDATE |
| [OpenSubdiv](https://github.com/PixarAnimationStudios/OpenSubdiv) | CPU subdivision, optional independently admitted acceleration, deforming-mesh regression | 3D Fabric; Bforartists/Blender; Character/Animation Studio; VFX | Tomorrow Open Source Technology License 1.0 | CANDIDATE |
| [OpenUSD-proposals](https://github.com/PixarAnimationStudios/OpenUSD-proposals) | USD schema and interoperability proposals, research horizon | 3D Fabric; Asset Graph; Reuse Discovery; future applications | Individual proposal/supplemental terms require review; no copied code | CANDIDATE |
| [Chook](https://github.com/PixarAnimationStudios/chook) | Webhook dispatch/test-event pattern **only** | Event Fabric; Agent Collaboration Room | Tomorrow Open Source Technology License 1.0 | CANDIDATE |
| [Xolo](https://github.com/PixarAnimationStudios/xolo) | Staged package-promotion and patch-lifecycle pattern **only** | Release Fabric; Developer Agent | Tomorrow Open Source Technology License 1.0 | CANDIDATE |

Observed upstream default-branch commits during this review (identification only; not an approved version pin):

| Source | Observed commit |
|---|---|
| OpenUSD | [`2a9a571d0f99`](https://github.com/PixarAnimationStudios/OpenUSD/commit/2a9a571d0f9957bad5c4a59ba859ebb8df518c51) |
| OpenSubdiv | [`c826d2713b51`](https://github.com/PixarAnimationStudios/OpenSubdiv/commit/c826d2713b51b64a9a6f6641c8c1e9a69f7aaa20) |
| OpenUSD-proposals | [`28aabccf6048`](https://github.com/PixarAnimationStudios/OpenUSD-proposals/commit/28aabccf6048818ad3578e59a34db14ad3eb2dc8) |
| Chook | [`a64e0eb52d08`](https://github.com/PixarAnimationStudios/chook/commit/a64e0eb52d088fc4b29e6e78f92b7a5431ac0536) |
| Xolo | [`89b7594fbff8`](https://github.com/PixarAnimationStudios/xolo/commit/89b7594fbff88bda139271a507a62540ffd24eca) |

License declarations above were checked against `LICENSE.txt` in the four corresponding implementation repositories. OpenUSD-proposals presents separate supplemental contribution terms; a repository-level license was not established during this review. **TOST 1.0 differs from Apache 2.0 in trademark terms**; do not silently record it as Apache 2.0.

## Other Pixar repositories inventoried, not captured as FA3 implementation donors

| Upstream | Disposition at this review |
|---|---|
| [ruby-jss](https://github.com/PixarAnimationStudios/ruby-jss) | Jamf Pro API wrapper; no demonstrated Linux FA3 need. |
| [windoo](https://github.com/PixarAnimationStudios/windoo) | Jamf Title Editor API wrapper; same boundary. |
| [pixar-ruby-extensions](https://github.com/PixarAnimationStudios/pixar-ruby-extensions) | Ruby language-specific extensions; no identified FA3 code-reuse need. |
| [depot3](https://github.com/PixarAnimationStudios/depot3) | Archived predecessor to Xolo; reference via Xolo, do not admit as a runtime. |
| [conda](https://github.com/PixarAnimationStudios/conda) | Fork of Conda; no need and conflicts with the FA3 venv-only environment policy. |

The organization index permits later discovery if a concrete reuse need emerges for an inventoried repository; the exclusions are **current-scope**, not bans.

## Planning contract

Every new or materially modified FA3 application, capability or module must first query the central Donor & Reference Registry through `FA3-REUSE-DISCOVERY-001`. For Pixar results, record capability-level reuse need, already available FA3/Khronos/Bforartists/Blender alternatives, exact upstream revision, complete license/dependency assessment, vendor-neutral and CPU-only viability, coexistence, and a separate admission decision. A `CANDIDATE` in the registry is never an implementation, installation or deployment approval.
