# FA3 Tutorial → Shared Capability → Application Manual plan

Status: **PROPOSED / plan only**  
Policy: `FA3-TUTORIAL-SHARED-CAPABILITY-POLICY-001`  
Capability baseline: **175 fixed**  
Runtime/current-host promotion: **none**

## 1. Goal

Turn owner-authorized internet tutorials into governed FA3 knowledge and, when justified, reusable functionality without creating duplicate application implementations.

A tutorial is never treated as executable authority. It is a reference source that can produce:

1. an FA3-native manual section for an already existing function;
2. an approved implementation proposal for a missing function;
3. a shared capability/service when the same function belongs to more than one FA3 application;
4. a retroactive migration plan for previously planned, in-progress and materialized applications.

## 2. Intake boundary

The central `FA3-DONOR-REFERENCE-REGISTRY-001` remains the only donor/reference registry. No tutorial-only donor database is created.

Remote links still follow the existing donor intake rule: an unmarked internet link remains analysis-only until the owner authorizes donor intake. A tutorial file supplied/downloaded by the owner, or material explicitly placed into an owner-approved tutorial-ingest task, may be analyzed as tutorial material, but analysis does not authorize copying code, assets, text or screenshots.

Each tutorial reference needs provenance and rights metadata before reuse:

- source/origin;
- retrieval date or local source identity;
- author/publisher when known;
- license/terms status;
- code/assets/text reuse allowance;
- reference-only restrictions;
- product/application/version demonstrated by the tutorial.

Unknown or incompatible rights permit factual/functional analysis only.

## 3. Feature extraction

Tutorial content is decomposed into atomic **Tutorial Feature Units (TFU)**. Each TFU records:

- feature name and intent;
- input/output;
- UI/workflow steps demonstrated upstream;
- required data types;
- dependency/runtime assumptions;
- candidate FA3 capability IDs;
- candidate FA3 applications;
- potential shared consumers;
- provenance and license constraints.

The tutorial wording and upstream UI are never copied blindly into FA3 manuals.

## 4. Existing-function path

For every TFU, Reuse Discovery and the application inventory must first determine whether the function already exists.

If it exists in one FA3 application:

- preserve the existing implementation;
- map the tutorial workflow to the actual FA3 controls and terminology;
- create/update the application's manual section;
- record differences between upstream tutorial behavior and FA3 behavior;
- do not claim functionality that the current application does not implement.

If it exists in several FA3 applications, continue through the shared placement path.

## 5. Shared placement path

When a function is useful to more than one FA3 application, the functional core must be implemented once in a shared FA3 layer.

Application-local code may contain only the application-specific:

- GUI integration;
- workflow adapter;
- contextual defaults;
- presentation/disclosure logic.

The shared core must expose a stable contract and must carry:

- capability identity;
- version;
- request/response contract;
- permission/scope requirements;
- cancellation and error semantics where applicable;
- provenance;
- test contract;
- hardware/resource requirements;
- coexistence requirements.

No application may silently fork the shared functional core merely to simplify local implementation.

## 6. Retroactive impact requirement

Every shared function must generate an impact set covering:

- applications already planned;
- applications currently being materialized;
- already materialized applications;
- GUI surfaces that expose the function;
- current-host/runtime components affected by the structural change.

For every affected application, classify the required action:

- `NO_CHANGE`
- `MANUAL_ONLY`
- `ADAPTER_REQUIRED`
- `LOCAL_TO_SHARED_MIGRATION`
- `REGRESSION_REVALIDATION`
- `CURRENT_HOST_REQUALIFICATION`
- `BLOCKED_BY_PENDING_DEPENDENCY`

Existing verified capability must not be lost during migration. A local implementation may remain temporarily only when an explicit compatibility bridge and removal/migration condition are documented.

## 7. Missing-function path

When no FA3 application contains the function:

1. determine whether the function belongs in FA3 at all;
2. identify its target application(s) and capability boundary;
3. query the published-main Donor & Reference Registry through Reuse Discovery;
4. assess license, provenance, security, Software Coexistence and Hardware Safety;
5. decide single-application versus shared placement;
6. produce an immutable implementation plan;
7. wait for explicit owner approval before implementation;
8. implement and verify;
9. update all affected application manuals.

A tutorial alone is not evidence that FA3 needs the function.

## 8. Capability-count rule

The canonical capability baseline remains **175**.

A tutorial-derived feature must first map to an existing capability or a subordinate implementation feature. If it genuinely requires a new top-level canonical capability, the tutorial workflow must stop at:

