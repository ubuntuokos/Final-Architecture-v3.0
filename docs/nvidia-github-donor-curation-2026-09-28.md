# NVIDIA GitHub donor curation — 2026-09-28

**Status:** selective, metadata-only, non-authoritative donor discovery. Canonical records live in `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`; this document is a human-readable index, not an admission decision.

**Scope:** 39 individually verified NVIDIA GitHub repositories plus one organization-level discovery index. Metadata was checked against the upstream GitHub repository endpoints on 2026-09-28. The organization index does not imply all repositories have been reviewed.

## Safety and Hardware Audit

- Donor capture does **not** approve code copying, installation, provider admission, model routing, automatic selection, architecture authority, or runtime promotion.
- Mandatory global hardware audit remains vendor-neutral, CPU-only viable, accelerator count `0..N`; no global NVIDIA/CUDA requirement. HRB is the sole runtime resource authority.
- NVIDIA-specific implementations may be considered only as separately admitted, optional backend adapters after license/provenance/security/coexistence checks and current-host evidence.
- An upstream `NOASSERTION` or missing license is **UNKNOWN**, not permission to import code. Declared licenses still require per-project and third-party dependency checks.
- The archived `NVIDIA/VideoProcessingFramework` is a **historical pattern reference only**; do not treat it as a current runtime or implementation recommendation.

## Selected repositories

