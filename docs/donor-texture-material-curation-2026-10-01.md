# FA3 Texture & Material Generator donor intake — 2026-10-01

**Authority:** metadata-only reference registration in `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`.

This intake is the exclusive donor-maintenance split requested after PR #581 was found to mix STTIF materialization with canonical donor mutation. It registers the three already owner-approved LTX/STTIF references plus seventeen Texture/Material Generator sources.

## Registered groups

- **Procedural / authoring:** Material Maker, tonym128/texgen.
- **Material semantics / interoperability:** OpenPBR.
- **UV / tangent correctness:** xatlas, MikkTSpace.
- **AI PBR / SVBRDF research:** MatFuse, StableMaterials, MaterialMVP.
- **Mesh texturing research:** Paint3D, SyncMVD, TEXTure, Text2Tex, TEXGen.
- **Texture synthesis:** mesh-texture-synthesis.
- **Dataset / benchmark references:** MatSynth, Poly Haven, ambientCG.
- **STTIF split references:** Lightricks/LTX-2, Lightricks/ComfyUI-LTXVideo and the pinned tiled-fusion documentation.

## Fail-closed boundaries

Registration is not adoption. No source code, model weights, datasets or binaries are downloaded or bundled by this change. No provider/model/runtime is admitted. No application donor-usage record is activated. The capability baseline remains **175** and architectural authority delta is **0**.

Text2Tex is retained as a non-commercial research/reference source because its declared license is restrictive for commercial reuse. StableMaterials, MatSynth, MaterialMVP, TEXGen and all model/data-bearing sources require separate exact-version License & Rights, model/data provenance and redistribution review before any use beyond reference. Dataset sources require per-ingest provenance and terms verification.

## Intended discovery targets

The new references are discoverable for later assessment by the planned FA3 Texture Generator / Texture & Material Generation Fabric, 3D Fabric, Geometry Fabric, Asset Graph, Render/VFX/World/Character surfaces, Model Router/Manager and evaluation/dataset governance as indicated by each registry record.

No such target binding is an implementation or adoption decision.
