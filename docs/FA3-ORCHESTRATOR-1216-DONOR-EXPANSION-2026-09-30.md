# FA3 Orchestrator v2.1 — 1216-donor-registry functional expansion

**Design status:** PROPOSED FOR OWNER REVIEW; no runtime integration, upstream code import, provider admission, current-host PASS, merged PR or deployment claimed.  
**Published planning source:** protected `main@653b1d0ba10fe8f584e66d0e3b7c054f8ec3ef71`, donor registry blob `56d0d69096f1b4b8a504d3c838bc2feb88c95a5e`. Registry holds **1216 records, 1216 distinct normalized source keys, 1216 distinct donor IDs**; donor-serialization, application-donor-inventory, capability-175 and release-projection checks succeeded on the exact cited main commit. Unmerged or pending donor PRs are excluded.  
**Existing detailed F1–F10 specification:** [FA3-ORCHESTRATOR-FUNCTIONAL-DONOR-EXPANSION-2026-09-29.md](FA3-ORCHESTRATOR-FUNCTIONAL-DONOR-EXPANSION-2026-09-29.md). This document updates its governance assumptions and is the **current integrated F1–F18 expansion plan**. Its historic registry-count/PR-status prose is superseded by this source-bound v2.1 preflight.

## A. Verified implementation boundary

The merged source contains canonical `FA3-ORCHESTRATION-WORKFORCE-001`, `src/fa3_orchestration_workforce.py`, the source-only `src/fa3_goal_execution.py`, task-local `FA3-AGENT-WORKLOAD-RUNTIME-001`, CAP-070 Federation contracts, FA3 Agent Sandbox, Skill Fabric, a scoped Browser Session contract, existing Work Management projection and canonical Reproducibility Fabric.

**Do not infer completion from historical PR numbers.** #392 (Objective Coordination) and #427 (Agent Collaboration) are CLOSED **UNMERGED**, with their proposed `src/fa3_objective_coordination.py` and `src/fa3_agent_deliberation*.py` absent from published main. Their archived designs are references, not admitted runtime. Any replacement must start with a fresh owner-approved design and the current canonical contracts, not silently revive or apply stale PR branches. #496 (independent goal evidence), #410 (retroactive Software Coexistence) and parts of Skill Fabric remain open and cannot confer runtime or GUI closure.

The Director may decompose, compile plans, make bounded pre-authorized recommendations, coordinate, report blockers and request approval. **Temporal alone** owns global durable workflow state; **UAF + Central MCP Gateway** mediate effectful actions and tools; **Security Governance/PKI/Secret Broker** control permission, identity and secrets; **HRB** owns device, host and lease admission; **Model Router** owns model/provider/runtime routing; **Journal, immutable artifacts and canonical Evidence/Gate** alone determine authenticated facts and promotion. Decision Fabric is advisory after deterministic hard filters. The CPU-only, vendor-neutral zero-to-N-accelerator baseline, device safety envelope and explicit display-GPU exception policy are unmodified.

## B. Source-bound donor review

Only records present in the published, exact-blob canonical registry above are used. Registry presence is neither code-copy approval nor provider/runtime admission.

