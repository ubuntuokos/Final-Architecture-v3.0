# Godot Engine GitHub donor curation — 2026-09-29

**Status:** selective, metadata-only donor candidate capture into `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. The [Godot Engine GitHub organization](https://github.com/godotengine) is an upstream discovery index, **not** an admission decision or a blanket approval of all repositories.

## Selective source registry

| Upstream source | Reference use within FA3 | Observed top-level license | Boundary |
| --- | --- | --- | --- |
| [godotengine](https://github.com/godotengine) | Organization-level ongoing repository discovery | N/A | No blanket repository/license approval |
| [godot](https://github.com/godotengine/godot) | Real-time 2D/3D scene graph, scene editor, animation, physics, renderer and workflow concepts for RT3D, 3D Fabric, World Generator, Character Studio, Video Editor | MIT (`LICENSE.txt`) | No mandatory engine/runtime, replacement Qt GUI, or unreviewed bundled third-party reuse |
| [godot-cpp](https://github.com/godotengine/godot-cpp) | C++ extension and GDExtension boundary/lifecycle patterns | MIT (`LICENSE.md`) | No implicit Godot runtime or native ABI dependency |
| [godot-demo-projects](https://github.com/godotengine/godot-demo-projects) | Real-time interactive 2D/3D scenes and animation examples | MIT (`LICENSE.md`) | Bundled assets and third-party parts need separate provenance/license review |
| [godot-docs](https://github.com/godotengine/godot-docs) | 2D/3D/editor and extension research reference | CC BY 3.0 (`LICENSE.txt`) | Attribute reused text; independently check embedded code/media |
| [godot-asset-library](https://github.com/godotengine/godot-asset-library) | Asset catalog metadata/API and application discovery patterns | Not established in this review | README describes maintenance mode and future deprecation; architecture reference only, not a backend dependency |
| [FBX2glTF](https://github.com/godotengine/FBX2glTF) | FBX-to-glTF interchange as optional 3D pipeline reference | BSD-style 3-clause (`LICENSE`) | Review FBX-related restrictions and transitive dependencies; no new mandatory codec |

The source repositories and listed license files/README were checked using GitHub on 2026-09-29. This is a **selective** review, not a complete inventory or license audit of every Godot organization repository.

## FA3 adoption boundaries

1. Every source starts as `CANDIDATE`; targeted Reuse Discovery can propose a source but does not approve it.
2. Preserve the native FA3 project model, planned Qt6 application UI, existing Khronos SDK Fabric and current rendering/interchange decisions. Neither the Godot editor nor a Godot runtime becomes an FA3-wide prerequisite.
3. Full provenance, license, security, Software Coexistence & Host Non-Interference, Hardware Audit and applicable current-host gates precede code import, dependency adoption, installation or runtime use.
4. Keep FA3 CPU-only viable, vendor-neutral and safe. Resource assignment remains exclusively with HRB, model routing with Model Router, and hardware mutation must remain inside the Hardware Safety Envelope.
5. Keep the capability baseline at **175**, provider count dynamic, and historical evidence intact. This curation does not claim completed RT3D functionality or close any runtime obligations.

## Reuse targets

- **RT3D / 3D Fabric:** scene graph, native extension, editor/animation and glTF interchange references.
- **World Generator / Character Studio:** hierarchical scenes, interactive animation, sample workflows and asset interchange.
- **Video Editor:** potential real-time scene preview and graphics workflow ideas without replacing the native video editor or render policy.
- **Application Fabric / Reuse Discovery:** asset catalog and extension patterns, with the legacy Asset Library treated only as a maintenance-mode research reference.

The canonical registry, not this document, is the deduplicated authoritative donor-note location. Each source has its own normalized GitHub key; org-level discovery and repository-specific entries are not duplicates.
