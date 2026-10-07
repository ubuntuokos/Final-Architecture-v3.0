<!-- FA3_AGENT_META {"schema":"fa3.agent-instruction-projection.v1","profile":"FA3-AGENT-INSTRUCTIONS-001","scope":".github/workflows/","authority":"NON_CANONICAL_PROJECTION"} -->
# CI workflow instructions

Workflows enforce repository policy; they do not create canonical architecture.

- Do not weaken, conditionally skip, or mask a mandatory fail-closed gate to make CI green.
- Keep reference/hosted CI evidence distinct from current-host runtime conformance.
- A workflow may regenerate derived release projection data, but must not silently alter canonical semantics.
- New agent-instruction changes must run the agent-instruction gate and the hardware portability regression gate.
- Preserve least privilege for workflow permissions and do not expose secrets in logs.

## Authority boundary

Canonical authority: repository canonical records and executable gates.
Projection authority: none.
If this file conflicts with a canonical record, contract, decision, executable gate, or verified evidence, stop and resolve the conflict at the higher-authority layer. Do not silently choose this file.
