# FA3-MENTOR-ENHANCEMENT-001 — Mentor v0.3 Capability Reinforcement Plan

**Architecture:** FINAL ARCHITECTURE v3.0
**Parent profile:** `FA3-MENTOR-001`
**Target implementation:** `FA3 Mentor v0.3.0`
**Plan status:** `FINAL PLAN / IMPLEMENTATION PENDING`
**Priority:** `P0 / MUST`
**Capability impact:** `0`; global baseline remains fixed at **175**
**Authority impact:** `0`; no new authority
**Runtime status:** `PENDING_CURRENT_HOST / PROMOTION_BLOCKED`
**Registry target:** `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`
**Registry delta:** `FA3-DONOR-MENTOR-ENHANCEMENT-DELTA-001.json`
**Date:** `2026-09-28`

## 1. Decision

FA3 will not install or elevate a foreign tutoring platform as the Mentor. The existing provider-independent `FA3-MENTOR-001` remains the single Mentor profile. Its next implementation generation will absorb selected, license-compatible patterns from multiple donors behind FA3-owned contracts and existing authorities.

The target is one coherent Mentor experience that can:

- build durable, consent-aware learning and competency projections;
- guide with questions and graduated hints instead of defaulting to complete answers;
- construct branching learning paths around observed misconceptions;
- generate and validate bounded practice tasks;
- use voice, screen and application context with explicit user consent;
- evaluate the pedagogical quality of its own responses independently;
- exchange interactive learning content and learning-event projections;
- provide the same contextual Mentor surface inside other FA3 applications.

This is a reinforcement of existing capabilities, not a new application authority, agent runtime, LMS authority, evidence authority or model-routing layer.

## 2. Selected donors and exact use

| Donor | Accepted patterns | Explicitly rejected | Primary FA3 consumers |
| --- | --- | --- | --- |
| `HKUDS/DeepTutor` | lifelong personalization substrate; books/courses/readings; teach-back; research-to-learning conversion; mastery workspace; proactive but policy-bounded intervention | its own global agents, MCP authority, memory authority, provider routing, workspace execution and unrestricted tools | Mentor, Knowledge/RAG, Research, Story/Documentation, Developer/ADE |
| `ls1intum/Artemis` family | typed exercises; templates/solutions/tests; automatic feedback; competency analytics; uncertain-answer human review; exercise lifecycle | built-in VCS/CI as FA3 authority, institutional LMS ownership, credential storage and autonomous execution | Mentor, Developer/ADE, Task Manager, Manager, Model/Code evaluation |
| `oppia/oppia` | branching explorations; misconception-specific branches; answer-dependent feedback; learning-by-doing flow authoring | separate learner identity, content registry, policy engine or production web platform dependency | Mentor, Onboarding, Help, all guided FA3 application workflows |
| `skillcoco/skillcoco` | BKT mastery estimation; local-first adaptive learning; practice loop; lab progression; spaced-practice inputs | provider/BYOK routing, independent course authority or unrestricted terminal execution | Mentor, Developer/ADE, application onboarding, user training |
| `kaushal0494/AITutor-EvalKit` | multidimensional pedagogical quality evaluation; mistake identification/location; guidance and actionability scoring; model comparison | LLM-as-judge as final authority, math-only scope, direct paid-provider coupling | Mentor QA, Coach QA, role-chat regression, Model Manager evaluation |
| `tryskilly/skilly` | voice-first assistance; visible context indicator; application-aware curriculum skills; referenced-UI pointing; bounded capture lifecycle | macOS/ScreenCaptureKit runtime, OpenAI Realtime hard dependency, continuous silent capture, external entitlement/control plane | Mentor GUI, Video Editor, Photo/Vector apps, Bforartists/Krita/Ardour guidance |
| `Flagrare/llm-tutor` | Socratic policy; layered hints; productive struggle; learner-independence objective; tutor personas as presentation policy | Claude-specific plugin/runtime dependency, prompt package as policy authority | Mentor, Developer/ADE, all application help surfaces |
| `open-spaced-repetition/free-spaced-repetition-scheduler` | DSR/FSRS scheduling model; difficulty, stability and retrievability; local scheduler/optimizer patterns | canonical learner-state ownership or automatic scheduling without evidence/consent | Mentor mastery scheduler, training and rehearsal modules |
| `jupyterlab/jupyterlab` | reproducible notebook/terminal/editor practice surface; rich outputs; kernel-isolated exercises | Conda/Mamba requirement, notebook server as execution authority, unrestricted extension installation | Developer Mentor, Data/Research, Model Manager experiments |
| H5P component family | interactive book/video/question/content packaging; portable interactive learning objects | mandatory PHP/LMS runtime, unrestricted embedded scripts, mixed-license code import without audit | Mentor content, Presentation, Story, Video Editor tutorials, Onboarding |
| Learning Locker/xAPI family | xAPI statement validation and interoperable learning-event projection | Learning Locker as canonical LRS, identity, memory, analytics or Evidence authority | Mentor, Unified Evidence projection, Analytics, Task/Progress views |

