<!-- FA3_AGENT_META {"schema":"fa3.agent-instruction-projection.v1","profile":"FA3-AGENT-INSTRUCTIONS-001","scope":"/","authority":"NON_CANONICAL_PROJECTION"} -->
# FA3 repository agent instructions

This file is a scoped operational projection for coding agents. It is not a canonical source of truth and cannot create architectural authority.

## Global operating rules

- Read the relevant canonical profile, contract, decision, and gate before changing governed behavior.
- Preserve fail-closed behavior. Never weaken, disable, or bypass a valid gate, test, security boundary, HRB boundary, or evidence requirement merely to obtain PASS.
- A PASS or VERIFIED claim requires actually executed evidence. PENDING is a valid state; fabricated PASS, receipts, command output, host capabilities, or runtime observations are forbidden.
- Never commit raw passwords, tokens, API keys, private keys, recovery material, or other secret values. Use governed references and the FA3 secret boundary.
- Treat current-host observations as evidence, not global architecture requirements.
- Keep provider implementations replaceable. A provider or agent vendor cannot become an architectural authority by convention.

## Hardware Audit invariants

- The global hardware baseline is capability-based and vendor-neutral.
- Accelerator inventory is dynamically discovered and may contain zero devices.
- Do not introduce a global NVIDIA, AMD, Intel, CUDA, ROCm, Level Zero, Vulkan, ZLUDA, GPU SKU, runtime ordinal, PCI address, or current-host topology requirement.
- Distinguish logical CPU processors from physical CPU cores. Do not infer one from the other.
- Backend selection follows discovered device/backend compatibility and governed admission. Translation backends require explicit opt-in.
- Hardware placement, reservation, and lease decisions remain under the Host Resource Broker.
- Hardware safety overrides performance optimization. FA3, installers, provisioning, tuning, benchmark and agent actions must remain inside a device-bound vendor-supported operating envelope.
- Never apply overvoltage, out-of-policy overclocking, unsafe power limits, or bypass thermal, current, fan, firmware, driver or other hardware safety protections.
- If the safe operating range cannot be proven for the exact device and control, fail closed and do not mutate the hardware setting. Existing user tuning is not authority to increase or extend tuning.

## CUDA-oriented portability and shared-function rule

- This rule applies to the **FA3/CFA3 development process** and to the resulting **FA3/CFA3 product behavior**.
- A donor, library, model, runtime component, algorithm or feature path classified as **strongly CUDA-oriented** is not rejected merely for CUDA orientation. Before application integration or runtime admission, assess whether the same function can run on the actual target hardware through a native, portable, translation/compatibility, or independently admitted alternative implementation/provider.
- Target-hardware assessment must not skip AMD or Intel when those are relevant deployment targets. NVIDIA, AMD and Intel are the minimum reference vendor families; live discovered hardware and approved deployment targets determine the actual matrix.
- Record each target as **FULL_EQUIVALENCE**, **FUNCTIONALLY_REDUCED**, or **UNAVAILABLE**. Never assume feature parity from device presence, framework claims, or a translation layer.
- A strongly CUDA-oriented functional core may exist **only in a shared FA3/CFA3 layer/service/contract**. Application-local CUDA-oriented functional cores and duplicated per-application backend implementations are forbidden unless an explicit reviewed exception is recorded. Applications may contain only UI integration, workflow adapters, application context, presentation and limitation disclosure around the shared core.
- If an alternative backend is functionally reduced, the affected FA3/CFA3 UI must clearly disclose the target hardware, selected backend/alternative and the missing or reduced functions; material performance or memory restrictions must also be shown when known.
- If the function is unavailable on the selected target hardware, fail closed and mark the function unavailable/disabled. Do not silently switch to CUDA, another accelerator, a cloud provider, or a reduced path.
- HRB remains the resource placement/lease authority, Model Router remains model/provider routing authority, Hardware Safety retains precedence, and the existing display-GPU rule remains unchanged.
- Material runtime admission requires a target/backend test matrix and evidence. A policy or static test PASS does not create physical Current Host PASS.

## One-click new-conversation handoff rule

