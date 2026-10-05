# G'MIC GitHub donor family — 2026-09-28

**Scope:** six verified upstream GitHub repositories, metadata-only donor curation for the existing FA3 Donor & Reference Registry. The previously analyzed source-less G'MIC record is **normalized in place** to the verified `GreycLab/gmic` upstream; five related projects are separate CANDIDATE records. Neither this page nor donor capture authorizes source copying, installation, dependency adoption, automatic model/provider selection or runtime promotion.

## Sources and scoped FA3 reuse

| Verified repository (observed branch head) | Donor scope and intended FA3 consumers | Source declaration and admission boundary |
|---|---|---|
| [GreycLab/gmic](https://github.com/GreycLab/gmic) — `0ae8bad5b32b0a1cc37f51746e28f66cb171218f` | G'MIC engine, `libgmic` C/C++ embedding, script/filter language, headless CLI; Krita Integration, FA3 Video Editor, QuickClip, VFX, Asset Graph, Creative Studio | Component-level CeCILL-C / CeCILL choice is documented in `src/gmic.h`; check each included component and its transitive dependencies. Existing `ANALYZED` registry status is retained, not promoted. |
| [c-koi/gmic-qt](https://github.com/c-koi/gmic-qt) — `aa4a6f4ab174b37fcdf4df5f94fde0898856523a` | **Out-of-process host adapter** and filter-selection UX for Krita Integration / Creative Studio; consult [new host HOWTO](https://github.com/c-koi/gmic-qt/blob/master/NEW_HOST_HOWTO.md), not a compulsory bundled GUI | GitHub GPL-3.0 declaration; separate compatibility review is required for host-side integration. Upstream branch was last pushed 2024-09-04 at intake. |
| [GreycLab/CImg](https://github.com/GreycLab/CImg) — `b89ff2b8f1b6cbfbbfb5100d8d5b6897b9294c6e` | Optional portable C++ image-processing primitives, image sequences and memory interchange; Asset Graph, Krita Integration, Creative Studio | Upstream describes component-level CeCILL-C / CeCILL. Evaluate composition independently from G'MIC; no mandatory library adoption. |
| [GreycLab/gmic-community](https://github.com/GreycLab/gmic-community) — `478cfd9c1493e6bdef926d6ca9414928b0d50cb9` | Community filter definitions and reusable procedural-image patterns; Krita Integration, VFX, FA3 Video Editor, Creative Studio | Exact code/filter and third-party asset licenses unverified. No automatic fetch or execution of remote filters/scripts. |
| [GreycLab/gmic-py](https://github.com/GreycLab/gmic-py) — `5517d689ce98c60a8d5e72a7143b3090357ab159` | Optional Python orchestration adapter for controlled offline processing and tests; Creative Studio, Krita Integration, Developer Agent | Upstream README states CeCILL; current binding was reworked, documentation/examples temporarily removed, and its PyPI `gmic` package was not updated at intake. Test exact pinned source in a Python venv before any admission. |
| [GreycLab/gmic-blender](https://github.com/GreycLab/gmic-blender) — `990324e645c56f4e2ef851d5b6ff99e8c28cc30b` | **Historical/experimental pattern only** for a Blender node-oriented integration; Bforartists / Blender interoperability, 3D Fabric, Creative Studio | Upstream labels itself pre-pre-alpha; last push 2020-06-30 and README targets Blender 2.8x. CeCILL-A declared in its README; do not install or assume compatibility with current Blender/Bforartists. |

The six repositories were checked through their GitHub repository metadata and exact default-branch heads on **2026-09-28**. GitHub `NOASSERTION` or missing license metadata is **not** permission to reuse source. The versions above are observation pins, not automatically admitted production dependencies. Official G'MIC documentation reports stable **4.0.5 (2026-09-04)**: https://gmic.eu/download .

## FA3 consumption design

- **Krita:** retain Krita's existing native G'MIC capability; prefer compatibility, project-file preservation and interoperable layer/filter metadata over creating a competing editor.
- **FA3 Video Editor / QuickClip:** explore an explicit, reproducible, per-frame or image-sequence **optional effects adapter** over the existing editor's MLT/FFmpeg pipeline and `.fa3video` / `.fa3clip` formats. Keep the FA3 timeline and command bus authoritative. Do not make G'MIC a separate FA3 editor.
- **VFX / Bforartists / Blender:** investigate texture generation, procedural image effects, compositing and controlled interchange, without depending on the obsolete Blender add-on or introducing Unreal Engine.
- **Asset Graph / automation:** store the exact filter command, vetted filter revision, color-space/pixel-format conversion and provenance; maintain deterministic replay and explicit user approval wherever execution policy requires it.
- **Security:** G'MIC supports programmable filters. Pin and validate permitted commands, inspect externally supplied scripts and third-party assets, block silent network fetch, and isolate any eventual processing worker under FA3's security and resource policies.

## Hardware Audit and authority

**Metadata-only change; no current-host execution or hardware mutation.** All references are optional, vendor-/accelerator-neutral in the FA3 architecture, keep a CPU-only path, and accept accelerator cardinality `0..N`. No CUDA, ROCm or other accelerator dependency is introduced. The Host Resource Broker remains the sole runtime resource authority. Where a provider or model is used by a later workflow, the central Model Router stays authoritative, with no fixed model, implicit provider admission or silent fallback.

Actual source copying or runtime adoption remains blocked until an exact-revision license and provenance review (including bundled filters/assets), security and host-coexistence assessment, CPU-only evidence and the existing FA3 admission/current-host gates. This donor-family curation creates **no new capability or architectural authority**.