## 3. Cross-application reuse map

The donor knowledge must be reusable through the central Donor & Reference Registry and Reuse Discovery, not copied into a Mentor-only list.

| FA3 consumer | Reusable donor-derived capability |
| --- | --- |
| Developer/ADE | Artemis exercises and feedback; Jupyter practice; Socratic hints; SkillCoco mastery progression |
| Story, Documentation and Research | DeepTutor reading/course conversion; teach-back; source-grounded learning paths |
| Video Editor, PhotoTux, Vector, Bforartists, Krita and Ardour surfaces | Skilly-derived contextual guidance; H5P-derived interactive walkthroughs; progressive hints |
| Model Manager | AITutor-EvalKit-derived pedagogical evaluation; notebook experiments; provider comparison without routing authority |
| Coach | typed knowledge-gap handoff; Mentor return conditions; shared progress evidence without role collapse |
| Task/Priority Manager | practice dependencies, non-interruptible learning steps, urgency-aware rescheduling and progress projection |
| Onboarding and Help | Oppia branching flows; H5P content; application-sensitive skill packs |
| Presentation and training modules | H5P interactive books/video; xAPI-compatible export projection |
| Unified Observability/Evidence | validated learning-event projection and lineage; never learner-state ownership |

## 4. Target architecture

### 4.1 Mentor Personalization Projection

FA3-owned projection combining:

- consented competency evidence;
- learning objectives and prerequisites;
- BKT-style mastery estimates;
- FSRS difficulty/stability/retrievability state;
- preferred explanation depth and modality;
- known misconceptions and uncertainty;
- source and evidence lineage.

Canonical state remains in the existing Memory, Knowledge/RAG and Evidence authorities. The Mentor holds only a scoped session/projection cache.

### 4.2 Learning Graph Engine

Oppia- and DeepTutor-derived graph with:

- objective nodes;
- prerequisite edges;
- misconception branches;
- evidence requirements;
- practice and assessment nodes;
- remediation and alternate-explanation branches;
- mastery exit conditions;
- human approval checkpoints where required.

The graph is a Mentor domain artifact, not a replacement for Temporal or the global durable workflow authority.

### 4.3 Pedagogy Policy Engine

Flagrare/llm-tutor and Artemis patterns become declarative Mentor policies:

1. ask for the learner's attempt;
2. identify the smallest blocking misconception;
3. choose question, analogy, example or partial hint;
4. expose increasingly specific hints only as needed;
5. allow an explicit answer-first mode when the operator requests it or time/risk policy requires it;
6. request human review when answer confidence or consequence thresholds fail;
7. record evidence without inflating mastery from conversation alone.

This engine selects pedagogy, not models, providers or tools.

### 4.4 Practice and Assessment Fabric

Artemis, SkillCoco and JupyterLab patterns become FA3-native practice definitions:

- programming exercise;
- notebook/data exercise;
- quiz and short answer;
- text/review exercise;
- modeling/diagram exercise;
- application task with expected UI or artifact state;
- teach-back assessment;
- bounded project/lab.

Every executable practice task is delegated through Central MCP and Agent Execution, requires Security/Governance authorization, HRB admission where compute is used, a sandbox/workspace lease, resource limits, cancellation, cleanup and evidence receipts.

### 4.5 Contextual Voice and Screen Mentor

Skilly contributes interaction patterns only. The FA3-native implementation uses:

