# Chip Huyen ML systems design — FA3 donor curation (2026-09-28)

**Status:** Two metadata-only `CANDIDATE` references in the existing canonical Donor & Reference Registry. This is a research/discovery index, not permission to copy code or text, install a dependency, admit a provider/model, or promote runtime behavior.

## Individually reviewed sources

| Upstream | Observed revision | Reusable reference | Primary FA3 targets |
| --- | --- | --- | --- |
| [Machine Learning Systems Design, 2019 booklet](https://github.com/chiphuyen/machine-learning-systems-design) | `15780893ea0d7ebf2c6f577328e0c84897ee64be` (`master`) | Iterative project setup → data pipeline → model selection/training/debugging → serving; case studies and 27 exercises; model baselines, evaluation and feedback design | Model Manager, Model Router, Data Pipeline, Training Fabric, Inference Fabric, Evidence Registry |
| [Designing Machine Learning Systems, 2022 book companion](https://github.com/chiphuyen/dmls-book) | `b9d1d085d121ec582ae2a41807b8b446d62492df` (`main`) | Published book's chapter summaries, MLOps tool discovery index and additional reading; deployment, distribution shift, monitoring and continual-learning checklists | Model Manager, Model Router, Data Pipeline, Training Fabric, Inference Fabric, Evidence Registry, Donor & Reference Registry |

The sources are distinct and complementary. Neither is a ready-to-integrate ML runtime. The 2019 booklet explicitly recommends the 2022 book as the more comprehensive and updated treatment; the newer repository explicitly contains **no code examples**.

## Targeted reuse without duplicate FA3 authorities

- **Model Manager:** use the research checklists to review experiment provenance, baseline comparison, evaluation metrics, model lifecycle, deployment and regression evidence. Existing model-management authority and implementation remain unchanged.
- **Model Router / provider admission:** assess route-specific performance and failure/feedback observability; preserve live provider/model discovery, explicit selection, no silent fallback, and Router → HRB → provider boundaries. No upstream text may choose or change providers.
- **Training / Data Pipeline:** review source and labeling quality, split/leakage checks, drift detection and data/model version evidence where the existing FA3 implementation lacks an equivalent control.
- **Inference / Evidence Registry:** compare offline and online evaluation plans, latency/cost budgets, production drift/feedback review and independently documented negative cases; no CI synthetic evidence may substitute for current-host runtime proof.
- **Reuse Discovery:** treat the newer book's MLOps tools list as a historical discovery index, not an automatically admitted collection. Cross-check each proposed downstream donor against existing FA3 registry entries before any additional candidate capture or promotion.

Existing FA3 capabilities, decisions and closed work take precedence: conduct a gap assessment before opening implementation issues. This curation does not create a new capability or architectural authority.

## License, currency and provenance

GitHub repo metadata for **both** sources has no declared license. Preserve `license: UNKNOWN` and `SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW`; cite links and concepts rather than copying book text, graphics, built HTML/PDF or other protected assets. Verify any third-party link, license, supported version, current security and reproducibility independently; a tool appearing in the MLOps index is not an FA3 approval. The early booklet is historical guidance, not 2026 production advice without reassessment. Pin the observed upstream revisions above for traceability.

## Mandatory Hardware Audit and safety

Registry updates and method reviews are **metadata-only**, CPU-only viable, vendor-neutral, and support accelerator cardinality `0..N`. There is no GPU/NPU requirement, hard-coded CUDA/ROCm/oneAPI/provider/model route, hardware mutation, or display-GPU enlistment. HRB retains sole resource authority and the central Model Router retains route/provider/model authority; existing display-GPU explicit app/model/task policy applies unchanged. Any later GUI must prefer Wayland while retaining X11 support. Any later code/runtime changes require independent licensing, security, coexistence, Hardware Audit and current-host evidence gates.

**Review status:** source content inspected and metadata captured; no imported code/assets, executable integration, deployment or current-host evidence is claimed.
