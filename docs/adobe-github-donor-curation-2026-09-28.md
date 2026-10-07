# Adobe GitHub donor curation — 2026-09-28

**State:** verified upstream repository identities and GitHub license metadata; metadata-only, non-authoritative candidate discovery. Canonical records: `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. This index records **36 repositories and 4 organization discovery sources**, not a blanket approval of all Adobe repositories or Adobe products.

**Hardware Audit:** capture and Reuse Discovery are vendor-neutral, CPU-only viable and accelerator-neutral (`0..N`). Each potential runtime integration must demonstrate CPU-only feasibility, alternative providers and current-host evidence; HRB remains sole resource authority. GUI workflows prefer Wayland while retaining X11 support, without KDE-only assumptions.

**Planning contract:** Every new/materially modified FA3 app or module consults the registry before implementation. Selectively reuse only the relevant algorithms, open interfaces, design principles or independently licensed components. Preserve existing `project.fa3video`, Krita `.kra`, native DCC/DAW projects and OTIO compatibility. Adobe proprietary application APIs are optional interoperability surfaces, never FA3 runtime dependencies. AI research donors may not silently select new models: Model Router → HRB → admitted provider/model remains mandatory.

**License boundary:** GitHub metadata is a declaration, not a legal audit. `UNKNOWN` and `Adobe Research License` entries are reference-only pending explicit rights review; ProcMatRL and EntitySeg are noncommercial-research restricted. EditVerse has component-specific licensing, so no blanket permission to copy. MIT, BSD-3-Clause, Apache-2.0 and OFL-1.1 still require per-file, dependency, data and distribution review. **No code, models, datasets, SDK binaries or fonts are imported by this PR.**

## UI / accessibility / visual design

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe/react-spectrum](https://github.com/adobe/react-spectrum) | FA3 GUI / QuickClip / Video Editor / Creative Studio | Apache-2.0 | accessible adaptive React UI design |
| [adobe/spectrum-css](https://github.com/adobe/spectrum-css) | FA3 GUI / Creative Studio / Model Manager | Apache-2.0 | Spectrum style tokens and visual consistency |
| [adobe/leonardo](https://github.com/adobe/leonardo) | FA3 GUI / Logo Designer / Creative Studio | Apache-2.0 | contrast-ratio-aware color generation |
| [adobe/react-spectrum-charts](https://github.com/adobe/react-spectrum-charts) | Analytics Fabric / Observability Fabric / Model Manager | Apache-2.0 | declarative accessible chart patterns |

## XMP and asset metadata

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe/XMP-Toolkit-SDK](https://github.com/adobe/XMP-Toolkit-SDK) | Asset Graph / Video Editor / Photo/Image Editor / Document Fabric | BSD-3-Clause | cross-format XMP metadata read/write |
| [adobe/xmp-toolkit-rs](https://github.com/adobe/xmp-toolkit-rs) | Asset Graph / Document Fabric / Creative Studio | UNKNOWN | Rust XMP toolkit bridge |
| [adobe/xmp-docs](https://github.com/adobe/xmp-docs) | Asset Graph / Document Fabric / Creative Studio | UNKNOWN | XMP open metadata standard documentation |
| [adobe/asset-compute-xmp](https://github.com/adobe/asset-compute-xmp) | Asset Graph / Document Fabric / Creative Studio | Apache-2.0 | XMP serialization in asset processing |

## 3D cross-application interchange

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe/substance-3d-connector](https://github.com/adobe/substance-3d-connector) | 3D Fabric / Bforartists Integration / Asset Graph / Creative Studio | Apache-2.0 | cross-application 3D asset interchange |

## provenance / authenticity

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe/c2pa-js](https://github.com/adobe/c2pa-js) | Asset Graph / Security Fabric / Video Editor / Creative Studio | UNKNOWN | C2PA client-side content provenance reference |
| [adobe/trustmark](https://github.com/adobe/trustmark) | Asset Graph / AI Red Flag Detector / Photo/Image Editor / Video Editor | MIT | image watermark embedding and detection |

## audio

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe/Deep-Audio-Prior](https://github.com/adobe/Deep-Audio-Prior) | Audio Fabric / Music Studio / Voice/Vocal | UNKNOWN | training-free audio source separation research |

## documents

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe/pdfservices-python-sdk-samples](https://github.com/adobe/pdfservices-python-sdk-samples) | Document Fabric / Creative Studio | MIT | PDF processing API samples |

## Adobe interoperability and APIs

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [AdobeDocs/uxp-photoshop-plugin-samples](https://github.com/AdobeDocs/uxp-photoshop-plugin-samples) | Krita Integration / Photo/Image Editor / Creative Studio | MIT | Photoshop UXP extension and automation examples |
| [AdobeDocs/photoshop-cpp-sdk](https://github.com/AdobeDocs/photoshop-cpp-sdk) | Krita Integration / Photo/Image Editor / Creative Studio | UNKNOWN | Photoshop C++ SDK interoperability surface |
| [AdobeDocs/after-effects](https://github.com/AdobeDocs/after-effects) | VFX / Gaffer / Video Editor / Creative Studio | Apache-2.0 | After Effects extensibility documentation |
| [AdobeDocs/uxp-after-effects](https://github.com/AdobeDocs/uxp-after-effects) | VFX / Gaffer / Video Editor / Creative Studio | Apache-2.0 | After Effects UXP integration reference |
| [AdobeDocs/uxp-premiere-pro-samples](https://github.com/AdobeDocs/uxp-premiere-pro-samples) | Video Editor / QuickClip / Creative Studio | Apache-2.0 | Premiere Pro UXP plugin sample workflows |
| [AdobeDocs/premiere-pro](https://github.com/AdobeDocs/premiere-pro) | Video Editor / QuickClip / Creative Studio | Apache-2.0 | Premiere Pro API and interchange documentation |
| [AdobeDocs/illustrator](https://github.com/AdobeDocs/illustrator) | Logo Designer / Krita Integration / Creative Studio | Apache-2.0 | Illustrator scripting and vector workflow documentation |

## video research

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe-research/EditVerse](https://github.com/adobe-research/EditVerse) | Video Editor / QuickClip / Creative Studio / AI Fabric | Adobe Research License | unified image and video editing research |
| [adobe-research/VideoDoodles](https://github.com/adobe-research/VideoDoodles) | Video Editor / Animation Studio / Creative Studio | UNKNOWN | sketch-driven video editing research |

## image research

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe-research/DiffusionHandles](https://github.com/adobe-research/DiffusionHandles) | Photo/Image Editor / VFX / 3D Fabric | UNKNOWN | 3D-aware image editing via diffusion handles |
| [adobe-research/figure-editing](https://github.com/adobe-research/figure-editing) | Document Fabric / Krita Integration / Creative Studio | UNKNOWN | scientific figure editing research |
| [adobe-research/sam_inversion](https://github.com/adobe-research/sam_inversion) | Photo/Image Editor / Character Studio / Creative Studio | UNKNOWN | GAN inversion and spatially adaptive editing |

## 3D research

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe-research/ProcMatRL](https://github.com/adobe-research/ProcMatRL) | 3D Fabric / Bforartists Integration / World Generator | Adobe Research License | reinforcement learning for procedural materials |
| [adobe-research/SuperGaussian](https://github.com/adobe-research/SuperGaussian) | 3D Fabric / World Generator / VFX | UNKNOWN | 3D Gaussian upsampling research |
| [adobe-research/obj-and-mat-selection](https://github.com/adobe-research/obj-and-mat-selection) | 3D Fabric / Bforartists Integration / Asset Graph | UNKNOWN | vision-language object and material selection |

## datasets

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe-research/EntitySeg-Dataset](https://github.com/adobe-research/EntitySeg-Dataset) | Krita Integration / Photo/Image Editor / Training Fabric | Adobe Research License | fine-grained entity segmentation dataset |
| [adobe-research/VideoSham-dataset](https://github.com/adobe-research/VideoSham-dataset) | AI Red Flag Detector / Security Fabric / Video Editor | UNKNOWN | video manipulation detection dataset |

## evaluation

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe-research/zs-video-eval](https://github.com/adobe-research/zs-video-eval) | Model Manager / AI Red Flag Detector / Video Fabric | UNKNOWN | zero-shot video model evaluation reference |

## typography

| Upstream | FA3 target(s) | License declaration | Candidate use |
|---|---|---|---|
| [adobe-fonts/source-sans](https://github.com/adobe-fonts/source-sans) | FA3 GUI / Video Editor / QuickClip / Creative Studio | OFL-1.1 | UI sans-serif typography |
| [adobe-fonts/source-serif](https://github.com/adobe-fonts/source-serif) | Document Fabric / Story Studio / Video Editor / Creative Studio | OFL-1.1 | editorial serif typography |
| [adobe-fonts/source-code-pro](https://github.com/adobe-fonts/source-code-pro) | Developer Agent / FA3 GUI / Document Fabric | OFL-1.1 | monospace programming typography |
| [adobe-fonts/source-han-sans](https://github.com/adobe-fonts/source-han-sans) | FA3 GUI / Subtitle Composer / Document Fabric | UNKNOWN | CJK sans-serif typography |
| [adobe-fonts/source-han-serif](https://github.com/adobe-fonts/source-han-serif) | Document Fabric / Subtitle Composer / Creative Studio | UNKNOWN | CJK serif typography |

## Organization discovery indexes

- [adobe](https://github.com/adobe) — find and verify future candidates; index is not blanket source/license admission.
- [adobe-research](https://github.com/adobe-research) — find and verify future candidates; index is not blanket source/license admission.
- [AdobeDocs](https://github.com/AdobeDocs) — find and verify future candidates; index is not blanket source/license admission.
- [adobe-fonts](https://github.com/adobe-fonts) — find and verify future candidates; index is not blanket source/license admission.

## Next steps before admission

1. Recheck exact upstream commit, LICENSE and subdirectory/binary/weights licenses at integration time.
2. Compare existing FA3 and open vendor-neutral/CPU-only donors in Reuse Discovery; avoid duplicating completed capabilities.
3. For candidate source reuse, complete provenance, security, dependency, hardware, native-file, coexistence and current-host evidence gates. For AI models, respect Model Router/HRB and the approved model set.
