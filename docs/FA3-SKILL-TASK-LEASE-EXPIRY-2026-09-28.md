# FA3 Skill Fabric — task-instance lease and worker expiry hardening

This PR is stacked above the verified worker-context reference flow.
The original activation lease bound only a task *class* such as "developer",
not the actual task ID. The worker also received verified bytes without
independently checking expiration at consumption time.

A new optional `task_id` argument preserves generic reference-use callers,
but the developer projection now **requires** an exact task-instance binding.
The coordinator refuses duplicate/reused lease IDs within one coordinator
instance and records consumed IDs even during failure cleanup. The fixture
worker checks bound_task_id and timezone-aware expiry before changing its
test output, and denies duplicate lease IDs in a projection. Tests cover
wrong task ID, replay attempt and an expired delivered projection.

This work remains CI_REFERENCE_ONLY unless the existing Security Governance
and authoritative skill admission/selection issuers authenticate the claims.
An authority callback's boolean result is not cryptographic proof; the
non-reference evidence label explicitly reflects that limitation. Replay
denial across distributed coordinators still requires the existing central
authority's shared lease state, not a new Skill Fabric authority.

Hardware audit: CPU-only; accelerator count 0..N, vendor-neutral, no
display GPU or GUI dependency. The historical 143-capability contract is
not rewritten, and the active 175 release baseline remains unchanged.
