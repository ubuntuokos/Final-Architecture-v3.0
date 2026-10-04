# CFA3 DirectX / Linux interoperability donor intake — 2026-10-04

## Scope

The owner explicitly marked the full submitted DirectX/Linux interoperability source set in the originating conversation as **donornak** and requested a whole-conversation implementation plan with technical donor traversal bounded to five layers.

This branch is **donor/reference intake only**. It does not implement DirectX compatibility, install Wine/DXVK/VKD3D, install Microsoft runtimes, change graphics drivers, create provider/runtime admission, create usage edges, mutate hardware, or claim Current Host PASS.

Verified published parent:

- main: `b5052f6595a3fdad84ed7a06e6276f8af5a8dcd8`
- donor registry blob: `1362d75186c6da74e5cf947fdf0b8867d462636a`
- donor registry entries: **1427**
- capability baseline: **175**

## Exact owner-marked source set and deduplication

Eleven exact URLs were submitted across the conversation.

### Already present in the canonical registry

These are not duplicated. The later intake turn must promote/enrich the existing record in place and preserve the exact submitted URL as provenance where it differs from the canonical locator.

| Submitted source | Existing identity | Planned action |
| --- | --- | --- |
| https://github.com/microsoft/DirectXShaderCompiler | `FA3-DONOR-MICROSOFT-DIRECTXSHADERCOMPILER-001` | enrich/promote in place |
| https://github.com/doitsujin/DXVK | `FA3-DONOR-DOITSUJIN-DXVK-001` | enrich/promote in place |
| https://github.com/microsoft/DirectXTex/wiki/DirectXTex | `FA3-DONOR-MICROSOFT-DIRECTXTEX-001` | wiki URL as provenance alias; no duplicate |
| https://github.com/microsoft/DirectX-Headers | `FA3-DONOR-MICROSOFT-DIRECTX-HEADERS-001` | enrich/promote in place |

### New source identities staged for later canonical intake

| Source | Proposed identity | Disposition |
| --- | --- | --- |
| https://github.com/microsoft/DirectXTK | `FA3-DONOR-MICROSOFT-DIRECTXTK-001` | D3D11 high-level capability/architecture reference; MIT |
| https://github.com/EduApps-CDG/OpenDX | `FA3-DONOR-EDUAPPS-CDG-OPENDX-001` | early native-Linux D3D architecture reference; file-level rights review required |
| https://github.com/microsoft/directxtk12 | `FA3-DONOR-MICROSOFT-DIRECTXTK12-001` | D3D12 resource/pipeline architecture reference; MIT |
| https://devblogs.microsoft.com/directx/directx-heart-linux/ | `FA3-DONOR-MICROSOFT-DIRECTX-LINUX-WSL-ARTICLE-001` | WSL GPU-PV / Linux D3D12 architecture reference only |
| https://github.com/microsoft/directml | `FA3-DONOR-MICROSOFT-DIRECTML-001` | ML operator/graph/dispatch and optional Windows/WSL provider reference; maintenance mode |
| https://github.com/OpenRA | `FA3-DONOR-OPENRA-ORG-001` | organization discovery index only; no child repository is recursively admitted |
| https://github.com/opencomputeproject/OpenNetworkLinux | `FA3-DONOR-OCP-OPENNETWORKLINUX-001` | network-appliance platform abstraction / hardware-management reference; maintenance mode; mixed-license review required |

Parent-relative canonical count after eventual slot admission would be **1434**, subject to rebase-time duplicate reconciliation.

## Architecture use boundary

The donor batch supports one **shared CFA3 DirectX Compatibility & Graphics Interop Fabric**. It must not create application-local DirectX cores and must not duplicate DirectX implementations per GPU vendor.

The planned fabric must integrate with existing CFA3 authorities and shared layers:

- Khronos Open Standards / Shader Fabric;
- Render Fabric;
- Host Resource Broker;
- Hardware Safety;
- Software Coexistence;
- License & Rights Authority;
- Model Router for ML/model/provider routing;
- existing shared cross-vendor compute/CUDA compatibility work.

DirectX, D3D, DXC, Vulkan, CUDA, ROCm, oneAPI and similar technologies are execution/API mechanisms, not CFA3 capabilities by themselves.

## Planning depth boundary

The requested technical donor analysis is bounded to at most five dependency layers. Planning may inspect already canonical donors and bounded associated sources. Any newly discovered, substantively processed source that becomes part of the approved implementation plan must be registered before implementation execution starts.

This intake itself creates **zero usage edges**. Actual adoption requires explicit canonical usage edges after donor publication and the normal License & Rights, Security, Software Coexistence, Hardware Safety and runtime gates.

## Rights notes

- DirectXTK / DirectXTK12: repository root MIT; exact copied files/dependencies still require normal review.
- OpenDX: root repository metadata and observed file-level SPDX information are not uniform; source copying remains blocked pending file-level License & Rights clearance.
- DirectML: repository source is MIT, but the DirectML redistributable/runtime is a separate distribution/admission concern.
- Microsoft WSL DirectX article: documentation/reference only; `libd3d12.so`, `libdxcore.so` and WSL GPU-PV runtime components are not authorized for bundling by this intake.
- OpenRA organization: no organization-wide license inference. Representative child repositories, including GPL-licensed projects, require separate source-level admission before material reuse.
- OpenNetworkLinux: upstream is maintenance-mode/pending archival. The repository has EPL-1.0 as a general default but also Debian-derived and vendor-specific components (including Broadcom terms); exact file/dependency rights review is mandatory before material reuse. It is a platform/network reference, not a CFA3 base OS or DirectX runtime.

## FIFO state

The observed rolling five-slot donor-intake window remains occupied by:

`#651, #657, #663, #664, #671`

Earlier waiting donor intakes include:

`#672, #673, #675, #676, #682, #683, #684, #686, #693, #699, #704`

Therefore this branch is intentionally **FIFO waiting** and does not mutate `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`.

## Invariants

- capability baseline: **175**
- capability delta: **0**
- architectural-authority delta: **0**
- donor usage-edge delta: **0**
- runtime/provider activation: **none**
- hardware mutation: **none**
- automatic dependency/fetch/install: **none**
- Current Host PASS claimed: **false**
- DirectX implementation started: **false**
