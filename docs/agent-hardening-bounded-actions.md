# FA3 selective agent hardening: bounded action binding

This is an additive, non-authoritative consumer of the existing Goal Execution Foundation and Decision Fabric. It creates a **design-time** intersection of goal-permitted actions, registered UAF actions, gateway-visible actions, Security-permitted actions and eligible registered agent identities. The typed Decision Fabric trace may select one candidate, but neither the trace nor this binding confers execution authority.

Callers must obtain authentic snapshots from the existing registry, Gateway and Security authorities. A string or caller-supplied snapshot alone does not constitute evidence. At runtime each effect requires fresh existing Security, UAF/MCP, HRB (where applicable) and Model Router admission. Temporal stays the sole durable owner.

Hardware Audit: metadata-only CPU-only operation; vendor neutral, 0..N accelerators, no display GPU enrollment, no hardware or port changes. Capability baseline 175; no new capabilities or architectural authorities. Repository CI tests are reference-level only, not current-host production evidence.
