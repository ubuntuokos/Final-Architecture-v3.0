# DirectX and Linux Direct3D donor curation — 2026-09-28

**Status:** 18 source-unique, non-authoritative donor candidates recorded in the existing `FA3-DONOR-REFERENCE-REGISTRY-001` on 2026-09-28. 17 independently resolved GitHub repositories plus the official WineHQ VKD3D Codeberg source. This document is a discovery index, not admission or an implementation plan.

## Scope and architectural fit

- Microsoft DirectX headers, HLSL/DXC compiler, texture/mesh/math facilities, samples and specifications are **selective references**. Official D3D12 Windows code cannot be assumed to execute natively on Linux.
- DXVK (D3D8–11→Vulkan), VKD3D-Proton (D3D12→Vulkan), official WineHQ VKD3D, Wine and Valve Proton form Linux compatibility/research references, not compulsory FA3 runtimes. Proton is a multi-component integration, not a stand-alone graphics API.
- Vulkan Headers/Loader and SPIR-V Headers/Tools are explicit dependency technology candidates, coordinated with existing Khronos Open Standards SDK Fabric. They do not create a second Khronos registry or architectural authority.
- RenderDoc and apitrace are optional graphics debugging, capture/replay and evidence patterns.
- Future applicable FA3 consumers: Render Fabric, 3D Fabric, VFX/Gaffer, Asset Graph, Bforartists (primary DCC), Krita integration, Creative Studio and Realtime / Virtual Production Interchange; narrower target hints are recorded per source. No new application, capability or authority is introduced. Unreal Engine remains excluded.

## Mandatory Hardware Audit

- **Metadata-only change; no current-host execution, Vulkan driver enumeration, shader compilation, Windows compatibility test or graphics benchmark is claimed.**
- Vendor-/accelerator-neutral; CPU-only donor capture and planning remain viable, accelerator cardinality **0..N**. D3D/Vulkan runtime references are optional acceleration paths, not CPU-only Vulkan runtime promises.
- `FA3-AUTH-HOST-RESOURCE-BROKER-001` (HRB) is the only resource authority. No fixed NVIDIA/CUDA, AMD/ROCm, Intel/oneAPI or other GPU binding; an actual adapter must discover available devices and earn task-scoped admission.
- GUI must remain session-neutral: Wayland preferred, X11 supported; no KDE-only assumption. Never replace native FA3 Video Editor, Krita or Bforartists project formats.
- Model Router stays the sole model-routing authority; these references create no model/provider route. No silent fallbacks.

## License / trust boundaries

Declared licenses below are **upstream observations, not legal admission**; compiler and aggregate distributions may include multiple third-party terms. `UNKNOWN` or `MIXED_REVIEW_REQUIRED` never means permission. Per-file/license, provenance, supply-chain/security, dependency, ABI, redistribution, device, coexistence and host-evidence checks block any future source copying, bundling, installing or activating.

DirectX-Headers includes WSL-specific shims expressly scoped by Microsoft to frameworks targeting WSL2 hardware acceleration; these shims are **not general-purpose native Linux DirectX support**. DXVK/VKD3D implement translation on Vulkan, commonly with Wine/Proton. WineHQ's official VKD3D source was confirmed through the May 2026 release announcement; do not substitute Proton's fork for upstream or treat a third-party GitHub mirror as authoritative.

## Official Microsoft DirectX