| Source (current registry status) | FA3-selective value | Existing consumer; forbidden duplicate |
| --- | --- | --- |
| Untrivial-ai/agent-orchestrator (CANDIDATE) | Project-specific work sessions, Git worktree + PR/CI feedback | Director / Developer Agent; not its daemon |
| jordanhindo/beadboard (CANDIDATE) | Addressed ACK, TTL workspace collision hints, blocker graph | Existing AgentMessage / CAP-070; not Beads/Dolt/bb-pi |
| poponline63/north-star (CANDIDATE) | Definition-of-done, deterministic-first acceptance, unproven criterion | Goal Execution / Evidence; no Jev approval |
| temporalio/sdk-python (CANDIDATE) | Signal, retry, suspend, cancel and compensation | Existing Temporal only; no second workflow engine |
| OpenHands/software-agent-sdk (CANDIDATE) | Ephemeral coding workspace and inspectable agent events | Existing Agent Workload; no direct LLM or tools |
| NVIDIA/OpenShell and NVIDIA/SkillSpector (CANDIDATE) | Scoped runtime policy and skill inspection | Existing Sandbox / Security / Skill Fabric; no second authority |
| Dagger (CANDIDATE) | Input-keyed incremental reuse, dependency invalidation | Existing Derived Artifact Lineage; no Dagger scheduler/cache owner |
| SkyPilot (CANDIDATE) | Data-locality and transfer-cost **advisory** | HRB and Artifact Fabric; no provisioning/cloud/payment authority |
| Inngest (CANDIDATE, original project key) | Fair queueing, debounce/backpressure, concurrency-key patterns | Existing Temporal/Workforce/HRB, no Inngest event hub |
| NVIDIA NeMo Agent Toolkit (CANDIDATE), Promptfoo (CANDIDATE), TestZeus Hercules (CANDIDATE), Toxiproxy (CANDIDATE) | Telemetry profiling, deterministic/adversarial/GUI/network tests | Existing Observability, Verification and current-host lab |
| pydantic/pydantic-ai and CUE (CANDIDATE) | Typed deferred actions and cross-constraint validation | Canonical contract validators / UAF; no SDK direct-provider path |
| AgentSwarms (CANDIDATE) | Visual **versioned** workflow draft snapshot | Existing Work Graph / Qt6 Control Center, no second graph engine |
| Pixar Chook (CANDIDATE) | Isolated webhook handlers and reproducible trigger fixtures | Existing FA3 event/JOURNAL/UAF boundaries, no webhook control plane |
| vectorize-io/hindsight and cytostack/openwolf (ACCEPTED_REFERENCE) | Permission-filtered recalled context + source-linked handoffs | Existing Memory/Knowledge + Journal; no new memory authority; openwolf AGPL code copy not approved |
| garrytan/gstack (ACCEPTED_REFERENCE) | Evidence fingerprints, freeze guard for approved decisions | Existing Evidence/Decision/Git approvals |
| karpathy/llm-council (CANDIDATE) and HarnessRouter/SystemOneHarness (ACCEPTED_REFERENCE) | Sealed independent proposals and bounded semantic challenge | Existing Decision Fabric; no synthetic independent verifier or automatic consensus authority |
| browser-use/browser-use-pi (ACCEPTED_REFERENCE) | Session continuity, HITL, action recording | Already canonical Browser Session contract; no silent login or browser profile export |
| showlab/MovieAgent, ZenStory drama-skills, ASWF/OpenCue (CANDIDATE) | Scene-shot-asset/crew handoff, continuity locks, render job dependencies | Native creative project graph / FA3 render master-slave; no new renderer/scheduler |
| johnvouros/skillmaxxing (CANDIDATE) and microsoft/mcp-gateway (ACCEPTED_REFERENCE) | Phase-aware skill checks and scoped session-aware MCP routing | Existing Skill Fabric / Central MCP Gateway; no duplicate gateway |
| modelcontextprotocol/specification and modelcontextprotocol/inspector (CANDIDATE) | Versioned protocol tool contract and negative interoperability fixtures | Existing MCP conformance/gate, no direct agent-server bypass |

Upstream licenses are metadata declarations only. Unknown, AGPL, TOST and transitive conditions block source import until individually audited. This plan uses **selective FA3-native design patterns** and does **not** add or reclassify donors, alter the fixed 175-capability baseline or admit new providers.

## C. Unified feature catalogue, F1–F18

### Carry-forward and strengthened F1–F10

