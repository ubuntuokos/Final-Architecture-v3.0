# FA3 Task Scope & Closure Policy — 2026-10-03

Decision: `FA3-DEC-TASK-SCOPE-CLOSURE-POLICY-2026-10-03`

## Purpose

FA3 treats one explicitly requested task as one bounded task session. Work required to satisfy that task may continue inside the same session; newly discovered work outside the explicit scope cannot silently enlarge the task.

This policy is shared platform governance, not a new application, capability, scheduler or orchestration authority. Capability baseline remains **175**. Temporal remains the sole global durable workflow lifecycle authority.

## Canonical behavior

- Goal scope is bound to an immutable goal revision and digest.
- Undeclared or explicitly out-of-scope work becomes a typed follow-up handoff draft.
- A follow-up never auto-starts and requires a new task ID plus explicit user start.
- The same blocker may receive at most **three** failed attempts.
- The third same-blocker failure freezes execution and requires a concrete human action.
- A fourth same-blocker attempt is mechanically rejected.
- While human intervention is required, automatic retry, replan and alternative-route widening are disabled.
- A VERIFIED/CLOSED task cannot execute again.
- User-facing closure projection is exactly `DONE`, `NEW_TASK_DISCOVERED`, or `HUMAN_INTERVENTION_REQUIRED`.

## Runtime binding

`src/fa3_task_scope_closure.py` provides provider-neutral policy/state validation.

Goal Execution emits a `fa3.goal-scope-binding.v1` with each goal-bound Agent Workload candidate. Agent Workload validates that binding. When a goal-bound workload is compiled for actual execution, an ACTIVE `fa3.task-scope-control.v1` state is required; frozen or closed task control fails closed.

The state envelope is not durable authority by itself. Temporal persists/resumes the lifecycle; UAF/Security authorize effects; HRB and Model Router retain their existing authorities.

## Follow-up handoff

A handoff preserves origin goal/task identity, revision/digests, the discovered issue, why it is outside scope, current state, evidence references, and a suggested new-task/conversation start. It explicitly carries:

- `requires_new_task_id=true`
- `requires_user_start=true`
- `automatic_start=false`
- `execution_performed=false`

## Retry semantics

The retry key is a deterministic blocker fingerprint over blocker code and context references. The attempt ledger is append-only in the task-control state. Three failed attempts for the same fingerprint force `HUMAN_INTERVENTION_REQUIRED`; the control then freezes all further execution until a separate authorized human-resolution path acts on it.

## Donor / reuse boundary

Planning is bound to published main `fd8adf5ab2ef12882c47250ecb5d5f22ff8e796b`, donor registry blob `6ca92f89dba92910b202d51e607b68cfee0cb488`, SHA-256 `f20260dc85bf9bf78f6456a2f2fbce426991832412a82cb8c66e8c347819488f`, **1423 entries**. Pending donor data is not consumed and no new donor usage edge is created.

## Current Host boundary

This is a static governance/runtime-admission contract delta. It does not claim a physical Current Host PASS, install a provider, change device placement, or mutate the host. Any future host/provider runtime delta remains subject to fresh physical Current Host evidence.