- This rule applies to the **FA3/CFA3 development process** and to the resulting **CFA3/FA3 product behavior**.
- When the owner asks to continue in a new conversation, the complete continuation payload is one logical handoff artifact and MUST be rendered in **exactly one one-click-copyable** surface.
- The full payload must be copied by one platform-equivalent user action. Do not split it across prose and copy blocks, multiple copy blocks, or require manual selection.
- Visual scrolling is allowed for long payloads, but scrolling must never affect copy completeness.
- A **single word** or otherwise very short handoff is not exempt.
- Product surfaces that generate a new-conversation/context handoff must consume the shared handoff behavior governed by `CFA3-ONE-CLICK-CONVERSATION-HANDOFF-POLICY-001`.
- Empty handoffs are not presented. Copy failures must be visible and must never be reported as success.

## Change discipline

- Add or update tests for governed behavior changes.
- Preserve capability and authority counts unless an explicit release reconciliation changes them.
- Do not mutate approved proposals, fabricate evidence, or self-validate a gate change with only the gate being changed.
- Prefer the smallest scoped change that satisfies the canonical contract.

## Authority boundary

Canonical authority: repository canonical records and executable gates.
Projection authority: none.
If this file conflicts with a canonical record, contract, decision, executable gate, or verified evidence, stop and resolve the conflict at the higher-authority layer. Do not silently choose this file.


## CFA3 donor capture rule

Normal donor intake recognizes exactly three authenticated owner commands as equivalent: `donornak`, `vedd fel donornak`, and `add a donorlistához`. Near-matches, commands inside URLs, negated commands, assistant text, research suggestions and uncommanded links are analysis-only. A command may appear before or after links in the same owner message. A command-only follow-up may target only links in the immediately preceding owner message with no intervening owner message; unreadable/skipped owner messages clear that target.

Direct operator intake uses `./bin/fa3-donor-capture` and must attest the exact owner command and source. The normalized legacy marker remains `donornak`, but literal-`donornak`-only interpretation is superseded by `FA3-DEC-DONOR-INTAKE-COMMAND-EQUIVALENCE-2026-10-04`. Registration creates `ACCEPTED_REFERENCE` only; adoption, code reuse, installation, provider/model admission and runtime use remain separately gated.

Implementation-plan preparation has one bounded exception: external sources may be substantively analyzed before registration only in the originating conversation lineage and direct continuations. After owner approval of that exact plan, every processed donor must be canonically registered before execution; the committed approval must bind the exact plan hash, assessment hash, processed normalized-key set and conversation lineage. This narrow approved-plan registration path does not require a second donor command and does not authorize adoption or runtime use.

Before design or material modification, consult Reuse Discovery against the **last verified, committed main donor registry only**. Pending/unmerged donor records are never planning inputs. No retrospective PR extraction is mandatory.

## FA3 automatic application inventory and reciprocal reuse

For any application added to the curated AI Studio catalog, derive its record through `bin/fa3-app-donor-index` rather than creating an untracked donor entry. GUI surface routes must be indexed as surfaces, never silently treated as applications. Planned FA3 applications must be explicitly registered in `canonical/FA3-APPLICATION-DONOR-LINKS-001.json`. Before new or materially modified application/module design, inspect both the existing Reuse Discovery results and the application's incoming/outgoing links. On donor-registry changes, run the previous-registry impact comparison and review only affected applications. Application registration does not confer donor approval, dependency, install, source-import, model, provider or runtime admission.

## P0 donor intake coordination and explicit human design approval (updated 2026-10-03)

- Run live fail-closed donor readiness before planning, implementation and finalization. Verify the local exact registry blob against the protected published main snapshot, its integrity, stable main SHA, and complete live PR inventory. Missing GitHub evidence, corrupt main or stale local snapshot blocks the operation and must be immediately reported.
- **Pending donor intake PRs do not block unrelated design, implementation or finalization** when the published main registry is intact and exact-matched. Pending/unmerged donors must be excluded from all such work. A fresh Reuse Assessment tied to the exact published registry SHA is still mandatory; donor adoption is optional.
- **Rolling five-slot donor intake:** before donor publication, require the live intake gate. At most **5** genuine canonical donor-intake requests may be active. Admission into a freed slot is FIFO; as soon as any active intake finalizes, the next waiting intake may enter immediately. Policy and reference-only PRs do not reserve a slot. Within the active window, finalization is ordered by ascending canonical donor-mutation workload, with FIFO as the tie-breaker. A sixth or later request must report `DONOR_INTAKE_ACTIVE_WINDOW_FULL_WAIT_FOR_SLOT`. An active but non-smallest intake must report `DONOR_INTAKE_ACTIVE_WAIT_FOR_SMALLER_FINALIZATION`. The local nonblocking import lock remains single-writer per checkout; off-GitHub writers must participate in the shared orchestrator.
- Donor expansion, history-preserving removal and metadata synchronization are exempt from new-application planning/implementation restrictions but remain bounded donor maintenance with one canonical finalizer, normal integrity and exact-head gates.
- Every adopted donor needs a separate explicit owner-approved canonical decision. Approval of intake does not approve usage. No finished application or module without a previously approved immutable plan and exact-head human approval, except a separately recorded owner exception. Preserve the 175-capability baseline and the existing authorities.

