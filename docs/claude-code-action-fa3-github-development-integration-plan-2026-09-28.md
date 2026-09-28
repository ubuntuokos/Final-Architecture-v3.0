# FA3 GitHub Development Integration — Claude Code Action donor implementation plan

Date: 2026-09-28
Status: TECHNICAL IMPLEMENTATION PLAN / NO RUNTIME ACTIVATION
Donor: https://github.com/anthropics/claude-code-action
Upstream main observed: 8ce9314fa9a404564fa7e954cd84f25bcba2b829 (2026-09-28)
Donor registry key: github:anthropics/claude-code-action
Donor registry ID: FA3-DONOR-CLAUDE-CODE-ACTION-001
Parent donor PR: #507

## 1. Scope and non-goals

Build FA3-native, provider-neutral GitHub PR/issue development workflows by selectively borrowing event-triggering, PR-review, issue-triage, progress projection, structured-output and GitHub tool-permission patterns from Claude Code Action. The action's MIT declaration is recorded upstream; any actual code copy or bundle needs independent SPDX/dependency/provenance/security/distribution review. No upstream runtime, Claude dependency or GitHub App is automatically installed.

The integration is a feature of existing CAP-028 Developer Agent / Agent Workload Runtime and the existing Work Management projection. The user-facing 'PR Watch' is a proposed view and task flow within the existing Work Management / Agent Workspace surfaces, not a separate FA3 authority, app, scheduler, model router or evidence store.

Zero new architectural authorities and zero capability-count changes. The active FA3 release baseline is 2026-09-26/v3.1.0, 175 capabilities, resolved dynamically from canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json. Older documents' 143 count is historical, not a new implementation default. No historical registry rewrite is in scope.

## 2. Required preflight and donor reuse

Each implementation PR first queries FA3-REUSE-DISCOVERY-001 and the canonical Donor & Reference Registry plus application donor index. Reuse current relevant reference entries without duplicate source keys:
- anthropics/claude-code-action: event-trigger modes, status comments, structured outputs, GitHub token scopes, review/triage examples; selective reference only.
- poponline63/north-star: explicit definition-of-done / deterministic acceptance-first pattern.
- OpenHands/software-agent-sdk: isolated coding workspace and inspectable agent events, reference only.
- garrytan/gstack, agent0ai/agent-zero: prior FA3 decision/provenance and isolated-worktree reuse candidates already in registry.
- Existing FA3 AX/ADK/Temporal, developer coordination, Closed-Loop Agent Operations, Goal Execution Foundation, Security Governance, Evidence and canonical Gate contracts supersede any conflicting upstream design.

Run existing reuse index queries and note exact applicable record IDs, versions, safety flags and rejection reasons in each subsequent PR. Donor capture is metadata and does not admit runtime, source copying, model/provider selection or CI promotion.

## 3. Canonical authority and ownership map

| Concern | Sole existing FA3 authority or contract | Integration rule |
| --- | --- | --- |
| External GitHub issue work identity | FA3-WORK-ITEM-PROJECTION-CONTRACTS-001 / Work Management | Preserve canonical work item ID; external issue/PR numbers are provider metadata. |
| User goal and acceptance | Goal Execution Foundation / Coach owner | Explicit acceptance criteria, immutable revision and authorization. |
| Task breakdown and specialist assignment | Orchestration Director / Workforce | Deterministic eligibility before optional bounded Decision Fabric advisory. |
| Durable cross-task workflow | Temporal | No GitHub Actions workflow becomes global FA3 orchestration authority. |
| Typed effects | Unified Action Fabric (UAF) | Trigger occurrence alone never authorizes execution or mutation. |
| External tools / GitHub operations | Central MCP Gateway, Security Governance | Scope by repo, task, actor, tool, branch and action type. |
| Task runner | FA3-AGENT-WORKLOAD-RUNTIME-001 | Immutable Git inputs; per-task isolated workspace and admitted runner. |
| Model route | FA3-AUTH-MODEL-ROUTER-001 | Approved route -> provider/runtime -> designated model -> LiteLLM plane; no fixed Claude route or silent fallback. |
| Host resource placement | Hardware Discovery + HRB | Fresh resource admission and lease for every effectful run/resume. |
| Credentials | Existing Secret Broker / Session Vault | Ephemeral least-privilege tokens; never expose credentials in prompts, artifacts or PR logs. |
| Execution records | FA3 Journal / Closed-Loop Agent Operations | Append-only event and attempt lineage; no self-certifying results. |
| Evidence and pass decision | FA3-AUTH-OBS-EVIDENCE-001 + Canonical Gate and human policy | Independent verifiers, immutable source and explicit gate disposition. |
| GUI | FA3 Control Center / WorkManagementPage.qml | Read-only projection with separately authorized commands; Wayland preferred, X11 supported. |