| Source | Upstream license claim | FA3 targets |
|---|---|---|
| [DirectX Graphics Samples](https://github.com/microsoft/DirectX-Graphics-Samples) | MIT (unreviewed) | Render Fabric, 3D Fabric, Realtime / Virtual Production Interchange, VFX/Gaffer |
| [DirectX Headers](https://github.com/microsoft/DirectX-Headers) | MIT (unreviewed) | 3D Fabric, Render Fabric, Developer Agent |
| [DirectX Shader Compiler](https://github.com/microsoft/DirectXShaderCompiler) | MIXED_REVIEW_REQUIRED (unreviewed) | Render Fabric, VFX/Gaffer, 3D Fabric, Creative Studio |
| [DirectX Specs](https://github.com/microsoft/DirectX-Specs) | UNKNOWN (unreviewed) | Render Fabric, Developer Agent, VFX/Gaffer |
| [DirectXMath](https://github.com/microsoft/DirectXMath) | MIT (unreviewed) | 3D Fabric, Render Fabric, Character Studio |
| [DirectXMesh](https://github.com/microsoft/DirectXMesh) | MIT (unreviewed) | 3D Fabric, Bforartists, Asset Graph, World Generator |
| [DirectXTex](https://github.com/microsoft/DirectXTex) | MIT (unreviewed) | Asset Graph, Krita Integration, 3D Fabric, Render Fabric |

## Linux Direct3D translation / compatibility

| Source | Upstream license claim | FA3 targets |
|---|---|---|
| [DXVK](https://github.com/doitsujin/dxvk) | ZLIB (unreviewed) | Render Fabric, 3D Fabric, Creative Studio, Developer Agent |
| [Valve Proton](https://github.com/ValveSoftware/Proton) | MIXED_REVIEW_REQUIRED (unreviewed) | Creative Studio, Developer Agent, Render Fabric |
| [VKD3D-Proton](https://github.com/HansKristian-Work/vkd3d-proton) | LGPL-2.1 (unreviewed) | Render Fabric, 3D Fabric, Creative Studio, Developer Agent |
| [Wine (GitHub mirror)](https://github.com/wine-mirror/wine) | LGPL-2.1 (unreviewed) | Creative Studio, Developer Agent, Render Fabric |
| [WineHQ VKD3D (official)](https://codeberg.org/vkd3d/vkd3d) | LGPL-2.1 (unreviewed) | Render Fabric, 3D Fabric, Creative Studio, Developer Agent |

## Graphics debugging

| Source | Upstream license claim | FA3 targets |
|---|---|---|
| [apitrace](https://github.com/apitrace/apitrace) | MIT (unreviewed) | Render Fabric, 3D Fabric, Developer Agent |
| [RenderDoc](https://github.com/baldurk/renderdoc) | MIT (unreviewed) | Render Fabric, 3D Fabric, VFX/Gaffer, Developer Agent |

## Vulkan / SPIR-V foundation

| Source | Upstream license claim | FA3 targets |
|---|---|---|
| [SPIRV Headers](https://github.com/KhronosGroup/SPIRV-Headers) | MIT (unreviewed) | Render Fabric, VFX/Gaffer, Developer Agent |
| [SPIRV Tools](https://github.com/KhronosGroup/SPIRV-Tools) | APACHE-2.0 (unreviewed) | Render Fabric, VFX/Gaffer, Developer Agent |
| [Vulkan Headers](https://github.com/KhronosGroup/Vulkan-Headers) | APACHE-2.0 (unreviewed) | Render Fabric, 3D Fabric, Developer Agent |
| [Vulkan Loader](https://github.com/KhronosGroup/Vulkan-Loader) | APACHE-2.0 (unreviewed) | Render Fabric, Developer Agent |

## Operational boundary

`CANDIDATE` means Reuse Discovery may surface the source for current and planned FA3 application designs. These records **do not** approve code import, download, install, driver changes, vendor-specific acceleration, provider/model admission, runtime enablement or release promotion. Reconcile concurrently open donor PRs by normalized source key before merge; update `backfill.entry_count`, regenerate exact-head release projection and rerun the full CI/current-host admission gates where applicable.

## Upstream evidence

- [Official DirectX-Headers scope and WSL caveat](https://github.com/microsoft/DirectX-Headers)
- [DXVK project scope and usage](https://github.com/doitsujin/dxvk)
- [VKD3D-Proton fork](https://github.com/HansKristian-Work/vkd3d-proton)
- [WineHQ VKD3D v2.0 announcement and official Codeberg/GitLab source locations](https://list.winehq.org/hyperkitty/list/wine-announce%40list.winehq.org/message/G5KBXSIU4U3WI6SY3OUPCWIAIQPQO4HA/)
- [Valve Proton aggregate licensing](https://github.com/ValveSoftware/Proton/blob/proton_11.0/dist.LICENSE)