- **F1 Project-aware supervision:** each work unit has immutable project/task/goal revision, approved participants, workspace, original commit/artifact digests, and PR/CI/reviewer refs. Failed CI becomes a typed draft for the same owner, not unapproved execution.
- **F2 Reliable typed handoff:** ACK-required HANDOFF/BLOCKED, independent consumer cursor, replay-safe IDs, signed CAP-070 peer messages, bounded hop/expiry; ACK is not completion or permission.
- **F3 Protected parallel work and continuation:** one mutating task per isolated worktree/overlay, distinct collision claim vs HRB lease, single integration committer; resumption revalidates Security and HRB.
- **F4 Criterion-level goal completion:** owner-authored observable acceptance, independent checker, immutable proof, targeted correction; a worker, advisory model or GUI cannot mark VERIFIED.
- **F5 Fair bounded scheduling:** per-project/application priority/concurrency and bounded queue/aging/backpressure; derived advisory to Temporal and HRB. Noninterruptible work is not preempted for urgency.
- **F6 Runtime least privilege and skill admission:** existing Sandbox and Skill Security Inspection enforce immutable task/skill snapshot, allowlisted paths, process/network scope, secrets and tool permissions.
- **F7 Provenance-bound incremental recomputation:** affected transitive subgraph only; reuse original artifacts and evidence with exact goal/input/config/source digests; nondeterministic media is never considered equivalent just from a repeated prompt.
- **F8 Transfer/locality comparison:** explain where a task could run, expected data bytes, measurement age, time/cost and approved alternatives. **Only HRB** can admit placement, and Artifact Fabric handles movement.
- **F9 Operator and performance observability:** per-task spans from existing Journal/Observability plus cost/time estimates clearly marked, not a separate trace or evidence authority.
- **F10 Fault and GUI qualification:** isolated Toxiproxy negative cases, Promptfoo-style adversarial regressions, real backend Qt6/Wayland + X11 GUI tests, two *distinct physical hosts* for CAP-070 production proof.

### Newly selected F11–F18

**F11 — Typed deferred actions and hard cross-contract validation (Pydantic AI + CUE patterns).** Add `DeferredActionProjection` to the existing UAF/Goal preflight: `goal_revision, task_id, action_schema_version, action_id, effect_class, expected_input/output_schema, external_approval_ref, max_wait, expiry, idempotency_key`. A PLAN or typed draft grants **zero authority**. An APPROVAL/HYBRID step may durably await the **existing human policy** with Temporal; after approval, fetch a new scope-bound UAF/Security/HRB/runner receipt, validate output against existing JSON-schema contracts and only then continue. Compare multi-constraint combinations (budget, destructive effect, participant, host, resource, dependency) as FA3-native checks; CUE/Pydantic are pattern references, not required dependencies.

**F12 — Versioned visual workflow drafts and what-if mode (AgentSwarms + SkyPilot + HRB read projections).** In the **existing Control Center** provide a versioned, diffable **non-authoritative plan graph** with explicit task, dependency, resource demand, human checkpoint, approved host alternatives, approval provenance and estimated critical path. Simulate `WHAT_IF` queue priority, removed host or changed input without dispatching, leasing, mutating, simulating authorization or claiming current-host evidence. Only owner-reviewed/authorized snapshots may be compiled to UAF/Temporal. Prefer CPU-only when eligible, keep network/render paths optional.

**F13 — Signed change-triggered dependency invalidation (Pixar Chook + Dagger + gstack patterns).** Transform authenticated, allowlisted change/webhook notifications into **typed proposed graph updates** with `event_id, source_id, source_revision, artifact_digest, correlation_id, affected_nodes, required_approvals`. Lossless Journal preserves original events; the Director deduplicates notifications without dropping Security/approval events. Invalid or untrusted external input cannot mutate code, scope, criteria, provider set, timeline or approved scenes. Dependency impact emits reviewable per-node stale/ready flags; only UAF/Temporal perform authorized work.

**F14 — Provenance- and permission-bound project knowledge (Hindsight + OpenWolf).** Existing Knowledge/Memory Fabric provides project-local read-only recall capsules, keyed to the authorized goal revision, scene/shot identity, original file digest, source consent, approval status, expiry and exact task purpose. Reuse known failure patterns and previous approved decisions without leaking information across unrelated projects or agents. Distinguish user facts and original artifacts from model summaries; conflict/expired records trigger human review, not hidden memory repair. Reuse existing `TaskContinuation` of F3 instead of another memory database.

**F15 — Independent challenge and disagreement handling (LLM Council + SystemOneHarness + existing Decision Fabric).** For high-impact **review proposals** request bounded independent agent drafts, seal until the allowed reveal barrier, compare contradictions, include a human-readable objection window and cite original artifacts. All participants are previously authorized; repeated use of the same underlying evidence/model is not falsely presented as independent. The decision engine may advise but **never authorizes**, verifies its own output or changes the accepted candidate set. Because #427 closed unmerged, phase/state contracts and executable integration must be revalidated and newly materialized on the then-current main.

