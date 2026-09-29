# FA3 Orchestrator — selective functional donor expansion and implementation plan

**Date:** 2026-09-29  
**Status:** IMPLEMENTATION PLAN / DONOR METADATA CAPTURE; runtime adoption and physical current-host qualification NOT CLAIMED.  
**Starting point:** Donor Registry consolidation PR #459 (550 unique entries before this branch); this branch adds exactly two new source-unique candidates, `dagger/dagger` and `skypilot-org/skypilot`, for **552** entries on the stack. This is **not** the merged main registry count.  
**Active baseline:** 175 capability IDs; provider count dynamic; authority delta = 0. Historical 143 references remain historical, not the active release baseline.

## 1. Functional outcome

Extend **the existing** FA3 Orchestration Director, Workforce, Goal Execution, Objective Coordination, Agent Workload Runtime, CAP-070 Agent Federation, Priority Manager, Skill Fabric, Security Governance, Artifact Fabric, Observability, Verification and Control Center into one governed orchestration flow:

`owner's goal -> acceptance contract -> deterministic Workforce eligibility -> versioned objective/dependency projection -> typed authorized UAF plan -> Temporal-owned durable execution -> scoped Agent Workload / federation -> original-artifact provenance -> independent canonical Evidence/Gate -> bounded correction or verified close`.

The Director decomposes, recommends, delegates and aggregates; it **cannot** authorize its own actions, mutate the single durable lifecycle, allocate resources, choose physical model/provider, run tools outside the MCP gateway or self-attest evidence. Temporal is sole durable workflow owner; UAF is the typed execution boundary; HRB is sole host resource and placement authority; Model Router is sole model/provider/runtime routing authority; Security/Identity/PKI, Central MCP Gateway, Secret Broker, Journal, Evidence/Gate, Reuse Discovery and Donor Registry retain their current scopes. CPU-only 0..N accelerators remain valid; no hardware mutation or automatic display-GPU recruitment.

## 2. Donor disposition: reuse rather than duplicate

All entries below must be queried through the existing central Donor & Reference Registry and Reuse Discovery for material orchestrator changes. `CANDIDATE` means research, not source-code reuse or provider/runtime admission. For pre-existing entries, preserve their ID, source key, historical data and status.

| Source | Registry disposition | Selected function | Existing FA3 consumer | Explicit non-adoption |
| --- | --- | --- | --- | --- |
| Inngest (`project:inngest`; resolve source equivalence before normalizing) | Existing CANDIDATE | Concurrency-key limits, fair bounded queue, event debounce/batch, backpressure | Workforce / Priority Manager, Temporal, HRB | No Inngest event bus, task registry or workflow authority |
| NVIDIA/OpenShell | Existing CANDIDATE | Fine-grained execution-time network, filesystem and process policy observation | Agent Sandbox, Security Governance, MCP Gateway | No parallel OpenShell gateway, broker or privileged authority |
| NVIDIA/SkillSpector | Existing CANDIDATE; existing FA3 inspection contract already references it | Immutable skill snapshot, static prompt/script/dependency/permission inspection and follow-up review | Skill Fabric / Skill Security Inspection | No direct auto-install, self-approval, or scanner as authority |
| cytostack/openwolf | Existing ACCEPTED_REFERENCE | Version/digest-bound compact context handoff, prior issues and decisions | Context Fabric, Journal, Workforce | No second memory/telemetry authority; AGPL source copy requires separate legal review |
| boadij/pi-herdsman | Existing ACCEPTED_REFERENCE | Async task continuation, narrowing of subagent delegation, explicit recovery | Developer Agent Coordination, Agent Workload, CAP-070 | No independent Pi agent runtime or global delegation owner |
| dagger/dagger | **New CANDIDATE**, pinned `fdb30c1d1b03b6ff22e90b30f9997c7e0b63e6e0`, upstream Apache-2.0 declaration | Input-keyed incremental execution, affected-subgraph recompute, artifact provenance, typed traces | Objective Coordination, Derived Artifact Lineage, creative and developer pipelines | No Dagger engine or second global cache; separate license/dependency review before copying |
| Shopify/toxiproxy | Existing CANDIDATE | Isolated fault injection: disconnect, latency, corruption/timeout, delivery ordering | CAP-070 current-host and Verification Fabric | Never apply proxy faults to normal host production traffic |
| test-zeus-ai/testzeus-hercules | Existing CANDIDATE; upstream AGPL-3.0 declaration | Repeatable UI/API workflow scripts and artifact/screenshot/test receipt patterns | GUI E2E / Verification / Evidence | No hard dependency or unreviewed AGPL source import |
| NVIDIA/NeMo-Agent-Toolkit | Existing CANDIDATE | Span-linked token/time/cost profile, bottleneck and ETA estimates | Observability, Priority Manager, Decision Inspector | No second tracing store, NVIDIA-only system path or profiling authority |
| skypilot-org/skypilot | **New CANDIDATE**, pinned `2df7061d22d6799339736659ca007bdd6ab49625`, upstream Apache-2.0 declaration | Host locality, data transfer and runtime-time tradeoff estimates; approved alternatives | Director, CAP-070, HRB read-only observation, Artifact Fabric | No SkyPilot scheduler, cloud provisioning, automatic paid providers or placement authority |

