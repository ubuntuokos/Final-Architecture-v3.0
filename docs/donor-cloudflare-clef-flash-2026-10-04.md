# FA3 Cloudflare Clef-Flash donor intake and applicability plan — 2026-10-04

## Owner marker and source normalization

The owner explicitly marked the previously supplied Clef-Flash source as `donornak`.

Canonical source:

- https://huggingface.co/Cloudflare/clef-flash
- planned donor id: `FA3-DONOR-CLOUDFLARE-CLEF-FLASH-001`
- planned normalized key: `https://huggingface.co/cloudflare/clef-flash`
- source class: `HUGGINGFACE_MODEL`
- intake scope: reference registration only

The originally pasted `-/huggingface.co/Cloudflare/clef-flash` text is normalized to the resolvable official Hugging Face model URL above. No alternate project identity is inferred.

## Verified upstream snapshot

Observed 2026-10-04:

- publisher: Cloudflare
- model: Clef-Flash
- size: 9B parameters
- tensor type: BF16
- base: Qwen/Qwen3.5-9B
- declared Clef-Flash license: Apache-2.0
- declared Qwen3.5-9B license: Apache-2.0
- latest observed model-card revision: `17f0b0a`
- original weights/head upload revision: `89c693f`
- model inputs: text, JSON, image, video
- model output: one score/logit per allowed option for every typed question, normalized per question to probabilities
- free-form generation: not required for the native decision path
- API compatibility: Jev / SystemOne
- upstream documented local stack: torch 2.11 + transformers 5.10.2
- upstream documented test hardware: one H200
- custom executable model-side code: `joint_schema_model.py`

The model therefore has strong architectural overlap with FA3's existing structured Decision Fabric and System One Reflex path, but the upstream H200 test does **not** prove the mandatory FA3 CPU-only local runtime path.

## Published FA3 donor/reuse context consulted

Planning uses the finalized published donor snapshot only. Pending donor PRs are excluded.

Relevant already-published references and implementation patterns include:

- `FA3-DONOR-SYSTEM-ONE-HARNESS-001` — bounded System One decision/reflex pattern already materialized through the Decision Fabric;
- `FA3-DONOR-HUGGINGFACE-DIFFUSERS-001` — provider-neutral model pipeline/admission pattern reuse where applicable;
- published Temporal references — durable workflow authority remains Temporal and is not delegated to a decision model;
- published LiteLLM-related references/data-plane architecture — physical model/provider transport remains below Model Router and existing authenticated transport boundaries.

No pending LocalAI/offline-AI donor intake is used as a planning dependency.

## Architecture decision

**Do not create a new FA3 decision subsystem.**

Clef-Flash should be evaluated as an optional model implementation behind the existing:

`FA3-DECISION-FABRIC-001`
→ `FA3-SYSTEM-ONE-REFLEX-001`
→ `FA3-PROVIDER-SYSTEM-ONE-DECISION-001`
→ Model Router logical route `fa3-decision-system-one`.

The existing bounded-action contract is already a close semantic match:

`bounded state + finite caller-authorized options -> typed probabilities -> confidence gate -> authorization-ready intent / handoff`.

Clef-Flash must not:

- expand the caller-authorized action/candidate set;
- invent free-text tool arguments;
- authorize execution;
- directly call tools;
- replace Model Router;
- replace HRB;
- replace MCP Gateway;
- replace Temporal;
- bypass the existing application/policy authority.

## Proposed implementation plan

### Phase 1 — model artifact and rights qualification

Create a model-admission evidence package only after this donor intake becomes canonical.

Required evidence:

1. Pin an immutable Hugging Face revision, not `main`.
2. Record SHA-256 for:
   - all backbone safetensor shards;
   - model index/config;
   - joint-head safetensor;
   - joint-head config;
   - tokenizer/processor/chat-template assets;
   - `joint_schema_model.py`.
3. Verify the Apache-2.0 Clef-Flash license.
4. Verify the Qwen3.5-9B base-model license chain independently.
5. Inspect dependency licenses and redistribution implications.
6. Treat model weights, executable Python and third-party runtime dependencies as separate License & Rights subjects.
7. No model/runtime package enters a release bundle before the corresponding License & Rights descriptors pass.

