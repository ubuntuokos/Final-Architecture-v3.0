# FA3 selective resume and replay preflight

Adds a stateless guard **under**, not beside, the existing Temporal, Journal, Agent Workload and Closed-Loop contracts. It validates event order, hash chaining and an independently authenticated terminal digest, and projects per-effect status. Already committed side effects require independent verification rather than replay. Pending approvals remain pending. New effects always require fresh Security, UAF/MCP, HRB (as applicable), Model Router and existing Temporal lifecycle admission.

This is deterministic source-level protection, NOT an installed Temporal worker or a current-host recovery claim. The injected ledger verifier MUST be bound by an admitted backend to actual canonical evidence; checking self-reported JSON is insufficient.

Hardware audit: CPU-only, vendor neutral, accelerators 0..N, no fixed devices, backend, display GPU recruitment or tuning; preserve capability count 175. No new durable/evidence authority and no donor source copied.