The Dagger and SkyPilot pins are upstream source snapshots observed during this research, **not immutable accepted vendor releases or FA3 runtime qualification**. Resolve all third-party license/asset/transitive obligations at any proposed code import. Upstream feature marketing is not conformance evidence.

## 3. Cross-component contracts and concrete behaviors

### F1 — Project-aware execution projection (Agent Orchestrator + existing FA3)
Extend existing Workforce/Developer Agent and Work Management **read models** with `project_ref, goal_id, goal_revision, task_id, authorized_agent_id, workspace_ref, input_commit, artifact_refs, source_digests, PR_ref, CI_run_refs, reviewer_refs`. All data derive from existing registered producers; no new persistent project, issue or workflow authority. CI failure and review requests return to the **same authorized owner/task** as a typed UAF draft; no direct unapproved rerun.

### F2 — Reliable addressed communication (BeadBoard + existing AgentMessage)
Use existing `AgentMessage, AgentMessageCursor, CoordinationEvent, AgentDelegation` and CAP-070 signed federation envelopes. Categories `HANDOFF, BLOCKED, DECISION, INFO`; require ACK for HANDOFF/BLOCKED, per-consumer cursor, message digest, expiry, bounded hops and replay-safe IDs. ACK proves receipt, **not** execution, resource authority or VERIFIED completion. Invalid identity, duplicate ID with changed payload, expired messages and unauthorized recipient fail closed. Each machine advertises approved application capabilities through existing discovery; remote execution must meet peer identity, UAF, Security, runner/provider and remote HRB admission.

### F3 — Safe parallelism and continuity (OpenWolf / Pi Herdsman)
Maintain distinct `work_item`, `AgentWorkloadTask`, workspace and HRB resource-lease identities. Each mutable developer task uses its own protected Git worktree/isolated overlay; one integration committer serializes repository mutations. Optional task-local workspace claim TTL is a collision hint, **never** HRB permission. On agent restart/context exhaustion, derive `TaskContinuation` as a typed projection of the current task, current commit/artifact digests, performed steps, evidence, unresolved issues, approved remaining budget and next authorized action; transmit via existing secure messaging. A stale heartbeat alone never grants takeover. Revalidate authorization, runtime and fresh HRB lease before resumption.

### F4 — Deterministic-first goals and bounded repair (North Star / Goal Execution)
Extend existing `FA3-GOAL-EXECUTION-CONTRACTS-001` and Objective Coordination #392: owner-written acceptance criteria -> criterion/verification mapping -> dependency-aware tasks -> original evidence -> canonical verifier. Record the **specific unproven criterion**; rerun only affected tasks. Semantic advice, model confidence and worker-written PASS are non-authoritative; all mandatory criteria and human approval gates must pass canonical Evidence/Gate. Replans cannot expand permissions, AI participant set, cost, fanout, side effects or model route.

### F5 — Controlled queue and workload pressure (Inngest patterns)
Implement only **advisory and permitted orchestration** with existing Temporal/work queues and HRB admission: bounded per-project/tenant/application/host concurrency, quota awareness, fair queue aging, backpressure, non-starving urgency, risk-class priority, safe debounce of replaceable project-change events. Never coalesce lossless security/approval/evidence/history events, and never interrupt a non-checkpointable workload. Produce an explicit `SchedulingImpactProjection` with observed-versus-estimated distinction; actual resource allocation/placement is HRB-only. Prove CPU-only operation and display-GPU rule.

