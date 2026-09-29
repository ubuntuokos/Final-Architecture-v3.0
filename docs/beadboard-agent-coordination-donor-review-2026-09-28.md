# BeadBoard selective donor review — 2026-09-28

Source: [jordanhindo/beadboard](https://github.com/jordanhindo/beadboard) at inspected upstream `9e3059dbb7c2e907cef79b5fa68d51f8cb390457` (2026-07-26); the README still refers to the prior `zenchantlive/beadboard` URL, which GitHub resolves to the same repository. Licence: MIT declared in upstream `LICENSE`. Registry record: `FA3-DONOR-JORDANHINDO-BEADBOARD-001`.

## Disposition

**CANDIDATE — selective coordination contracts and operator UX; not a runtime provider.**
BeadBoard is a Beads-backed multi-agent task coordination dashboard, `bb` CLI and work-in-progress embedded `bb-pi` runtime. It is **not** a beat-maker, musical beat tracker or narrative-storyboard tool. Its main reference value for FA3 lies in task-scoped handoff/ack, stale-agent and contention visibility, agent role/pool monitoring and evidence-linked completion. The upstream README specifically warns that `bb-pi` is under construction, with known silent failures and rapid-session race behavior; upstream documentation is not FA3 runtime evidence.

## Mandatory overlap check: use existing FA3 contracts

FA3 already defines `FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001` with `AgentTask`, `AgentDelegation`, `WorkspaceLease`, `AgentMessage`, `CoordinationEvent`, `ExecutionEvidence`, `HumanApprovalReceipt` and `IntegrationLedgerEvent`. Director/Workforce contracts govern specialist eligibility, authority separation, human escalation and evidence-bound runtime admission. **Do not add a second canonical issue registry, mailbox authority, workflow engine or reservation authority.** Query the existing Donor & Reference Registry / Reuse Discovery before a material implementation.

| Selective upstream pattern | Existing FA3 consumer | Required adaptation |
| --- | --- | --- |
| HANDOFF / BLOCKED / DECISION / INFO messages and ack states | AgentMessage, AICommunicationEnvelope, UAF, Central MCP Gateway | Human-auditable `FA3-AI-COMMS-001`, bounded hops, independent consumer cursor, replay-safe IDs and typed ack transitions. |
| Work-surface reservations with TTL and liveness | WorkspaceLease, Developer Agent integration broker | Only local workspace collision hints; cross-host CPU/GPU/memory reservation or lease is exclusively HRB. Expiry must not authorize silent takeover of protected work. |
| Blocked chains and task/dependency DAG | Temporal-backed production graph, Goal-to-Acceptance, Director | Display existing graph, check cycles and evidence blockers without replacing Temporal durable lifecycle. |
| Agent roles, squad roster and stale heartbeat monitor | Workforce specialist eligibility, Agent Collaboration Room | Respect anti-capabilities, pre-authorized AI participants, runner admission and human escalation. Absence of heartbeat is not proof of safe recovery. |
| Evidence-required task close and activity stream | Verification Fabric, Journal, Evidence Registry | Close only from independently verified receipts; never rely solely on worker success text or dashboard colors. |
| Social/Graph/Swarm operations console | Agent Collaboration Room GUI | FA3-native Qt6/QML components, Wayland-preferred with mandatory X11 support; optional web views must not introduce a second control plane. |

## Suggested application contract

`AgentCoordinationView` consumes immutable/append-only FA3 events keyed by `project_id`, `task_id`, `agent_id`, `message_id` and monotonic `event_id`. It produces *user intents*, never authoritative decisions: acknowledge handoff, inspect blocker, request assignment, review evidence, propose takeover, escalate to human. UAF validates the intent before mutation; Temporal owns durable workflow state; the integration broker owns one controlled integration path; Journal/Evidence retains provenance.

Distinct operation states are mandatory: `UNASSIGNED`, `ASSIGNED`, `IN_PROGRESS`, `BLOCKED`, `READY_FOR_VERIFICATION`, `VERIFIED`, `FAILED`; the visual UI may summarize these but must not infer `VERIFIED` from task status alone. Keep narrative and music 'beat' data out of this agent task schema.

## Hardware Audit / model and security boundaries

- **Registry change: METADATA-ONLY PASS.** No hardware probes, runtime dependencies, providers, network services or accelerator requirements. CPU-only viable and vendor-neutral for accelerator cardinality 0..N.
- Any later runtime/agent use requires scope-bound current-host E2E, Security admission, HRB placement/resource/lease decisions, explicit Model Router selection and Central MCP Gateway mediation. No silent fallback, model recruitment or direct external-tool channel.
- Display GPU remains display-only by default, with existing explicit designation and no-other-GPU/NPU exception unchanged.
- `bb-pi`, Pi, Beads and Dolt must not be auto-installed. Independently review transitive licences, dependency provenance, update policy, attack surface, replay and secret-handling before considering a narrowly scoped adapter.

## Testable follow-up gates (not claimed implemented)

1. Registry identity/alias de-duplication, exact source provenance and non-authoritative candidate status.
2. Typed mailbox: HANDOFF/BLOCKED acknowledgement; duplicate event and out-of-order delivery are idempotent; private model language rejected.
3. Parallel work: same-scope contested edits fail closed; stale heartbeat alone cannot break an active HRB lease or bypass single integration committer.
4. Completion: fake worker PASS, missing receipt and modified-after-approval artifact fail independent evidence verification.
5. Recovery: agent crash, replay, missed SSE update, offline GUI and restart reconcile from authoritative Journal/Temporal state with no silent task transition.
6. GUI: Qt6/QML Wayland and X11, accessible blocker chain/ack/evidence detail and user-directed interrupt/escalation, no direct provider execution.
7. Runtime gate only after explicit admission and real current-host E2E; registry or static CI never activates a provider.

This document is an assessment, not an implementation or promotion receipt.
