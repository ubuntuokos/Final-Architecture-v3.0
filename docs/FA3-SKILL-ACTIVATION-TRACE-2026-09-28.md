# FA3 Skill Activation Trace and Reuse Audit (2026-09-28)

Status: **source-level audit and implementation baseline, NOT a current-host execution PASS**. Main snapshot: `4fed951f30d5a6a43c4df2f3dc9fc8f829358ec7`. Scope: the canonical `FA3-SKILL-FABRIC-001` path and the five FA3-native quality skills. Does not create a capability, authority, daemon, provider, or new skill registry.

## Required donor/reuse lookup (before implementation)

Consulted `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`, `canonical/FA3-EXTERNAL-SKILL-RADAR-001.json`, and `canonical/assessments/FA3-SKILL-FABRIC-REUSE-ASSESSMENT-001.json`. Reuse the existing Skill Fabric, FA3-SCS-001, Reuse Discovery, Context Selection, UAF/Central MCP Gateway, Model Router, HRB, Language Gateway, existing Agent Coordination and Evidence authority. Agent Skills format, addyosmani/agent-skills, NVIDIA/SkillSpector and microsoft/SkillOpt are pattern references **only**, subject to source/license and separate admission checks; radar membership is not admission.

## Static source trace

| Stage | Existing source | Verified at source level | Remaining physical proof |
|---|---|---|---|
| Registry | `canonical/skill-registry.json` | Five admitted FA3-native quality SKILL.md entries; metadata SSOT explicitly not an execution authority | Per-entrypoint digest-bound admission receipts and actual use evidence |
| Discovery | `src/fa3_skill_discovery.py` | Read-only fingerprint and deterministic admitted/task-class prefilter | All real consumer entrypoints must call the common selector |
| Candidate normalization and inspection | `src/fa3_skill_ecosystem.py` | Immutable source metadata, instruction scan; external candidates kept untrusted | Real candidate inspection with source snapshots, negative/adversarial cases |
| Package admission | `src/fa3_skill_fabric_gate.py` | Declarative immutable source, digest syntax and equality of supplied attestation, review/license/evaluation checks | Match supplied digest with **bytes actually opened** for task use |
| Preview and projection | `src/fa3_skill_fabric_v13.py` | Typed interface, bounded context, side-effect-free preview, host collision checks | Actual host projection and physical per-task materialization |
| Hardening | `src/fa3_skill_fabric_v14.py` | Quality floor, provenance/source grounding, path/action preconditions and artifact binding | Consumer-verified admission/use receipts and evidence attribution |
| Use-receipt validation | `skill_use_allowed` in `src/fa3_skill_fabric_gate.py` | Structural validation of receipt fields, routes and digest **format** | Bind independently verified exact source bytes, selection/task identity and expiry to use |
| Developer workers | `src/fa3_developer_agent_coordination.py` | Typed task, isolated worktrees, provider adapters and reference E2E | Real opt-in, prevalidated skill context delivered to a worker without adding worker authority |
| Language | `src/fa3_language_gateway_gate.py`; `src/fa3_language_bridge.py` | Existing user/work/output language and admitted mediation policy | Task-level skill-language eligibility and no silent language fallback |
| CI | `.github/workflows/fa3-skill-ecosystem.yml` | Static syntax, regressions and existing gates | Watch all affected runtime/worker/GUI paths; physical current-host tests separate |
| Physical producer | `src/fa3_cap080_verified_skill_supply_chain_current_host.py` | Positive, negative, rollback reference producer and physical host prerequisites | Physical run for admitted native skill + independent receipt/source tamper tests |

**Finding (static-source scope):** `skill_use_allowed` checks receipt-supplied hexadecimal digests rather than reopening the materialized skill. The inspected production coordination path does not visibly invoke skill materialization; this is an **integration gap to close and test**, not a claim that some other uninspected application bypasses a gate. Existing PR #412 already proposes cross-authority execution binding and receipt validation on top of PR #410; avoid duplicating its scope or treating it as merged.

## Implementation acceptance sequence

1. Add one read-only, exact-byte, no-symlink, task-scoped activation primitive under existing Skill Fabric. It must reopen a locally snapshotted admitted SKILL.md **without any remote fetch**, compare actual bytes with the admitted digest and verify the exact task/skill/selection/admission tuple. For a multi-file package fail closed until the complete normalized manifest/snapshot verifier is available.
2. Integrate through the existing Developer Agent Coordinator's **opt-in** typed task path after admission, selection, preview and language policy checks. A skill document never grants tool, shell, model, secret or resource authority; only UAF/Central MCP and existing runtime authorities can execute actions.
3. Produce deterministic receipt + per-task cleanup; forward evidence **only** through existing Evidence authority. No unsigned JSON receipt or self-declared PASS must become an authority.
4. Add tamper, stale/foreign-task, symlink, traversal, selection expansion, no-activation and non-regression tests. Extend the existing Skill Fabric workflow, do not replace `bin/fa3-enforce`.
5. Expose operator **read-only** activation and denial state in the existing Control Center. Do not fabricate empty/PASS production telemetry if a live evidence bridge is absent.
6. Run static regressions and physical CAP-080 positive/negative/rollback on the actual target host. Only a fresh host-specific evidence artifact may claim current-host PASS.

## Hardware Audit

CPU-only is mandatory; vendor-neutral AMD/Intel/NVIDIA/other 0..N accelerators; no globally required GPU/NPU, no fixed machine SKU or provider. Optional semantic checking uses the central Model Router and HRB. A display-designated GPU remains excluded from automatic AI selection if other GPU/NPU resources are present. Qt6/QML must remain session-agnostic (Wayland preferred, X11 supported, no KDE-only assumption).

## Release and dependency boundaries

Read active capability count from `canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json` (current v3.1.0 = 175); preserve historical 143 contracts/tests. Capability delta 0; authority delta 0. PR #412 (pending, stacked on #410) owns the wider cross-authority execution closure; this work covers exact-byte task activation, consumer integration and corresponding physical evidence, not a duplicate execution authority.
