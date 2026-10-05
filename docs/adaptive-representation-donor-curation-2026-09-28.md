# FA3 Adaptive Representation Fabric — donor curation

Date: 2026-09-28. Scope: metadata-only candidate capture into the existing `FA3-DONOR-REFERENCE-REGISTRY-001`, not a new authority or implementation admission.

## Scope and constraints

- Query the central registry before designing any new or materially modified Creative Studio, 3D Fabric, Character Studio, VFX, BIM, Asset Graph or Virtual Production Interchange module.
- Keep canonical source/master assets immutable. Model display LOD and BIM Level of Development as separate schemas; do not treat BIM stages as runtime draw modes.
- Do not introduce a new resource authority: the existing HRB controls runtime budgets. CPU-only operation and vendor/accelerator-neutral backends are mandatory. A dedicated GPU fast path is optional, never a mandatory dependency.
- Preserve Wayland preference plus X11 support; do not introduce a KDE- or proprietary-engine-only dependency. Unreal Engine must remain excluded.
- No entry below grants permission to copy, install or activate upstream source. Exact revisions, SPDX and transitive licenses, data rights, security review, API coexistence and current-host gate evidence must precede code reuse.

## Candidate donor matrix

| Area | Donor / upstream | Proposed FA3 reuse | Role | Stated license / gate |
|---|---|---|---|---|
| Geometry | [meshoptimizer](https://github.com/zeux/meshoptimizer) | mesh simplification, meshlet generation, geometry optimization | PRIMARY | MIT |
| Geometry | [clusterlod.h](https://github.com/zeux/meshoptimizer/blob/master/demo/clusterlod.h) | continuous hierarchical cluster LOD and screen-space error | PRIMARY | MIT |
| Geometry | [gltfpack](https://github.com/zeux/meshoptimizer/tree/master/gltf) | glTF asset preprocessing and meshopt compression | OPTIONAL | MIT |
| Geometry | [libigl](https://github.com/libigl/libigl) | edge-collapse decimation and geometry-processing algorithms | OPTIONAL | UNKNOWN |
| Geometry | [CGAL Surface Mesh Simplification](https://github.com/CGAL/cgal) | surface mesh simplification algorithm reference; package-specific licensing | LICENSE_CAUTION | PACKAGE SPECIFIC GPL OR COMMERCIAL |
| Interchange | [Assimp](https://github.com/assimp/assimp) | legacy 3D model ingestion and mesh preprocessing | ADAPTER | BSD-3-Clause |
| Interchange | [Draco](https://github.com/google/draco) | alternative mesh and point-cloud compression | OPTIONAL | Apache-2.0 |
| Scene | [MaterialX](https://github.com/AcademySoftwareFoundation/MaterialX) | shader graphs, baking and material representations | PRIMARY | Apache-2.0 |
| Texture | [OpenImageIO](https://github.com/AcademySoftwareFoundation/OpenImageIO) | mipmaps, tiled image processing and texture baking inputs | PRIMARY | Apache-2.0 WITH THIRD PARTY |
| Texture | [KTX-Software](https://github.com/KhronosGroup/KTX-Software) | KTX2 generation and texture transport | PRIMARY | UNKNOWN |
| Texture | [Basis Universal](https://github.com/BinomialLLC/basis_universal) | GPU-portable texture transcoding and compression | PRIMARY | UNKNOWN |
| Interchange | [glTF MSFT_lod](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Vendor/MSFT_lod) | node and material LOD import/export | ADAPTER | SPECIFICATION OWFA 1 0 |
| Interchange | [glTF EXT_meshopt_compression](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Vendor/EXT_meshopt_compression) | ratified meshopt glTF compression transport | ADAPTER | SPECIFICATION REVIEW |
| Interchange | [glTF KHR_meshopt_compression](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_meshopt_compression) | release-candidate glTF compression compatibility | REFERENCE | SPECIFICATION RELEASE CANDIDATE |
| Interchange | [glTF KHR_texture_basisu](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_texture_basisu) | GPU texture transmission interoperability | ADAPTER | SPECIFICATION REVIEW |
| Animation | [Animation Compression Library (ACL)](https://github.com/nfrechette/acl) | skeletal animation compression and sampling | PRIMARY | MIT |
| Animation | [ozz-animation](https://github.com/guillaumeblanc/ozz-animation) | animation optimizer, reduced runtime skeleton evaluation patterns | OPTIONAL | MIT |
| Volume | [OpenVDB](https://github.com/AcademySoftwareFoundation/openvdb) | master sparse volumes and volume hierarchy | PRIMARY | Apache-2.0 |
| Volume | [NanoVDB](https://github.com/AcademySoftwareFoundation/openvdb/tree/master/nanovdb) | read-only CPU/GPU sparse-volume proxy | PRIMARY | Apache-2.0 |
| Support | [Embree](https://github.com/RenderKit/embree) | visibility queries, occlusion and representation validation | OPTIONAL | UNKNOWN |
| Physics | [Bullet Physics](https://github.com/bulletphysics/bullet3) | collision representation and simplified physics proxies | OPTIONAL | Zlib |
| Physics | [Jolt Physics](https://github.com/jrouwe/JoltPhysics) | alternative collision proxy and physics provider | OPTIONAL | MIT |
| Scene | [Godot Visibility Ranges / HLOD](https://docs.godotengine.org/en/stable/tutorials/3d/visibility_ranges.html) | distance-based HLOD and visibility architecture reference | REFERENCE | DOCUMENTATION |
| Scene | [NVIDIA vk_lod_clusters](https://github.com/nvpro-samples/vk_lod_clusters) | cluster residency, mesh shader and streaming reference; optional GPU-specific paths only | REFERENCE | UNKNOWN |
| Scene | [Cesium 3D Tiles](https://github.com/CesiumGS/3d-tiles) | HLOD trees, SSE refinement and implicit spatial tiling | REFERENCE | SPECIFICATION REVIEW |
| Terrain | [Terrain3D](https://github.com/TokisanGames/Terrain3D) | geometric clipmaps, foliage LOD and region streaming | PRIMARY_REFERENCE | MIT |
| Point Cloud | [PotreeConverter](https://github.com/potree/PotreeConverter) | out-of-core point cloud octree LOD generation | PRIMARY_REFERENCE | BSD-2-Clause |
| Point Cloud | [Potree](https://github.com/potree/potree) | point cloud adaptive streaming and renderer reference | REFERENCE | UNKNOWN |
| Impostor | [IMP](https://github.com/MaxRoetzler/IMP) | hemisphere/full-sphere billboard and impostor atlas baking | REFERENCE | UNKNOWN |
| Impostor | [jppark impostor](https://github.com/jppark/impostor) | dynamic view-dependent impostor reference; source verification pending | UNVERIFIED_REFERENCE | UNKNOWN |
| Hair | [Blender Hair Curves](https://github.com/blender/blender) | native groom, strand-density and guide-curve workflows; use through Bforartists/Blender adapter | PRIMARY_REFERENCE | GPL REVIEW |
| Hair | [GBH Tool](https://github.com/GixoXYZ/BlenderGBHTool) | strand-to-card workflows and hair rigging reference | LICENSE_CAUTION | GPL-2.0-or-later |
| Hair | [Strands2Cards](https://github.com/kenji-tojo/strns2cards) | hair strand clustering, texture and card fitting research | LICENSE_CAUTION | UNKNOWN NO LICENSE CONFIRMED |
| Hair | [Hair Card Generator](https://github.com/PurgatoryMP/Hair-Card-Generator) | card generation workflow reference; license verification required | LICENSE_CAUTION | UNKNOWN |
| Rig | [GPUInstance](https://github.com/mkrebser/GPUInstance) | skeleton LOD, crowd LOD and GPU instancing concepts without Unity runtime dependency | REFERENCE | UNKNOWN |
| Virtual Texture | [LibVT](https://github.com/core-code/LibVT) | virtual-texture pagetable, residency, cache and feedback patterns; modernize backend | REFERENCE | MIT |
| Virtual Texture | [virtual-textures prototype](https://github.com/shlomnissan/virtual-textures) | minimal page residency, atlas streaming and GPU feedback reference | REFERENCE | MIT |
| Virtual Texture | [bgfx Sparse Virtual Texturing](https://github.com/bkaradzic/bgfx/blob/master/examples/40-svt/svt.cpp) | portable SVT renderer reference with CPU-only fallback | REFERENCE | UNKNOWN |

## Integration and deduplication rules

1. `meshoptimizer`, `clusterlod.h` and `gltfpack` share upstream, but remain separate capability-level donor records. Apply the same rule to OpenVDB/NanoVDB and separate glTF extensions.
2. Existing OpenUSD and OpenImageIO entries are updated/linked, not duplicated; existing status is preserved. New entries are captured as `CANDIDATE`.
3. Build around FA3-owned `RepresentationNode`, source lineage, recipe, screen-space/error budget, multi-representation validation and provenance. Use existing OpenUSD, Khronos and creative integrations rather than parallel replacements.
4. Distinguish GPU-only research paths (NVIDIA, Unity, GPU animation) from implementation candidates; every production path must have a CPU-only alternative.
5. Keep GPL or unclear-license projects (CGAL package, Blender plugin, GBH Tool, Strands2Cards, Hair Card Generator) isolated as research/reference until explicit legal review. Do not treat the existence of public source as permission to incorporate it.
6. Include viewport, offline render, film/shot, asset graph, BIM coordination, point cloud and terrain use cases in future validation. `FA3-REUSE-DISCOVERY-001` queries this registry before future application design.

## Hardware Audit — pre-implementation assessment

| Check | Candidate-only curation result |
|---|---|
| Vendor-neutral baseline | Preserved; no fixed CUDA/ROCm/oneAPI/Vulkan route required |
| CPU-only | Preserved for planning; all GPU fast paths remain optional, conditional on later runtime evidence |
| Accelerator cardinality | `0..N` baseline unchanged |
| Runtime resource authority | Existing `FA3-AUTH-HOST-RESOURCE-BROKER-001` exclusively |
| GUI compatibility | Platform/DE neutral, Wayland preferred, X11 supported |
| Runtime/host promotion | Not performed; required only for later implementations |

## Licensing notes

- `OpenImageIO` now declares Apache-2.0 for original code with residual BSD/third-party material; inspect `THIRD-PARTY.md` before redistribution.
- PotreeConverter **current README** states BSD-2-Clause for its 2.x free branch; inspect pinned exact revision and full license for any commercial packaging.
- `MSFT_lod` is a specification under Microsoft Open Web Foundation terms, not an MIT C++ library.
- `KHR_meshopt_compression` is listed as release candidate at this review; keep `EXT_meshopt_compression` interoperability.
- Verify legal status for all records marked `UNKNOWN`, `REVIEW`, or `LICENSE_CAUTION` against pinned source versions.
