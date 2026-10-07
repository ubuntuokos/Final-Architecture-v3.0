<!-- FA3_AGENT_META {"schema":"fa3.agent-instruction-projection.v1","profile":"FA3-AGENT-INSTRUCTIONS-001","scope":"bin/","authority":"NON_CANONICAL_PROJECTION"} -->
# Executable entrypoint instructions

Files under bin/ are operational entrypoints and must remain thin, deterministic, and auditable.

- Entrypoints may invoke governed modules but must not become parallel policy authorities.
- Propagate non-zero exit status from fail-closed gates.
- Do not hide failures, suppress required checks, or introduce convenience flags that bypass security, approval, evidence, or hardware admission.
- Do not embed secrets or host-specific hardware identities.
- Prefer repository-root discovery over hard-coded user paths.

## Authority boundary

Canonical authority: repository canonical records and executable gates.
Projection authority: none.
If this file conflicts with a canonical record, contract, decision, executable gate, or verified evidence, stop and resolve the conflict at the higher-authority layer. Do not silently choose this file.
