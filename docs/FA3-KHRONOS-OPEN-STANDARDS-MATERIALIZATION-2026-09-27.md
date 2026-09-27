# FA3 Khronos Open Standards SDK Fabric

This materialization strengthens existing **CAP-083 – Open Standards Graphics/Compute/XR/3D**. It adds **0 capabilities** and **0 architectural authorities**.

## Adopted SDK set

The immutable set covers Vulkan Headers/Loader/Validation Layers/Profiles, SPIRV-Tools, glslang, SPIRV-Cross, KTX-Software, glTF Validator, OpenXR-SDK, OpenCL Headers/ICD Loader, ANARI-SDK, OpenVX sample implementation and NNEF-Tools.

Stable releases are pinned to release tags and exact commits. Repositories without a suitable stable release are pinned to an exact commit. Floating upstream branches are never used at production materialization time.

## Fabric placement

- **HRB:** Vulkan Profiles and OpenCL observations are read-only capability inputs. HRB retains admission, placement, reservation and lease authority.
- **Shader Fabric:** glslang -> SPIR-V -> SPIRV-Tools -> SPIRV-Cross.
- **Asset Graph:** glTF validation and KTX2 texture interchange. Native FA3/integrated application project formats remain preserved.
- **Render Fabric:** ANARI is a replaceable provider abstraction; Vulkan Loader/Validation Layers remain scoped execution/validation components.
- **XR:** OpenXR is the vendor-neutral runtime boundary.
- **Compute:** OpenCL is an optional heterogeneous backend; no silent device fallback.
- **Vision:** OpenVX contributes graph/operator provider semantics.
- **Model Artifact Fabric:** NNEF is an optional import/export interchange adapter.

## Hardware Audit

Vendor-neutral, accelerator-neutral, dynamic accelerator cardinality **0..N**, CPU-only conformance retained. Physical and logical CPU counts remain distinct. No NVIDIA/AMD/Intel SKU, CUDA, ROCm, oneAPI or Vulkan device becomes a global requirement.

The mandatory Hardware Safety Envelope remains intact. This materialization does not alter clocks, voltage, power limits, thermals, firmware, fan controls, kernel boot parameters or device safety protections.

## Software Coexistence / CAP-175

SDK sources live under `$XDG_DATA_HOME/fa3/khronos-sdk`; build state lives under `$XDG_CACHE_HOME/fa3/khronos-sdk`. FA3 does not uninstall or replace system Vulkan/OpenCL/OpenXR components, does not hijack loader/ICD configuration, and does not set global loader environment variables. Any runtime environment projection must be child-process scoped.

## Distribution

Third-party source is **not vendored into the FA3 release bundle** by this change. Materialization fetches immutable upstream commits into the user's FA3 namespace. GitHub API license metadata marked `NOASSERTION` or undeclared is treated as insufficient for redistribution; bundle inclusion would require a separate Distribution Compliance admission.

## Evidence boundary

Hosted CI proves canonical structure, pins and integration contracts only. The physical `fa3-current-host` job may prove source materialization of all 15 repositories. Neither result is a compiled/runtime CAP-083 PASS. Runtime promotion remains fail-closed until separate physical execution evidence satisfies the CAP-083 proof obligations.
