# FA3 Development Mode + Unified Update Fabric

Reconciled: **2026-09-23**. Capability delta: **0**. Authority delta: **0**.

Development is a bounded mutable trust domain, never a Production bypass. Git-index snapshots are deterministic and non-authoritative; taint is sticky; Freeze creates a local immutable promotion candidate but is not Promotion.

GUI, agent and automation mutations use typed UAF actions. The Update Center creates only `DRAFT_NOT_SUBMITTED` intents and cannot install packages, restart services/host, write canonical state or self-approve.

Actions: `development.enter`, `development.snapshot`, `development.freeze`, `update.check`, `update.apply-selected`, `update.security`, `update.restart-choice`, `update.rollback`.

There is no blind Update All. Low-risk OS security maintenance may install in background, protected workloads cannot be silently interrupted, and host reboot is never silently forced.

Restart choices remain `RESTART_NOW`, `WHEN_IDLE_SAFE`, `SCHEDULE`, `LATER`. Decision Fabric cannot override user restart timing.

Host-critical categories are provider-neutral: `kernel`, `accelerator_driver`, `accelerator_runtime`, `critical_host_runtime`. Accelerator cardinality is `0..N`, CPU-only hosts are valid, and no vendor backend is globally pinned.

`FA3-DEV-UPDATE-RUNTIME-CONFORMANCE-001` remains `EXECUTABLE_REFERENCE_MATERIALIZED_CURRENT_HOST_E2E_PENDING`; no PR/reference result is a current-host promotion claim.
