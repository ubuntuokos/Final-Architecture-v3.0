# FA3 Goal Execution P2 — source-bound design preflight

Status: IMPLEMENTED SOURCE-LEVEL DESIGN PREFLIGHT, EXTERNAL RUNTIME ADMISSION PENDING.
Parent foundation: merged PR #479. Parent donor and final plan: merged PR #476. Tracking issue: #482.

## What is implemented

The existing FA3 GoalContract is now consumable by a strictly design-only preflight that reads **real immutable repository records**, not caller-supplied synthetic success declarations. src/fa3_goal_preflight.py uses existing FA3 components instead of duplicating their functions:

- Reuse Discovery's assess_intent/resolve/build_catalog, including central Donor Registry and mandatory source-family review.
- FA3 application donor index generated from the canonical app catalogs and donor registry, with cardinality and authority flags checked.
- The existing 175-capability UserOwnedGoal and goal execution policy, bound to an exact GoalRevision digest.
- The real UAF ActionRegistry/ActionContract, verifying allowed action IDs, canonical mutating semantics, required authentication/authorization/audit, agent exposure and evidence.
- The real FA3 Agent Definition Registry, restricting roles to canonical definitions already included in the goal's explicit authorized participant set. A role record cannot grant runtime admission.
- A deterministic, cycle-free, budget-bound task DAG, over the existing Orchestration Workforce design routing and AgentWorkloadTask schema. Dependency depth must not exceed the owner's existing limits.
- A source identity check that compares each critical canonical file with the exact bytes committed in the local Git HEAD, binds source SHA-256 and the immutable Git commit to the plan and refuses untracked/dirty intent references.
- A mandatory portable Hardware Audit: CPU-only viable, vendor-neutral 0..N accelerators, HRB-only resources and central Model Router. Hardware Audit of the actual executing host remains an independent runtime responsibility.

The output is deliberately SOURCE_BOUND_DESIGN_ONLY. Static source verification and source hash checks must NOT masquerade as Security approval, model admission, HRB lease, current-host runtime evidence or canonical proof. Existing authorities independently validate these at effect time and on resume.

## Interfaces

- design_preflight(root, user_goal, canonical_intent_path, task_steps): non-executing immutable-source and DAG report, with source hashes and explicit outstanding admissions.
- compile_source_bound_plan(root, user_goal, canonical_intent_path, task_steps): composes the first function with existing compile_plan and AgentWorkloadTask validation; refuses reuse gaps or blocked existing checks.
- canonical/intents/FA3-GOAL-EXECUTION-APPLICATION-INTENT-2026-09-28.json: the module's own ApplicationIntent, namespace/coexistence envelope, required reuse lookups and portable Hardware Audit.
- tests/test_goal_preflight.py and the dedicated workflow check real committed catalogs, no unknown UAF/agent admission, no write-via-read declaration, no dangling/cyclic/deep DAG, and no runtime or current-host promotion claims.

This extension introduces zero capabilities and zero architectural authorities. Temporal remains sole global durable lifecycle authority, UAF and central MCP Gateway mediate effects, HRB alone admits CPU/GPU/NPU/NUMA resources, Model Router owns provider/model routing, the existing Security authority grants approvals, and canonical Evidence/Gate alone can VERIFY a result. Decision Fabric/Jev may advise only over already deterministically eligible candidates; no source content can authorize its own execution.

## Next implementation gates

P2 completion requires genuine authenticated, exact-scope Security approval and live HRB/Model Router/runner receipts from existing interfaces; the committed-source design preflight cannot generate or approve these receipts. Add an authorized per-task dependency DAG-to-UAF plan compiler with idempotency and revocation semantics.

P3 requires an admitted existing Temporal workflow and Agent Workload bridge, real pause/restart/cancel, runtime Security/HRB validation and actual task effects through UAF only. P4 requires independently fetched and verified canonical evidence, test artifacts and human signoff before VERIFIED. P5 adds bounded authorized retries and rollback. P6/7 add Control Center and per-application adapters, preserving native project files and retaining both Wayland and X11.

## Mandatory acceptance boundaries

Run the dedicated preflight workflow and exact-head full repository Canonical, Reuse Discovery, Capability Model, Agent Workload and distribution gates. The release projection must be regenerated from the final, clean committed snapshot using existing governed tooling; no hand-edited hashes or gate bypass. This PR does not claim current-host E2E, specific host accelerator availability, production runner admission, permission to add an AI participant, or new provider installation.

Do not modify protected system ports (including existing AdGuardHome endpoints), vendor hardware operating envelopes or excluded proprietary real-time engine integrations as a hidden goal side effect.
