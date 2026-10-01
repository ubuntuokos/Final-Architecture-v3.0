<!-- SPDX-License-Identifier: Apache-2.0 -->
# FA3 AI Module Factory — approved materialization plan

## Decision

Materialize `fa3.ai-module-factory` as the user-facing workspace for turning approved work created in FA3 applications into governed AI-module drafts. The application reuses CAP-095 rather than creating a parallel trainer.

Capability baseline stays **175**. No new architectural authority is created.

## Work-derived pipeline

```text
FA3 application work
  -> approved final / human correction / workflow trace
  -> provenance + License & Rights + consent gate
  -> dataset/module strategy
  -> Knowledge | Preference | Skill Adapter | Workflow | Native Model draft
  -> human approval
  -> CAP-095 or Knowledge/Retrieval handoff
  -> Model Router
  -> HRB
  -> evaluation/evidence
  -> separately governed publication
```

The application never treats ordinary project access as training consent.

## Module strategies

1. **Knowledge** — retrieval/RAG representation; no model training required.
2. **Preference** — preference/correction-derived adaptation.
3. **Skill Adapter** — LoRA/PEFT-style task adaptation through CAP-095.
4. **Workflow** — learned application/capability sequencing for Orchestrator/Conductor consumption, without gaining orchestration authority.
5. **Native Model** — escalated strategy only; still a CAP-095 draft and never default.

## Source applications

Initial adapters target:

- FA3 Video Editor
- FA3 QuickClip
- FA3 Story/Screenplay
- FA3 Music Studio
- FA3 Character Studio

The shared-first rule applies retroactively: other FA3 applications that later expose approved-work/correction contracts consume the same factory core rather than implementing their own trainer.

## Research donor findings

The research set includes Kiln, Data-Juicer, NeMo Curator, Argilla, Distilabel, Label Studio, FiftyOne, PEFT, TRL, Diffusers, sd-scripts/kohya_ss, lm-evaluation-harness, OpenCompass, OpenRLHF and mergekit.

These sources are **analysis only** in this change. They are not donor IDs, dependencies, code imports, providers or runtime admissions. Repository policy requires the owner's literal `donornak` marker before registration, and live donor intake is currently owned by PR **#581**, so the new research batch cannot be published in parallel.

The existing CAP-095 implementation already references Axolotl, LLaMA-Factory, Unsloth, OneTrainer, Ostris, fairseq2, DVC+Git and MLflow+PostgreSQL. The factory consumes CAP-095 rather than duplicating these engines.

## GUI

The standalone Qt6/QML app exposes:

- source-work candidate collection;
- rights/provenance/consent indicators;
- module strategy selection;
- governed plan preparation;
- draft persistence;
- guard-state inspection.

Advanced engine parameters are intentionally not the default surface. Runtime parameterization belongs to CAP-095/provider adapters after approval.

## Fail-closed rules

A training-capable artifact is rejected unless all are true:

- human-approved final;
- provenance VERIFIED;
- use rights ALLOWED;
- training rights ALLOWED;
- derivative-model rights ALLOWED;
- consent scope is PRIVATE, PROJECT or SHARED.

Knowledge modules do not require training/derivative-model rights, but still require approved final, verified provenance, permitted use and an explicit consent scope.

AI disabled means no AI-module plan. Missing or unknown rights are denied; the factory does not substitute a permissive execution route.

## Decision Fabric applicability

The current materialization uses deterministic eligibility plus explicit user choice for module strategy. Decision Fabric is therefore **NOT_APPLICABLE** to authorization or strategy selection in this version; it may not expand candidates, grant permissions, admit models/providers, or replace human approval. A future advisory ranking path requires a separately approved change.

## Authority boundaries

The factory does not:

- select or call a provider directly;
- lease or select accelerators;
- write secrets;
- promote models;
- claim Current Host PASS;
- change the 175-capability baseline.

Model Router, HRB, License & Rights, Evidence, orchestration/UAF and CAP-095 remain authoritative.

## Current Host

This is a structural/runtime-surface change. Static tests and compilation are not physical closure. Fresh current-host startup, negative path, draft persistence, handoff and rollback evidence are required before promotion. Central 175×3 reconciliation remains coordinated with active PR #559.
