# CFA3 Shared Semantic, Ontology & Operational Knowledge Fabric

**Profile:** `FA3-SHARED-SEMANTIC-ONTOLOGY-001`  
**Status:** owner-approved static materialization  
**Capability baseline:** 175 → 175  
**Capability delta:** 0  
**Architectural authority delta:** 0  
**Current Host:** NO_RUNTIME_IMPACT for this static phase

## Purpose

This shared fabric gives CFA3 applications one provider-neutral semantic contract instead of embedding independent ontology engines in each application. It reuses the existing Shared Knowledge & Retrieval layer, CAP-155 Knowledge Provenance & Citation Graph and CAP-156 Evidence Reasoning & Claim Verification.

It does not replace the Donor & Reference Registry, Model Router, Security authority, Evidence authority, Registry authority or application-specific source-of-truth stores.

## Architecture

```text
CFA3 applications
       |
       v
CFA3 Semantic SDK
       |
       +-----------------------------+
       |                             |
       v                             v
Semantic Runtime               Management Plane
query / reasoning              authoring / versions
validation / proof             diff / migration
identity / alignment           catalogue / provenance
       |                             |
       +--------------+--------------+
                      |
                      v
             Development Plane
      ingestion / taxonomy / extraction
      synthesis / patterns / CQ / quality
                      |
                      v
              CFA3 Semantic IR
                      |
           Provider / Storage SPI
```

## Source-role mapping

The following owner-approved sources are design inputs for this work. Their canonical donor intake is deliberately not mutated on this branch while the active donor-intake/source-graph work is unresolved.

| Source | Intended reusable role | Runtime authority |
| --- | --- | --- |
| https://github.com/fabio-rovai/open-ontologies | reasoning, validation, proof and governed change patterns | no |
| https://github.com/microsoft/Ontology-Playground | visual authoring, catalogue, RDF/OWL round-trip and graph UX | no |
| https://github.com/ozekik/awesome-ontology | ecosystem discovery/meta-donor index | no |
| https://infranodus.com/skills/ontology-creator | semantic proposal, text-to-graph and gap-analysis patterns | no |
| https://github.com/nicovlr/smart-ontology-generator | structured data profiling and data-to-semantic compilation | no |
| https://github.com/arunsr1ni/databricks-ontology-generator | taxonomy/ontology extraction, incremental ingestion and cross-domain identity patterns | no |
| https://github.com/topics/ontology-development | discovery index for ontology-development references | no |

The Databricks ontology generator and InfraNodus code paths remain code-reuse blocked until repository-specific rights/licence review passes. Discovery-index child repositories are not automatic donors.

## Semantic lifecycle

```text
DISCOVERED
  -> IMPORTED / AI_PROPOSED
  -> NORMALIZED
  -> VALIDATED
  -> REVIEWED
  -> CANONICAL
  -> SUPERSEDED
```

AI output is never canonical truth. Canonical publication requires structural/reference integrity, semantic validation, provenance, rights-policy checks, required reasoning/competency tests and the applicable human/policy gate.

## Identity model

Cross-domain identity is first-class but fail-closed. Relations are:

- IDENTICAL
- EXACT_MATCH
- CLOSE_MATCH
- POSSIBLE_MATCH
- RELATED
- CONFLICTING_IDENTITY

Only evidence-gated IDENTICAL or EXACT_MATCH links may participate in canonical identity closure. CLOSE_MATCH never merges entities. The UI must expose source domains, evidence, confidence/conflicts and require explicit apply/undo.

## Application integration

Applications consume the fabric through `FA3-SDK-SEMANTIC-ONTOLOGY-CONTRACTS-001`, not through direct provider calls.

| Consumer | Primary semantic use |
| --- | --- |
| Donor & Reference Registry | source/dependency/reference graph projection, provenance and L1-L5 relationships |
| Knowledge / RAG | ontology-guided retrieval, claim/source lineage and entailment-preservation checks |
| Search | entity-aware, relation-aware and taxonomy-aware search |
| Agent Native / AgentScope | typed semantic tools/actions and governed semantic mutations |
| Medical / Anatomy / Dental | domain vocabularies, alignment, terminology/entity resolution |
| Story / Screenplay | character, location, event, continuity and temporal semantics |
| World Studio | scene/location/object/environment and asset relations |
| Meta Human | person/character identity, anatomy, traits, rigs and source assets |
| Asset / Render | asset derivation, dependency and scene/render-job relations |
| Webdesign / CMS | content model, taxonomy, linked content and schema mapping |
| Business / Collaboration | project/task/contact/message/event semantic graph |
| Logistics | resource/task/location/dependency/state graph |
| Import / Export | semantic mapping and fidelity checks |
| Evidence / Verification | evidence binding, assertion verification and proof provenance |

Future applications declare semantic needs in their application manifest rather than introducing another ontology stack.

## Donor/source graph boundary

Canonical donor mutation and L0-L5 materialization remain blocked on this branch by active parallel donor work. This branch therefore creates no donor IDs, usage edges, source promotions or child-source admissions.

## Runtime boundary

This materialization adds static contracts, validation logic and documentation only. No service, daemon, socket, port, package dependency, model/provider activation, credential delivery or physical GUI execution is introduced.