### Phase 2 — security and supply-chain qualification

Because Clef-Flash includes custom executable Python, safetensors alone is insufficient evidence.

Required controls:

- static review of `joint_schema_model.py`;
- prohibited filesystem/network/process behavior checks;
- dependency pinning;
- isolated runtime environment;
- no `trust_remote_code`-style uncontrolled remote execution;
- no runtime download from Hugging Face;
- Model Manager performs explicit user-initiated acquisition;
- immutable artifact manifest + hashes;
- fail closed on hash or revision drift;
- deny redirect/unapproved-origin artifact substitution;
- preserve source/model/runtime provenance in Decision Trace.

### Phase 3 — CPU-only feasibility gate

This is the principal technical blocker for local FA3 admission.

Test the exact Clef joint schema head on CPU, not merely the Qwen backbone.

Qualification matrix:

- BF16/FP32 CPU reference execution;
- supported lower-precision CPU execution where numerically valid;
- RAM requirement;
- cold-load time;
- decision latency at representative context lengths;
- text-only request;
- JSON state;
- image state;
- video state;
- multi-question / multi-option batch;
- probability stability versus the pinned reference implementation.

A GGUF/llama.cpp/Ollama/LM Studio variant must **not** be assumed compatible merely because the Qwen backbone has quantizations. The custom joint schema head and typed probability semantics must be preserved and verified end-to-end.

If no compliant CPU path exists, local runtime admission remains blocked. GPU/NPU support may not waive the CPU-only baseline.

### Phase 4 — FA3 model descriptor and Model Router registration

If Phases 1–3 pass, add an FA3 model descriptor, conceptually:

- model id: `FA3-MODEL-CLEF-FLASH-001`
- family: `STRUCTURED_DECISION`
- contract: `BOUNDED_ACTION`
- logical route: `fa3-decision-system-one`
- input modalities: text / JSON / image / video
- output: typed option probability distributions
- authority: none
- provider/model selection authority: Model Router
- resource placement authority: HRB
- acquisition authority: Model Manager
- default install: false
- optional user download: true after admission
- CPU-only support: evidence-derived, never declarative-only

Do not create a second model-routing authority or a Clef-specific application.

### Phase 5 — System One/Clef protocol adapter

Prefer a thin compatibility adapter over a new execution stack.

Responsibilities:

1. Map the existing FA3 `BOUNDED_ACTION` finite schema into Clef/SystemOne questions.
2. Preserve stable action/parameter IDs.
3. Submit only bounded state approved by the calling authority.
4. Receive complete option distributions.
5. Validate:
   - all requested questions are present;
   - no unknown question/action/option appears;
   - probabilities are finite and normalized within tolerance;
   - schema/request digest matches;
   - result belongs to the pinned model/runtime instance.
6. Feed the distributions into the **existing** FA3 confidence gate.
7. Emit the existing Decision Trace schema.
8. Never call an action directly.

If Jev/SystemOne wire compatibility is exact after verification, keep the implementation configuration-driven and avoid duplicate provider code.

### Phase 6 — multimodal bounded-state extension

Clef-Flash adds particular value because the decision state can include image/video evidence.

Extend Decision Fabric inputs only where an existing FA3 authority has already bounded the media:

- browser screenshot classification;
- media QC/routing;
- shot/image/video workflow state;
- safety/quality triage;
- UI state classification;
- document/image intake classification.

Rules:

- media input is evidence, not authority;
- no model-selected filesystem path;
- no model-selected camera/device activation;
- no hidden network fetch;
- provenance links every media item to the caller-approved source;
- large media is preprocessed under existing FA3 media/resource policy.

### Phase 7 — confidence, fallback and dual-model policy

Clef-Flash should be a fast decision candidate, not an unconditional default.

Model Router may rank it only among already-admitted compatible decision models using:

- task/contract compatibility;
- modalities;
- current hardware;
- RAM/VRAM availability;
- measured latency;
- measured calibration/accuracy;
- privacy/locality constraints;
- user/project preference.

