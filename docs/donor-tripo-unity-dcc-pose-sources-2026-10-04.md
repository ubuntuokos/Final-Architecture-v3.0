# FA3 donor intake — Tripo, Unity, ZBrush, Cinema 4D and pose sources — 2026-10-04

## Scope

Owner instruction: **elemezd és donornak**.

- staged branch: `fa3/donor-tripo-unity-dcc-pose-20261004`
- base published main: `b5052f6595a3fdad84ed7a06e6276f8af5a8dcd8`
- parent donor registry: **1427**
- staged donor registry: **1463**
- submitted URLs: **48**
- unique submitted URLs: **46**
- canonical source identities: **36**
- exact duplicate submissions: **2**
- capability baseline: **175**
- capability delta: **0**
- authority delta: **0**
- usage edges: **0**

## Admission rules

All submitted URLs were explicitly owner-marked for donor intake. GitHub topic language/sort/filter variants are collapsed to one canonical topic identity while every unique submitted view is retained in `source.discovery_urls`. Account and topic pages are discovery indexes only and do not recursively admit child repositories.

All 36 new records are `ACCEPTED_REFERENCE` and are discoverable for later planning. This intake grants no execution authority and creates no code import, dependency install, runtime/provider/model/dataset admission, usage edge or Current Host PASS.

## Analysis

### Tripo / generated 3D

`VAST-AI-Research/tripo-3d-for-blender` is a strong Blender interoperability reference for text/image/multiview 3D generation, task progress, task management and generated-asset import. Its cloud API-key model must remain behind FA3 provider/security boundaries.

`m4rio/TRELLIS-Tripo-3D` is useful for Gaussian/radiance-field/mesh generation and GLB post-processing patterns. Observed usage is GPU/CUDA-centric, so runtime use remains blocked pending Hardware Safety, CPU-baseline and model-rights review.

`tianyilt/FastAPI-TRIPOSR` is useful for persistent model loading, request handling, result caching and GLB/OBJ service handoff. No root LICENSE was observed during intake, so source copying is blocked.

### Unity

The Unity topic family is registered as discovery metadata for editor extensions, runtime 3D/game workflows, URP, ShaderLab, examples and framework patterns. It does not admit Unity itself, proprietary SDKs/editor components, or any child repository.

### ZBrush / Maxon

`Maxon-Computer/ZBrush-Python-API-Examples` is an official API reference. The observed repository license is **CC BY-ND 4.0**, therefore derivative adaptation/source copying remains blocked unless a separate rights determination permits it.

`PacktPublishing/ZBrush-Cookbook` is a useful production-workflow/tutorial reference for sculpting, retopology, UV and lookdev handoff. The repository declares MIT, but book text/media and third-party assets may carry separate rights.

The Maxon organization URL is retained as an organization discovery index; each child repository remains separately licensed and separately admissible.

### Cinema 4D

Cinema 4D/C4D topic sources provide plugin, scripting, C++/JavaScript and resource discovery. They are metadata indexes only; host/runtime licensing and concrete repositories require independent review.

### Pose disambiguation

`pnm4sfix/PoseR` is a BSD-3-Clause napari/deep-learning toolbox for decoding **animal behaviour**. It is not the Poser DCC application; its FA3 relevance is pose/behavior analysis.

`sevdeawesome/POSER` studies detection of **alignment-faking/deceptive LLM behavior**. It is not a 3D Poser project; its possible FA3 relevance is model-assurance research. No root LICENSE was observed during intake, so source copying is blocked.

The submitted `flack` account URL is retained as an owner-marked discovery reference without inferring or admitting a specific child repository.

## Serialization state

At staging time the live donor-intake window already contained five active canonical intake PRs. Current policy permits at most five. Therefore this batch is staged but **no sixth intake PR is opened**.

Before PR creation/finalization, the branch must be reconciled against the then-current published `main` and exact donor-registry state; stale evidence must fail closed.


## CUDA portability follow-up

The canonical `FA3-CUDA-PORTABILITY-SHARED-FUNCTION-POLICY-001` is now applied to this intake.

- `VAST-AI-Research/tripo-3d-for-blender`: **not a local CUDA core**. It is a Blender client for a remote Tripo API. If later adopted, provider access belongs behind a shared provider adapter; it does not justify application-local provider authority.
- `m4rio/TRELLIS-Tripo-3D`: **STRONGLY_CUDA_ORIENTED**. NVIDIA/CUDA is the upstream full path. The reviewed setup contains partial HIP/ROCm support for PyTorch/xFormers and an MI300/gfx942 FlashAttention path, but Kaolin, nvdiffrast, diffoctreerast, mip-splatting rasterization, vox2seq and spconv remain CUDA-only in that setup. Therefore AMD and Intel **must not be shown as full TRELLIS support**. End-to-end status is currently `UNAVAILABLE` until equivalent shared backend components pass feature/numerical/runtime evidence.
- `tianyilt/FastAPI-TRIPOSR`: **CUDA_FIRST_WITH_EXPLICIT_CPU_FALLBACK**. NVIDIA/CUDA remains the accelerated upstream path. AMD and Intel hosts are currently `FUNCTIONALLY_REDUCED`: the function can remain available through the documented CPU path, but native target-GPU acceleration is not proven and must be disclosed as such. CPU is functionally available with a material performance warning where applicable.
- `pnm4sfix/PoseR`: CUDA is optional; upstream separately documents CPU-only PyTorch installation, so it is not classified as strongly CUDA-oriented.

All strongly CUDA-oriented 3D generation paths are bound to the existing shared `FA3-GENERATIVE-MEDIA-MESH-001` / `FA3-GENERATIVE-MEDIA-MESH-CONTRACTS-001`. Blender, Unity, ZBrush, Cinema 4D and other applications may consume UI/workflow adapters only; they may not carry duplicated CUDA/AMD/Intel functional cores.

The previously researched five-depth cross-vendor technical donor set is currently represented by PR #699 and is **not consumed here while pending/unmerged**. This intake records only technology-path classes (ROCm/HIP, XPU/OpenVINO, portable/translation kernels, CPU stage decomposition and explicit remote NVIDIA) until the relevant references are canonical on `main`.
