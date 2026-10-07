# Pixar OpenUSD — scoped FA3 donor assessment (2026-09-28)

**Registry ID:** `FA3-DONOR-PIXAR-OPENUSD-001`
**Upstream:** https://github.com/PixarAnimationStudios/OpenUSD
**Verified reference:** signed upstream tag `v26.08` resolves to commit `ee47c679abde5b467a7b6a41f3b2285564a4222e` (2026-09-28 check).
**Upstream license declaration:** Tomorrow Open Source Technology License 1.0 (`TOST-1.0`); https://github.com/PixarAnimationStudios/OpenUSD/blob/v26.08/LICENSE.txt . This is a declaration, **not** a completed redistribution or bundled-dependency clearance.

## Scope and FA3 reuse mapping

OpenUSD is a **non-authoritative CANDIDATE** in the *existing* `FA3-DONOR-REFERENCE-REGISTRY-001` and therefore discoverable through `FA3-REUSE-DISCOVERY-001`. No application, architectural authority, capability, provider, SDK installation or runtime is created by this change.

| FA3 consumer (including planned applications) | Candidate reuse | Admission/fidelity boundary |
| --- | --- | --- |
| 3D Fabric, Bforartists, World Generator | USD stage composition; `Sdf` layers, references, payloads and variants; `UsdGeom` | Interchange bridge only. Keep the originating DCC's native project, object relationships and version provenance. |
| Asset Graph and cross-application interchange | `ArResolver` extension and stable asset identifiers | Do not permit arbitrary file, URI or network resolution from untrusted scene data; governed asset resolver required. |
| Character Studio and animation | `UsdSkel`, time samples, scene/shot references | Verify rig, pose, timing, constraints and skeleton export/import fidelity before enabling round trips. OpenUSD is not itself a rigging system. |
| FA3 Video Editor, VFX/Gaffer and Realtime / Virtual Production Interchange | Scene/shot/camera/light/material interchange; `UsdShade`, `UsdLux`, `UsdRender` | Video Editor keeps `project.fa3video` and its own timeline/command bus. Unreal Engine interoperability is eligible only as a separately admitted, explicit, optional workflow only under the now-canonical superseding decision `FA3-DEC-UNREAL-CONDITIONAL-ADMISSION-2026-09-29` (merged PR #523), with separate physical admission; no installation, execution or runtime PASS follows from this donor record. |
| Render Fabric and Khronos-adjacent graphics work | Hydra scene/render delegates, optional `usdview` reference, USDZ export | Rendering delegates are optional and independently admitted; Vulkan/OpenGL/Metal, vendor driver, GPU or renderer is **not** mandated globally. |

Interchange evaluation should cover `usda`, `usdc` and `usdz`, with explicit unit/up-axis/timecode/color/material and external-asset handling. Keep native Krita `.kra` and any participating native DCC project intact. Use project-local tested adapters, not an FA3-global assumption of perfect format fidelity.

## Hardware Audit (mandatory)

**This PR is metadata-only.** Candidate capture and reuse lookup need no accelerator and work on CPU-only machines. Preserve vendor/accelerator neutrality, dynamic `0..N` device inventory and independent backend admission. No specific NVIDIA/AMD/Intel, CUDA/ROCm/oneAPI, GPU ordinal, Vulkan/OpenGL driver, desktop session or GPU memory capacity is a global requirement. `FA3-AUTH-HOST-RESOURCE-BROKER-001` remains the exclusive resource authority; the central Model Router remains the sole model-routing authority. Future GUI adapters must support Wayland and X11 without depending on KDE specifically. This donor registration makes **no** claim of current-host rendering, import/export, runtime, GPU or physical evidence PASS.

## Trust, licensing and engineering gates

1. **Source and license:** TOST differs from Apache-2.0 in its trademarks section; examine `LICENSE.txt`, `NOTICE.txt` and actual linked/redistributed third-party packages, and record legal/provenance review before source copying or redistribution. Upstream SHA is a research snapshot, not a lockfile dependency.
2. **Untrusted assets:** Treat `usda/usdc/usdz`, referenced textures/paths, plugins and procedural loaders as untrusted. Validate archive extraction paths, resource bounds, asset-resolution policies and plugin discovery/loading; default deny network/external filesystem access without explicit capability.
3. **Reuse:** Read metadata first, compare existing Khronos/MaterialX/Asset Graph/creative adapters, and introduce an adapter only where a demonstrated gap remains. Maintain provenance and upstream attribution. No parallel scene authority or replacement of FA3 native project formats.
4. **Runtime:** Separate adapter design, license/security/coexistence review, CPU-only tests, representative asset round-trip tests, graphics/backend tests, fresh current-host Hardware Audit, UAF/HRB admission and evidence registry promotion. Fail closed on missing evidence. Preserve the historical Unreal exclusion decision/evidence without reinstating its blanket ban; the canonical conditional-admission decision merged in PR #523 requires an independent physical current-host, GUI, MCP, production E2E, license, Hardware Audit and Software Coexistence review.

**Disposition:** candidate/reference for immediate planning discovery. No automatic fetch, install, code import, model/provider admission, architectural authority or runtime activation.