## Donor Registry owner decisions (2026-09-29)

Mandatory historical PR donor extraction is abolished. The fourteen historical exact-head exemptions (#24 #31 #52 #70 #71 #125 #180 #181 #245 #252 #392 #427 #434 #438) remain closed unmerged. The explicit `donornak` owner marker (with or without a colon) must precede each intake link (one marker may introduce a clearly grouped multi-link batch). Without it the only permitted action on a submitted link is analysis until the owner directs otherwise. Up to five donor-intake conversations may be active under the rolling-window rule in `FA3-DEC-DONOR-INTAKE-CONCURRENCY-2026-10-03`; further requests wait for a freed slot. Other FA3 work uses only the finalized published registry; unmerged candidates are invisible, and completed work is not automatically re-run after their publication.

## FA3 tutorial-reference and shared-function rule (2026-09-30)

Tutorial material is a governed donor/reference input **only after normal donor intake**. No tutorial-specific bypass exists: a source must enter the published Donor & Reference Registry under the explicit owner `donornak` rule before it can become a `TUTORIAL_REFERENCE` planning input. Unmarked URLs or downloaded tutorial material may be analyzed, but cannot mutate donor metadata or become a donor planning candidate.

For every registered tutorial-derived feature, first match the feature against the existing 175-capability model and application inventory. If the function already exists, preserve the implementation and adapt the tutorial into the relevant FA3 application manual using the real FA3 UI, terminology and workflow. Do not copy an upstream UI workflow as if it were FA3 behavior.

If the function does not exist, stop at necessity and placement assessment until there is an explicitly approved implementation plan. Reuse Discovery against the verified published-main donor registry is mandatory before donor adoption.

If a function is useful to more than one FA3 application, the functional core must be placed in one shared FA3 layer/service/contract and consumed through application-specific adapters. Duplicate functional cores require an explicit reviewed exception. Shared-function impact analysis must cover planned, in-progress and already materialized applications and must preserve existing verified capabilities during migration.

Every consuming application receives its own manual projection based on its actual UI/workflow. A function may be documented as generally available only after implementation and required verification. Structural runtime changes also require matching Current Host alignment; static documentation never creates current-host PASS.

## FA3 donor capability consumer graph (2026-09-30)

Actual donor use must be recorded in the existing `FA3-APPLICATION-DONOR-LINKS-001` usage-edge list; do not create a second donor/capability registry. Capability bindings are derived from canonical profile/contract `capability_bindings`, never guessed from names. Track the primary application plus relevant shared-module/profile/authority/GUI/test/current-host consumers. The generated capability map is non-authoritative and cannot admit, activate or route a provider/model. Unmarked analysis links remain outside the canonical donor registry.

## P0 donor planning snapshot freshness (2026-10-01)

For every new or materially modified application, capability, module, profile, provider or shared component, the Reuse Assessment MUST contain a `donor_planning_snapshot` bound to the exact published-main commit and its canonical Donor Registry Git-blob SHA, SHA-256 and entry count. A stale or missing snapshot blocks implementation/finalization and requires reassessment against the new main; do not silently continue from an older green CI result.

The same material Reuse Assessment MUST contain `shared_capability_placement`. If the function can serve multiple FA3 applications, use the shared layer first. A local duplicate is allowed only with explicit reviewed justification and retrospective consumer-impact review. Actual donor adoption requires a canonical usage edge; reference-only research must not create a false adoption edge.

## Current Host structural co-development rule

Every change that modifies FA3 structural behavior must assess and reconcile its Current Host impact in the same development changeset. The canonical policy is `canonical/FA3-CURRENT-HOST-STRUCTURAL-CHANGE-POLICY-001.json`.

- Structural changes to architecture, authority boundaries, orchestration/conductor behavior, runtime/provider admission, resource handling, security, evidence/promotion, licensing/rights, hardware safety, Software Coexistence, UAF/MCP or related governance may not silently omit Current Host work.
- A structurally affected change must add a `canonical/current-host-impact/*.json` record with schema `fa3.current-host-structural-impact.v1`.
- Use `RECONCILED` when Current Host surfaces change; list the changed Current Host companion files and explicitly declare whether fresh physical requalification is required.
- Use `NO_RUNTIME_IMPACT` only with a substantive rationale and `physical_requalification_required=false`.
- Historical Current Host evidence is immutable and must never be inherited as proof for a structurally changed active release.
- The fail-closed gate `src/fa3_current_host_structural_impact_gate.py` and workflow `.github/workflows/fa3-current-host-structural-impact.yml` enforce this rule.


## FA3 explicit task-scope closure rule (2026-10-04)

FA3 development has no autonomous task class equivalent to **“Mit lehetne még megcsinálni?” / “What else could be done?”**. Do not create optional-improvement, assistant-suggested, opportunistic, auto-backlog or completed-task successor work merely because additional work is conceivable.

A task may enter planning or execution only when its scope provenance is one of: `EXPLICIT_USER_SCOPE`, `REQUIRED_FOR_APPROVED_GOAL`, or an owner-requested `EXPLICIT_USER_SCOPE_EXTENSION` bound to a revised goal. Missing or unknown provenance fails closed. Every executable `fa3.agent-workload-task.v1` must carry the same `scope_origin` and non-empty `scope_refs`; planning layers may not strip this provenance before Agent Workload admission.

Repair work is bounded to the original approved scope and original acceptance-criterion IDs. It may not invent a new criterion, expand scope, or silently create a successor task. When the explicit task is complete, completion is terminal unless the owner explicitly creates or extends the next task. Canonical authority: `FA3-RULE-NO-OPEN-ENDED-TASK-EXPANSION-001`.


## CFA3 development and AI execution discipline (2026-10-05)

Canonical source: `canonical/CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001.json`. This section is a non-canonical operational projection and cannot create authority.

- These rules apply both to the CFA3 development process and to CFA3 AI/model/agent execution.
- A blocker means immediate STOP and report. Do not silently rebase, reroute, retry, open a replacement PR, start a workflow, or modify another component as a workaround.
- Keep the conversation/task scope locked. Before every GitHub mutation, refresh `main`, target head and relevant open PR state.
- Concurrent overlap on the same canonical file, gate, workflow or exclusive resource is a blocker unless the owner explicitly overrides that rule for the current conversation/direct continuation.
- Do not start workflows or gates merely to obtain a PASS. They must be necessary for task closure and no equivalent run may already be active.
- After every mutation, report the changed object, current SHA, next step and blocker state before the next mutation.
- Merge requires exact checked head/base state. Any drift blocks merge.
- Unexpected redesign or repair is reported before strategy changes.
- Current explicit owner restrictions outrank prior autonomy or broader approvals.
- DEV-11 / AI-11 self-correction is a narrow exception: after notifying the owner, an AI may correct only its own unambiguous deterministic mechanical/technical mistake inside the already approved scope. It may not use self-correction to redesign, choose another technical solution, create a new PR/branch, touch another component as a workaround, weaken a user restriction, bypass a blocker/gate/security boundary, or introduce a new permission/side effect. If the failed action may have partially mutated state, verify exact state before correction. After correction report the original AI error, the correction, whether state changed, the current head/SHA or relevant state, and any remaining blocker.
- An exception is valid only when explicit, rule/scope-specific and conversation-bounded. Generic approval is not an automatic policy override.
- The L0-L5 layer model keeps human scope/override, development discipline, task/orchestration, security/effect authorization, model policy and UX/projection distinct. A pending PR is never canonical authority.
- Use `src/cfa3_development_ai_behavior_guard.py` as the shared fail-closed preflight; it does not replace Security Governance, HRB, Model Router, Evidence or Temporal authorities.