- Wayland-first portal capture and X11 fallback;
- PipeWire audio;
- explicit per-session screen/microphone consent;
- persistent visible capture indicator;
- application/window/region scoping;
- redaction and sensitive-field exclusion;
- operator-controlled push-to-talk or bounded live mode;
- local/offline path when an admitted local provider is available;
- Model Router selection and HRB lease for all inference.

No silent capture, hidden accessibility control, direct UI execution or OpenAI-specific hard dependency is allowed.

### 4.6 Pedagogical Quality Gate

AITutor-EvalKit-derived evaluation expands beyond mathematics and scores at minimum:

- error/misconception identification;
- error location and evidence;
- correctness;
- relevance;
- guidance quality;
- actionability;
- appropriate hint disclosure;
- source grounding;
- uncertainty calibration;
- safety and authority-boundary compliance;
- learner-independence support;
- accessibility and language quality.

LLM-as-judge output is advisory. Promotion requires deterministic checks, curated fixtures, human-reviewed gold cases and negative tests.

### 4.7 Learning Content and Event Interchange

- H5P is an import/export and rendering compatibility profile for admitted content types.
- Active content is sandboxed, inspected and origin-tracked.
- xAPI is an interoperability projection for learning events.
- xAPI/Learning Locker never becomes the canonical Evidence, identity, analytics, Memory or mastery authority.

## 5. Canonical contracts

The implementation must add or version the following contracts without creating new authorities:

- `MentorPersonalizationProjection`
- `LearningObjectiveGraph`
- `LearningObjectiveNode`
- `PrerequisiteEdge`
- `MisconceptionHypothesis`
- `HintLadder`
- `PedagogyPolicyDecision`
- `PracticeDefinition`
- `PracticeExecutionRequest`
- `PracticeExecutionReceipt`
- `AssessmentRubric`
- `AssessmentResult`
- `TeachBackAssessment`
- `PedagogicalQualityReport`
- `HumanTutorReviewRequest`
- `ContextObservationRequest`
- `ContextObservationReceipt`
- `CaptureConsentReceipt`
- `LearningContentPackage`
- `LearningEventProjection`
- `MentorCoachHandoff`
- `MentorDonorReuseReceipt`

Every contract carries version, provenance, actor, consent scope, policy decision reference, evidence references and failure state.

## 6. GUI plan

The Mentor remains available as a standalone workspace and a context-sensitive panel inside FA3 applications.

### Standalone workspace

| Area | Contents |
| --- | --- |
| Learn | objective graph, current concept, source-grounded explanation, alternate explanation |
| Practice | admitted exercises, sandbox status, resource/evidence state |
| Ask | Socratic dialogue, hint ladder, explicit answer-first control |
| Review | submitted work, automated checks, Mentor feedback, human escalation |
| Progress | demonstrated mastery, uncertainty, next review, evidence links |
| Sources | Knowledge/RAG citations, donor/reuse lineage, content licenses |
| Context | selected application/window/region, microphone/screen state and redaction |
| Settings | language, accessibility, explanation depth, learning preferences, capture and memory consent |

### Embedded application panel

- compact objective and current step;
- ask/explain/show-next-hint actions;
- contextual source and selected object;
- capture indicator and stop control;
- practice handoff;
- progress/evidence receipt;
- no duplicated application toolbar or execution controls.

## 7. Implementation work packages

### WP0 — Registry and baseline reconciliation

- losslessly upsert donor records by normalized source key;
- reconcile against PR #459 and all still-open donor branches;
- preserve existing records and unresolved conflicts;
- run Donor Inventory, Reuse Discovery and Canonical gates;
- keep the fixed capability count at 175 and authority delta at zero.

### WP1 — Core learning and pedagogy

- implement Personalization Projection;
- implement Learning Graph and misconception branches;
- implement Hint Ladder and productive-struggle policies;
- integrate BKT/FSRS state with evidence thresholds;
- add Mentor↔Coach typed handoff.

### WP2 — Practice and assessment

- implement typed PracticeDefinition and rubric system;
- add programming/notebook/quiz/text/modeling/application tasks;
- integrate sandbox and workspace lease;
- add cancellation, cleanup, negative and resource-denial paths;
- implement human review for uncertain or consequential feedback.

### WP3 — Contextual multimodal Mentor