**F16 — Authorized persistent browser work (browser-use-pi + existing Browser Session contracts).** For a task requiring web interaction, create or borrow only approved scoped tab leases (`origin, permitted_action, TTL, user_assistance`). Human login, OTP, CAPTCHA, payments and protected consent require first-class human handoff. Mask sensitive screenshot/log regions and prohibit cookie, profile or token export. On origin change or stale observation, revoke, re-observe and reauthorize. A browser session cannot directly bypass UAF/MCP or self-assert completion. No new desktop/browser control plane.

**F17 — Production-native scene/shot/crew/render coordination (MovieAgent + ZenStory + OpenCue).** The production graph links Story/Screenplay `scene_id/revision` to approved shot plan, location/props, character/continuity constraints, source prompt, asset/version, native editing timeline, sound/subtitle jobs and render work batches. Director schedules only dependency-ready work; changed scene or style invalidates exactly dependent downstream nodes and presents human approval diffs. Optional FA3 master/slave LAN renderer may use **only explicitly enabled hosts** and normal HRB leases; keep `.fa3video`, `.fa3clip`, `.kra`, audio/DCC native project files and original editable layers. Credits metadata remains Story-owned. No upstream paid rendering dependency or unapproved Unreal install.

**F18 — Phase-aware governed skills and MCP interoperability (skillmaxxing + SkillSpector + Microsoft MCP Gateway + MCP upstream reference).** Bind each task phase (`RESEARCH, PLAN, REVIEW, IMPLEMENT, VERIFY, HANDOFF`) to a **pre-admitted exact-byte Skill Fabric snapshot**, caller identity, AI participant set and lease expiry; permissions never grow by transition or downstream subagent request. Run phase-transition negative tests for unauthorized skill promotion, forged activation, injection, stale context, tool-schema mismatch, unsupported MCP protocol and server identity change. Central MCP Gateway alone negotiates and routes admitted tool capabilities; optional Inspector-like fixtures are CI-only.

## D. Concrete end-to-end flow

1. Owner approves goal revision, scope, acceptance, responsible application, authorized AI participants and approval policy; plain-language text is untrusted.
2. Fresh Reuse Discovery from the **published exact main** donor registry, existing application donor index and admissible current-host providers; metadata candidates never become auto-activated dependencies.
3. Hard eligibility check: Security/PKI -> UAF action schema -> existing agent and Skill Fabric policy -> Model Router -> HRB compatibility. Decision Fabric may advise **only within** pre-authorized alternatives.
4. Director compiles a versioned typed goal-to-project dependency view. Show dry-run impact/critical path/transfer estimates for human approval without fake receipts.
5. Authorized UAF action starts the sole Temporal workflow; task-local Agent Workload and signed CAP-070 delegate to admitted CPU-only or explicitly approved accelerators/hosts.
6. Existing Journal, TaskContinuation, original artifacts, app handoffs, HRB/Model Router receipts and workflow events populate F1–F18 projections. No external app is a new authority.
7. Runtime errors become typed blockers; bounded compensation, valid retry or human review, never infinite loops or permission growth.
8. Existing independent Evidence/Gate checks **each criterion** against the exact revision and distinct verifier and only it can promote VERIFIED. Approved immutable results remain available for exact-provenance incremental reuse.

## E. Stage-gated implementation roadmap (requires separate owner approval after this design)

