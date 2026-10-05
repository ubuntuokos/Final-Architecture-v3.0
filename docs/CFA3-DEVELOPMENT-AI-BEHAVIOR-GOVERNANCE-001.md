# CFA3 Development and AI Behavior Governance

Canonical policy: `CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001`

## Purpose

This layer makes the same fail-closed execution discipline mandatory in two places:

1. the CFA3 development process; and
2. CFA3 AI/model/agent execution.

It does not replace orchestration, security, model-routing, resource or evidence authorities.

## Layer model

| Layer | Responsibility | Existing work coordinated |
|---|---|---|
| L0 | Current explicit owner scope, restrictions and scoped overrides | conversation/task authority |
| L1 | Development and AI execution discipline | this policy |
| L2 | Task lifecycle, orchestration and guard chain | PR #661, PR #623 |
| L3 | Security and effect authorization | PR #631 |
| L4 | Model-development and model-selection policy | PR #681 |
| L5 | Agent projection, naming compatibility and handoff UX | PR #702, PR #703 |

Open PR references are coordination metadata only. An unmerged PR is never canonical authority and is never consumed as published-main truth.

## Composition rule

Layers compose restrictively. A lower layer may deny an action already permitted by a higher operational layer, but it may not silently grant authority that a higher-priority rule denied.

A contradiction, unknown authority, uncertain live state or unresolved non-overridden overlap is a blocker.

```
REQUESTED
  -> SCOPE_LOCKED
  -> STATE_VERIFIED
  -> AUTHORIZED
  -> EXECUTING
  -> MUTATION_REPORTED
  -> VERIFIED
  -> COMPLETED

BLOCKER_DETECTED
  -> STOPPED
  -> BLOCKER_REPORTED
  -> AWAITING_HUMAN_DECISION
  -> REAUTHORIZED
  -> STATE_VERIFIED
```

There is no direct transition from a blocker to execution, merge, release or an external side effect.

## Development rules

- DEV-01: blocker means immediate stop and report.
- DEV-02: no autonomous workaround.
- DEV-03: conversation/task scope is locked.
- DEV-04: fresh live state is required before every GitHub mutation.
- DEV-05: overlap is a blocker unless explicitly overridden for the scoped conversation.
- DEV-06: workflows and gates are not started unless required for closure and no equivalent run is active.
- DEV-07: every mutation is followed by a status report.
- DEV-08: merge requires exact head/base verification.
- DEV-09: no silent redesign or repair.
- DEV-10: the current explicit owner restriction outranks earlier autonomy grants.
- DEV-11: after notifying the owner, the development AI may correct only its own unambiguous deterministic mechanical/technical error without separate approval when the correction stays inside the approved scope, intent, architecture, authority, policy and plan. Possible partial mutation requires exact-state verification first; redesign, workaround, new PR/branch, cross-component change, new permission/side effect, review-discovered substantive defect or uncertainty remains BLOCKER -> STOP -> REPORT.

## AI/model rules

- AI-01: stop on blocker.
- AI-02: no inferred bypass from the desired end goal.
- AI-03: every execution carries an active task-scope binding.
- AI-04: fresh verified state outranks memory and cache.
- AI-05: cross-agent collisions block mutation.
- AI-06: side-effect levels require explicit permission; PLAN is not WRITE, WRITE is not PUSH, PUSH is not MERGE.
- AI-07: every mutation is attributable and auditable.
- AI-08: authorization is bound to the exact state used to make the decision.
- AI-09: uncertainty fails closed.
- AI-10: the latest explicit owner constraint outranks prior model autonomy.
- AI-11: CFA3 AI/models/agents receive the same narrow self-correction exception as DEV-11. A valid correction must be the AI's own error, deterministic, scope-preserving and authority-preserving, must not bypass a blocker/gate/security rule, and requires a post-correction report containing the AI error, correction, state-change result, current head/SHA or relevant state, and any remaining blocker.
- AI-12: an AI assertion about external state is never a CFA3 fact merely because the AI asserted it or repeated an earlier AI statement. Available authoritative/deterministic verification is mandatory and takes precedence; without qualifying verification the claim remains HYPOTHESIS/UNVERIFIED, and a contradictory verified result overrides the AI claim.

## Self-correction boundary

DEV-11 / AI-11 is not a general repair or autonomy grant. It exists only to avoid stopping for a correction whose technically correct form is already determined by the approved operation.