### F6 — Runtime least privilege and skill supply chain (OpenShell / SkillSpector)
Extend `FA3-AGENT-SANDBOX-001` and `FA3-SKILL-SECURITY-INSPECTION-CONTRACTS-001` only: admitted sandbox receives scope-bound policy and immutable skill/source digests; default-deny egress, explicit path and process allowlists, scoped Secret Broker projection, validated MCP destinations. Policy violation emits auditable block and mandatory human escalation when needed. Reinspect skill changes and revoke stale receipt. Optional scanners can supply findings but never authorize/override mandatory static rules; no proprietary/unapproved hard runtime requirement.

### F7 — Incremental invalidation and reproducible reuse (Dagger patterns)
Reuse existing Derived Artifact Lineage and Objective Coordination dependency graph. A `DerivedWorkReuseCandidate` is bound to input artifact/commit digests, relevant scene/layer revision, execution code+skill versions, tool settings, model route/provider/model identity **where result-affecting**, security/policy context and original immutable evidence. The graph identifies the **transitively affected subgraph**, not arbitrary global rebuilds. Reuse existing validated outputs only if contracts and evidence remain applicable to the exact goal revision; nondeterministic generation may reuse a preserved artifact but never infer equivalence from matching text prompts alone. Expiration or contradictory evidence invalidates reuse and propagates to dependents.

### F8 — Host/data locality advisory (SkyPilot patterns)
Read current approved host/app inventories, expected artifact byte counts, historical or measured bandwidth, data locations and verified HRB capability envelopes. Estimate alternatives: move an artifact, execute near data, or wait for an approved machine; show transfer-time/egress cost and confidence/age of inputs. The plan is advisory. A final remote action requires current Security/UAF, exact host admission and Artifact Fabric transfer receipts; no silent alternate host, cloud/API purchase, model, GPU or provider activation. Unknown bandwidth yields UNKNOWN estimate rather than a fabricated score.

### F9 — Connected performance and operator UX (NeMo Agent Toolkit / existing Observability)
Derive per-task and per-goal read-only OTel-style projections: spans for delegation, queue wait, approval, model route, HRB lease, tool call, handoff, evidence check and approved repair. Persist durable facts in existing Journal and Evidence; cost/time estimates are identified as models, not verified facts. Control Center embeds Work Graph, Workforce, Hosts, Priority, Evidence and Activity views. It must never show RUNNING/VERIFIED/CONNECTED without authenticated source state or grant direct provider authority.

### F10 — Adversarial network + GUI validation (Toxiproxy / TestZeus / existing Promptfoo)
Isolated fault tests cover lost ACK, duplicate/out-of-order delivery, restarted Temporal workers, broken transport, host disappearance, stale lease, blocked dependency and recovery after offline GUI. Native Qt6 Wayland and X11 GUI tests must inspect real backend-driven state; browser-only tests cannot prove native GUI. Store raw test artifacts/digests; actual Evidence authority authenticates final receipts.

## 4. Dependencies and ordered implementation work packages

**P0 — Registry and shared infrastructure.** Losslessly reconcile this branch with #459 and all newer donor PRs by exact normalized keys; preserve pre-existing record order/history. Finish #459 same-key Pixar review taking #523 Unreal policy reversal into account. Repair shared `current_host_batch_orchestration` integrity issue before global CI current-host claims. Reconcile Software Coexistence #410 retroactively, current Canonical release projection, Reuse Discovery and reference gates on exact head. Historical evidence snapshots are immutable.

**P1 — Non-authoritative contracts.** Refresh ApplicationIntent and ReuseAssessment for the material Orchestrator/Objective Coordination/Agent Sandbox/Skill/Artifact/Verification changes. Define typed projections for F1–F9 using **existing** contract families; forbid new independent stores, queues and authority. Start with deterministic fixtures, fail-closed schema/compatibility tests.

**P2 — Coordination and load.** Reconcile open Objective Coordination #392 and Agent Collaboration #427 to merged Goal Execution and CAP-070. Implement F2/F3/F5: addressed ACK, bounded retry, state-lag distinction, valid resumption, queue aging and critical-path advisory. Preserve existing federation signed envelope/hop budgets. Validate nonblocking CPU-only operation and anti-starvation.

**P3 — Resource-aware workload and incremental artifact logic.** Implement F7/F8 atop existing Derived Artifact Lineage, Artifact Fabric and HRB read-only telemetry. Evaluate data locality without authorizing placement. Preserve all native creative project formats, edits, original assets, revision ancestry and source approval. Test changed-scene-only invalidation and lossless rollback.

