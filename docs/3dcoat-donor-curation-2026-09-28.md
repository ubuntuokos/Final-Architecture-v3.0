# 3DCoat donor curation and FA3 integration study — 2026-09-28

**Status:** four distinct sources captured as non-authoritative `CANDIDATE` records in `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. This is a scoped architectural analysis and metadata-only donor capture, **not** an approved code import, installer, vendor dependency, production integration, model admission or current-host PASS.

## Verified source inventory

| Source | Observed capabilities | Intended FA3 reuse | Source licensing and constraint |
| --- | --- | --- | --- |
| [3DCoat](https://3dcoat.com/) | Voxel/surface sculpting, auto/manual retopo, UV editing, PBR painting, parametric hybrid modelling, GPU nodes, lattice generation, Python and C++ extension API | Optional external DCC and research into workflows; no source copying | Proprietary commercial program; integration subject to end-user agreement |
| [AndrewShpagin/io-coat3d](https://github.com/AndrewShpagin/io-coat3d) | Vendor-shipped Blender 4.2/4.3 Applink, exchange-file and mesh/texture round trip | Protocol, interoperability and optional separately admitted Bforartists/Blender add-on | `__init__.py` declares GPL-2.0-or-later; evaluate full-file and third-party provenance before reuse |
| [LiamSmyth/LKS_3DCTools](https://github.com/LiamSmyth/LKS_3DCTools) | Configurable radial tree menu, selected/subtree/all batch operations, instance-aware density resampling, visibility, hotkey conflict resolution | UI/workflow patterns, idempotent scoped batch operations and recovery design | README grants informal permission, but no standard license established; source-copy **blocked** pending legal clarification |
| [Blender io_coat3D addon](https://github.com/blender/blender-addons/tree/main/io_coat3D) | Independent Blender-side Applink with file exchange and mesh/texture transfer | Comparative interoperability and regression-test baseline | `__init__.py` declares GPL-2.0-or-later; no automatic copying or dual bundling |

Observed upstream default-branch identification commits (not admission pins): `AndrewShpagin/io-coat3d@15b51ab8d1bfe9937fb6ecf967581c9a239b12b3`, `LiamSmyth/LKS_3DCTools@8b69798f9ead57068aa8e53e7d05f45a947439c1`, `blender/blender-addons@b42d68627734cb18af0e6f41537063984313a284`. Exact source revision, manifest and hashes must be frozen in an independent future implementation PR.

Primary vendor references: [2026.11 release details](https://3dcoat.com/release_note/v202611/), [feature matrix](https://3dcoat.com/features/), [Python and Core API](https://3dcoat.com/documentation/manual/scripting-and-core-api/), [Blender Applink documentation](https://3dcoat.com/documentation/manual/getting-started/app-links/blender-4-2-applink/), [Linux system requirements](https://3dcoat.com/system-requirements/), and [Pilgway terms](https://pilgway.com/page/terms_of_use). Vendor documents provide product feature claims; they are not FA3 runtime test evidence.

## FA3 placement and scope

The FA3 Creative Studio remains the user-facing entry, **Bforartists remains the primary DCC**, and Blender integration stays available. Introduce a separately admitted, optional **3DCoat external-workflow connector** under 3D Fabric / Asset Graph rather than a second authoritative FA3 DCC or a standalone FA3 architecture.

Potential selective applications:

1. **3D Fabric / Creative Studio:** send sculpt meshes for optional 3DCoat voxel sculpting, retopology, UV or painting; require explicit return/import and non-destructive provenance.
2. **Bforartists/Blender bridge:** compare the two open Applink implementations; document FBX/OBJ/GLB import/export feasibility per installed versions, axis/unit, material channel mapping, object naming and exchange-file protocol. Prefer interoperability over taking ownership of upstream assets or GUI.
3. **Asset Graph:** store project-owned exchange manifest, external source reference, texture/material metadata, original and returned file hashes, transform/scale, author/approval, format versions and repeatable export provenance.
4. **Character Studio / World Generator / VFX:** optional outputs from retopo, voxel and procedural-lattice workflows; no premature runtime bindings or mandatory feature promises.
5. **3D printing:** record voxel-lattice workflow as a reference; require explicit manifold, wall-thickness, units and output verification by the responsible print pipeline, not vendor marketing assumptions.

Avoid duplicating existing FA3/OpenUSD/OpenSubdiv/Khronos or Bforartists capabilities solely because a competing app offers them. Query Reuse Discovery and the existing donor relationships at implementation time.

## Proposed narrow architecture

```text
FA3 Creative Studio / 3D Fabric
  -> explicit user-approved Export Job and Asset Graph manifest
  -> scoped, versioned exchange directory (no global implicit watcher)
  -> optional installed 3DCoat, using documented export/import and
     separately admitted Python API helpers only when necessary
  -> explicit reviewed Return Job
  -> verify file hashes, mesh hierarchy, object IDs, transforms/units,
     UV sets, normal maps, PBR channels, color-space intent and provenance
  -> Bforartists / 3D Fabric / Asset Graph; retain original native projects