- implement Wayland Portal/PipeWire capture adapter;
- add push-to-talk and bounded live modes;
- add visible indicators, scoping and redaction;
- connect perception/inference through Model Router and HRB;
- prohibit automatic display-GPU enlistment.

### WP4 — Quality and regression evaluation

- create domain-independent pedagogical rubrics;
- add curated gold conversations and adversarial cases;
- add deterministic policy and authority tests;
- add model/provider comparison through Model Router;
- require human approval for benchmark/rubric changes.

### WP5 — Content and event interoperability

- admit selected H5P content types individually;
- implement safe import/export and artifact lineage;
- validate xAPI projections;
- map learning events into Unified Evidence without creating another LRS authority.

### WP6 — GUI integration

- build standalone Mentor workspace;
- provide shared embedded panel component;
- connect the first reference hosts: Developer/ADE, Story/Documentation, Video Editor and Model Manager;
- add accessibility, keyboard, screen-reader and two-language tests;
- keep GUI send/action controls adapter-gated.

### WP7 — Physical current-host closure

- run Hardware Audit first;
- apply Software Coexistence & Host Non-Interference;
- run as admitted non-root current-host runner;
- prove Central MCP, Knowledge/RAG, Memory, Model Router, HRB, sandbox and Evidence paths physically;
- prove CPU-only operation;
- prove display-GPU rules and explicit selection;
- generate fresh, append-only Evidence Bundle;
- reconcile release, inventory and evidence projections.

## 8. Mandatory gates

1. `FA3-GATE-MENTOR-DONOR-REUSE-001` — exact donor identity, license, provenance and permitted-use validation.
2. `FA3-GATE-MENTOR-AUTHORITY-BOUNDARY-002` — deny direct tool, agent, model, memory, resource, policy and evidence authority.
3. `FA3-GATE-MENTOR-PEDAGOGY-001` — hint ladder, misconception handling, evidence-backed mastery and learner-independence regression.
4. `FA3-GATE-MENTOR-PRACTICE-SANDBOX-002` — authorization, sandbox, resource, cancellation, cleanup and negative paths.
5. `FA3-GATE-MENTOR-CONTEXT-PRIVACY-001` — explicit consent, visible capture, scoping, redaction and retention.
6. `FA3-GATE-MENTOR-EVAL-001` — independent pedagogical evaluation with deterministic and human-reviewed fixtures.
7. `FA3-GATE-MENTOR-INTERCHANGE-001` — safe H5P and xAPI projection, provenance and active-content isolation.
8. `FA3-GATE-MENTOR-COEXISTENCE-001` — paths, ports, services, caches, environments, sockets, DB, IPC, desktop and GPU-runtime collision checks.
9. `FA3-GATE-MENTOR-HARDWARE-SAFETY-001` — fail-closed Hardware Safety Envelope and HRB admission.
10. `FA3-GATE-MENTOR-CURRENT-HOST-002` — physical production E2E; mock or historical evidence rejected.

## 9. Acceptance criteria

The plan is implementation-complete only when:

- every donor is present in the single central registry or losslessly reconciled from its canonical delta;
- every reused pattern has a source, license, version/commit and provenance receipt;
- the Mentor remains advisory and authority-neutral;
- learner state is consented, evidence-backed, inspectable and deletable through canonical authorities;
- branching learning, graduated hints, practice, assessment, voice/screen context and pedagogical QA work through typed contracts;
- the same reusable components work in at least four non-Mentor FA3 application surfaces;
- CPU-only operation passes;
- no silent provider, model, resource, display-GPU or capture fallback occurs;
- all safety, privacy, coexistence and negative gates pass;
- physical current-host receipts prove the full dependency chain;
- release/inventory/evidence projections retain the global baseline of 175 and authority delta zero.

## 10. Ordered delivery

1. Merge/reconcile the donor delta into the canonical registry.
2. Land contracts, schemas and static gates without runtime promotion.
3. Implement WP1 and WP2 as the first usable Mentor v0.3 slice.
4. Add independent pedagogical QA before expanding provider coverage.
5. Add contextual voice/screen support only after privacy and Portal capture gates pass.
6. Add H5P/xAPI compatibility after artifact/security admission.
7. Integrate embedded panels into reference applications.
8. Run physical current-host closure and global reconciliation.

No stage may infer production admission from source presence, GUI availability, mock success or a donor project's upstream claims.
