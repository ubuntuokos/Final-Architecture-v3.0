# FA3 Skill Fabric — opt-in developer agent and language preflight

This is a **stacked PR** on top of the verified-materialization change.
Existing `AgentTask` gains an optional tuple of `required_skill_ids`.
When set, `Coordinator.spawn_workers` fails closed unless it receives an
explicit callback returning exactly the expected verified, developer-scoped
skill receipts. The callback runs immediately before each provider spawn.
Legacy tasks with no skill requirement retain the existing execution path.

`fa3_skill_task_binding.py` supplies such a callback function:
`task_skill_preflight(task, bindings, language_context)`. It calls the
shared rehash-at-use materializer and the existing Language Gateway
validation helpers. Work and output languages must have an explicitly
supplied NATIVE, VALIDATED or BRIDGED status from the Language Admission
authority; there is no implicit English or Hungarian fallback.

The caller MUST authenticate the supplied registry/receipt/language-status
snapshots with their actual FA3 authorities. This patch neither grants
new authority nor routes models, tools or resources. The existing
`ProviderAdapter.spawn` contract is unchanged: verification is a
coordinator-side preflight and does **not** automatically project SKILL.md
bytes into the worker. A true production consumer still needs an approved
task-scoped projection/channel and an independent end-to-end test.

Hardware audit: all paths are CPU-only, vendor-neutral and
accelerator-neutral; no GUI/session/vendor requirement is introduced.
No current-host runtime promotion is asserted.
