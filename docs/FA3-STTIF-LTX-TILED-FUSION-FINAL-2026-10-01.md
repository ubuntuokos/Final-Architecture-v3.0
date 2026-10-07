# FA3 Spatial-Temporal Tiled Inference Fabric (STTIF)

## Status

**Materialized static FA3-native shared control plane.** Capability baseline remains **175**. This change creates no architectural authority and makes no Current Host runtime-promotion claim.

## Purpose

STTIF centralizes high-resolution and long-form inference planning so FA3 applications do not each invent local tiling, temporal-windowing, overlap-fusion or memory-budget logic. It binds to existing CAP-159, CAP-160, CAP-161 and CAP-163.

The implementation independently materializes the reusable architecture pattern observed in the LTX-2.5 / ComfyUI-LTXVideo tiled-fusion documentation: one logical canvas/noise trajectory, overlapping spatial tiles, temporal windows and per-step fusion semantics. No upstream source code or model artifact is copied.

## Authority boundary

STTIF is not a model router, provider registry, HRB, render authority, video-generation authority or license authority. Model/provider choice remains with Model Router; resource admission and placement remain with HRB; external code/model/runtime rights remain under License & Rights and Security Governance.

No silent fallback is permitted. Unsupported samplers, illegal spatial alignment, invalid temporal shape constraints and insufficient declared resource budgets fail closed.

## External references

- LTX-2 pinned reference revision: `2d6e71c88be37b55a2dd698c2dff447edfbe5898`.
- ComfyUI-LTXVideo pinned reference revision: `bf2ca0264f706db64cb8931155695ca481fc9d91`.
- LTX values such as 32-pixel tile alignment, ~0.5 overlap guidance, 97-frame temporal windows / 8n+1 shape and documented discrete sampler examples are **reference observations**, not FA3 global defaults.
- Both upstream sources are held **REFERENCE_ONLY** in this materialization. An LTX model/provider adapter is not admitted here.

## Shared consumers

Primary internal consumers are FA3 Video Editor, QuickClip and Character Studio. Reference/integration surfaces include ComfyUI, InvokeAI, Kdenlive, Natron, Gaffer and Bforartists. Future affected applications must consume the shared contract rather than duplicate the functional core.

## Current Host

The change adds deterministic planning/validation code and static contracts only. It installs no provider/model, performs no network fetch, opens no service/port, changes no device placement and mutates no hardware. Therefore the structural impact is `NO_RUNTIME_IMPACT` and physical requalification is not claimed for this static materialization. Any future provider/model execution requires its own physical Current Host evidence.

## #401 compatibility

Open PR #401 remains a separate Motion & Video runtime materialization stream. This change does not import, rewrite or promote it. When that runtime is reconciled, it should consume STTIF through provider-neutral constraints instead of embedding a second tiling authority.
