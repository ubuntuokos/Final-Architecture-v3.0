# Houdini C-topic donor collection — 2026-09-28

Source: [GitHub topic `houdini` filtered to language=C](https://github.com/topics/houdini?l=c&o=desc&s=).
Snapshot: **27 GitHub repository matches** observed on 2026-09-28, plus the topic page as a standing discovery index.
Disposition: **26 SideFX Houdini / procedural VFX records captured as non-authoritative candidates**; one unrelated Android translation/injection project deliberately omitted from FA3 donor candidates. This index is not an exhaustive inventory of all languages or future changes to the topic.

## Curated scope and FA3 beneficiaries

| Source | Reusable scope | Primary FA3 targets | Caveat |
|---|---|---|---|
| [wdas/partio](https://github.com/wdas/partio) | Particle attribute abstraction, BGEO/PDB/PTC IO, C++ and Python bindings | 3D Fabric, Asset Graph, World Generator, VFX/Gaffer | Per-format import/export and licensing audit before use |
| [MysteryPancake/Houdini-VBD](https://github.com/MysteryPancake/Houdini-VBD) | VBD/AVBD solver and optional OpenCL patterns | 3D Fabric, Animation/Character Motion, VFX/Gaffer | Experimental; upstream warns of buggy collision handling |
| [AdrianPanGithub/HoudiniPackage](https://github.com/AdrianPanGithub/HoudiniPackage) | Procedural city, terrain and landscape workflows | World Generator, 3D Fabric, VFX/Gaffer | Upstream Houdini 22 and CUDA >=12.2; concepts only until portable alternatives are assessed |
| [thi-ng/vexed-generation](https://github.com/thi-ng/vexed-generation) | VEX/OpenCL geometry utilities | 3D Fabric, World Generator, VFX/Gaffer | Optional accelerator examples; no backend requirement |
| [tangentbloom/Hinge-Energy](https://github.com/tangentbloom/Hinge-Energy) | Developability of triangle meshes | 3D Fabric, World Generator | Research/pattern reference only |
| [ttvd/houdini-sop-shapefile](https://github.com/ttvd/houdini-sop-shapefile) | Shapefile SOP/HDK import | World Generator, 3D Fabric, Asset Graph | Archived; import does not imply reverse export |
| [jtomori/VDB_activate_from_points](https://github.com/jtomori/VDB_activate_from_points) | HDK/OpenVDB volume-node patterns | 3D Fabric, VFX/Gaffer, World Generator | Archived legacy ABI reference |
| [ttvd/houdini-sop-triangulate-earcut](https://github.com/ttvd/houdini-sop-triangulate-earcut) | Earcut 2D triangulation integration | 3D Fabric, World Generator | Archived; separate upstream dependency audit |
| [glebnovodran/groundwork](https://github.com/glebnovodran/groundwork) | Visual-development math, motion and model export | 3D Fabric, Animation/Character Motion, Asset Graph | Interchange capabilities unverified |

**VEX, HDA, procedural workflow and educational references:**
[jtomori/vex_tutorial](https://github.com/jtomori/vex_tutorial),
[NiklasRosenstein/houdini-library](https://github.com/NiklasRosenstein/houdini-library) (archived),
[lcrs/_.hips](https://github.com/lcrs/_.hips),
[csdjk/LcLLib-for-Houdini](https://github.com/csdjk/LcLLib-for-Houdini),
[alt-shiftov/Houdini-Snippets](https://github.com/alt-shiftov/Houdini-Snippets),
[a-riccardi/ar_tools](https://github.com/a-riccardi/ar_tools),
[drichardson/HoudiniExamples](https://github.com/drichardson/HoudiniExamples),
[jdvfx/houdini_vex_python](https://github.com/jdvfx/houdini_vex_python),
[AreChen/VEX.Tutorial.Chinese.Version](https://github.com/AreChen/VEX.Tutorial.Chinese.Version),
[robertkist/houdini](https://github.com/robertkist/houdini) and
[Wambosa/houdini-wrangler](https://github.com/Wambosa/houdini-wrangler). The last repository's Unreal Engine examples and dependencies are **outside FA3 scope**.

**Rendering, image effects and archived interface references:**
[jtomori/vft](https://github.com/jtomori/vft) (archived fractals),
[MonkeyRaveProduction/houdini_configs](https://github.com/MonkeyRaveProduction/houdini_configs) (materials),
[groundflyer/physhader-for-mantra](https://github.com/groundflyer/physhader-for-mantra) (archived Mantra shaders),
[melMass/cops-cl](https://github.com/melMass/cops-cl) (Copernicus OpenCL),
[ttvd/houdini-rop-cop-gif](https://github.com/ttvd/houdini-rop-cop-gif) (archived GIF exporter) and
[ttvd/erlang-houdini-engine-nif](https://github.com/ttvd/erlang-houdini-engine-nif) (archived, explicitly deprecated: historical API patterns only).

Excluded: [luruizhe953-netizen/android-houdini-injection](https://github.com/luruizhe953-netizen/android-houdini-injection) is about the **different Android Houdini ARM translation layer**, not SideFX Houdini or procedural VFX; it is not a donor to this scoped collection.

## Capture and promotion boundary

- Source of truth: `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`; topic index and each curated repository have a unique normalized source key, `CANDIDATE` status and discoverable target hints.
- GitHub language `C` is **only GitHub's classification**, not verification that the project is portable C: sources mix VEX, HDK/C++, Python, OpenCL, HIP projects and documentation.
- GitHub-reported MIT/Apache metadata is recorded as **unverified upstream metadata**. Unknown and NOASSERTION remain unknown. **All source copying stays blocked** until repository-specific license, provenance, security, redistribution and coexistence review.
- Registering a reference does not install SideFX Houdini, adopt the upstream full application, add a provider, select a model or activate any runtime. Archived/deprecated sources are historical references only.
- FA3's native 3D-ready Scene/Shot/Camera/Rig/Pose/Clip/Constraint/Automation/Graph/Render/Asset Graph must remain independently owned; only selective capabilities and interchange patterns are candidates.
- The FA3 Video Editor remains the sole FA3 editor, and Unreal Engine remains excluded. If a codec is admitted for import, plan its corresponding export path under the owning module's contracts.

## Hardware Audit — metadata-only registration

- Vendor-neutral discovery and **CPU-only viable**, with **0..N optional accelerators**.
- No global CUDA, NVIDIA, AMD, ROCm, OpenCL, Houdini or other vendor runtime requirement is introduced by this registry update.
- FA3-AUTH-HOST-RESOURCE-BROKER-001 (HRB) retains live resource authority; the central Model Router retains model route authority.
- No current-host GPU, physics solver, software, license, build or codec execution evidence is claimed. Runtime adoption will need a separate Hardware Audit, current-host evidence, risk review and admission.

This document is a dated source review, not a promise that every linked repository remains unchanged or technically compatible.