Low confidence or unsupported input follows the existing handoff:

- System Two;
- human review;
- deterministic policy path where defined.

No silent switch to cloud, Jev, another model, or another device.

For high-risk decisions, retain stricter existing confidence thresholds and policy authorization. Clef probability is never permission.

### Phase 8 — GUI integration

Extend the existing Decision Fabric / Model Manager surfaces rather than creating a separate Clef application.

Decision Fabric UI should show:

- active decision route;
- selected model;
- why it was selected;
- local/remote execution mode;
- CPU/GPU/NPU placement;
- installed/not-installed state;
- model revision and integrity state;
- modalities supported;
- current confidence thresholds;
- returned option distributions;
- handoff reason;
- authorization state;
- Decision Trace link.

Model Manager should show Clef-Flash after model admission as:

- **Compatible / recommended** when current hardware and task qualify;
- **Compatible alternative** when admitted but not preferred;
- **Available to download** when admitted but not installed;
- **Blocked** with an explicit reason when rights/security/hardware/current-host evidence is incomplete.

The user can manually select any compatible admitted alternative. Automatic selection remains within Model Router policy and the existing display-GPU rule.

### Phase 9 — application rollout

First consumers should be areas already using the Decision Fabric, not every FA3 application indiscriminately.

Recommended order:

1. System One Reflex / agent bounded-action routing.
2. MCP bounded tool/action choice.
3. Browser/Web AI bounded action selection.
4. Orchestration specialist/task-group advisory ranking after deterministic eligibility.
5. Security/support/operations triage.
6. Multimodal media and QC classification where the calling app supplies an explicit candidate set.

Each consumer requires an explicit applicability assessment. A donor/model admission does not create automatic application usage edges.

### Phase 10 — validation and promotion

Required tests:

- positive bounded-choice path;
- low-confidence handoff;
- explicit escalation;
- unknown option rejection;
- missing question rejection;
- probability validation;
- free-text parameter rejection;
- candidate-set expansion rejection;
- direct execution rejection;
- Model Router bypass rejection;
- HRB bypass rejection;
- unauthorized device selection rejection;
- runtime network-fetch rejection;
- artifact hash mismatch rejection;
- invalid/changed license descriptor rejection;
- CPU-only positive path;
- display-GPU policy negatives;
- text, JSON, image and video modality tests;
- restart/reproducibility;
- Decision Trace completeness.

Promotion sequence:

`REFERENCE -> MODEL_CANDIDATE -> STATIC_ADMISSION_PASS -> CURRENT_HOST_CANDIDATE -> PHYSICAL_CURRENT_HOST_PASS -> AVAILABLE_MODEL`.

No simulated Current Host PASS.

## Expected FA3 impact

- capability baseline: **175 unchanged**
- new architectural authority: **0**
- new mandatory vendor dependency: **0**
- provider count: dynamic, no forced increase from donor registration
- Decision Fabric: extended model choice, unchanged authority
- Model Router: unchanged authority, broader candidate set after admission
- HRB: unchanged authority
- Temporal: unchanged durable workflow authority
- MCP Gateway: unchanged tool/capability authority
- user model choice: increased after admission
- multimodal bounded decision capability: materially strengthened

## Donor intake serialization state

Published parent main:

`07518f8a55c49fec5efa010ea285ff0a736e9524`

Published donor registry blob:

`1362d75186c6da74e5cf947fdf0b8867d462636a`

Published registry entries: **1427**.

The five active donor-intake slots are currently occupied by:

- #651
- #657
- #663
- #664
- #671

Earlier FIFO-waiting intakes are:

- #672
- #673
- #675
- #676
- #682
- #683

Therefore this Clef-Flash intake must remain **FIFO waiting**. The central donor registry is intentionally unchanged until this intake reaches an active slot. Until then, Clef-Flash is not a canonical planning input for other FA3 work.

## Planning result

**Recommended disposition: ACCEPTED_REFERENCE once FIFO-admitted.**

The strongest fit is as a model behind the existing provider-neutral System One route. The expected implementation is an incremental model/runtime adapter and admission package, not a new subsystem. The fixed 175-capability baseline does not need to change.
