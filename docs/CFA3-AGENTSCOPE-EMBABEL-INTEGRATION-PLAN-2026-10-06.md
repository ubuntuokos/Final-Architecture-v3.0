# CFA3 AgentScope–Embabel Integration Plan

Date: 2026-10-06
Status: OWNER-APPROVED IMPLEMENTATION PLAN / DONOR REGISTRATION BARRIER ACTIVE
Capability baseline: 175
Capability delta: 0
Architectural authority delta: 0

## Goal

Integrate AgentScope ecosystem patterns for agent runtime, teams/federation, MCP/skills, sandbox/workspace, memory, evaluation and agent UX, plus Embabel patterns for typed Goal/Action/Condition planning and bounded replanning, without creating a parallel CFA3 authority.

## Fixed CFA3 authorities

- Temporal: sole global durable workflow lifecycle authority.
- Work Management: canonical work identity/truth.
- Orchestration Director/Workforce: decomposition and deterministic specialist eligibility.
- Adaptive Conductor: task-local bounded adaptive graph only.
- Unified Action Fabric: effectful action boundary.
- Security Governance: authorization authority.
- Trust PKI: identity/trust only; certificates do not grant authorization.
- Host Resource Broker: sole resource admission, placement, reservation and lease authority.
- Model Router: sole model/provider/runtime routing authority.
- Central MCP Gateway: sole MCP/tool mediation boundary.
- Secret Broker: governed secret projection boundary.
- Skill Fabric: skill normalization/admission boundary.
- Agent Workload Runtime: task-local execution boundary.
- Agent Federation: authenticated delegation/coordination transport.
- Journal: historical/provenance projection.
- Evidence/Gate: canonical proof and promotion authority.
- FA3 OS Work Context: reference projection, never a duplicate task store.
- Current Host: physical proof only where runtime requalification is required.

CPU-only remains valid; accelerator cardinality is 0..N; no silent model/provider/device fallback; existing display-GPU rules remain unchanged.

## Architecture

OWNER -> Scope/Goal -> Work Management -> Goal Execution -> Reuse Discovery
-> Agent/Application Blueprint -> Task Group/Director -> Adaptive Conductor
-> {typed planner + Agent Federation/team runtime}
-> Agent Workload Runtime -> UAF
-> {Security/PKI, MCP/Skill, Secret Broker, HRB, Model Router/Decision Fabric}
-> Execution -> {Memory, Artifacts/Logistics, Application Handoff}
-> Journal -> Evidence/Gate -> Goal evaluation -> Work Management
-> Control Center -> OWNER.

## Embabel-derived planner semantics

Map Goal to existing CFA3 Goal/Work contracts; Action to registered UAF Action Contracts; Condition to deterministic state/policy/scope predicates; Domain Object to typed CFA3 entities; Plan to task-group-scoped execution plans; Replan to bounded plan revision.

An action is eligible only when REGISTERED, IN_SCOPE, AUTHORIZED, STATE_COMPATIBLE, CAPABILITY_AVAILABLE, RUNTIME_ADMITTED, RESOURCE_ADMISSIBLE and REQUIRED_APPROVAL_VALID. FALSE or UNKNOWN means DENY/BLOCKER. Planning cannot create authority, capability, provider routes, tool rights or fallback routes.

Typed entities include Organization, Production, Project, Workstream, Milestone, Task, Scene, Shot, Character, Location, Asset, Artifact, Application, Capability, Agent, Provider, Workspace, RenderJob, Approval and Evidence, each with stable identity, revision/schema, provenance and canonical-vs-projection semantics where applicable.

## AgentScope-derived execution

Use two replaceable adapter positions:
1. Orchestration Provider Adapter for already-authorized task-group team/pipeline execution.
2. Agent Workload Runner Adapter for one admitted AgentWorkloadTask.

The two adapters cannot collapse into a new authority.

