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

## Reuse Discovery integration

The derived reuse catalogue indexes each concrete pattern as a `SHARED_MODULE_PATTERN` candidate. Matching therefore sees the pattern name, class, shared-module targets, registered donor IDs and the display names of analysis-only research sources.

Analysis-only source IDs themselves are **not** reuse candidates and are explicitly marked `analysis_sources_are_donors: false`. Reuse Discovery can propose the FA3-native pattern while donor registration/adoption remains separately gated.

This integration extends the existing `FA3-REUSE-CATALOG-001` source policy and `src/fa3_reuse_catalog.py`; it does not create a second discovery authority and does not modify the capability-usage graph owned by the separate capability-map work.


## Materialized FA3-native shared AI composition

The approved analysis is materialized as five **shared profile/contract families**, not as a new chat application and not as an upstream framework stack.

| Shared component | Canonical purpose | Existing capability coverage |
| --- | --- | --- |
| `FA3-SHARED-AI-INTERACTION-001` | capability-oriented AI request/stream/result contract behind Model Router | CAP-005, CAP-098, CAP-138, CAP-140, CAP-148, CAP-149 |
| `FA3-SHARED-KNOWLEDGE-RETRIEVAL-001` | source-aware RAG, embedding, hybrid retrieval, reranking, provenance and claim linkage | CAP-010, CAP-021, CAP-102, CAP-153, CAP-155, CAP-156 |
| `FA3-SHARED-MULTIMODAL-SOURCE-001` | original + derived text/image/audio/video representations with temporal alignment | CAP-017, CAP-037, CAP-066, CAP-084, CAP-085, CAP-086, CAP-088, CAP-115, CAP-116, CAP-167, CAP-168 |
| `FA3-SHARED-CONVERSATION-SESSION-001` | versioned session/events, streaming, persistence and explicit memory/knowledge references | CAP-004, CAP-021, CAP-102, CAP-106, CAP-110, CAP-116 |
| `FA3-SHARED-TOOL-ACTION-MEDIATION-001` | typed action request → policy/approval → MCP/UAF → isolated execution → receipt | CAP-003, CAP-007, CAP-011, CAP-013, CAP-051, CAP-079, CAP-144, CAP-145, CAP-172 |

The table is descriptive. The machine-readable Capability Map does **not** trust manually copied CAP IDs: it derives them only from the canonical profile/contract `capability_bindings` fields.

### Rejected direct-stack assumptions

The shared contracts explicitly reject the weaknesses found in the analyzed material:

- no hard-coded physical provider/model selection;
- no silent local→cloud fallback;
- no framework object serialization as the canonical session format;
- no fixed global RAG chunk-size or top-k magic number;
- no implicit use of a generation model as an embedding model;
- no claim of video understanding from one midpoint frame or a fixed tiny sample;
- native-audio and transcription-derived semantic paths remain distinct;
- Base64 is treated as encoding, not compression;
- no model-output → `subprocess`/shell/provider execution path;
- prompt-injection classification is advisory and cannot grant authorization;
- no Streamlit, LangChain, Ollama, Chroma, LLaVA, MoviePy, Firejail or Docker component becomes architectural authority or mandatory dependency through this materialization.

The supplied chat/tutorial text itself has no donor ID because it was not submitted through the explicit owner `donornak` intake rule. Its useful ideas are cleanly re-expressed under existing FA3 authorities.

### Shared capability consumer map

`src/fa3_application_donor_index.py` now emits a separate
`fa3.shared-capability-consumer-map.v1` view alongside the donor usage map.
For each materialized shared component it derives capability IDs from canonical
profile/contract bindings and projects reverse lookup by capability and by
application. Manual CAP-ID declarations fail closed.

This keeps the Donor ↔ Capability ↔ Consumer graph semantically clean: donor
usage edges remain donor usage, while FA3-native shared components have their
own derived consumer projection.

## Current Host

The catalogue itself remains metadata and mapping, but the later `FA3-SHARED-EXECUTION-SECURITY-001` materialization adds an execution-enforcement boundary. The aggregate alignment record is therefore `RUNTIME_REQUALIFICATION_REQUIRED`; no physical PASS is implied by static materialization.

Current Host alignment is recorded in `FA3-SHARED-MODULE-PATTERN-CATALOGUE-CURRENT-HOST-IMPACT-001`. If a shared contract later gains a real service, daemon, port/socket, package/runtime dependency, provider/model activation, host-resource execution, credential delivery, mutating action path or physical GUI/application runtime binding, physical positive/negative/rollback requalification becomes mandatory before promotion.

## Validation

Run:

```bash
./bin/fa3-shared-pattern-catalogue --check --summary
python3 -m unittest tests.test_shared_module_pattern_catalogue
```

The validator fails closed on unresolved canonical donor IDs, analysis sources pretending to be donors, unknown application consumers, single-consumer "shared" modules, unknown pattern classes or shared targets, capability baseline drift and authority/runtime-policy violations.
