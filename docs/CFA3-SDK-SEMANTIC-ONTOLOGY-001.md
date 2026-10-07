# CFA3 Semantic / Ontology SDK

**Contract:** `FA3-SDK-SEMANTIC-ONTOLOGY-CONTRACTS-001`

## Goal

Applications program against stable CFA3 semantic types and SPIs. They do not depend on Open Ontologies, Databricks, InfraNodus, Palantir, a particular RDF store, an embedding vendor or a concrete reasoner.

## Namespace families

- `cfa3.semantic.core`, `graph`, `entity`, `relationship`
- `ingest`, `profile`, `extract`, `taxonomy`, `synthesis`
- `ontology`, `authoring`, `pattern`, `competency`
- `validation`, `reasoning`, `proof`, `quality`
- `identity`, `alignment`, `resolution`
- `provenance`, `change`, `diff`, `migration`
- `query`, `rag`, `storage`, `provider`, `export`

## Provider SPIs

```text
SemanticReasonerProvider
SemanticValidationProvider
SemanticExtractionProvider
SemanticAlignmentProvider
SemanticEmbeddingProvider
SemanticStorageProvider
SemanticGraphStoreProvider
SemanticInterchangeProvider
```

A provider implementation cannot acquire model-routing, security, evidence, registry or application authority.

## Model and AI route

```text
Application
   -> Semantic SDK
   -> semantic intent
   -> FA3-AUTH-MODEL-ROUTER-001
   -> eligible provider/model
   -> AI_PROPOSED result
   -> deterministic validation/review
```

Silent local-to-cloud fallback is forbidden. A CPU-only reference path is mandatory.

## Application manifest

Illustrative contract shape:

```yaml
semantic:
  consumes:
    - entity_lookup
    - ontology_query
    - provenance
  produces:
    - project_entity
    - asset_relation
  optional:
    - reasoning
    - ontology_authoring
  required_contract_versions:
    - FA3-SHARED-SEMANTIC-ONTOLOGY-CONTRACTS-001
  data_classification: PROJECT_PRIVATE
  offline_requirement: REQUIRED
```

Unknown semantic capabilities fail closed.

## Data-to-semantic paths

Structured sources use deterministic profiling before AI-assisted semantic proposal:

```text
CSV / JSON / XLSX / Parquet / SQL
 -> profile
 -> schema inference
 -> entity/relation candidates
 -> Candidate Semantic IR
```

Unstructured sources use extraction and taxonomy:

```text
document / text / corpus
 -> segmentation
 -> extraction
 -> taxonomy/normalization
 -> entity resolution
 -> Candidate Semantic IR
```

Both converge on the same validation, provenance and canonical-publication gates.

## Interchange

The contract reserves provider-neutral interchange for CFA3 Semantic IR, RDF/XML, Turtle, JSON-LD, OWL, SKOS, SHACL, LinkML and common structured data formats. Export success alone is not semantic-fidelity proof; round-trip and equivalence checks are separate gates.

## Donor-derived SDK policy

A donor record is not an SDK dependency. A donor can be:

1. design/reference input;
2. algorithm/pattern source;
3. provider candidate;
4. code-reuse candidate after rights/security/compatibility review.

Actual use triggers the existing first-class canonical-source promotion rule. No automatic donor-to-SDK adoption rule is introduced here.