AgentTeams patterns feed manager/worker collaboration, heterogeneous runtimes, human intervention, audit, progress/history and intermediate-result handoff. Manager is a role, not authority.

A2A is an Agent Federation transport adapter only. Federation owns addressing, signed envelopes, replay protection, TTL/hop/delegation budgets, claims, ACK/handoff and result correlation. It does not own security approval, HRB leases, model routing, durable lifecycle or Evidence PASS.

## Skills, MCP and sandbox

External skill path:
immutable snapshot -> Skill Fabric parser -> UNTRUSTED_CANDIDATE -> license/provenance -> security/dependency/permission inspection -> routing tests -> admission -> CFA3 Skill.

Skill metadata and allowed-tools are not authorization. Effectful skill execution is Skill -> Agent Workload -> typed UAF action -> MCP Gateway -> Tool.

Sandbox profiles: Code, Browser, GUI, Filesystem, Data Science, Build, Tool and Media. Every sandbox carries filesystem, network, process, secret, resource, tool allowlist, Work Context, CapabilityGrant, audit identity and expiry envelopes.

## Memory and context

Memory classes: Conversation, User/Profile, Project, Application, Agent Operational, Tool Experience and Knowledge.

A file-native long-term backend may use Markdown + frontmatter + stable IDs + provenance + relations/wikilinks + rebuildable indexes. Retrieval may combine metadata, BM25, optional embeddings and graph expansion, followed by deterministic filtering and bounded context.

Writes are observation -> MemoryCandidate -> provenance/conflict/policy checks -> admission -> persistent memory. Memory never becomes authorization or authoritative truth by itself.

## Models, hardware and fallback

Runtimes request logical model capabilities, not physical providers/models/devices. Selection remains Model Router + HRB. Framework-native silent fallback is forbidden. Provider failure results in a Model Router policy decision for an explicitly permitted alternate route or BLOCKED.

Strongly CUDA-oriented functional cores remain shared and require target-hardware equivalence classification FULL_EQUIVALENCE, FUNCTIONALLY_REDUCED or UNAVAILABLE, with UI disclosure and fail-closed unavailable behavior.

## Research, browser and evaluation

Research flow: goal -> decomposition -> pre-search -> hypothesis tree -> search/browser/RAG -> source acquisition -> provenance validation -> evidence graph -> contradiction detection -> synthesis -> report. Model statements alone are not authoritative facts.

Browser/GUI effect path: Task -> Action Contract -> Scope Guard -> Security -> UAF -> sandbox -> browser/native GUI -> observation -> artifact/evidence.

Evaluation order: schema -> deterministic -> security -> capability -> artifact/evidence validation -> optional semantic judge -> independent verification -> Evidence Gate. Semantic judges cannot independently grant Current Host PASS, security/license approval, provider admission or release promotion.

## Training and improvement

Trinity-RFT/TuFT-style ideas are consumed only through the existing AI Module Factory/Model Manager candidate path:
approved trajectories/human corrections/failures/tool traces/verified outcomes -> dataset qualification -> candidate training -> candidate model/adapter/policy -> evaluation -> Security -> License & Rights -> Model Manager -> Current Host when applicable -> Model Router availability.

No live self-modification and no automatic production promotion.

## Bidirectional integration contracts