Examples include a typo, wrong variable/file name, syntax or formatting error, malformed tool/API argument, an unambiguous command parameter error, a consistency error in an AI-generated file, a retry proven to have caused no state change, or the technically correct resubmission of the same approved operation.

It cannot authorize redesign, another technical solution, a new PR/branch, another component, weaker owner restrictions, a substantive design/implementation defect found by review, a new permission or side effect, or any correction whose correct form is uncertain. Current explicit owner prohibitions, scope-lock, safety/authority boundaries, exact-state requirements and real blockers always take precedence.

## Owner overrides

A policy exception is valid only when it is:

- explicit;
- scoped to named rules or scope;
- bound to the current conversation or an explicitly identified direct continuation;
- applicable to the current action.

Generic approval is not automatically a policy override. Overrides do not propagate to unrelated tasks or later conversations.

## Runtime enforcement wiring

The product-side rule is enforced at the existing shared Agent Workload execution-plan boundary. `src/fa3_agent_workload.py::compile_execution_plan` requires an explicit, scope-bound behavior context and calls the shared CFA3 behavior guard before it can emit `fa3.agent-execution-plan.v1`. The resulting plan contains a `cfa3.behavior-preflight-receipt.v1`. Because both `agent.workload.start` and `agent.workload.resume` already require an execution-plan reference, the normal Agent Workload start/resume path cannot bypass this preflight.

The behavior preflight is **not** effect authorization. UAF remains the action/effect boundary; Security Governance remains authorization authority; HRB remains resource authority; Model Router remains model/provider routing authority; Evidence remains promotion authority.

## Shared guard

`src/cfa3_development_ai_behavior_guard.py` provides a shared, authority-neutral preflight. It does not schedule work or authorize models, security-sensitive effects, hardware resources or evidence. Existing authorities remain responsible for those decisions.

Consumers provide explicit live facts. Missing or unknown facts fail closed.

## Enforcement

- gate record: `FA3-GATE-CFA3-DEVELOPMENT-AI-BEHAVIOR-001`
- gateset: `CFA3-DEVELOPMENT-AI-BEHAVIOR-GATESET-001`
- implementation: `src/cfa3_development_ai_behavior_gate.py`
- regressions: `tests/test_cfa3_development_ai_behavior.py`

The gateset is registered in the canonical gate registry and mirrored into the compatibility enforcement policy.

## Current Host

This change does not create a new provider, model, daemon, scheduler, driver, hardware path, lease or Current Host evidence class. Static or policy PASS cannot be interpreted as a physical Current Host PASS.

## Mandatory FA3/CFA3 work-session prenotice and status protocol

The canonical development policy also applies the following mandatory discipline to both FA3 and CFA3 development sessions:

- **DEV-12 — long/multi-operation task prenotice:** when a task is expected to be long-running or involve many operations, notify the owner before the first substantive operation. Post-hoc notice is not compliance.
- **DEV-13 — new long phase prenotice:** when another long or multi-operation phase begins during the task, notify the owner again before that phase starts.
- **DEV-14 — blocker/GitHub/security prenotice:** before acting on a blocker, unexpected GitHub state, exact-state drift, conflict, failed gate, or security-sensitive operation, send a separate prior notice. Notice never authorizes bypassing the blocker.
- **DEV-15 — no silent long GitHub sequence:** long GitHub operation sequences require concise status updates at meaningful phase boundaries; they may not run silently.

The development preflight entrypoint is `src/cfa3_development_ai_behavior_guard.py::authorize_development_action`. It composes with, but does not weaken or replace, the existing blocker, scope, exact-state, side-effect authorization, security, Current Host, evidence, or owner-approval rules.


## External-state fact verification

CFA3 applies `CFA3-EXTERNAL-STATE-FACT-VERIFICATION-001` to AI/model/agent external-state claims. The shared entrypoint is `src/cfa3_development_ai_behavior_guard.py::evaluate_external_state_claim`.

An AI statement, self-check, memory/cache entry, inference, or earlier AI statement is not authoritative evidence. A claim may be promoted to `FACT` only after qualifying `AUTHORITATIVE` or `DETERMINISTIC` verification with provenance. When such verification is available, using it is mandatory. When it is unavailable, an AI-origin external-state claim may remain only `HYPOTHESIS` or `UNVERIFIED`.

If the external result contradicts the AI claim, the external result wins and the AI claim cannot be promoted. This rule creates no new Evidence authority: `FA3-AUTH-OBS-EVIDENCE-001` remains the evidence/promotion authority.
