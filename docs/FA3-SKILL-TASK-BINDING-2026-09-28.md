# FA3: skill/task language and Developer Agent Coordinator binding

Date: 2026-09-28. Scope: existing Skill Fabric and existing Developer Agent Coordinator. Reference integration only; **NOT** a current-host production promotion or an issuer implementation. No new authority, capability, provider, daemon, GPU requirement or implicit provider selection.

## Integration

1. Existing Skill Fabric admission, deterministic selection, side-effect-free preview and existing issuer-verified admission/selection/lease callbacks remain prerequisites to \`activate_admitted_skill\`.
2. The task owner keeps the \`with activate_admitted_skill(...)\` scope live through coordinator use; the ephemeral source context is closed and the buffer cleared on scope exit. Workers never receive arbitrary repository paths or an opportunity to reopen an unchecked skill.
3. \`bind_language_checked_skill\` requires user/work/output language tags, an independently verified FA3 Language Admission receipt matching the exact task skill and source content digest, and NATIVE, VALIDATED or BRIDGED operability. A BRIDGED task requires separately verified \`fa3.language-bridge-mediation-receipt.v1\` bound to exact input/output digests; no silent EN/hu/default fallback and no automatic mediation or provider selection.
4. \`AgentTask.required_skill_id\` is an optional field. A task without a required skill follows the previous provider adapter path unchanged. A task with it **must** receive exactly one matching live \`TaskSkillBinding\` and an explicit \`spawn_with_skill\` adapter method. Generic \`spawn\` is never used as silent fallback for a required skill.
5. The adapter consumes the already verified content as **untrusted data**. It must still use existing UAF/Central MCP, Model Router, HRB, Secret Broker, sandbox and applicable approval gates for any action. \`SKILL_TASK_CONTEXT_DELEGATED\` logs digest/provenance/language only; no skill body in the log.
6. In the current reference test the fixture adapter records the safe metadata but delegates to the old deterministic worker, so the test demonstrates bounded wiring and denied fallback, **not a real external agent provider consuming instructions**. Real provider adapters and cross-host physical evidence need separate admission.

## Evidence and conflict boundaries

PR #412 (pending on #410) provides broader cross-authority execution bindings; avoid redefining them. Parent Skill Fabric remains the static/reference gate; the language admission issuer, bridge issuer, user authorization and Evidence authority remain separate. The reference tests use exact-object issuer callbacks as fixtures; production callbacks must validate issuer identity and authenticity. Context language validation does not create native language support on its own.

## Hardware Audit

CPU-only compatible; vendor and accelerator neutral 0..N; optional semantic model use only via Model Router and HRB. A display GPU cannot be silently co-opted. Control Center integration must remain Wayland-preferred/X11-compatible and session/desktop neutral.

## Required tests

Missing or extra skill context, generic-adapter fallback, expired or closed source context, wrong task, wrong language, invalid/unverified admission evidence, mismatched bridge source/target digests, and one positive two-worker reference flow with explicit skill-aware adapter.
