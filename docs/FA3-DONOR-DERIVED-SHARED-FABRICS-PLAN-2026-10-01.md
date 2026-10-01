# FA3 donor-derived shared fabrics — approved materialization plan

**Date:** 2026-10-01  
**Status:** OWNER-APPROVED STATIC MATERIALIZATION; donor intake for newly submitted links remains fail-closed on the literal owner `donornak` marker rule.  
**Baseline:** 175 capabilities, dynamic provider count, authority delta 0.

## Scope

Materialize the approved classification:

- ReelMimic, ShapeCast, automate-faceless-content, agentic-ai-apis, OpenHands ecosystem, Refine, Elasticsearch, PulsarAI RAG, quiche and awesome-ai-tools are research/donor inputs according to the owner-approved plan.
- No item becomes a new mandatory FA3 application.
- No plugin is created merely because an upstream project exposes plugin/API/MCP surfaces.
- Cross-application behavior is materialized shared-first.
- Existing FA3 authorities remain exclusive.

## Donor-intake boundary

The repository importer accepts a new canonical donor identity only when the user-authored message itself contains the literal `donornak` marker before the link. The analyzed links in this batch were approved through the derived classification/plan, but the literal marker is not present in the originating user messages. Therefore this changeset MUST NOT forge donor IDs, usage edges, code-import permission, runtime admission or provider/model admission.

OpenHands/software-agent-sdk already has published canonical provider/reference records; these are reused and not duplicated.

## Materialized shared compositions

### 1. Agent Operations Composition

Composes existing Agent Workload Runtime, Agent Execution, Conversation/Session, Tool/Action Mediation, Model Router, HRB, Secret Broker and Evidence boundaries.

Patterns: backend-independent agent sessions, workspace ownership, resumable conversations, normalized event stream, execution receipts, automation trigger separation, progressive skill loading, compatibility-floor checks.

### 2. Resource & Application Composition

FA3-native headless contract for resource descriptors, provider adapters, authentication-vs-authorization separation, live events, audit before/after state and schema-derived Qt/QML projections.

Refine React/UI packages are not admitted as a mandatory runtime.

### 3. Retrieval Quality & Knowledge Composition

Extends the existing Shared Knowledge & Retrieval profile; does not create a second RAG authority.

Adds domain-aware segmentation, query planning, lexical/vector/structured/graph selection, fusion/reranking, retrieval-quality gate, rights/provenance filter, evidence context packs, contradiction/coverage checks and regression evaluation.

Elasticsearch is optional backend/reference only, never source authority. PulsarAI material remains educational/pattern reference only.

### 4. Network Transport Composition

Provider-neutral transport intent with optional QUIC/HTTP/3 backend, transport/session telemetry, stream/flow budgets, congestion-policy mediation and protocol qualification.

quiche is not made mandatory. Any later quiche runtime admission requires exact source/dependency License & Rights, Software Coexistence, security and physical Current Host proof.

### 5. Creative Production Composition

Composes existing FA3 creative capabilities for plan/approval, parallel artifact ownership, independent review, evidence-backed repair, generation recipes/snapshots, content derivation, platform profiles, 3D productionization and batch scheduling.

ReelMimic, ShapeCast and automate-faceless-content remain source/reference inputs; no competing video editor, 3D authority or social scheduler is created.

## Discovery sources

agentic-ai-apis and awesome-ai-tools inform discovery/catalog patterns only. Discovery is not admission. External catalog categories are normalized into FA3 semantic classes before any later admission.

## Retroactive consumers

The integration record enumerates impacted existing/planned applications and shared authorities. When executable materialization occurs, local duplicate implementations must migrate through adapters with capability non-regression.

## License policy

- OpenHands: existing canonical reference/provider record; exact source reuse still needs file/dependency clearance.
- Refine: MIT observed upstream, but no source is copied by this changeset.
- quiche: BSD-2-Clause observed upstream, transitive dependencies still require clearance.
- Elasticsearch: mixed/triple-license repository; source reuse remains file-level license gated.
- ShapeCast / PulsarAI / workflow catalogues: reference/pattern only unless separate rights evidence exists.
- No third-party source is copied by this changeset.

## Current Host

This changeset is static contract, mapping, validation and CI only. It does not add a daemon, port, socket, package, provider activation, model selection, credential path or hardware mutation. Any later executable/shared-GUI/runtime binding triggers the structural Current Host rule and requires physical positive/negative/rollback evidence before promotion.

## Closure definition

Static materialization closes when:
1. the integration record, profiles/contracts, owner decision, intent, Reuse Assessment and Current Host impact are committed;
2. dedicated fail-closed validation and regression tests pass;
3. global repository gates pass at exact head;
4. no donor identity is forged around the owner-marker rule;
5. runtime promotion is not claimed from static CI.
