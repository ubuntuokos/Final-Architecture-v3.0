# FA3 Khronos Open Standards SDK Fabric

This materialization strengthens existing **CAP-083 – Open Standards Graphics/Compute/XR/3D**. It adds **0 capabilities** and **0 architectural authorities**. Reuse Discovery binds the work to CAP-146/CAP-147, and Software Coexistence & Host Non-Interference is enforced through CAP-175.

## Adopted SDK set

The primary immutable source set contains 15 projects:

- Vulkan-Headers, Vulkan-Loader, Vulkan-ValidationLayers and Vulkan-Profiles;
- SPIRV-Tools, glslang and SPIRV-Cross;
- KTX-Software and glTF-Validator;
- OpenXR-SDK;
- OpenCL-Headers and OpenCL-ICD-Loader;
- ANARI-SDK;
- OpenVX-sample-impl;
- NNEF-Tools.

Stable releases are pinned to release tags and exact commits. Repositories without a suitable stable release are pinned directly to an exact commit. Floating upstream refs are never used at production materialization time.

A separate **build-only immutable dependency set** contains four sources required by the pinned Khronos build graphs:

- SPIRV-Headers;
- Vulkan-Utility-Libraries;
- jsoncpp;
- valijson.

These four sources are build inputs only. They do not become FA3 runtime providers or architectural authorities.

## Fabric placement

- **Host Resource Broker:** Vulkan Profiles and OpenCL observations are read-only capability inputs. HRB retains admission, placement, reservation and lease authority.
- **Shader Fabric:** glslang -> SPIR-V -> SPIRV-Tools -> SPIRV-Cross.
- **Asset Graph:** glTF validation and KTX2 texture interchange. Native FA3 and integrated-application project formats remain preserved.
- **Render Fabric:** ANARI is a replaceable provider abstraction; Vulkan Loader and Validation Layers remain scoped execution/validation components.
- **XR:** OpenXR is the vendor-neutral runtime boundary.
- **Compute:** OpenCL is an optional heterogeneous backend; no silent device fallback is permitted.
- **Vision:** OpenVX-sample-impl is a **sample implementation and design/pattern source only**. Its own upstream documentation explicitly states that it is not intended to be a reference implementation. FA3 therefore does not admit it as a production or reference runtime provider.
- **Model Artifact Fabric:** NNEF is an optional import/export interchange adapter.

## Deterministic materialization and build

Sources are materialized under:

- `$XDG_DATA_HOME/fa3/khronos-sdk/src`

Build state is isolated under:

- `$XDG_CACHE_HOME/fa3/khronos-sdk/build`

The FA3 install prefix is:

- `$XDG_DATA_HOME/fa3/khronos-sdk/prefix`

The materializer has two explicit modes:

- `--source-only`: exact immutable source materialization;
- `--build-core`: deterministic core SDK build from the already pinned source/dependency set.

For the core build, upstream automatic dependency fetching is disabled: `UPDATE_DEPS=OFF`. Missing host build prerequisites fail closed with an actionable dependency error. FA3 does not silently run a distro package manager from this build path and does not replace host packages.

The core build includes the pinned Vulkan/SPIR-V shader stack, KTX, OpenXR, OpenCL and ANARI front-end surfaces. glTF-Validator, OpenVX-sample-impl and NNEF-Tools remain separately admitted specialized toolchains because they have distinct runtime/build dependency surfaces.

## CAP-083 physical proof

The previous generic 3D-application smoke test is no longer sufficient for CAP-083 after the Khronos decision became part of its source-decision coverage.

CAP-083 now uses the dedicated producer:

- `src/fa3_cap083_khronos_current_host.py`

Positive physical evidence requires:

1. all 15 adopted sources and all 4 build-only dependencies at their exact immutable commits;
2. an exact-repository-HEAD core-build receipt;
3. a real Shader Fabric path: glslang compile -> SPIR-V validation -> SPIR-V optimization -> SPIRV-Cross reflection;
4. real KTX CLI execution;
5. namespaced installed Vulkan Loader, Vulkan Validation Layers, OpenXR Loader, OpenCL ICD Loader and ANARI front-end artifacts.

The negative proof verifies host non-interference: no global Vulkan layer/ICD, OpenCL ICD or OpenXR runtime override is injected, and OpenVX remains non-admitted as a runtime provider.

The rollback proof mutates only a scope-local child-runtime projection and requires exact hash restoration.

A physical accelerator, XR headset or OpenCL device is **not** globally required for this baseline proof. CPU-only FA3 remains valid. Any actual accelerator execution remains subject to HRB admission and separate capability-specific evidence.

## Hardware Audit

The materialization is vendor-neutral and accelerator-neutral with accelerator cardinality **0..N**. Physical and logical CPU counts remain distinct. No NVIDIA, AMD or Intel SKU, CUDA, ROCm, oneAPI or Vulkan device becomes a global requirement.

The mandatory Hardware Safety Envelope remains intact. This materialization does not alter clocks, voltages, power limits, thermals, firmware, fan controls, kernel boot parameters or device safety protections.

## Software Coexistence / CAP-175

FA3 does not uninstall or replace system Vulkan, OpenCL or OpenXR components. It does not hijack the system Vulkan loader, layer path, ICD configuration or OpenXR runtime selection.

Any runtime environment projection is child-process scoped. No default port, service, MIME association, global environment, driver, package, or system configuration is claimed by the Khronos fabric.

## Distribution

Third-party source is **not vendored into the FA3 release bundle** by this change. Materialization fetches immutable upstream commits into the user's FA3 namespace.

GitHub API license metadata reported as `NOASSERTION` or undeclared is treated as insufficient for redistribution. Release-bundle inclusion requires a separate Distribution Compliance decision even where upstream source is publicly available.

The primary source reference, materialization record and build-only dependency record are all excluded from the FA3 product bundle.

## Evidence boundary

Hosted CI proves canonical structure, immutable pins, integration contracts, distribution classification and producer registration. It is not current-host runtime evidence.

The dedicated `fa3-current-host` workflow checks out the **exact PR head** and can prove immutable source plus core-build materialization. This still does not itself promote CAP-083.

On the protected main path, the global physical current-host closure builds the Khronos core set in the same exact commit execution before CAP-083 positive/negative/rollback producers run. Only that full qualification chain may contribute to CAP-083 current-host admission.

Current-host and global promotion remain fail-closed.