`BLOCK_PENDING_EXPLICIT_CAPABILITY_MODEL_RECONCILIATION`

The tutorial pipeline may not silently change the capability count.

## 9. Manual generation

Documentation has two levels.

### Shared technical documentation

Written once for the shared service/contract. It describes architecture, API/contract, limits, security/resource boundaries, testing and provenance.

### Application manual projection

Written separately for every consuming application. It must use that application's:

- real GUI names;
- real menu/toolbar placement;
- actual workflow;
- application-specific defaults;
- supported inputs/outputs;
- warnings and limitations.

A manual entry may be marked generally available only after the underlying implementation and the required verification are complete.

## 10. Development work packages

### TUT-01 — Tutorial reference classification

Extend donor/reference metadata to classify `TUTORIAL_REFERENCE` sources without introducing a second registry.

Deliverables:
- tutorial source type and provenance fields;
- rights/licensing classification;
- source-version metadata;
- tests preventing tutorial registration from implying donor adoption or runtime admission.

### TUT-02 — Tutorial Feature Unit extractor

Create a non-authoritative analyzer that transforms tutorial material into structured TFUs.

The analyzer must never execute tutorial commands merely because they appear in tutorial content.

### TUT-03 — Capability/application matcher

Match TFUs against:
- the 175-capability model;
- Reuse Discovery;
- curated/planned application inventory;
- application donor links.

Output must distinguish existing, partial, missing and ambiguous matches.

### TUT-04 — Shared placement planner

Add a shared-use decision stage.

If two or more relevant FA3 applications consume the same functional core, the planner must propose one shared layer and per-application adapters. Duplicate functional cores are a blocking design finding unless an explicit architecture exception is approved.

### TUT-05 — Retroactive application impact analyzer

Extend the application inventory so a proposed shared function is checked against planned, in-progress and materialized applications, not only future applications.

Output includes migration class, documentation impact, regression scope and current-host impact for every affected application.

### TUT-06 — Manual adaptation pipeline

Generate manual work items, not copied prose.

For each application:
- resolve the actual FA3 UI surface;
- map tutorial concepts to FA3 terminology;
- require verification that documented controls actually exist;
- retain source attribution/provenance without importing copyrighted tutorial text beyond permitted use.

### TUT-07 — Gates and CI

Add fail-closed checks for:
- missing provenance/license classification;
- undocumented shared consumers;
- duplicate shared cores;
- missing retroactive impact analysis;
- manual claiming an unimplemented function;
- unauthorized top-level capability growth;
- runtime/current-host claims without physical evidence.

### TUT-08 — Current-host alignment

Any tutorial-derived implementation that changes structural runtime behavior must be included in the FA3 current-host structural impact process.

The current-host layer must be updated together with the structural change. Static documentation can never satisfy physical current-host evidence.

## 11. Planned repository changes after plan approval

The implementation stage should add or modify, at minimum:

- `src/fa3_tutorial_reuse_planner.py`
- `bin/fa3-tutorial-reuse-plan`
- structured tutorial-reference schema under `canonical/schemas/`
- shared-function consumer/impact projection using existing application inventory inputs;
- `src/fa3_application_donor_index.py` for retroactive shared-function impact;
- Reuse Assessment integration;
- test coverage under `tests/`;
- CI gate/workflow;
- user-manual projection hooks;
- current-host structural-impact integration where runtime structure changes.

Do not implement a new architectural authority or a second donor registry.

## 12. Interaction with active PRs

This plan is based only on published `main` as required by donor-readiness rules.

Active work that is relevant but not canonical must be reconciled later rather than consumed as authority:

- #557 Scope & Authority Guard;
- #558 License & Rights Authority;
- #559 Current Host reconciliation.

After those changes become canonical, this work must be rebased/reassessed against their final contracts before implementation/finalization.

## 13. Acceptance criteria

The implementation is acceptable only when all of the following are true:

- one central donor/reference registry remains;
- tutorial rights/provenance are explicit;
- existing function reuse is preferred to new implementation;
- multi-application functions have one shared functional core;
- all affected planned/in-progress/materialized applications appear in the impact result;
- no verified capability is lost during migration;
- application manuals reflect real FA3 UI/workflows;
- 175 capability baseline remains unchanged unless a separate approved reconciliation changes it;
- no runtime promotion is inferred from documentation;
- current-host changes receive physical, non-simulated evidence when required;
- exact-head owner approval and normal FA3 gates remain mandatory before finalization.
