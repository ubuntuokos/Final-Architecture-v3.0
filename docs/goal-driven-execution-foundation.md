# FA3 Goal-Driven Execution Foundation — executable P1/P2/P4 baseline

Status (2026-09-28): source-level and deterministic tests only. This is **not a production goal executor or a new canonical authority**.

Parent research and donor plan: PR #476, goal-driven-agent-donor-curation-2026-09-28.md. This code reuses the existing 175-capability baseline, FA3 Coach, Orchestration Workforce, Agent Workload Runtime, Decision Fabric, Reuse Discovery, HRB, Model Router, UAF/MCP Gateway, Journal and canonical Evidence/Gate.

## Implemented scope

- canonical/contracts/FA3-GOAL-EXECUTION-CONTRACTS-001.schema.json: versioned user-owned goal, explicit scope, mandatory independently verifiable criteria, AUTO/APPROVAL/HYBRID modes and exact bounded Agent Workload limits.
- src/fa3_goal_execution.py: prepare_goal and validate_goal reject invalid acceptance criteria, secrets/physical model pins and unsafe scope; compile_plan invokes **existing** Workforce design routing and validates **existing** AgentWorkloadTask records. Receipt strings are preflight **references only**, not permissions. assess_evidence reports per-criterion provenance completeness, but never declares VERIFIED; propose_repair returns only an in-scope bounded proposal and cannot invoke tools.
- tests/test_goal_execution_foundation.py: typed contract, criteria, authorization, route/workload, duplicate fanout, forged evidence, stale revision and bounded repair conformance.
- .github/workflows/fa3-goal-execution-foundation.yml: focused source/negative regression and existing related contracts.

A plain-language goal is not executable, a goal plan grants no tool/model/resource permissions, and a semantic judgment or a self-authored evidence reference cannot promote a goal.

## Workflow

1. Collect user-owned goal, measurable criterion, workspace, forbidden effects, approved modes, existing policy refs and seven explicit fanout/budget dimensions. All goal text is descriptive untrusted data.
2. Query existing Reuse Discovery and donor/application index; obtain real Security and Hardware Audit receipts before authorization. The current source-level preflight records references only; P2 must authenticate them.
3. Compile typed task candidates with the existing Orchestration Workforce design router, then validate against the Agent Workload contract. Each actual effect later requires UAF/MCP and fresh Security/HRB admission.
4. Run permitted tasks through **existing** Temporal as sole durable lifecycle owner; P3 must implement the actual runtime bridge. No direct third-party agent framework may execute these candidates.
5. Check independent criterion evidence through existing Journal/original artifacts and canonical Evidence/Gate. Source-level assess_evidence only requests independent verification; it cannot authenticate evidence or close a goal by itself.
6. Repair within granted limits or escalate, without permission expansion, newly introduced AI participants, hidden model fallback or infinite retries.

## Hardware Audit

Planning is CPU-only viable, vendor-neutral and works at 0..N accelerators. No fixed CUDA, ROCm, oneAPI, NPU, NUMA or display session assumption is introduced. Hardware discovery and actual resource placement remain the existing Hardware Discovery/HRB authorities. With any other GPU or NPU present, a display GPU may join AI only after explicit task-and-model-specific in-application assignment; never automatically. Wayland preferred, X11 supported when GUI arrives. Do not alter AdGuardHome ports or the host hardware/driver configuration as an incidental goal step.

## Remaining required for real execution

P2: consume authenticated scope-bound reuse/security/hardware/agent/runner receipts, verify registered AgentDefinition and UAF action contracts, compile dependency and idempotency-aware DAG.
P3: Temporal workflow and Agent Workload runtime bridge with real CPU-only current-host path, durable approvals, crash recovery, fresh HRB admission on resume and no direct provider calls.
P4: authenticated canonical evidence/artifact/independent-verifier integration with protected checkers, exact revision checks and independent human signoff.
P5: authorized bounded repair and compensation through UAF and existing policies, no permission enlargement.
P6: existing Control Center/Agent Workspace GUI, real isolated Developer Agent pilot on disposable Git branch and positive/negative/rollback evidence in each approval mode.
P7: attach the same goal contracts to Story/Screenplay, Prompt Creator, native FA3 Video Editor and QuickClip as appropriate, preserving .fa3video, .fa3clip, .kra, Ardour and all native project formats. Unreal remains excluded.

## Command-line usage

The implemented bin/fa3-goal entrypoint provides validate, plan, assess and repair commands. Each command consumes versioned JSON from --goal and optional --steps/--preflight/--observations files; use --goal - for stdin. None of these commands performs effects or grants authorization; plan returns typed candidates, assess always requires independent canonical verification, and repair only proposes bounded next steps. Invalid input returns status REJECTED without echoing secrets or untrusted content.

## Tests and release rules

Run: PYTHONPATH=src python3 -m unittest discover -s tests -p test_goal_execution_foundation.py -v

At merge time reconcile against exact main and all concurrent donor changes. Regenerate the canonical release projection with the governed repository generator from a clean committed snapshot; rerun exact-head CI. No source-only PASS implies current-host runtime qualification, provider admission, a completed goal, or global production promotion.
