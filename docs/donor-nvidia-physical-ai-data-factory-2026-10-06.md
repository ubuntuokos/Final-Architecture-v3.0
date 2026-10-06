# CFA3 NVIDIA Physical AI Data Factory donor intake — 2026-10-06

## Scope

This donor-only intake records the owner-explicit source:

- https://github.com/NVIDIA/physical-ai-data-factory

Observed upstream main revision: `e4c663cbbdcf159ad952751274c883c81d3ab4be`.

The repository describes repeatable agent-driven Physical AI data workflows for synthetic generation, enrichment, labeling, augmentation, curation and distributed execution. The root README identifies PAIDF workflow links for orchestration, auto-labeling, augmentation, anomaly generation, simulation, and curation/retrieval.

## Exact parent

- published main: `35a6f54b968d65564e0d2f829531cff688189f76`
- published donor registry blob: `2bb6a74dd415b6374e4a6d5adce1bc9265229b63`
- published donor registry count: **1792**
- this source-intake contribution: **1**
- capability baseline: **175**
- capability delta: **0**
- authority delta: **0**
- usage-edge delta: **0**

## Authorization

The immediately preceding owner message supplied the exact URL and the current owner message explicitly commanded `donornak`. The canonical donor-chat contract permits a command-only follow-up to target the immediately preceding owner link when no owner message intervenes.

## License/provenance observation

The upstream root README/LICENSE declares Apache-2.0 for code and CC-BY-4.0 for documentation/skill content. This is metadata for reference registration only; any material reuse still requires file/component-level rights and provenance review.

## Non-recursive related-source boundary

The upstream README links these related repositories, which were inspected for dependency/reference analysis but are **not** automatically registered by this intake:

- NVIDIA/paidf-orchestration
- NVIDIA/paidf-auto-labeling
- NVIDIA/paidf-augmentation
- NVIDIA/paidf-simulation
- NVIDIA/paidf-curation-and-retrieval
- NVIDIA/paidf-anomalygen

No child repository, model, NGC image, Hugging Face asset, OSMO service, Airflow deployment or Kubernetes runtime is admitted by this donor record.

## CFA3 boundaries

Temporal remains the durable workflow authority; HRB remains the resource authority; Model Router remains the model-routing authority when a model route is used. CPU-only viability, 0..N accelerators, Hardware Safety, Software Coexistence and no-silent-fallback remain mandatory. This intake does not implement the Reconstruction Validation & Synthetic Test Fabric or claim Current Host PASS.