Every affected layer has an explicit forward and return path:
- Owner Scope: goal/scope/approval -> Work/Goal; blocker/result/approval request <-.
- Work Management: task identity -> Blueprint/Workforce; progress/blocker/check-in <-.
- Goal Execution: criteria/policy/budget -> planner; criterion/evidence state <-.
- Blueprint/Workforce: typed tasks/handoffs -> Temporal/Conductor; validation/liveness/result <-.
- Temporal/Conductor: durable or bounded execution -> workload; result/checkpoint/replan reason <-.
- Federation: signed delegation -> peer; ACK/result/evidence refs <-.
- Agent Workload/UAF: execution plan/action -> authorities; output/receipt/deny <-.
- Security/PKI: identity/authorization -> execution; audit/revocation <-.
- MCP/Skill: admitted call -> tool; typed result/security finding <-.
- Secret Broker: scoped secret projection -> adapter; expiry/revoke/audit <-.
- HRB: lease -> workload; usage/release/failure <-.
- Model Router: logical requirement -> provider; result/failure/usage <-.
- Decision Fabric: finite candidates -> judge/rule; advisory result <-.
- Memory: scoped retrieval -> agent; provenance-bound candidate <-.
- Artifact/Logistics and App Handoff: artifact/addressed operation -> target; receipt/result/event/cancel <-.
- Journal/Evidence: events/proof -> verifier; PASS/FAIL/BLOCKED -> Goal/Work.
- Control Center/Messenger: governed request/message -> owner/target; authenticated projection/ACK/status <-.
- Current Host: exact runtime candidate -> physical qualification; PASS/FAIL/rollback <-.

Handoff or ACK is never authorization or VERIFIED completion.

## L0-L5 composition

L0 current explicit owner scope/override.
L1 CFA3 development and AI execution discipline.
L2 Goal/Work/Blueprint/Director/Conductor/Temporal/Workforce/Federation/Agent Workload.
L3 Security/CapabilityGrant/PKI/UAF/MCP/Secret/Sandbox/HRB.
L4 Model Router/model admission/Decision Fabric/AI Module Factory.
L5 Control Center/Agent Workspace/Unified Messenger/Assistant/Coach/Mentor/Manager/application projections.

Higher UX/projection layers cannot bypass lower authority layers.

## Consumer compatibility

All current/future consumers are classified NO_CHANGE, GUI_PROJECTION, CONTRACT_ADAPTER, SHARED_CAPABILITY_BINDING, LOCAL_TO_SHARED_MIGRATION or RUNTIME_REQUALIFICATION. Initial consumers include CFA3, Assistant, Coach, Mentor, Manager, Agent Workspace, Developer Agent, Research, Browser/Computer Interaction, Unified Messenger, Control Center, Story/Screenplay, World/Character/Shot/Production and future agentic applications. No per-application duplicate agent core.

## Forbidden shortcuts

Direct Agent->Provider, Agent->Tool, Agent->Secret Store, Agent->GPU selection, Agent->Evidence PASS, Planner->Security authorization, Planner->new capability, Memory->authorization, ACK->completion, remote trust->permission expansion, framework fallback->provider change, skill metadata->permission, GUI->provider execution, semantic judge->Current Host PASS and training result->automatic production are fail-closed forbidden.

## Implementation work packages

P0 exact reuse/impact closure.
P1 contract reconciliation.
P2 typed structured planning.
P3 runtime/team adapters.
P4 Skill/MCP/Memory.
P5 Evaluation/improvement.
P6 Application/Messenger links.
P7 Control Center.
P8 negative/failure tests.
P9 final exact-head physical Current Host qualification where required.

## Definition of Done

Capability baseline stays 175; authority delta stays 0; all effects use UAF; all tools use MCP Gateway; all model calls use Model Router; all resources use HRB; Temporal remains sole global durable lifecycle authority; all cross-layer paths have forward/return contracts; delegation and memory writes preserve provenance/scope; Journal/Evidence closes the goal loop; all consumers receive impact classification; actual donor use has usage edges; runtime adoption passes Security/License/Current Host gates; CPU-only remains usable; silent fallback is absent; Current Host PASS is physical only; main-task identity cannot switch automatically; completion creates no automatic follow-up task.

## Donor registration barrier

The substantively processed AgentScope/Embabel sources used to produce this approved plan are absent from the verified published-main donor snapshot. Under FA3-DEC-IMPLEMENTATION-PLAN-DONOR-EXCEPTION-2026-10-04, implementation execution is STOPPED until every processed source is published and visible in a verified canonical donor snapshot. The intake is reference registration only and does not authorize donor adoption, code import, installation, runtime/provider/model admission or Current Host promotion.