- **P0 / Fresh source preflight:** pin verified published registry blob and main SHA, record new ApplicationIntent and ReuseAssessment; require exact-head donor readiness, main integrity, no use of unmerged donor additions, deterministic 175/authority tests. No donor registry mutation in this work.
- **P1 / Contracts and missing foundations:** extend existing Goal, Workforce and Work Management child contracts for F11/F12, with explicit non-authoritative state; materialize Objective Coordination and Collaboration from current base because archived #392/#427 were not merged. Gate: cycle/conflict/replay and schema negatives.
- **P2 / Event, memory and context:** implement F13/F14 from authorized Event/JOURNAL, Knowledge and Artifact Fabric read paths; audit source and permission cross-boundary. Never create a second event, memory or content-store authority.
- **P3 / Safe task actions:** implement F11/F16/F18 on existing UAF, Temporal, Sandbox, Skill Fabric, Browser Session and MCP Gateway; integrate only current-host admitted providers/runners.
- **P4 / Independent deliberation:** materialize F15 new current-base contract and source runtime, test sealed independent drafts, objection handling, evidence and human intervention, with no autonomous acceptance.
- **P5 / Media and multi-host:** materialize F17 in the existing creative and master/slave render work graph; prior F7/F8 ensure versioned invalidation, transfer plan, CPU-only baseline, native project files and no unauthorized host/device activation.
- **P6 / GUI and planning:** F12 graphical work graph, F1/F9 monitoring and F5 priority impact in the existing Qt6 Control Center; Wayland-first, X11 fallback; read-only projection until user-authorized UAF intent.
- **P7 / Verification and rollout:** source/test/fixture positive and negative, fail-closed Hardware Audit, Software Coexistence #410 retroactive checks, isolated fault test, real CPU-only current-host workflow, physical Qt6 GUI qualification and distinct two-host CAP-070 E2E. Full Canonical/Reuse/Release exact-head gates after any implementation PR, preserved historical evidence.

## F. Extended required negative tests

Keep F1–F10 original T01–T16 tests. Add:

| ID | Input | Expected fail-closed result |
| --- | --- | --- |
| T17 | Deferred tool response arrives after approval expired or goal revised | DENY; require fresh approval and receipt |
| T18 | Proposal mixes independently valid but mutually contradictory resource/effect/policy constraints | No executable DAG, report precise conflict |
| T19 | What-if graph requests disallowed model/host/tool | Denied alternative; simulation confers no rights |
| T20 | Duplicate valid webhook after an approved scene revision | Preserve event record, idempotent proposal and no duplicate work |
| T21 | Untrusted webhook contains tool instructions, modified signature or unknown source | Quarantine; no UAF side effect |
| T22 | Retrieval capsule belongs to another project or has stale source digest | Redacted or denied, no silent answer contamination |
| T23 | Two challenge agents share same underlying evidence/model and claim independence | Expose shared provenance; no independent-verifier receipt |
| T24 | High-impact review unresolved objection or reviewer timeout | HUMAN_REQUIRED or bounded policy fallback, never self-approve |
| T25 | Browser tab changes origin or requests cookie/token export | Revoke or deny; human handoff for login/OTP/payment |
| T26 | Creative scene change after locked shot/audio approvals | Mark only true dependents stale; require reapproval, preserve old version |
| T27 | Remote render node has insufficient lease or network failure | Explicit BLOCKED/RETRY, no silent new slave or hardware tuning |
| T28 | A skill phase changes with expired snapshot/lease or unadmitted MCP tool | DENY, report exact mismatch, no secret leakage |
| T29 | Cross-host output produced by local loopback fixture | Never count as two-host production PASS |
| T30 | CI static PASS but physical GUI/runtime evidence missing | PENDING_CURRENT_HOST; no production release promotion |

## G. Release and change discipline

This file updates the **plan and donor reuse mapping**, not executable orchestration code. No new provider, source-code dependency, machine host setup, donor registration or architecture authority is introduced. The 175 capability baseline is preserved and provider count remains dynamic. All new material code requires an immutable, **owner-approved plan**, fresh exact-published-registry Reuse Assessment, new scoped PRs and exact-head gates. Candidate/reference donor source code remains blocked until separately owner-approved and license/third-party dependency/security/coexistence reviewed. Even accepted references are not automatically installed.

**Plan delta from 2026-09-29:** updates previously stale #459/#549/#392/#427 assumptions to exact published 1216-registry source; adds F11–F18 (deferred actions, visual what-if, signed triggers, permission-scoped recall, bounded independent challenge, governed browser, production shot-to-render, phase-aware skill/MCP), T17–T30, and staged acceptance. Supersedes only the old plan's source counts and historic PR claims; F1–F10 remain as specified.
