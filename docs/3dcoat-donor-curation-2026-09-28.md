# 3DCoat AppLink and LKS 3DCTools: selective FA3 donor capture — 2026-09-28

**Status:** Two independent `CANDIDATE` records in `FA3-DONOR-REFERENCE-REGISTRY-001`. This is metadata-only source discovery; it is not installation, license approval, application admission, architecture authority, or evidence of runtime compatibility.

## Upstream verification

| Source | Observed default-branch commit | Directly observed | Restriction |
| --- | --- | --- | --- |
| [AndrewShpagin/io-coat3d](https://github.com/AndrewShpagin/io-coat3d) | [`15b51ab8d1bf`](https://github.com/AndrewShpagin/io-coat3d/commit/15b51ab8d1bfe9937fb6ecf967581c9a239b12b3), 2024-11-25 | The upstream README identifies it as the 3DCoat-shipped Blender 4.2/4.3 AppLink; `__init__.py` specifies Blender 4.2 and a GPL-2.0-or-later header. `folders.py` handles exchange-folder discovery on Linux and other systems; `data.json` maps PBR texture channels. | No assumption that current Blender, Bforartists or installed 3DCoat versions work unchanged. GPL header verified in one source file, not a complete repository-wide legal review. |
| [LiamSmyth/LKS_3DCTools](https://github.com/LiamSmyth/LKS_3DCTools) | [`8b69798f9ead`](https://github.com/LiamSmyth/LKS_3DCTools/commit/8b69798f9ead57068aa8e53e7d05f45a947439c1), 2026-07-28 | README documents hierarchical radial menus, scene-wide batch tools, target density/polycount operations, symmetrize, split-masked workflows, and hotkey conflicts. `LKS.py` uses 3DCoat `cPy.cCore` / `coat`, PySide6, and an automatic `ftfy` installation attempt. | README contains informal permission wording, but a standard repository LICENSE/SPDX declaration was not observed. Treat source copy and redistribution as blocked until license review. Hotkey editor explicitly warns to back up original shortcuts. AutoPo-to-multires is WIP. |

## Selective FA3 reuse targets

1. **3D Fabric / Bforartists / Blender MCP:** Study the first project's file-based transfer handshake, exchange-folder/event detection, PBR map metadata and explicit reimport flow. Implement an FA3-owned, versioned, safely isolated adapter; do not make the proprietary 3DCoat application or the addon mandatory.
2. **Asset Graph / Creative Studio:** Preserve provenance, material/channel identities, native project files and explicit user approval when receiving exchanged assets. Existing OpenUSD, OpenSubdiv and Khronos pathways must be consulted through Reuse Discovery before any new code.
3. **3D Fabric / Character Studio:** Study LKS's hierarchical radial menus, target-density previews, instance-aware bulk operations, masked sculpt actions, and context-sensitive shortcut conflict management. Treat 3DCoat-specific `coat` / `cPy` code as nonportable reference, not an FA3 runtime dependency.
4. **LOD / geometry processing:** Candidate patterns include target-polycount and world-space density controls, per-subtree scope, shared-instance deduplication and preview-before-apply. Any eventual FA3 implementation must use existing approved mesh/LOD providers rather than import a vendor-specific cModule blindly.

These are feature-level references for existing or planned FA3 applications, not proposals to create two additional standalone applications. Only approved human-reviewed operations may mutate a working scene. Preserve Bforartists/Blender and any other connected application's native project format.

## Hardware Audit and safety boundary

- **Compliance for candidate registration:** metadata only; no workload, installer, device probe, hardware change, model-route change, secret access or host evidence is claimed.
- FA3 baseline remains vendor-neutral and **CPU-only viable**, with independently discovered optional accelerators `0..N`. No CUDA, GPU vendor, PCI slot or workstation topology is implied.
- HRB remains exclusive authority for placement, reservations and leases; Model Router remains the sole model-routing authority. Prefer Wayland, retain X11 and avoid a KDE-only coupling.
- Do not install or execute either upstream repository as part of candidate capture. No automatic 3DCoat installation, background texture watcher, `pipInstall`, permission changes or generated file overwrite.
- Before any source use: per-file license/third-party provenance review, secure import and path traversal review, version compatibility, DCC coexistence, reversible project/shortcut backup, regression tests and current-host evidence. Unknown license means no source copy.

## Registry linkage

| Normalized source key | Registry ID |
| --- | --- |
| `github:andrewshpagin/io-coat3d` | `FA3-DONOR-ANDREWSHPAGIN-IO-COAT3D-001` |
| `github:liamsmyth/lks_3dctools` | `FA3-DONOR-LIAMSMYTH-LKS-3DCTOOLS-001` |

FA3 application planning queries these records through the central Reuse Discovery and application/donor inventory. A `CANDIDATE` never authorizes code import or runtime use.
