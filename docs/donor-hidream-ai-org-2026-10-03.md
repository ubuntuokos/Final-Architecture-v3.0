# FA3 HiDream-ai GitHub organization donor intake — 2026-10-03

## Owner marker

The owner explicitly marked the exact source `https://github.com/HiDream-ai` as **donornak** on 2026-10-03 and requested donor-list registration plus an FA3 usability plan.

## Source classification

- canonical source key: `github:hidream-ai`
- donor id: `FA3-DONOR-HIDREAM-AI-ORG-001`
- source kind: `GITHUB_ORGANIZATION`
- status: `ACCEPTED_REFERENCE`
- mode: metadata-only `DISCOVERY_INDEX`
- observed public child repositories during intake scan: **27**
- capability delta: **0**
- authority delta: **0**
- capability baseline: **175**
- runtime impact: **NO_RUNTIME_IMPACT**

Organization-level registration is a discovery index only. It does not recursively admit repositories, source code, models, checkpoints, datasets, services, providers or runtimes.

## High-value FA3 discovery areas

The current organization portfolio exposes strong research/reference material for:

- unified image generation, editing, text rendering, subject personalization and storyboard generation;
- instruction-guided image editing;
- object and camera motion controlled image-to-video generation;
- regional/instructional video editing and reference-conditioned video editing;
- diffusion-based video super-resolution;
- virtual try-on quality/preference evaluation and refinement;
- diffusion training / reinforcement-learning sampling acceleration;
- multimodal skill routing and agent evaluation;
- benchmark, dataset and evaluation design.

Representative observed repositories include `HiDream-O1-Image`, `HiDream-I1`, `HiDream-E1`, `VAREdit`, `MotionPro`, `ReCo`, `PS-SR`, `VTON-VLLM`, `DMSampler` and `MM-SkillRouter`.

## License and runtime boundary

The organization index has no single code/model license. Child projects must be reviewed independently. During analysis, several repositories declared MIT or Apache-2.0, while at least some child repositories did not expose a root LICENSE file. Model-weight, dataset and transitive dependency rights remain separate from repository code licensing.

Several projects are GPU/CUDA/Flash-Attention oriented. Those upstream assumptions do not alter FA3 invariants:

- CPU-only execution remains the baseline path;
- Model Router remains model/provider routing authority;
- HRB remains resource/device-placement authority;
- display GPU is not automatically enrolled for AI;
- Hardware Safety Envelope and Software Coexistence remain fail-closed;
- no silent fallback or automatic model/provider admission is introduced.

## Candidate FA3 targets

Likely future target surfaces include Image/Photo Studio, Story/Screenplay and Storyboard, Shot Designer, Video Editor, Quick Video, Animation/Motion tools, Character Studio, shared Image Generation and Motion/Video fabrics, Model Router / Engine Provider Selector, AI Module Factory / training governance, Evaluation/Benchmark Fabric and Shared Interactive Workspace.

## Admission boundaries

No code is copied and no package is installed. No provider, model, runtime, dependency, service, checkpoint, dataset or child repository is admitted. No usage edge is created by this intake.

Repository-level material adoption requires:

1. explicit child-repository donor/reuse eligibility;
2. exact upstream provenance;
3. License & Rights clearance for code, weights, datasets and assets as applicable;
4. security review;
5. Software Coexistence review;
6. Hardware Safety/model-runtime review;
7. Model Router/HRB placement when execution is involved;
8. capability/layer placement and non-regression review;
9. canonical typed usage-edge registration;
10. Current Host requalification only if runtime behavior is actually affected.

The fixed FA3 capability baseline remains **175**.

## Rolling intake state

At creation time the rolling five-slot donor intake window is full with earlier canonical donor-intake requests. This request is therefore created as a FIFO waiting intake and must not be finalized ahead of the active-window ordering.
