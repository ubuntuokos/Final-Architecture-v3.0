# CFA3 Task Scope & Closure Policy — 2026-10-03

Decision: `FA3-DEC-TASK-SCOPE-CLOSURE-POLICY-2026-10-03`

One explicitly requested task is one bounded task session. Required work may continue inside the bound goal revision, but newly discovered work cannot silently enlarge scope.

The immutable `fa3.goal-scope-binding.v1` binds the exact goal ID, revision, goal digest and scope digest. `in_scope` and `out_of_scope` may not overlap. Every executable workload origin (`EXPLICIT_USER_SCOPE`, `REQUIRED_FOR_APPROVED_GOAL`, and `EXPLICIT_USER_SCOPE_EXTENSION`) must preserve its original `scope_origin`, carry this immutable binding, and enter the same task-control admission path.

Each active task uses a `fa3.task-scope-control.v1` envelope. The blocker ledger is append-only and reconstructed against its counters. The same blocker may fail at most three times; the third failure moves the task to `HUMAN_INTERVENTION_REQUIRED`, freezes execution, and disables automatic retry, replan and alternative routing. A fourth attempt is mechanically rejected.

Compilation alone is not sufficient to execute. `agent.workload.start` and `agent.workload.resume` require a fresh task-scope admission receipt. The admission check revalidates the current task-control revision and digest; a cached execution plan cannot bypass a later freeze or closure.

A task can become `CLOSED/VERIFIED` only with an Evidence-authority receipt bound to the task and the immediately preceding task-control revision. Non-verified terminal conditions freeze the task and require human intervention.

Out-of-scope work becomes a persisted `fa3.task-followup-handoff.v1` inside the task control. It records the origin goal/task IDs and digests, classification reason, issue, current state, evidence references and suggested next task. It always requires a new task ID and explicit user start; it never auto-executes.

This policy creates no new scheduler, orchestration authority, resource authority, model-routing authority, action authority or Evidence authority. Temporal, UAF/Security, HRB, Model Router and Evidence retain their existing roles. Capability baseline remains **175**.

This materialization changes shared runtime-admission validation but claims no Current Host PASS and does not reuse historical physical evidence. Current Host qualification remains governed separately and stays pending where required by the existing stabilization policy.


## CFA3 Main Task Continuity — 2026-10-05

Canonical extension: `CFA3-DEC-MAIN-TASK-CONTINUITY-2026-10-05`. Runtime invariant: `CFA3-MAIN-TASK-CONTINUITY-001`.

This is a **CFA3 application-runtime rule**, not a CFA3 development-process rule. Every active task control binds one immutable `main_task_id` to the goal/root task for the life of that task session. New rules, parallel tasks, PRs, monitoring obligations, dependencies, blockers and discovered follow-up work are recorded as constraints/events/handoffs under that task; they cannot silently replace the active main task.

A blocker may freeze execution, but the blocked object remains the same main task. Start/resume revalidates the exact main-task identity and binding revision through the shared Agent Workload execution plan. An explicit owner decision to switch main tasks requires a new or explicitly rebound task-control session; automatic reassignment is forbidden.

The shared runtime rule applies to Assistant, Coach, Mentor, Manager, Agent Workload, Orchestration Workforce, Temporal-backed workflows and all current/future CFA3 applications that execute through the shared task path. It creates no scheduler or authority. Temporal remains durable lifecycle authority; Security/UAF, HRB, Model Router and Evidence retain their existing boundaries.

The task-control read model exposes `main_task_id` plus `main_task_events` so CFA3 GUI surfaces can render the main task separately from blockers, monitored PRs, parallel tasks, constraints and follow-ups without changing focus automatically.
