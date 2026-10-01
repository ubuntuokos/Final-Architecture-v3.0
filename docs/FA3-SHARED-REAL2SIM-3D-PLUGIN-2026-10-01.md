# FA3 Shared Real2Sim 3D Plugin

Date: 2026-10-01  
Status: implementation draft; static core materialized; Current Host/runtime promotion pending.

## Purpose

Provide one shared FA3 Real2Sim pipeline for every relevant Bforartists/Blender-engine application instead of duplicating indoor-video reconstruction and motion logic in each app. The plugin composes existing FA3 capabilities and authorities; it does not create a new application, top-level capability, provider, model router, geometry authority, resource authority, daemon or network port.

The public `KevinXu02/aha-3d` repository was inspected at commit `82f4b1110cfe4b55fff19df3b3790852ce07b171` as an analysis source. Because the source has not been entered through the owner `donornak` donor-intake rule, this change does **not** copy AHa-3D code, create a donor usage edge, install AHa-3D, bundle its external models/assets or claim an admitted AHa-3D runtime. The FA3 implementation re-expresses the observed workflow shape using existing FA3 contracts.

## Shared capability surface

The plugin binds only existing capability IDs:

- `CAP-032` — Metric 3D Reconstruction;
- `CAP-163` — Neural Rendering & Reconstruction Enhancement;
- `CAP-164` — Character Motion Synthesis, Retargeting & Performance Transfer;
- `CAP-166` — Scene / Shot / Camera / Rig Interchange;
- `CAP-167` — Vision Detection, Tracking & Segmentation Fabric.

The global capability baseline remains 175.

## Pipeline

A request selects the needed features. The resulting plan can contain source analysis, room reconstruction, camera recovery, actor reconstruction, contact refinement, motion transfer, scene assembly, placement validation and preview/review. Planning never authorizes execution.

Provider/model choice remains with Model Router. CPU/GPU/NPU placement remains with HRB. Actions go through UAF and MCP mediation. Geometry semantics remain with `FA3-3D-GEOM-001`; final scene/camera/asset authority remains with `FA3-DCC-RT3D-001`.

## DCC host adapters

`BFORARTISTS` is the primary DCC host projection. `BLENDER` is a compatibility host projection. Neither adapter is allowed to mutate a host directly from the shared plugin core. A DCC handoff requires an explicit matching approval receipt and still does not itself authorize execution; the governed DCC/UAF path performs the actual commit.

This separation lets Character Studio, World / Environment Studio, Scene / Shot Designer, Animation Department and future Blender-engine FA3 applications share one implementation while retaining app-specific UI/workflow projections.

## Safety and coexistence

The control path remains CPU-valid. Compute-heavy stages may be unavailable when no compatible admitted provider exists; there is no silent CPU/GPU/provider fallback. The display GPU is never enlisted implicitly. No hardware tuning is performed. AI enable/disable is explicit; disabled AI cannot imply hidden model/provider calls.

The plugin claims no default port, daemon, service, global environment mutation or upstream uninstall. Native project preservation and Blender-compatible interchange are mandatory on handoff.

## Upstream boundary

A future **direct AHa-3D bridge** is intentionally left outside this implementation. To admit it later, the source must first satisfy the canonical donor intake/adoption flow, then pass exact source/license/provenance review, Security Governance, Software Coexistence, Hardware Safety, model/data rights, provider/runtime admission and physical Current Host evidence. A direct bridge must remain optional and cannot replace the FA3-native shared contract.

## Verification performed for this draft

The plugin core has isolated Python unit coverage for: 175-capability preservation, authority binding, no AHa-3D runtime dependency, Bforartists and Blender host projections, explicit approval before DCC handoff, no execution authorization from planning/handoff, explicit AI/network switches and fail-closed unknown features.

This is static/unit evidence only. It is **not** physical Current Host proof and does not promote any runtime.