Any proposed contract is a non-authoritative child of these existing contracts. The reviewer and implementer are separate agent sessions/roles; a checker has read-only or strictly restricted access and cannot repair its own finding.

## 4. Ingress: GitHub events and work-item reconciliation

A. Implement a narrow FA3 GitHub development event adapter. First source can be GitHub API observation / GitHub Actions event data exported through an explicit, read-only UAF/Gateway path; later allow a separately admitted GitHub App/webhook adapter. No inbound listening port or AdGuardHome port changes are mandatory.

B. Normalize only allowlisted event classes: pull_request opened/synchronize/reopened/ready_for_review, issues opened/assigned/reopened, issue_comment created from authorized actors, review submitted, and workflow/check results. Ignore unknown events. External GitHub issue identity projects into canonical Work Management IDs; PR/review/check metadata attaches to the work item without becoming a second work registry.

C. Every event envelope records repository identity, delivery/event ID, event type, immutable observed head/base SHA where applicable, issue/PR ID, actor, installation identity, timestamp, source revision, redacted raw-payload digest and an explicit trust class. Webhook mode requires verified HMAC before parsing into executable decisions; API-observed and runner-dispatched mode requires separately authenticated source/permission validation. Never treat unsigned comments or text-only claims as authenticated commands.

D. Dedupe by authenticated delivery ID plus event type/repository, and reconcile by canonical work-item ID and observed remote revision. Handle redelivery, out-of-order synchronization, force-push, base movement, rate limit, 403, deleted/closed PR, duplicate comment and self-trigger loops; stale revisions become CONFLICT/STALE and require explicit reconciliation.

E. Split observation from action. Untrusted users may create visible read-only triage candidates, but cannot trigger mutating agent workloads or obtain elevated tokens merely by mentioning an agent. Bot allowlist uses exact approved identities, never '*'. Automated classification does not create an authorized AI participant or expand tool privileges.

## 5. Development workflow and safe code modification

Stage 1 — Observe: collect minimal permitted GitHub metadata, canonical work item, selected immutable Git SHA/diff and existing CI/check results. Store raw untrusted PR content separately as data; ignore embedded instructions, model-role impersonation, hidden markdown, unexpected MCP config and repository-provided execution hooks.

Stage 2 — Preflight: bind goal revision, acceptance criteria, exact work scope, application donor assessment, approved agent set, allowed actions, cost/tool/time/fanout budgets, Security decision, runner admission, model route availability and Hardware Audit. An ambiguous or missing high-impact preflight result means BLOCKED or human escalation, not fallback.

Stage 3 — Plan: Director emits typed subtasks referencing existing AgentTask and UAF actions. Temporal owns durable lifecycle; Decision Fabric/Jev can advise only within the eligible set. Task assignment and model route are explicit. No task text launches Bash, installs dependencies, fetches skills, modifies test fixtures or uses network until the corresponding typed effect is approved.

