# FA3 Goal-Driven Agent Execution — selective donor curation and implementation plan

Research date: 2026-09-28. Scope: planning and metadata-only donor capture. No runtime adoption, source copy, provider activation, deployment, capability increment or new architectural authority.

## Architectural decision

Build the goal-to-evidence closed loop *inside existing FA3*, not as another orchestrator, agent manager, scheduler, approval authority, model gateway, memory authority, or evidence store. The user owns the goal and authorization. Start from existing FA3 Coach (`FA3-COACH-CONTRACTS-001`), Orchestration Workforce, Agent Workload Runtime, Temporal, Decision Fabric, Reuse Discovery/Donor Registry, UAF, MCP Gateway, central Model Router, HRB, Journal and the canonical Evidence/Gate authority. The repository already contains bounded action/STOP_CONTINUE Decision Fabric contracts and goal work; this proposal closes the missing goal contract -> typed execution -> criterion-level proof -> bounded repair -> verified closure connection.

Important reconciliation: newer canonical profiles/decisions use the 175-capability baseline, but some historical runtime docs/registry fields still display 143. Resolve references against the current canonical capability model when implementation PRs touch them; do not invent a new number or globally change historical snapshots to force uniformity.

## Donor selection and dispositions

All nine newly captured sources remain **CANDIDATE** in the canonical registry. In each case the licensing below is a *source-level upstream declaration*, not independent dependency/asset review or permission to import into FA3. Every code copy, runtime import, installation, model/provider binding, secret, network access, and release promotion requires its own existing admission.

