# CFA3 Semantic / Ontology Studio GUI

**Contract:** `FA3-SEMANTIC-STUDIO-GUI-CONTRACTS-001`  
**Status:** static GUI contract; no physical GUI PASS claim

## Surface model

```text
+------------------------------------------------------------------+
| CFA3 Semantic / Ontology Studio        MODE: <global mode>       |
+----------------+-------------------------------------------------+
| Dashboard      |                                                 |
| Ontologies     |                Graph Canvas                     |
| Taxonomies     |                                                 |
| Entities       |         o------o---------o                       |
| Relations      |         |     /         /                        |
| Authoring      |         o----o---------o                         |
| Import         |                                                 |
| AI Proposals   +-------------------------------------------------+
| Alignment      | Inspector                                       |
| Identity       | source | provenance | evidence | version        |
| Validation     | validation | reasoning | identity conflicts      |
| Reasoning      +-------------------------------------------------+
| Diff/Migrate   | Issues / proposals / activity                   |
| Provenance     |                                                 |
| Donors         |                                                 |
| Providers      |                                                 |
| Export         |                                                 |
+----------------+-------------------------------------------------+
```

## Required workflows

### Import and synthesis

```text
Import
 -> source preview
 -> discovered entities/relations
 -> reuse/alignment candidates
 -> AI proposals
 -> validation/reasoning
 -> diff
 -> explicit publish
```

### Identity review

The UI must never silently merge identities. It must show:

- candidate relation;
- contributing domains;
- source identities/revisions;
- evidence and confidence;
- conflicting assertions;
- intended canonical effect;
- preview;
- explicit Apply;
- Undo.

### AI proposal review

AI proposals are visually distinct from verified/canonical assertions. Direct AI-to-canonical apply is forbidden. The user sees proposal diff, provenance/evidence and gate results before acceptance.

### Donor panel

The Donors view is a projection, not a second donor authority. Once canonical donor intake is available, it may display source identity, lifecycle status, L0-L5 provenance depth, licence/security state, SDK-use state, application consumers and first-class promotion state.

## CFA3 GUI requirements

- CFA3 look and feel;
- mandatory global Workload Mode indicator on the surface;
- keyboard navigation and accessibility;
- no raw secret display;
- no direct model/provider controls that bypass the Model Router;
- Preview -> Apply -> Undo for mutating semantic operations;
- explicit offline/cloud/data-classification state where model-assisted functions are available.

Actual QML/application registration is deferred until the static contracts are reconciled with current application inventory and the donor/source-graph blocker is cleared.