Stage 4 — Execute: Agent Workload Runtime opens an isolated worktree at immutable approved base SHA, obtains fresh HRB admission/lease, projects admitted skills through Skill Fabric and tools through Central MCP Gateway, runs admitted model route, and records every effect under the existing Journal. Concurrent writers to the same integration target are serialized by existing coordination claims / single Integration Committer. Runner network is default-deny with exact allowed destinations. No direct provider/API, credential or workspace bypass.

Stage 5 — Propose: collect bounded diff, source and changed-artifact digests, commits, testing claims and explicit open risks. The Integration Committer performs DIFF_COLLECT_CHECK_THEN_APPLY on a fresh approved base; an approved proposal is digest-bound and immutable. Candidate output goes to a disposable branch and (subject to policy) a human-reviewed PR; direct protected-branch updates and automatic merge remain forbidden.

Stage 6 — Verify: execute independent read-only or restricted checker against immutable source and reviewer-owned test definitions. Run deterministic tests, lint/type checks, security and dependency checks, scope/changed-path and unchanged-test-integrity checks, applicable FA3 gates and provenance verification. Semantic commentary or an upstream 'completed' comment is never independent proof. Store criterion-by-criterion results and immutable receipts through the existing Evidence authority.

Stage 7 — Repair/close: if criteria fail, create only a bounded new authorized repair attempt within existing retry/budget/approval constraints. STOP on repeated identical failure, missing evidence, cost spike, permission drift, cancelled authorization or missing verifier. Goal VERIFIED is reserved for existing canonical acceptance authority after all mandatory independently verified criteria and required human approvals succeed. PARTIAL, BLOCKED, FAILED, CANCELLED and AWAITING_SIGNOFF remain visible.

GitHub Actions is a trigger or CI signal source; its green check alone never proves current-host FA3 runtime admission and never overrides the Canonical Gate. GitHub status comments are projections of the existing run ledger, not the ledger of record.

## 6. Security / supply-chain and secrets

Upstream Claude Code Action security advisory GHSA-8q5r-mmjf-575q affected versions below 1.0.74; the original issue combined attacker-controlled PR checkout, .mcp.json loading and automatic project MCP server enablement. For any optional runtime trial pin a reviewed immutable upstream commit at or after the fix, verify upstream dependency lock and transitive vulnerabilities again at admission time, and maintain a revocation/rollback path. This plan does not endorse the upstream's entire runtime or claim a reviewed source import.

For privileged pull_request_target/workflow_run, never place attacker-controlled PR head in the privileged workspace root, never evaluate repo-defined hooks/scripts/package configs with privileged secrets, and never run untrusted modifications under the secret-bearing FA3 workstation profile. Separate trusted base configuration from untrusted PR data and run any required untrusted-code analysis in an isolated, unprivileged, ephemeral workspace without external credentials and with an explicit egress allowlist. Even a trusted base hook must not indirectly execute PR-controlled package scripts.

Use short-lived repo-scoped GitHub App/job tokens where admitted; no long-lived PAT default; enforce event actor authorization, credential minimization, no wildcard allowed bots, environment scrubbing and redacted outputs. Disable full raw tool logs by default. Workflow permissions are job-specific (observe: read; comment: narrow PR/issues write; candidate branch: narrowly scoped contents write only after human/policy approval). Untrusted content never authorizes a command and an AI agent cannot modify the independent checker or approve itself.

## 7. Structured contracts and code boundaries (proposed, not materialized)

One non-authoritative child contract, suggested file: canonical/contracts/FA3-GITHUB-DEVELOPMENT-INTEGRATION-CONTRACTS-001.json, referencing the existing Work Item, Developer Agent Coordination, Agent Workload Runtime, Goal Execution, Closed-Loop Agent Operations, UAF and evidence contracts. Suggested types:
- GitHubEventEnvelope: repo, provider_event_id, event_kind, actor/installation, trust_class, delivery_time, base_sha, head_sha, object_revision, payload_digest, source_auth_receipt.
- GitHubWorkItemLink: canonical_work_item_id, external provider ID/PR/issue/revision, reconciliation_state, repository_scope, provenance refs.
- DevTaskIntent: goal_revision, criterion IDs, base_sha, changed-path scope, authorized agents, typed UAF action refs, approved logical model route and budgets.
- DevRunProjection: Temporal run and AgentTask IDs, worktree lease, runtime/HRB/security/model admission refs, attempt ID, sanitized progress.
- DevVerificationProjection: independently verified criterion, artifact digest, reviewer-owned verifier/version, deterministic result, gate receipt, required human approval and open deficits.

