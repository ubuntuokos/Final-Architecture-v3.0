# Curated Intel GitHub donor sources for FA3 — 2026-09-28

This bounded, non-authoritative curation captures **54 verified project repositories** and **5 standing ecosystem organization indexes** in the existing `FA3-DONOR-REFERENCE-REGISTRY-001`. GitHub upstream repository existence/archive status was checked on 2026-09-28. It does not audit source licenses, security, build reproducibility, current-host compatibility, provider suitability or upstream release quality.

## Planning integration

Every reference is searchable via the existing donor registry / Reuse Discovery federation, including planned future applications. A group page is a **discovery index**, not automatic permission to enroll all repositories in that organization. Project-specific `target_hints` below are selective potential FA3 beneficiaries, not automatic implementation decisions.

| Ecosystem index | Role |
|---|---|
| [intel](https://github.com/intel) | Intel CPU/GPU/NPU, security, media and observability |
| [oneapi-src](https://github.com/oneapi-src) | oneAPI toolchain, math, scheduling and hardware API references |
| [openvinotoolkit](https://github.com/openvinotoolkit) | OpenVINO serving, generative AI and model workflow references |
| [HabanaAI](https://github.com/HabanaAI) | Intel Gaudi/Habana HPU optional backends |
| [opea-project](https://github.com/opea-project) | Intel-participating OPEA modular AI reference patterns |

## Scoped projects and intended FA3 targets

### Intel CPU/GPU/NPU, security, media and observability

| Upstream repository | FA3 targets | State |
|---|---|---|
| [intel/AI-Playground](https://github.com/intel/AI-Playground) | FA3 GUI, Model Manager, Generative Media Studio | Candidate reference |
| [intel/auto-round](https://github.com/intel/auto-round) | Model Manager | Candidate reference |
| [intel/compute-runtime](https://github.com/intel/compute-runtime) | Hardware Audit, Compute Fabric | Candidate reference |
| [intel/confidential-computing.sgx](https://github.com/intel/confidential-computing.sgx) | Security Governance, Secret Broker | Candidate reference |
| [intel/gmmlib](https://github.com/intel/gmmlib) | Compute Fabric, Hardware Audit | Candidate reference |
| [intel/intel-cmt-cat](https://github.com/intel/intel-cmt-cat) | Hardware Audit, Observability | Candidate reference |
| [intel/intel-device-plugins-for-kubernetes](https://github.com/intel/intel-device-plugins-for-kubernetes) | Deployment Fabric, Hardware Audit | Candidate reference |
| [intel/intel-extension-for-pytorch](https://github.com/intel/intel-extension-for-pytorch) | Model Manager, Inference Fabric | ARCHIVED, historical reference only |
| [intel/intel-extension-for-tensorflow](https://github.com/intel/intel-extension-for-tensorflow) | Inference Fabric | Candidate reference |
| [intel/intel-extension-for-transformers](https://github.com/intel/intel-extension-for-transformers) | Model Manager, Inference Fabric | ARCHIVED, historical reference only |
| [intel/intel-graphics-compiler](https://github.com/intel/intel-graphics-compiler) | Compute Fabric, Hardware Audit | Candidate reference |
| [intel/intel-npu-acceleration-library](https://github.com/intel/intel-npu-acceleration-library) | Hardware Audit, Inference Fabric | ARCHIVED, historical reference only |
| [intel/intel-resource-drivers-for-kubernetes](https://github.com/intel/intel-resource-drivers-for-kubernetes) | Deployment Fabric, Hardware Audit | Candidate reference |
| [intel/intel-xpu-backend-for-triton](https://github.com/intel/intel-xpu-backend-for-triton) | Inference Fabric, Compute Fabric | Candidate reference |
| [intel/ipex-llm](https://github.com/intel/ipex-llm) | Model Manager, Inference Fabric | ARCHIVED, historical reference only |
| [intel/ittapi](https://github.com/intel/ittapi) | Observability, Performance Fabric | Candidate reference |
| [intel/libvpl](https://github.com/intel/libvpl) | FA3 Video Editor, Media Fabric | Candidate reference |
| [intel/linux-npu-driver](https://github.com/intel/linux-npu-driver) | Hardware Audit, Inference Fabric | Candidate reference |
| [intel/linux-sgx](https://github.com/intel/linux-sgx) | Security Governance, Secret Broker | Candidate reference |
| [intel/llm-scaler](https://github.com/intel/llm-scaler) | Inference Fabric, Model Manager | Candidate reference |
| [intel/llvm](https://github.com/intel/llvm) | Compute Fabric, Build Fabric | Candidate reference |
| [intel/media-driver](https://github.com/intel/media-driver) | FA3 Video Editor, Media Fabric | Candidate reference |
| [intel/metrics-discovery](https://github.com/intel/metrics-discovery) | Hardware Audit, Observability | Candidate reference |
| [intel/metrics-library](https://github.com/intel/metrics-library) | Hardware Audit, Observability | Candidate reference |
| [intel/neural-compressor](https://github.com/intel/neural-compressor) | Model Manager | Candidate reference |
| [intel/pcm](https://github.com/intel/pcm) | Hardware Audit, Observability | Candidate reference |
| [intel/pepc](https://github.com/intel/pepc) | Hardware Audit, Observability | Candidate reference |
| [intel/pti-gpu](https://github.com/intel/pti-gpu) | Hardware Audit, Observability | Candidate reference |
| [intel/scikit-learn-intelex](https://github.com/intel/scikit-learn-intelex) | Data Fabric, Model Manager | Candidate reference |
| [intel/SGXDataCenterAttestationPrimitives](https://github.com/intel/SGXDataCenterAttestationPrimitives) | Security Governance, Secret Broker | Candidate reference |
| [intel/torch-xpu-ops](https://github.com/intel/torch-xpu-ops) | Inference Fabric, Hardware Audit | Candidate reference |
| [intel/xpumanager](https://github.com/intel/xpumanager) | Hardware Audit, Observability | Candidate reference |

### oneAPI toolchain, math, scheduling and hardware API references

| Upstream repository | FA3 targets | State |
|---|---|---|
| [oneapi-src/oneapi-ci](https://github.com/oneapi-src/oneapi-ci) | Build Fabric, Compute Fabric | Candidate reference |
| [oneapi-src/unified-memory-framework](https://github.com/oneapi-src/unified-memory-framework) | Compute Fabric, Inference Fabric | Candidate reference |
| [oneapi-src/level-zero-spec](https://github.com/oneapi-src/level-zero-spec) | Hardware Audit, Compute Fabric | Candidate reference |
| [oneapi-src/DPCPP_Reference](https://github.com/oneapi-src/DPCPP_Reference) | Build Fabric, Compute Fabric | Candidate reference |
| [oneapi-src/level-zero](https://github.com/oneapi-src/level-zero) | Hardware Audit, Compute Fabric | Candidate reference |
| [oneapi-src/oneAPI-samples](https://github.com/oneapi-src/oneAPI-samples) | Hardware Audit, Build Fabric | Candidate reference |
| [oneapi-src/oneCCL](https://github.com/oneapi-src/oneCCL) | Distributed Training Fabric, Inference Fabric | Candidate reference |
| [oneapi-src/oneDAL](https://github.com/oneapi-src/oneDAL) | Data Fabric, Model Manager | Candidate reference |
| [oneapi-src/oneDNN](https://github.com/oneapi-src/oneDNN) | Inference Fabric, Model Manager | Candidate reference |
| [oneapi-src/oneDPL](https://github.com/oneapi-src/oneDPL) | Compute Fabric, Data Fabric | Candidate reference |
| [oneapi-src/oneMKL](https://github.com/oneapi-src/oneMKL) | Compute Fabric, Data Fabric | Candidate reference |
| [oneapi-src/oneTBB](https://github.com/oneapi-src/oneTBB) | Compute Fabric, Media Fabric | Candidate reference |
| [oneapi-src/SYCLomatic](https://github.com/oneapi-src/SYCLomatic) | Compute Fabric, Build Fabric | Candidate reference |

### OpenVINO serving, generative AI and model workflow references

| Upstream repository | FA3 targets | State |
|---|---|---|
| [openvinotoolkit/model_server](https://github.com/openvinotoolkit/model_server) | Model Router, Inference Fabric | Candidate reference |
| [openvinotoolkit/open_model_zoo](https://github.com/openvinotoolkit/open_model_zoo) | Model Manager, Inference Fabric | Candidate reference |
| [openvinotoolkit/openvino](https://github.com/openvinotoolkit/openvino) | Model Manager, Model Router, Inference Fabric | Candidate reference |
| [openvinotoolkit/openvino_notebooks](https://github.com/openvinotoolkit/openvino_notebooks) | Model Manager, Training Fabric | Candidate reference |
| [openvinotoolkit/openvino.genai](https://github.com/openvinotoolkit/openvino.genai) | Generative Media Studio, Model Router, Model Manager | Candidate reference |

### Intel Gaudi/Habana HPU optional backends

| Upstream repository | FA3 targets | State |
|---|---|---|
| [HabanaAI/gaudi-pytorch-bridge](https://github.com/HabanaAI/gaudi-pytorch-bridge) | Hardware Audit, Inference Fabric | Candidate reference |
| [HabanaAI/Model-References](https://github.com/HabanaAI/Model-References) | Model Manager, Inference Fabric | ARCHIVED, historical reference only |

### Intel-participating OPEA modular AI reference patterns

| Upstream repository | FA3 targets | State |
|---|---|---|
| [opea-project/GenAIComps](https://github.com/opea-project/GenAIComps) | Agent Fabric, Model Router, Retrieval Fabric | Candidate reference |
| [opea-project/GenAIExamples](https://github.com/opea-project/GenAIExamples) | Agent Fabric, Retrieval Fabric | Candidate reference |

## Mandatory Hardware Audit and architecture boundaries

- **Metadata capture only:** CPU-only available by policy; vendor-/accelerator-neutral baseline; 0..N accelerators; no Intel GPU, NPU, Gaudi, oneAPI, SYCL, Level Zero or OpenVINO becomes mandatory.
- Optional Intel-specific driver and codec backends must be admitted **only** through their governed FA3 adapters. HRB remains the single resource inventory/lease authority. No direct application device selection or display-GPU fallback is introduced.
- OpenVINO, OPEA, Intel LLM and Gaudi projects are **references**, not model/provider permissions. The sole model routing authority is the FA3 Model Router, via provider/runtime and LiteLLM data plane as configured; no fixed model or silent fallback is introduced.
- `intel/pepc`, `intel/pcm`, metrics libraries and NPU/GPU tooling may inform *read-only* hardware observation. Never copy configuration advice into unsafe overclock, power-limit, driver, thermal or firmware mutations.
- Intel Kubernetes device-plugin and DRA projects are design references; they do not introduce a Kubernetes requirement. SGX/attestation sources do not replace Security Governance or Secret Broker.
- Video-specific Intel libvpl and media-driver references remain optional under FA3 Video Editor / Media Fabric, alongside CPU-only media paths and the existing MLT/FFmpeg boundary. No replacement of the native FA3 Video Editor is implied.
- Archived Intel Extension for PyTorch, Extension for Transformers, ipex-llm, NPU Acceleration Library and HabanaAI Model-References remain **historical-only**. Intel recommends upstream PyTorch rather than the archived extension; no retired project may be automatically installed or used as an unreviewed runtime dependency.
- **All 59 entries:** `CANDIDATE`, not an architectural authority; no code copy, dependency, automatic fetch, install, activation, provider admission, model selection, or current-host PASS. All licenses are deliberately **UNKNOWN until individually audited**, irrespective of upstream public GitHub display metadata.

## Follow-on admission, separate from donor capture

For any selective implementation: perform per-source license/provenance/security and coexistence review, then full hardware audit with CPU-only evidence where applicable, exact current-host checks, applicable gates and explicit owner approval. NVIDIA PR #447 is reconciled. If concurrent AMD/ROCm #448 or Houdini #449 merges before this PR, reconcile again without losing entries or earlier accepted donor lifecycle state.

**Reconciled baseline:** main includes the NVIDIA donor curation. This branch contributes 59 Intel ecosystem candidates (54 scoped project repositories and 5 ecosystem indexes), preserving all previously admitted donors and adding no capability or authority. No new capability or architectural authority.
