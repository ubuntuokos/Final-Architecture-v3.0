# FA3 Shared Module Pattern & Donor Catalogue

**Status:** owner-approved materialization, metadata/reference only  
**Capability baseline:** 175, unchanged  
**Architectural authority delta:** 0  
**Runtime / provider / model admission:** none

## Purpose

This catalogue answers a different question from the canonical Donor & Reference Registry.

- The Donor Registry answers **which external sources are registered for FA3 planning**.
- This catalogue answers **which reusable data-model, UI, workflow, engine, adapter, search, review, provenance, interchange, performance, test, security, project-context, temporal, multimodal or composite patterns may strengthen shared FA3 modules**.

It is not a second donor registry and cannot create donor identity, code-import permission, dependency admission, provider/model admission or Current Host evidence.

## Core flow

```text
registered donor / analysis-only research source
                    ↓
             reusable pattern
                    ↓
              shared-module target
                    ↓
       retrospective application impact
                    ↓
      separately approved FA3-native implementation
```

## Pattern classes

The canonical catalogue defines:

- DATA_MODEL_PATTERN
- UI_PATTERN
- WORKFLOW_PATTERN
- ENGINE_PATTERN
- ADAPTER_PATTERN
- SEARCH_PATTERN
- REVIEW_PATTERN
- PROVENANCE_PATTERN
- INTERCHANGE_PATTERN
- PERFORMANCE_PATTERN
- TEST_PATTERN
- SECURITY_PATTERN
- PROJECT_CONTEXT_PATTERN
- TEMPORAL_PATTERN
- MULTIMODAL_PATTERN
- COMPOSITE_REFERENCE_PATTERN

A donor may contribute multiple patterns. A pattern may cite multiple registered donors and multiple analysis-only research sources.

## Shared-module pattern groups

| Shared pattern target | Main use |
| --- | --- |
| Shared Media Asset Fabric | media assets, metadata, collections, derivatives, rights and provenance |
| Multimodal Retrieval Fabric | text/image/video/transcript/metadata hybrid retrieval |
| Temporal Media Fabric | scenes, shots, frames, speech, word timing, speaker/silence/music regions |
| Media Review & Annotation Fabric | human review, annotation, machine proposals, corrections and approvals |
| Shared Creative Canvas Toolkit | canvas/layer/mask/selection/reference/variant interaction patterns |
| Shared Workflow Graph Model & UI | typed nodes/ports/edges/subgraphs/templates and execution preview |
| Media Representation Resolver | original/direct → remux/proxy → transcode decision pattern |
| Creative Provenance Fabric | source/workflow/model/parameter/edit/approval lineage |
| Structured Document Intake Fabric | production-document structure and source provenance |
| Shared AI Composition | retriever/tool/structured-output/prompt/middleware/event/streaming adapters |
| Stateful Workflow Adapter | state/checkpoint/interrupt/resume/HITL semantics |
| UI Prototyping & Inspection | diagnostics, probes, dashboards, evaluators and prototypes |

These are **shared-module design targets**, not claims that a production implementation already exists.

## Registered donor mappings in this materialization

The catalogue resolves the following already-published donor identities from the 1287-entry main-branch registry:

- ComfyUI
- FiftyOne
- CVAT Community
- Krita AI Diffusion
- WhisperX
- PySceneDetect
- LangGraph

Their presence here does not promote their status or authorize runtime/code reuse.

## Analysis-only research sources

The internet research also identified strong patterns in Immich, PhotoPrism, InvokeAI, Label Studio, MediaCMS, LosslessCut, Jellyfin, Docling, LibreChat, AnythingLLM, Dify, Langflow, Open WebUI, LangChain, Subtitle Edit and Streamlit.

These sources were **not** submitted with the repository-required literal owner `donornak` marker. Therefore they are recorded only as `OWNER_MARKER_REQUIRED` analysis sources. They have no donor ID and may not appear in donor usage edges or be treated as admitted dependencies.

If the owner later marks the relevant links `donornak`, normal serialized donor intake can register them. The pattern catalogue can then be reconciled from analysis-source references to canonical donor IDs without changing the extracted pattern intent.

## Composite assistant/workbench reference

The previously designed multimodal assistant/workbench concept is deliberately retained as:

`FA3-MULTIMODAL-ASSISTANT-WORKBENCH-REFERENCE-PATTERN-001`

It is a **COMPOSITE_REFERENCE_PATTERN**, not a mandatory new application. Its value is to demonstrate how shared multimodal input, project context, retrieval, tools, workflows, human approval, streaming, artifacts, review and evidence can compose into a higher-level surface.

It can later inform assistants, research tools, production coordination, creative copilots, media-review tools or project-knowledge surfaces without forcing any one UI/runtime framework.

## Authority and safety boundaries

Pattern extraction never transfers authority. In particular:

- Model Router remains sole model/provider routing authority.
- HRB remains sole host-resource authority.
- Orchestrator/Temporal boundaries remain unchanged.
- Secret Broker remains credential authority.
- Security/UAF/MCP, Evidence/Gates, Layer Guard and AI enable/disable policy remain mandatory.
- Streamlit is treated as a prototyping/inspection UI pattern, not the default production GUI for timeline/canvas/DAW/3D/compositor work.
- LangChain is an AI composition/adaptation pattern, not routing/tool/secret/orchestration authority.
- LangGraph is a stateful-workflow adapter/reference under the existing orchestration boundary, not a second global lifecycle owner.

## Current Host

This materialization is metadata + validation + CI only and is classified `NO_RUNTIME_IMPACT`.

When a pattern is later materialized as a real shared runtime, service, GUI, adapter or host-integrated component, the structural-change rule applies: affected Current Host obligations must be aligned and physical positive/negative/rollback evidence is required before promotion.

## Validation

Run:

```bash
./bin/fa3-shared-pattern-catalogue --check --summary
python3 -m unittest tests.test_shared_module_pattern_catalogue
```

The validator fails closed on unresolved canonical donor IDs, analysis sources pretending to be donors, unknown application consumers, single-consumer "shared" modules, unknown pattern classes or shared targets, capability baseline drift and authority/runtime-policy violations.