Extend existing Work Management and Agent Workload code first; if no suitable module exists, candidate narrow additions are src/fa3_github_development_adapter.py (read/normalize/reconcile), src/fa3_github_dev_plan_bridge.py (existing contracts only), and src/fa3_github_dev_evidence_projection.py (read-only canonical receipts). Never create independent durable state, model authority, resource authority, permission authority or evidence authority in those files.

The UI is a 'PR Watch' tab or panel within apps/fa3-control-center/qml/WorkManagementPage.qml and linked Agent Workspace, not a new top-level application. Present repo/PR, observed SHA and revision, goal and criterion coverage, delegate and exact authorized model route, live attempt/budget, trusted/untrusted content boundary, checker findings, immutable proof links and required approvals. Actions: read-only refresh/inspect, authorize bounded run, pause/cancel, request bounded repair, open candidate PR and provide human approval. Control Center calls typed UAF commands, never GitHub APIs or models directly.

## 8. Explicit Hardware Audit and host coexistence

Planning/event normalization is CPU-lightweight, CPU-only viable and does not require an accelerator. Hardware Discovery accepts 0..N CPU/GPU/NPU devices across vendors; HRB alone grants scheduling, NUMA placement and leases. No hardcoded Xeon/NVIDIA/CUDA/ROCm/oneAPI/PCI identity, GPU ordinal or resource assignment; no host-wide tuning, package install, service replacement, firewall opening or AdGuardHome port change.

Display GPU remains display-only by default. If no other GPU and no NPU exist, its AI usage may be eligible subject to existing admission; if another GPU or NPU exists, allow display GPU AI only on explicit in-application selection for a concrete authorized model AND task, with fresh HRB approval. It is never recruited for throughput or automatic fallback.

Use hosted CI for schema/static/negative tests only. Real scope-bound physical acceptance, if requested, uses the existing non-root [self-hosted, linux, x64, fa3-current-host] runner and the existing resource-admission bridge; that workstation is NOT a default place to execute arbitrary external PR code. Keep runtime and GUI qualification independent; visible Control Center GUI smoke is manual-only in a verified local Wayland or X11 session. Real provider/current-host E2E receipt cannot be synthesized from static CI.

## 9. Implementation PR sequence and exact exit criteria

P0 (this draft PR): donor candidate plus this integration plan; single source-unique donor key, baseline/authority map, Hardware Audit, security issues and no runtime activation. Rebase against then-current main and preserve every concurrent donor entry before merge. No candidate->ACCEPTED_REFERENCE promotion solely on metadata.

P1 — Event/identity contracts + read-only adapter. Add schema, source-auth verification, actor and bot policy, deterministic event normalization, revision/ID reconciliation and idempotent dedupe tests. No mutating token or AI runner. Exit: replayed/forged/unsupported/out-of-order/unauthorized event cases fail closed; source-bound read-only task projection passes.

P2 — PR Watch/Work Management read-only projection. Link PRs/issues/check statuses to existing canonical work items, enable repo/branch/commit view, initial goal criteria and missing-proof display. Exit: remote outages never corrupt canonical work identity; no GUI click bypasses UAF; headless QML/build and projection tests pass.

P3 — Director/Workforce + Temporal + Agent Workload bridge. Compile only approved DevTaskIntent to existing AgentTask/UAF, immutable commit workspace and admitted runner with fresh HRB lease/model route. Manual or explicitly policy-admitted bounded pilot only. Exit: unsafe workspace, missing admissions, unapproved new agent/model/tool and silent fallback all denied; cancellation/resume/idempotency/cost limits proven.

