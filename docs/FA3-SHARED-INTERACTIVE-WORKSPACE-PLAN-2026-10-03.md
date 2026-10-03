# FA3 Shared Interactive Workspace — approved materialization plan — 2026-10-03

## Goal

Materialize one shared, provider-neutral interaction layer that can be projected into many FA3 applications without creating a standalone Renoise-like application, new capability or new architectural authority.

The layer combines:
- natural-language application actions;
- application context and capability descriptors;
- typed action proposals, preview/approval, execution receipts and rollback;
- shared generative workspace surfaces;
- MMG Context IR editing/projection;
- reference, consistency, variant and lineage views;
- review/revision annotation;
- capability-driven skill/runtime composition;
- semantic theme/appearance projection.

## Canonical reuse

Planning is bound only to published main `5d99e09b674877bcf4c057ec7af82e5d819ee616`, donor registry blob `6fcd9a7f5b3e3c5c54b1ae1b5227b37a9bb6a951`, SHA-256 `7dfe58f105a0100948ae19f58925a9deba0b4036544b883b1b63740f3791c7ac`, count **1422**.

Published donor-backed FA3-native patterns reused:
- ComfyUI + LangGraph: typed workflow graph, subgraph, checkpoint and HITL patterns;
- Krita AI Diffusion: canvas, mask, region, layer, reference and non-destructive result patterns;
- FiftyOne + CVAT: review, annotation and comparison patterns;
- WhisperX + PySceneDetect: temporal media alignment and shot/scene boundaries;
- Creative Provenance + Media Asset patterns: lineage, source, derivative and approval traceability.

No donor source code, runtime, provider, model, dataset or framework is adopted in this materialization. The five new Renoise-related donor sources in PR #657 are pending and are explicitly excluded from planning input and usage edges until publication and later reassessment.

## Architecture

```text
FA3 application
  -> Application Context Adapter
  -> Application Capability Descriptor / Capability Resolver
  -> Shared Interactive Workspace
       -> Natural-Language Action Surface
       -> Generative Workspace
       -> Review & Revision Canvas
       -> Skill Runtime projection
       -> Theme & Appearance projection
  -> typed path:
       UAF / MCP Gateway -> native application command -> receipt / rollback
  -> generative path:
       FA3-MMG-CONTEXT-IR-001 -> Model Router -> admitted provider/engine
```

## Workspace profiles

- G0: headless/API only.
- G1: inline action/generate entry.
- G2: Assistant + Generative Dock + lightweight review.
- G3: Canvas + variants + compare + lineage.
- G4: domain workspace with storyboard/timeline/3D/audio projections.

The initial 17 canonical consumers receive only eligibility/profile metadata; no runtime UI is activated by this static change.

## Mandatory boundaries

- `FA3-MMG-CONTEXT-IR-001` remains the only canonical provider-neutral multimodal generation context IR.
- Model Router remains the sole provider/model routing authority.
- UAF/MCP Gateway mediates mutating application actions.
- Temporal remains the sole global durable lifecycle authority.
- HRB remains the sole host resource/device placement authority.
- Secret Broker remains the credential delivery boundary.
- Security Governance and Evidence/Gate remain authoritative.
- arbitrary generated-code `eval` / `loadstring` execution is forbidden;
- generic AI auto-execute is forbidden;
- capability matching never grants permissions;
- profile assignment never grants provider/runtime admission;
- AI-disable deny wins;
- silent local-to-cloud fallback is forbidden;
- application-local duplication of the shared core is forbidden without reviewed justification.

## Result insertion

The shared adapter contract supports typed targets such as NEW_ASSET, NEW_LAYER, REPLACE_SELECTION, NEW_SHOT, NEW_CLIP, NEW_TRACK, NEW_SLIDE_OBJECT, NEW_MATERIAL, NEW_TEXTURE, NEW_NODE, NEW_NOTE and ATTACH_REFERENCE. Each application advertises only its supported insert modes.

## Theme projection

Theme semantics use role tokens rather than hard-coded palettes. Theme packs are optional projections; no external theme becomes the FA3 visual authority.

## Current Host

This change is static contracts, profile, mapping and tests only. It adds no executable service, daemon, socket, port, dependency, provider/model activation, credential path or physical GUI binding. Any later executable/GUI binding triggers physical current-host positive, negative and rollback evidence before promotion.

## Invariants

- capability baseline: **175 -> 175**
- capability delta: **0**
- architectural authority delta: **0**
- donor usage edges created: **0**
- pending donors consumed: **false**
- runtime promotion claim: **false**