| Source | Selective reusable material | Intended FA3 consumer | Source/licensing notes | Disposition |
|---|---|---|---|---|
| [User-supplied article: Stop Prompting Endlessly](https://dev.to/saaro_net/stop-prompting-endlessly-give-the-agent-a-goal-om5) | Goal-oriented prompting/research signal | Goal contract design | Article content and reuse rights need independent source review | Methodology candidate only |
| [poponline63/north-star](https://github.com/poponline63/north-star) | Explicit definition of done, checkable requirements, deterministic checks before optional semantic judgment, next-unproven-criterion feedback | Goal-to-Acceptance compiler, acceptance evaluator | MIT LICENSE inspected; formerly `poponline63/hermes-jev-north-star`, now redirected to the canonical repo | P0 pattern review, no direct Hermes/Jev import |
| [orziz/odai](https://github.com/orziz/odai) | Risk-adaptive task governance: clarify only material ambiguities, preserve authorization and stop line, choose right verification depth | Goal intake, execution policy and repair-loop policy | MIT LICENSE inspected; bundled host routing/installer must **not** be imported | P0 pattern review |
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | Typed outputs, tool approval/deferred tools, Pydantic/Temporal durable-execution integration | Schema/type validation and optional narrowly scoped adapter | MIT LICENSE inspected; examples use direct physical providers and are not FA3-compliant unchanged | P1 selective code/API review; no new model gateway |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | Interrupt/resume, checkpoint semantics and stateful task-graph examples | Workforce/Temporal interoperability research | MIT in official project metadata; **do not** create a second durable lifecycle owner; security advisories/version review required before adoption | Reference-only for state/approval patterns |
| [temporalio/sdk-python](https://github.com/temporalio/sdk-python) | Durable workflow/activity, signal, retry and cancellation patterns | Existing FA3 Temporal lifecycle | MIT LICENSE inspected. Existing authority: **reuse**, not parallel scheduler | Existing-runtime strengthening |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | Trace/observation and evaluation UX; correlate criterion, request and execution span | Decision Inspector / Observability and evidence projection | Core MIT; `ee/` and other EE paths separately licensed; telemetry settings require review | Reference or optional telemetry adapter only; not canonical evidence |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | Reproducible agent/LLM evaluations and adversarial regression cases | Canonical Gate test fixture generation, isolated CI | MIT upstream declaration; CLI/Node dependencies reviewed separately | Offline CI test reference, no direct model/provider bypass |
| [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) | Ephemeral coding workspace, task tracker, scoped agent-server work items, inspectable agent events | Developer Agent pilot under Agent Workload Runtime | MIT LICENSE inspected; default direct LLM/tool/host access conflicts with FA3 authority boundaries | Developer Agent reference only; no unsandboxed SDK execution |

Already present, source-unique donor records to **reuse without duplication**: `garrytan/gstack` (decision/evidence fingerprints and freeze guard), `agent0ai/agent-zero` (workspace isolation/agent lifecycle), `vectorize-io/hindsight` (memory/evidence provenance). Existing FA3 CrewAI/ADK/AX provider and runtime plans also remain eligible through Reuse Discovery. A donor record never implies automatic installation, runtime admission, model selection or code import.

## Proposed internal implementation

1. **Goal Intake / contract**: versioned `FA3-GOAL-EXECUTION-CONTRACTS-001` child contract that REFERENCES existing Coach `UserOwnedGoal`, `GoalConstraint`, `SuccessCriterion`, `ExecutionDelegationRequest` and existing Agent Workload/UAF task identities. Fields: `goal_id`, immutable `revision`, `owner_ref`, objective, in-scope/out-of-scope, explicit `acceptance_criteria` with per-criterion `evidence_kind` and independent verifier, bounded `execution_policy` (AUTO/APPROVAL/HYBRID), `budget`, `stop_rule`, external side-effect restrictions, `authorized_ai_participants`, authorization references and audit refs. The natural-language source is **never** executable.
2. **Preflight**: existing Reuse Discovery and application donor index, Security/approval, Hardware Audit, capability and agent eligibility, deterministic conflict checks. Produce machine-readable reuse assessment, hardware audit and typed eligibility receipts before an executable plan is assembled.
3. **Typed plan compiler**: existing Orchestration Director and Workforce map criteria to a DAG of existing `AgentTask`/UAF action envelopes. Each task has expected inputs, concrete outputs, effect class, approver when required, verifier, bounded retries, timeout, recovery/compensation and permission to create children. Decision Fabric may *advise* from the complete pre-authorized candidate set, `authority=false` and `candidate_set_expanded=false` always.
4. **Execution**: only Temporal owns the durable cross-workflow lifecycle. Agent Workload Runtime admits each workload. UAF/MCP Gateway enforce effects, Security enforces permissions, HRB grants runtime resources/leases, and Model Router selects a designated admitted route/provider/model without fixed pins or silent fallback. Secrets only through Secret Broker. A semantic goal alone cannot launch shell, install packages, network egress or approve itself.
5. **Criterion-by-criterion evidence**: the existing Journal/original artifacts are source truth, canonical Evidence/Gate stores authorized proof. First execute deterministic checks. Optional Decision Fabric/Jev judges remaining *semantic uncertainty* as non-authoritative evidence; an empty, self-reported or contradictory evidence set cannot be marked complete. Persist the weakest genuinely unproven criterion and the targeted next authorized step.
6. **Bounded repair**: retry only safe, pre-authorized, idempotent units, with caps on attempts, wall clock, tokens/cost, depth, fanout, CPU/memory and approved HRB leases. Any changed goal scope, new tool/model/provider, larger budget, new AI participant, destructive action or revised acceptance rule needs the appropriate fresh authorization. Escalate rather than widening rights or looping forever.
7. **Completion**: only the existing acceptance/promotion authority can close a goal when every mandatory criterion has trustworthy evidence and required user approvals. Preserve PARTIAL, BLOCKED, FAILED, CANCELLED and VERIFIED terminal distinctions, and a replayable trace of what was done, not a model-generated assertion of success.
8. **GUI**: existing FA3 Control Center / Agent Workspace shows goal, criterion-to-task-to-evidence links, pending approval, failed test, remaining budget, reason for pause, stop/resume and reversible adjustments. No new desktop application; Wayland preferred and X11 supported.

### Explicit Hardware Audit

The planning/data contracts require no new device and work CPU-only on zero accelerators. Vendors/backend count are 0..N. All execution CPU/GPU/NPU discovery and resource placement pass through the existing Hardware Discovery + HRB; no fixed CUDA/ROCm/oneAPI, OS desktop or local host assumptions. When another GPU/NPU exists, a designated display GPU can execute AI **only** after the app's explicit model-and-task-specific assignment; never automatic extra GPU enrollment or fallback. No port changes to AdGuardHome and no host parameter mutation from the planning profile. No local runtime PASS is claimed by this PR.

### Proposed implementation PR boundaries and done conditions

- **P0 (this PR)**: capture/curate donor candidates, existing-authority map, risk/Hardware Audit, static donor regression test. Exact-head CI, reuse impact and any concurrent-registry PR reconciliation before merging.
- **P1 contract**: schema, validators and positive/negative fixtures for user-owned criteria, revisioning, executable-plan separation, authorization, budgets and deterministic verifier coverage. No execution side effects. Missing acceptance evidence must fail closed.
- **P2 plan bridge**: compile authorized GoalPlan into existing Workforce/UAF/AgentTask contracts with donor/reuse/hardware receipts. Reject unauthorized participant expansion, unknown action, physical model pin, unsafe provider, and external source prompt-injection attempts. No second orchestration authority.
- **P3 Temporal/workload**: real scoped AUTO/APPROVAL/HYBRID execution with durable pause/restart, cancellation, compensating actions, new HRB admission on resume, approved route binding and no silent fallback.
- **P4 evidence/repair**: deterministic-first per-criterion proof, optional admitted semantic advisory, bounded replan, clear PARTIAL/BLOCKED/VERIFIED outcome and full provenance; the canonical gate alone may authorize closure.
- **P5 UX + controlled pilot**: Developer Agent pilot on a disposable branch with an immutable input commit, synthetic test task and no production write. After current-host PASS extend to Story/Screenplay -> FA3 native Video Editor / QuickClip / Creative Studio; keep their native project formats and human approval rules.

### Mandatory negative tests

Require: no self-approval; no direct provider/MCP/Secret Broker/HRB bypass; no unadmitted new AI participant; no shared private model language; no empty/forged proof; no premature `FINISH`; no infinite retry; no lease reuse after restart; no unauthorized model switch; no display-GPU automatic recruitment; no side effects from copied/hostile task text; no unreviewed donor installation; no claim of global current-host runtime admission from CI-only checks. Verify cancellation, provider outages, duplicate task delivery/idempotency, evidence mismatch, timeouts, conflict resolution, and revoked approval.

### Merge and promotion caveat

Many parallel donor PRs touch the same canonical JSON. Prior to merging, reconcile by exact normalized source key with the then-current `main`, retain every unrelated donor, regenerate required release/impact projections using governed repository tooling and run exact-head static CI. A green research/metadata PR is **not** current-host evidence, optional-provider admission or production promotion.


---

## Final implementation specification v1.0

Status: **FINAL TECHNICAL PLAN / IMPLEMENTATION PENDING**, 2026-09-28.
This appendix supersedes the high-level P0–P5 planning sequence above whenever a detail conflicts. It neither changes the canonical 175-capability model nor claims current-host closure or application production admission.

### A. Bounded product outcome and exclusions

Deliver a reusable, FA3-native **goal -> authorized work -> criterion-level proof -> bounded repair -> verified outcome** workflow to the existing Agent Workspace / Control Center. The user remains goal owner. Intake supports three authorization modes: AUTO, APPROVAL and HYBRID. AUTO means *only within a previously approved scope*, never automatic approval of a new operation, a new AI participant, a new budget, or a destructive action outside the signed policy.

In scope: explicit acceptance criteria, environment and source-of-truth hints, reuse assessment, hardware and policy preflight, typed plan compilation, approved task execution, pause/stop/resume, independent verification, bounded replan and inspectable provenance. First production-target pilot: Developer Agent working in a disposable, isolated workspace. Subsequent app consumers are adapters to the SAME goal contracts.

Explicitly out of scope: a new FA3 app, capability ID, architecture authority, global orchestrator, independent long-term memory, provider/model router, ad hoc GPU scheduler, proprietary upstream framework bundled by default, autonomous source ingestion that executes untrusted instructions, new AI participants selected by agents, any Unreal installation or runtime, a new video editor, or replacement of native creative project files.

The original 2026-09-21 user-provided article establishes the three authoring inputs **Goal, Acceptance Criteria, Context** and motivates autonomous plan/execute/verify behavior. This FA3 specification adds scoped authorization, full provenance and independent machine evidence. A semantic judge's confidence is NEVER authorization or independent proof.

### B. Existing authority map — required for every PR

| Concern | Existing FA3 owner | Goal-driven consumer obligation |
|---|---|---|
| Goal ownership, user constraints, user commitment | FA3 Coach; existing FA3 human-approval policy | Reference existing UserOwnedGoal, GoalConstraint, SuccessCriterion and ExecutionDelegationRequest. Coach remains PROPOSAL_ONLY and does not directly execute. |
| Task decomposition and specialist eligibility | FA3 Orchestration Director and Workforce | Deterministic hard filtering before optional Decision Fabric advisory; do not enlarge candidate or authorized participant sets. |
| Typed effects and tools | FA3 Unified Action Fabric + Central MCP Gateway | Every effectful step compiles to authorized, typed UAF action and gateway capability. |
| Cross-workflow durable state | Temporal | Sole global lifecycle authority; use existing workflow, signals, activities and event receipts. |
| Per-task execution | Agent Workload Runtime | Use FA3 AgentWorkloadTask, immutable Git input, default-deny network envelope, admitted runner and per-task limits. |
| Host devices and resource allocation | Hardware Discovery + HRB / ACCEL-GUARD | Deterministic compatibility and a fresh lease/admission when required, including resume. |
| Model, provider and runtime route | FA3-AUTH-MODEL-ROUTER-001 | Explicit admitted logical route -> authorized provider/runtime -> designated model -> LiteLLM data plane. No physical model pin in task and no silent fallback. |
| Language-based judgment | Decision Fabric, optional separately admitted Jev | Only advisory over a pre-authorized finite candidate set; semantic evaluation alone cannot pass an acceptance criterion. |
| Secrets and network access | Existing Secret Broker and security authority | Scoped projected credentials; no prompt, trace or source file contains secrets. |
| Reuse and outside sources | FA3 Reuse Discovery, Application Donor Index, Donor & Reference Registry, Skill Fabric | Mandatory deterministic preflight. Donor presence is not code/runtime admission. |
| Durable facts, proof and promotion | Original artifacts, FA3 Journal, canonical Evidence/Canonical Gate, existing approval/promotion authority | Persist criterion -> verifier -> immutable evidence reference -> result. Never self-approve a gate. |

Implementation must reuse these ownership rules even if an optional external agent framework becomes an admitted runner adapter.

### C. Proposed non-authoritative contract family

Proposed identifier **FA3-GOAL-EXECUTION-CONTRACTS-001**, an extension/consumer of existing Coach, Orchestration Workforce and Agent Workload Runtime contracts, NOT a new authority or capability.

**GoalIntent / GoalRevision:** immutable goal ID and revision digest; owner, application/workspace scope, original natural-language statement, explicit in/out-of-scope and forbidden effects; existing Coach commitment and human policy refs. Every revision change invalidates stale authorization, plans, acceptance receipts and evidence that depend on the changed claim. Persist original text as untrusted descriptive input, never an instruction to executor.

**GoalAcceptance:** stable criterion ID; precise expected observation and pass/fail semantics; verifier class (deterministic, approved external check, human sign-off, or semantic advisory plus independent corroboration); environment and artifact preconditions; independent verifier identity; required evidence kinds and minimum provenance. A criterion whose verification method is unspecified or non-falsifiable is INVALID, not silently downgraded to a narrative checklist. Preserve an optional human acceptance step separately.

**GoalExecutionPolicy:** AUTO/APPROVAL/HYBRID, exact signed scope and revision, action effect classes, tool allowlist, network envelope, approved agents/models/routes, time and cost/tokens/tools/fanout/retry budgets, cancellation conditions, required per-effect human approval and permitted recovery/compensation. Deny by default. Defaults use existing FA3 runtime policies; do not hardcode new global retry, confidence or cost constants.

**GoalPreflight:** links to FA3 ApplicationIntent, machine-readable reuse assessment, donor index impact, hardware audit, deterministic specialist eligibility, Security approval and runtime admission evidence; each field is an immutable or refreshable receipt tied to the same goal revision. Current-host admissibility is independent of donor status and CI reference results.

**GoalPlan:** a DAG of GoalStep records. Each step records criterion mapping, existing typed UAF action/AgentTask projection, input/output artifact contract, admitted candidate set, authorized AI participants, resource envelope, side-effect risk, verifier, idempotency key, compensation if meaningful, timeout, retry cap and approval dependency. An advisory provider may reorder/select from existing eligible candidates; it cannot introduce participants, abilities, action parameters or authority.

**CriterionEvaluation / GoalOutcome:** record the specific checker, input artifact and digest, execution/ref environment, unredacted-independent evidence stored through established authority, sanitized projection, outcome and reason codes. The aggregate state is NEVER a scalar LLM confidence. A goal is VERIFIED only when all required independent checks pass, original claims are not contradicted, and every required approval is valid for the exact goal revision and effect scope.

Required lineage across contracts: goal ID/revision -> criterion ID -> plan revision -> task/action ID -> runtime admission -> execution events -> original artifact digest -> verifier result -> canonical Evidence reference -> acceptance authority disposition.

Suggested file boundaries for implementation PRs, contingent on exact-main reconciliation: canonical/contracts/FA3-GOAL-EXECUTION-CONTRACTS-001.schema.json, src/fa3_goal_contracts.py, src/fa3_goal_plan_bridge.py, src/fa3_goal_acceptance.py, tests/test_goal_*.py. Reuse pre-existing interfaces before naming new modules.

### D. State machines and deterministic closure

Distinct states for the *goal* and for each *task*, so completed task does not imply completed goal.

Goal lifecycle (Temporal-owned): DRAFT -> VALIDATING -> PREFLIGHT -> PLAN_READY -> AWAITING_APPROVAL or RUNNING -> EVALUATING -> VERIFIED, PARTIAL, BLOCKED, FAILED, CANCELLED, or AWAITING_SIGNOFF. PARTIAL and BLOCKED may permit a new authorized revision; VERIFIED and CANCELLED are terminal for that revision. State transitions emit existing Journal/Evidence/approval references.

A task follows existing Agent Workload phases and legal transitions; never add an incompatible second task-state authority. Crash recovery, duplicate delivery, Temporal replay and checkpoint resume must not repeat a non-idempotent external effect. A durable checkpoint is claimed ONLY when its admitted runner actually supports APPLICATION, PROCESS or VM mode. Resumption revalidates policy, model route and fresh HRB authority.

STOP/CONTINUE: evaluate deterministic criteria first. Optional Decision Fabric can identify the next weakest unproven claim from the permitted set; non-admitted or unreachable Jev yields an explicit uncertainty/handoff, not an implicit fallback or a pass. A rejected/expired approval or missing verifier is BLOCKED. Failure to achieve an independently verifiable mandatory criterion is PARTIAL or FAILED according to established policy, never VERIFIED.

No autonomous alteration of acceptance criteria mid-run. The executor cannot edit the verifier or validation fixtures used to grade its own submitted output. If a changed goal requires a new verifier, that verifier must be independently approved and versioned.

### E. Execution workflow

1. **Intake**: collect objective, acceptance, context pointers, project-native format and human autonomy choice; deterministically identify missing/contradictory material requirements without initiating effects. If a safe bounded assumption is possible, mark it and stay inside the owner's policy; for unsafe ambiguity return structured human escalation.
2. **Discovery/preflight**: query the source-unique Donor Registry AND existing Reuse Discovery and the application donor index; record considered/rejected donor candidates. Hardware Audit is mandatory, including host constraints, CPU-only and display GPU rules. Check existing skill/runner/agent admission, exact authorized participants, current policy, available logical model routes and existing evidence truth. The planner cannot admit a new provider.
3. **Plan**: invoke the existing Director/Workforce to decompose into criterion-linked tasks after hard filters. Each task receives bounded resources, side-effect envelope, verifier and dependency. Run structural and policy checks before approval.
4. **Authorize**: obtain the correct existing human/security authority's grant for the exact plan revision and effects. AUTO must rely on a previously approved matching policy; APPROVAL pauses before specified actions; HYBRID combines both without hiding consequential actions.
5. **Execute**: Temporal orchestrates durable activities, UAF/MCP mediates actions, Agent Workload Runtime manages admitted task-local execution, HRB grants resources and Model Router resolves the approved route. Execute only approved actions; application-to-application handoff is allowed through audited existing gateways.
6. **Verify**: process original artifact truth and deterministic tests before any semantic advisory. Each criterion has a durable independent result and evidence ref. A criterion that requires human review goes to AWAITING_SIGNOFF rather than a proxy model approval.
7. **Repair/stop**: for failed criteria, choose only in-scope correction tasks, require idempotency/replay guarantees and re-run relevant acceptance and regression checks. Stop on success, a hard budget, exhausted admissible actions, policy change, provider/resource loss without an explicitly approved alternative, user cancellation or escalation.
8. **Close/inspect**: the existing acceptance/promotion authority issues the final outcome; present the concrete artifacts, per-criterion state, outstanding blockers, actual costs and provenance. Never generalize one pilot's current-host PASS to all providers, backends, workspaces or applications.

### F. Hardware Audit and operational non-interference

Planning, schema validation, deterministic checks and inspection must work on CPU-only hosts with 0 accelerators. Hardware discovery is vendor-neutral and reports physical/logical CPU topology plus supported vendor/runtime characteristics (Intel/AMD/NVIDIA/other; CUDA/ROCm/oneAPI/Vulkan/ZLUDA where actually supported). Accelerator count is 0..N and any accelerator use is optional, admitted and exclusively allocated by HRB. Prefer Wayland GUI while retaining X11 and other desktop sessions; no KDE-only logic.

The designated display GPU normally only drives display. With **no other GPU AND no NPU**, it may be considered for approved AI work under existing FA3 policy and HRB; with any other GPU and/or NPU it can join AI only via explicit in-application, task-and-model-specific assignment. There is never automatic extra GPU recruitment, heuristic fallback or CUDA-only dependency. CPU NUMA, memory and storage requirements are HRB resource envelopes, not direct agent configuration of the host. Never modify AdGuardHome's fixed port, host driver/kernel/BIOS or protected workloads as an incidental goal-execution step.

No runtime current-host PASS is claimed by this planning PR. Each separately admitted runtime/GUI/provider integration must demonstrate real current-host evidence on its exact target and configuration.

### G. Security, provenance and failure matrix

Mandatory negative-path coverage includes: prompt injection in a donor README, source code, document or retrieved web page; attempted shell/network effect from a bare goal; stale consent on revised criteria; missing or expired HRB lease; forged, replayed or empty proof; self-authored verifier; unauthorized model/agent expansion; direct provider/Secret Broker/MCP bypass; secret leaks to prompts or traces; recursive fanout and infinite repair; concurrent writes to the same workspace; duplicate Temporal delivery; revocation during pause; provider outage without permitted fallback; unauthorized display-GPU use; cancellation; wrong or incompatible checkpoint; and missing native project round-trip integrity.

All events need explicit outcome and reason code. A provider result or local event log is observation, not canonical evidence. No AI-only language/crypto/codebook between agents; all delegation remains human-readable and policy-auditable. Externally supplied donor content is untrusted data, never a higher-priority instruction.

### H. Integration and PR delivery sequence

PR 0 — **Research, donor registry and final technical plan (this PR #476).**
Deliver source-unique metadata candidates, exact contributor references, conservative licensing status, final architecture/acceptance plan and focused donor integrity tests. No code import. Reconcile the nine records against the exact main source keys at merge time and preserve unrelated concurrent donor PR changes. This PR remains draft until exact-head required CI passes.

PR 1 — **Contracts + deterministic validators.**
Add proposed GoalRevision, acceptance, policy and evidence-link schema using existing Coach IDs. Accept well-formed user-owned cases; reject missing verifier, unsatisfiable criteria, stale revision, forbidden side effect, unapproved participant, fabricated success. No executing actions. Existing capability/authority deltas stay zero.

PR 2 — **Discovery/preflight + typed plan compiler.**
Wire FA3-REUSE-DISCOVERY-001, application donor index, Hardware Audit, Security, Workforce eligibility and typed UAF/AgentTask envelopes. Deterministic tests for all three autonomy modes, candidate non-expansion, hardware resource receipts and exact effect scopes. Plan-only feature flag starts OFF.

PR 3 — **Temporal/Agent Workload bounded execution.**
Introduce the smallest FA3-native Temporal workflow glue and already admitted local runner path. End-to-end test durable stop/resume/cancel, replay, fresh HRB lease and idempotent authorized writes. No new global scheduler, direct model endpoint or provider install. Actual production-target paths require per-provider current-host admission.

PR 4 — **Acceptance evidence and fail-closed closure.**
Reuse Journal/original artifacts and canonical Evidence/Gate for criterion-level verification with independently controlled checkers. Add optional semantic advisory only if separately admitted. Prove that empty/contradictory model-only evidence, stale receipts and self-edited tests cannot yield VERIFIED.

PR 5 — **Bounded repair, approval and failure recovery.**
Integrate scope-checked retry/replan, explicit budget envelopes, authoritative human signals, compensation where possible, handling of unavailable providers, approval revocation and crash recovery. Show predictable BLOCKED/PARTIAL/FAILED results for unresolved cases.

PR 6 — **Control Center + Developer Agent current-host pilot.**
Add existing-surface GUI projections for goal, criteria, tasks, evidence, approvals, remaining budget, cancellation and blockers. First pilot uses a disposable immutable input Git commit and isolated branch, performs a small FA3 module change, runs existing and new regression tests and stops before writing to a protected branch. Run real approved AUTO, APPROVAL and HYBRID tests on a CPU-only path as well as suitable HRB-authorized hardware configurations; prove negative/rollback boundaries.

PR 7 — **Optional application adapters after evidence.**
Integrate the same contract family with Story/Screenplay, Prompt Creator, FA3 Video Editor, QuickClip and other Creative Studio/Research consumers as those modules are built. Retain the single FA3 video editor, native project.fa3video/.fa3clip and external Krita (.kra), Ardour sessions and other native projects. AI notes stay separately attributed; human approval and edit detection remain application-owned. App-specific current-host admission and native project round-trip gates precede activation.

Every PR has its own changed-scope acceptance evidence, a provenance-aware negative suite, canonical policy and 175-capability baseline conformance, Hardware Audit, exact-head CI and no hidden runtime promotion. Avoid gating unrelated feature delivery behind an optional upstream project's readiness.

### I. Final acceptance matrix and pilot definition of done

| Check | Proof demanded | Required outcome |
|---|---|---|
| G-01 | GoalRevision and all mandatory criteria are well-formed and owner-bound | Invalid/ambiguous dangerous input rejected before execution |
| G-02 | Source-unique donor lookup and reuse assessment receipt | Every new/materially changed consumer completes Reuse Discovery |
| G-03 | Hardware Audit + HRB path | CPU-only success and correct optional accelerator authorization |
| G-04 | Closed model/agent/tool topology | No independent model addition, backend bypass or unauthorized participant |
| G-05 | Valid AUTO, APPROVAL, HYBRID traces | Every effect matches explicit authority and exact plan revision |
| G-06 | Durable replay, stop and restart | No repeated irreversible effect; fresh lease on resumption |
| G-07 | Criterion-by-criterion independent check | Green test logs, artifact digests and source-grounded refs |
| G-08 | Adversarial and negative tests | Injected instructions/forged evidence/self-approval never pass |
| G-09 | Bounded repair and cancellation | No runaway loop, right compensation and explainable BLOCKED |
| G-10 | Final approval/provenance projection | Only existing acceptance authority can issue VERIFIED; no self-declared completion |
| G-11 | App-native project integrity where applicable | No lossy replacement of the owner application's project format |
| G-12 | Current-host and release governance | Exact-head CI + appropriate real execution proof, no document-only promotion |

The Developer Agent pilot fixture: from a pinned, disposable FA3 commit, implement one small synthetic module feature in an isolated branch with two deterministic acceptance tests, run regression checks, provoke one intentional test failure and bounded repair, force one cancellation/restart, deny one unauthorized model/tool request and one forged proof, then produce a criterion-to-artifact-to-verifier-to-Evidence trace. Zero prohibited side effects; no write to protected main.

### J. Observability and outcome quality

Record whether criteria were independently verified, how many repair cycles occurred, time/cost/token/tool usage versus the approved budget, reasons for escalation, duplicate-effect prevention, approval latency and false-completion attempts detected. These are engineering diagnostics, not an AI-authored success score. Langfuse is optional noncanonical telemetry/UX; Promptfoo is optional offline evaluation reference. The authoritative artifact graph remains FA3-native.

### K. Exact PR #476 outstanding release-gate repair

The first CI execution on head 6d9d023dd6f9d23830f75cee7eafde4fb2e2e97f recorded **17 successful workflows and 2 failing** (Permanent Canonical + Promotion Gate and Reuse Discovery Gate). Both failures contain release-projection test failures; other focused donor inventory checks passed. The reported blockers are an unchanged projection manifest containing the old canonical donor-registry Git blob and two new unmanifested files (this curation document and its regression test).

This failure MUST NOT be bypassed or declared benign. After the final documentation edits are committed, use the existing governed scripts/fa3_reconcile_release_projection.py (or the currently prescribed release projection generation workflow) on a **clean committed snapshot**, commit the regenerated canonical projection, run the complete exact-head CI again, and review all new errors independently. If concurrently merged donor PRs alter main, first reconcile every source-unique donor and regenerate the release projection **after** that reconciliation. The release projection can only represent an immutable pre-projection commit/snapshot; do not hand-edit manifest hashes to force a PASS. Static research PR merge-readiness, runtime production admission and global release promotion remain distinct states.