P4 — Independent verification + bounded repair. Connect existing Closed-Loop Agent Operations, Goal Execution Foundation, Journal and Evidence/Gate; immutable diff/test baselines, independent checker and criterion-level proof, narrow repair and STOP. Exit: self-certification, missing verifier, modified checker fixture and approval/proposal digest drift cannot yield VERIFIED; deterministic negative tests pass.

P5 — Governed candidate PR / controlled end-to-end pilot and optional GUI operator controls. Human approval binds exact proposed digest/base SHA; protected-branch merge is not automated. Perform one synthetic owned-repo disposable-branch real flow and a separately authorized scope-bound current-host run only on safe test input. Exit: independently verified task proof, authentic GitHub status projection, no secrets/external-code execution on privileged host, manual GUI native-session qualification when appropriate, explicit rollback/kill switch.

P6 (optional, separate decision): upstream Claude Code Action adapter or Claude provider trial. Only if there is a demonstrated FA3-native functionality gap, new license/security/provenance review, exact SHA and explicit Model Router + HRB admission. The upstream action can be run as a GitHub-side optional external automation within a limited job but may not bypass FA3 ingress, tool, model, security or evidence authorities. Never require Claude for the FA3-native path.

Every implementation PR includes exact-main source reconciliation, scoped immutable-SHA tests, negative fixtures, relevant permanent gates, source license/provenance checks, and clear distinction between STATIC_PASS, CI_REFERENCE_PASS, CURRENT_HOST_PENDING and scope-bound CURRENT_HOST_PRODUCTION_E2E_PASS. Existing global promotion rules remain untouched.

## 10. Mandatory negative regression matrix

- Forged webhook signature, replayed delivery ID, duplicated actor event, unknown event, out-of-order revision and force-pushed PR.
- Comment from non-write user, wildcard bot, fake automation identity and event text requesting elevated GitHub permissions.
- PR-authored .mcp.json, CLAUDE.md, package scripts, runner hooks, hidden markdown/tool prompt and untrusted checkout in privileged workspace.
- Repository secret in prompt, artifact or progress comment; full debug trace in public CI; stale token; GitHub 403/429/network outage.
- Missing current-head SHA/base SHA, conflicting worktree claim, changed approved diff, concurrent writer and protected-branch direct commit.
- Direct model/provider, tool/GitHub API, Security, Secret Broker or HRB bypass; unauthorized AI participant or forced model fallback.
- Failed, absent or author-controlled verifier, modified independent checker fixtures, semantic-only PASS and forged/empty evidence.
- Retry/cost/tool/fanout budget overflow, Temporal duplicate delivery, resume with old HRB lease, revocation not honored, uncontrolled PR self-trigger loops.
- CPU-only host wrongly rejected; unauthorized display GPU recruited; accidental AdGuardHome/service/port changes; CI-only result claimed as physical runtime or GUI PASS.

A successful implementation preserves human choice, fails closed on proof or authorization gaps and changes neither the current canonical capability count nor any existing architectural authority.

## 11. Acceptance and rollback

Acceptance is based on actual separately verified evidence for the exact source SHA, authorized scope and selected host/runner, not on upstream documentation or a model's completion statement. Required output: read-only event trace; work-item reconciliation receipt; authorized typed task plan; executor/verification session separation; immutable proposal and independent test digests; budget and HRB/model admissions; canonical Gate outcome; signed human approval where needed; redacted progress projection and rollback/kill-switch exercise.

Stop path disables GitHub event ingestion for the affected installation/repository, stops new UAF task admission, cancels/pauses Temporal and active runner tasks through existing authorities, revokes scoped GitHub credentials, retains sanitized append-only evidence and leaves existing FA3 Work Management and Developer Agent functioning without the optional adapter. Never delete the user's native project files or rewrite protected branches during rollback.