### inference

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA cudnn-frontend](https://github.com/NVIDIA/cudnn-frontend) | Inference Fabric, Training Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA cutlass](https://github.com/NVIDIA/cutlass) | Inference Fabric, Training Fabric | Unknown / review required | CANDIDATE |
| [NVIDIA Model Optimizer](https://github.com/NVIDIA/Model-Optimizer) | Inference Fabric, Model Manager, Training Fabric | Apache-2.0 | ACCEPTED_REFERENCE |
| [NVIDIA Personal-AI-Router](https://github.com/NVIDIA/Personal-AI-Router) | Inference Fabric, Model Router | Apache-2.0 | CANDIDATE |
| [NVIDIA TensorRT](https://github.com/NVIDIA/TensorRT) | Inference Fabric, Model Manager | Apache-2.0 | CANDIDATE |
| [NVIDIA TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) | Inference Fabric, Model Manager, Model Router | Unknown / review required | CANDIDATE |
| [NVIDIA TransformerEngine](https://github.com/NVIDIA/TransformerEngine) | Model Manager, Training Fabric | Apache-2.0 | CANDIDATE |

### retrieval

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA cuvs](https://github.com/NVIDIA/cuvs) | Embedding Fabric, Knowledge Fabric, PageIndex | Apache-2.0 | CANDIDATE |
| [NVIDIA NeMo-Retriever](https://github.com/NVIDIA/NeMo-Retriever) | Document Fabric, Knowledge Fabric, PageIndex | Apache-2.0 | CANDIDATE |

### agents

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA NeMo-Agent-Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) | Agent Collaboration Room, Agent Runtime, Decision Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA NemoClaw](https://github.com/NVIDIA/NemoClaw) | Agent Runtime, Model Router, Security Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA skills](https://github.com/NVIDIA/skills) | 3D Fabric, Developer Agent, Skill Fabric | Apache-2.0 | CANDIDATE |

### security

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA garak](https://github.com/NVIDIA/garak) | AI Red Flag Detector, Model Manager, Security Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA NVFlare](https://github.com/NVIDIA/NVFlare) | Security Fabric, Training Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell) | Agent Collaboration Room, Agent Runtime, Security Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) | AI Red Flag Detector, MCP Gateway, Skill Fabric | Apache-2.0 | CANDIDATE |

### creative

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA GenerativeAIExamples](https://github.com/NVIDIA/GenerativeAIExamples) | Agent Runtime, Creative Studio, Knowledge Fabric | Apache-2.0 | CANDIDATE |

### creative-3d

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA cosmos](https://github.com/NVIDIA/cosmos) | 3D Fabric, Creative Studio, World Generator | Unknown / review required | CANDIDATE |
| [NVIDIA Isaac-GR00T](https://github.com/NVIDIA/Isaac-GR00T) | 3D Fabric, Character Studio, Choreography Planner | Apache-2.0 | CANDIDATE |
| [NVIDIA physicsnemo](https://github.com/NVIDIA/physicsnemo) | 3D Fabric, World Generator | Apache-2.0 | CANDIDATE |
| [NVIDIA warp](https://github.com/NVIDIA/warp) | 3D Fabric, VFX, World Generator | Apache-2.0 | CANDIDATE |

### creative-video

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA nvImageCodec](https://github.com/NVIDIA/nvImageCodec) | Asset Graph, Krita Integration, Video Editor | Apache-2.0 | CANDIDATE |
| [NVIDIA VideoProcessingFramework](https://github.com/NVIDIA/VideoProcessingFramework) | QuickClip, Video Editor, Video Fabric | Apache-2.0 | Archived; patterns only |

### creative-audio

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA audio-flamingo](https://github.com/NVIDIA/audio-flamingo) | Audio Fabric, Music Studio, Voice/Vocal | Unknown / review required | CANDIDATE |
| [NVIDIA personaplex](https://github.com/NVIDIA/personaplex) | Agent Runtime, Audio Fabric, Voice/Vocal | MIT | CANDIDATE |

### data

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA cudf](https://github.com/NVIDIA/cudf) | Data Fabric, Knowledge Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA cuml](https://github.com/NVIDIA/cuml) | Analytics Fabric, Training Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA DALI](https://github.com/NVIDIA/DALI) | Creative Studio, Training Fabric, Video Editor | Apache-2.0 | CANDIDATE |
| [NVIDIA raft](https://github.com/NVIDIA/raft) | Embedding Fabric, Knowledge Fabric | Apache-2.0 | CANDIDATE |

### training

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA NeMo-Fabric](https://github.com/NVIDIA/NeMo-Fabric) | Model Manager, Training Fabric | Apache-2.0 | CANDIDATE |

### evaluation

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA RULER](https://github.com/NVIDIA/RULER) | AI Red Flag Detector, Model Manager | Apache-2.0 | CANDIDATE |

### tooling

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA cccl](https://github.com/NVIDIA/cccl) | Developer Agent, Inference Fabric | Unknown / review required | CANDIDATE |
| [NVIDIA cuda-python](https://github.com/NVIDIA/cuda-python) | Hardware Audit, Inference Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA cuda-samples](https://github.com/NVIDIA/cuda-samples) | Developer Agent, Hardware Audit | Unknown / review required | CANDIDATE |
| [NVIDIA DeepLearningExamples](https://github.com/NVIDIA/DeepLearningExamples) | Model Manager, Training Fabric | Unknown / review required | CANDIDATE |

### hardware

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA DCGM](https://github.com/NVIDIA/DCGM) | Hardware Audit, Host Resource Broker | Apache-2.0 | CANDIDATE |
| [NVIDIA dcgm-exporter](https://github.com/NVIDIA/dcgm-exporter) | Hardware Audit, Observability Fabric | Apache-2.0 | CANDIDATE |
| [NVIDIA gpu-operator](https://github.com/NVIDIA/gpu-operator) | Deployment Fabric, Hardware Audit | Apache-2.0 | CANDIDATE |
| [NVIDIA nvidia-container-toolkit](https://github.com/NVIDIA/nvidia-container-toolkit) | Deployment Fabric, Hardware Audit | Apache-2.0 | CANDIDATE |

### upstream-discovery-index

| Repository / index | Intended FA3 targets | GitHub license metadata | State |
|---|---|---|---|
| [NVIDIA GitHub organization (discovery index)](https://github.com/NVIDIA) | Donor & Reference Registry, Reuse Discovery | Unknown / review required | CANDIDATE |

## Planning contract

Every new or materially modified FA3 application/capability/module must query the donor registry through Reuse Discovery and consider relevant records. The organization index acts as a discovery trigger for later source-specific assessments; it does not override existing local FA3 solutions, approved providers, Model Router bindings, HRB, or runtime evidence gates.

When evaluating an NVIDIA donor, document the reusable capability/pattern, competing vendor-neutral and CPU-only solutions, exact upstream revision and license, any hardware-specific restrictions, security and coexistence assessment, and explicit admission decision. A candidate remains reference-only until that process completes.
