# FA3 selective Developer Agent workspace hardening

Hardens the existing deterministic Developer Agent reference coordinator. Path checks deny Git metadata, symlink traversal (including dangling links), path escapes, unbounded agent/task IDs, control roots inside the canonical repo, and worktree-root symlinks. It does NOT claim that the deterministic host-process fixture is an admitted sandbox for arbitrary untrusted code.

Actual untrusted execution stays governed by FA3 Agent Workload Runtime and FA3-AGENT-SANDBOX-001 (admitted gVisor/WASI or permitted OCI). New changes are negative/path and reference regression gates only.

Hardware Audit: no device requirement, CPU-only test path, accelerators 0..N, no global vendor pin, HRB unchanged, no display GPU recruitment and no host tuning. Existing 175 capability/authority model unchanged. Donor references remain non-authoritative.