```

**Native preservation:** preserve 3DCoat `.3b` project files as opaque linked assets; do not replace Bforartists/Blender native project or FA3-native project records with interchange snapshots. Exchange files are derived artifacts. No format support is assumed until verified in the installed upstream version. Preserve original and returned copies for reversibility. A recognized external change must not silently overwrite an internal scene.

**Two Applink references:** inspect exchange-folder protocol, object and material identifiers, model and texture refresh, app discovery, version checks, unit/axis conversions and error handling. Implement a minimal FA3-owned compatibility surface only if needed. GPL code requires a separately approved licensing/distribution boundary. Do not copy LKS source without license clarification.

**LKS workflow-pattern candidate:** use radial menu schema migration, explicitly scoped selected/subtree/all operations, deduplication of shared mesh instances, dry-run estimates, transaction/undo and backup-before-hotkey-write as design input. Treat upstream-described crash workarounds and WIP autopo-to-multires as unverified examples, not current-host fixes or approved features.

## Mandatory Hardware Audit

- Donor registration and planned connector are **metadata/planning only**: CPU-only viable, vendor-neutral, zero-to-many accelerators; no mandatory CUDA, ROCm, Vulkan, GPU count, GPU ordinal or installed commercial product in FA3's global baseline.
- 3DCoat advertises Linux Ubuntu 20.04+; this does **not** establish working Ubuntu 26.04, KDE/GNOME/other desktops, Wayland or X11 compatibility. Require separate installation and GUI evidence for the specific build, compositor and driver. Wayland is preferred, X11 is supported by the FA3 interface contract, and vendor-specific hacks cannot become defaults.
- Vendor GPU-based texture nodes remain optional external-application features, not an FA3-wide acceleration prerequisite. HRB remains the sole FA3 resource and lease authority. Display GPU stays dedicated by default; optional FA3-controlled AI work on it follows the existing explicit approved display-GPU rules, and the other GPU/NPU is **never** enlisted by automatic fallback.
- The Model Router remains the only AI model-routing authority if AI features are later proposed. This donor capture creates no model, provider, auto-selection, parallel accelerator enlistment or admission.
- No unsafe clock/voltage/power/thermal configuration, global dependency or AdGuardHome port change is part of this proposal.

## Independent implementation gates

| Gate | Demonstration required | Stop condition |
| --- | --- | --- |
| License / provenance | Separate declared license review for each repository, selected exact commits, dependencies, snippets and distribution model | Unknown, incompatible or commercially prohibited source use |
| Security | Approved user path, symlink/path-traversal protection, bounded scoped exchange storage, no implicit deletion, secure temporary files, optional application consent | Path escape, unsafe file overwrite, executable injection, unapproved external process |
| Application | Optional external app discovery, explicit opt-in, no mandatory 3DCoat installation, Bforartists remains default | 3DCoat becomes a required FA3 dependency |
| Geometry | Test round-trip on a multi-object mesh with UVs, normals, material IDs, named components and non-default axis/scale | Lost object identity, scale mismatch or destructive topology changes not explicitly approved |
| Texture | Test at least albedo, roughness, metallic, normal maps, transparency/color-space and 4k textures; log any unsupported channel | Silent map loss or wrong interpretation |
| Desktop / hardware | Real Linux test on Wayland and X11 where supported, with documented device/backend discovery and CPU-only-safe FA3 operation | Unverified build treated as supported or GPU required by global gate |
| FA3 governance | Existing Reuse Discovery, HRB, native-project rules and current-host evidence receipt for each promoted integration path | Captured donor mistaken for accepted dependency or PASS |

**Implementation sequence:** (1) keep these four registry entries discoverable; (2) check current FA3 DCC/Asset Graph/Creative Studio interfaces and existing donors; (3) write a versioned interchange contract and permission model; (4) build a small opt-in connector without upstream copying; (5) test protocol against both Applink references and a legitimately installed 3DCoat on a suitable current host; (6) independently review source licensing if an upstream addon is actually reused; (7) admit only proven compatibility paths and record all failures and limitations.

### External-source review boundary

The official 3DCoat product is proprietary, notwithstanding its bundled third-party open-source components. Open libraries listed in a vendor EULA do not give permission to redistribute the vendor application. LKS's README permission is not a substitute for checking exact legal rights and included third-party assets. Registry `CANDIDATE` status grants neither code-copy nor runtime authority.
