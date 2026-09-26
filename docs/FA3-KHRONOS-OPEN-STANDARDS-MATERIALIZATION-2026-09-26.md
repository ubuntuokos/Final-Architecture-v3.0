# FA3 Khronos Open Standards materialization

## Scope

This work materializes the Khronos projects required by existing **CAP-083 – Open Standards Graphics/Compute/XR/3D**. It adds no capability and no architectural authority. Khronos components remain replaceable SDKs, validators, loaders, reference implementations or interchange adapters.

## Hardware Audit

The architecture is vendor-neutral and accelerator-neutral. Accelerator cardinality remains `0..N`; CPU-only FA3 conformance is preserved. HRB remains the only host resource admission/placement/reservation/lease authority. No GPU vendor, SKU, CUDA/ROCm/oneAPI runtime or Vulkan device is globally required.

The mandatory Hardware Safety Envelope remains fail-closed. This integration does not change power, clocks, voltages, thermal limits, fan policy, firmware, PCIe tuning, memory timings or storage safety settings.

## Materialization plans

| Project | Pin | FA3 destination | Materialization |
|---|---|---|---|
| Vulkan-Headers | e3b1eec0 | graphics/compute interface | namespaced source + build interface |
| Vulkan-Loader | 5f157b62 | render/compute runtime | namespaced source + build |
| Vulkan-ValidationLayers | f4874eee | validation/evidence | namespaced source + build; runtime PASS still needs physical execution |
| Vulkan-Profiles | 1f139a2e | HRB capability discovery | profile-driven discovery, no SKU inference |
| SPIRV-Tools | b707790a | Shader Fabric | validate/optimize SPIR-V |
| glslang | e1b562a8 | Shader Fabric | GLSL/HLSL to SPIR-V |
| SPIRV-Cross | aa217aeb | Shader Fabric | cross translation/reflection |
| KTX-Software | 4d6fc70e | Asset Graph | KTX2 texture pipeline |
| glTF-Validator | 434283be | Asset Graph | glTF validation; native project files remain canonical for their applications |
| OpenXR-SDK | f2448a87 | XR provider | replaceable OpenXR adapter |
| OpenCL-Headers | 6fe718c3 | Compute provider | interface only |
| OpenCL-ICD-Loader | b7bd2803 | Compute provider | loader; device choice remains HRB governed |
| ANARI-SDK | 7534bd26 | Render Fabric | renderer-provider abstraction |
| OpenVX-sample-impl | 031f44bd | Vision Fabric | reference graph semantics/provider implementation |
| NNEF-Tools | 765d27d9 | Model Artifact Fabric | optional import/export interchange |

## Deliberate non-imports

Vulkan Samples/Tutorial, glTF sample assets/tutorials, OpenXR CTS, SYCL documentation/CTS and OpenCL Guide remain reference/test material rather than production SDK dependencies. SYCL is retained as an optional backend family in FA3 hardware discovery; Khronos does not provide a production SYCL runtime SDK that should become a canonical FA3 dependency.

## Integration boundaries

- **HRB:** Vulkan Profiles and OpenCL loader observations may describe capabilities; neither admits or leases resources.
- **Shader Fabric:** glslang -> SPIR-V -> SPIRV-Tools -> SPIRV-Cross. Validation is fail-closed.
- **Asset Graph:** glTF and KTX2 are interchange boundaries, not replacements for `.kra`, `.kdenlive`, Ardour sessions or FA3 native project formats.
- **Render Fabric:** ANARI is a provider abstraction/reference; FA3 retains policy and scheduling ownership.
- **Vision Fabric:** OpenVX graph/operator semantics can back provider-neutral vision graphs.
- **XR:** OpenXR is the vendor-neutral device/runtime boundary.
- **Model Artifact Fabric:** NNEF is an optional interchange adapter alongside other admitted model formats.

## Current-host truth boundary

Repository materialization and hosted CI can prove static contract consistency and immutable pins. They do **not** prove that any of these SDKs are installed, loadable or executable on the physical current host. Such promotion requires a separately captured materialization receipt plus real executable evidence.