**P4 — Hardened execution and real host proof.** Bind F6 to existing Security, Agent Sandbox, Skill Fabric #511, Model Router, MCP/Secret Broker and HRB runtime. No new scanner as authority. Physically prove CPU-only native Agent Workload, fresh HRB bridge receipt, pause/resume and cleanup on the exact source head. Do not treat hosted CI static PASS as physical closure.

**P5 — Independent evidence, recovery and test.** Wire F4/F10 to live canonical Evidence/Gate and existing verification #496, without reviewer/claimant identity collapse. Exercise network fault injection solely in an isolated authorized lab, then independently qualify **two distinct real hosts** for CAP-070 production E2E. Test positive, negative, stale evidence and rollback paths.

**P6 — GUI and observability.** Add F9 to existing Qt6/QML Control Center instead of a second desktop application. Show project->objective->task->agent->host->artifact->criterion->receipt; stale/estimated state prominently labelled. Verify accessibility, Wayland preferred/X11 fallback and physical current-host GUI interaction.

**P7 — Pilots and release.** First a disposable isolated Developer Agent Git branch with PR/CI/refinement loop; then Story/Screenplay -> Prompt Builder -> Shot Designer -> FA3 native Video Editor/QuickClip, adding Audio/VFX as admitted. Preserve `.fa3video`, `.fa3clip`, `.kra` and native audio/project formats. Any optional Unreal use is handled under the updated #523 policy and separate real current-host/runtime/GUI/E2E admission. Regenerate canonical release/impact and exact-head gates; only signed genuine physical Evidence/Gate can promote a scope.

## 5. Acceptance test matrix and mandatory negative cases

| ID | Test | Expected |
| --- | --- | --- |
| T01 | Repeat exactly the same HANDOFF event | One logical delivery; ACK cursor stable |
| T02 | Same event ID with tampered payload or expired signature | Rejected without downstream task mutation |
| T03 | Two writers claim the same protected workspace | No simultaneous protected writes; no unauthorized takeover |
| T04 | Crash between handoff and ACK, then recover | Reconcile original task once with verified ownership |
| T05 | High-priority request while noninterruptible render runs | Explain delay; no forced preemption or resource bypass |
| T06 | Prompt-injected skill requests secrets/network | Block, log, no expansion of permission |
| T07 | Change only one scene with unrelated approved scenes | Recompute only affected subgraph; reuse is provenance/evidence bounded |
| T08 | Cached artifact's goal or input revision is stale | Reject reuse and prior proof as current |
| T09 | Network fails after remote acceptance | No duplicate execution, no fake completion, bounded recover/escalate |
| T10 | Disconnected/stale second host | No silent rescheduling or fabricated cross-host PASS |
| T11 | Incomplete worker success text or forged checker receipt | Goal remains unverified |
| T12 | Estimated bandwidth missing or outdated | Label UNKNOWN/stale, require fresh observation or operator decision |
| T13 | Provider disallowed or display GPU not explicitly assigned with other GPU/NPU present | No silent provider/device fallback |
| T14 | Optional donor adapter absent | FA3 native CPU-only path still usable |
| T15 | Fault test against production network or host-global tuning | Rejected by lab isolation/hardware/coexistence gates |
| T16 | Different UI consumer/restarted GUI | Rebuild from authenticated Journal/Temporal state; no invented PASS |

## 6. Gate and promotion discipline

Mandatory: central donor registry/read-only Reuse Discovery, updated ApplicationIntent+ReuseAssessment, Security/PKI, Software Coexistence & Host Non-Interference, Hardware Safety Envelope, HRB-only lease/placement, Model Router-only physical route, Central MCP Gateway, immutable signed evidence, fail-closed static enforcement, latest-main release reconciliation and exact-head CI. The current-host batch orchestration integrity blocker must be repaired at shared infrastructure level.

**Explicit exclusion:** no auto dependency from donor presence; no new universal orchestrator/scheduler/cache/memory/secret/evidence authority; no raw keys in prompts/CI logs; no paid/cloud service automatic selection; no static/mock/loopback proof claimed as real two-host production qualification; no historical evidence overwrite.

**PR sequencing:** This donor metadata/plan branch is intentionally stacked **on #459** to avoid replacing its 550-entry reconciled registry with the shorter main version. After #459 is reconciled/merged, rebase this delta onto exact main, retain any newer donor records by normalized key, regenerate release projections and rerun all applicable gates before merging. Do not merge only because source-level checks are green.
