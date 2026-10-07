# Linux Maya ecosystem: scoped FA3 GitHub donor candidates (2026-09-28)

This curation registers **eight independently checked public upstream repositories** in the existing `FA3-DONOR-REFERENCE-REGISTRY-001` (do not create a parallel donor authority). Autodesk Maya itself is proprietary and is **not** proposed as an open-source donor or an FA3 prerequisite. Some open-source Maya plugins require the proprietary Maya runtime or devkit when built or run.

| Public upstream | Selective FA3 use | Upstream license declaration | Boundary |
|---|---|---|---|
| [Autodesk/maya-usd](https://github.com/Autodesk/maya-usd) | openusd-scene-interchange, usd-layer-editor, dcc-usd-translation, usd-edit-routing | Apache-2.0 | CANDIDATE; separate review |
| [Autodesk/maya-hydra](https://github.com/Autodesk/maya-hydra) | hydra-scene-index, viewport-render-delegate, usd-interactive-viewport | Apache-2.0 | CANDIDATE; separate review |
| [Autodesk/bifrost-usd](https://github.com/Autodesk/bifrost-usd) | procedural-usd-node-graph, usd-variant-authoring, usd-stage-procedural-editing | Apache-2.0 | CANDIDATE; separate review |
| [mgear-dev/mgear](https://github.com/mgear-dev/mgear) | modular-rigging, character-constraint-solvers, rig-graph-organization | MIT | CANDIDATE; separate review |
| [morganloomis/ml_tools](https://github.com/morganloomis/ml_tools) | animator-workflow-tools, pose-animation-utilities, non-destructive-animation-workflows | MIT | CANDIDATE; separate review |
| [Autodesk/arnold-usd](https://github.com/Autodesk/arnold-usd) | hydra-render-delegate, usd-render-schema, render-procedural-interchange | Apache-2.0 | CANDIDATE; separate review |
| [PixarAnimationStudios/OpenUSD](https://github.com/PixarAnimationStudios/OpenUSD) | cross-dcc-scene-description, layered-scene-composition, asset-referencing, usd-animation-interchange | TOST-1.0 | CANDIDATE; separate review |
| [AcademySoftwareFoundation/OpenColorIO](https://github.com/AcademySoftwareFoundation/OpenColorIO) | scene-linear-color-workflows, ocio-config-interchange, cross-dcc-color-management | BSD-3-Clause | CANDIDATE; separate review |

## Cross-application mapping

- **3D Fabric / Bforartists / Blender / Asset Graph:** OpenUSD schema, layer composition, cross-DCC interchange, Maya USD translation architecture. Keep Bforartists primary; do not install or require Maya.
- **Animation / Character Motion / Performance:** modular rigging, animation utilities, skeletal/constraint abstractions inspired by mGear and ml_tools. Preserve FA3 native projects and an editable Scene/Shot/Camera/Rig/Pose/Clip/Constraint/Automation/Graph/Render/Asset Graph.
- **VFX/Gaffer / World Generator:** Bifrost USD procedural graph and variant authoring; Hydra SceneIndex and optional render-delegate interoperability.
- **Video Editor / Krita / virtual production:** OpenColorIO scene-linear configuration and OpenUSD scene/camera/asset exchange. Keep the FA3 Video Editor's own project and timeline authority.
- **Arnold USD:** reference its Hydra render-delegate integration only; the commercial Arnold renderer is not bundled, installed, admitted or assumed available.

## Linux / compatibility / licensing

- These are upstream repository references, **not** a guarantee that any upstream binary works on the FA3 Kubuntu host. mGear documents Linux CMake builds, ml_tools Linux environment setup, Maya USD publishes Linux artifacts, and Arnold USD documents Linux dynamic library paths. Maya/Bifrost/OpenUSD/Arnold ABI and version matching remain a separate compatibility gate.
- License identifiers above are *declared upstream observations*, not completed legal review. OpenUSD's source `LICENSE.txt` states Tomorrow Open Source Technology License 1.0, **not** ordinary Apache-2.0. Autodesk plugin license files are in `doc/LICENSE.md` (Maya USD/Hydra) or `LICENSE.md` (Bifrost USD/Arnold USD); mGear and ml_tools provide MIT license files. OpenColorIO's `LICENSE` is BSD-3-Clause style.
- All eight remain `CANDIDATE` with `SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW`. No code import, proprietary SDK/renderer installation, provider/model admission or runtime activation is implied.
- Maya developer documentation (not a GitHub donor): https://help.autodesk.com/view/MAYADEV/2026/ENU/ . Use for Python/C++ API compatibility only.

## Hardware Audit — mandatory

Metadata-only capture, CPU-only viable, vendor-/accelerator-neutral, with accelerator cardinality `0..N`. No fixed GPU vendor, CUDA, ROCm, display session or Maya/Arnold/Bifrost runtime dependency. The existing Host Resource Broker remains sole resource authority. Model Router remains sole model authority. KDE/GNOME/XFCE are not assumptions; future GUI work prefers Wayland and also supports X11. No current-host runtime execution or production admission is claimed.

## Conflict/reconciliation

Other 2026-09-28 donor PRs (AMD/ROCm, Houdini, Intel/oneAPI and other concurrent donor additions) may change the same canonical JSON on parallel branches. Before merge, reconcile by `source.normalized_key` without dropping either branch's candidates, refresh `backfill.entry_count`, and regenerate the repository's required release projection for the exact resulting head. A static registry change does not pass the physical current-host gate.
