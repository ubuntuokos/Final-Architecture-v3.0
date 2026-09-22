<!-- FA3_AGENT_META {"schema":"fa3.agent-instruction-projection.v1","profile":"FA3-AGENT-INSTRUCTIONS-001","scope":"evidence/","authority":"NON_CANONICAL_PROJECTION"} -->
# Evidence instructions

Evidence records describe work that was actually executed or explicitly remains pending.

- Never fabricate receipts, command output, runtime observations, hashes, host capabilities, or PASS states.
- Preserve the distinction between reference/CI evidence and real current-host evidence.
- PENDING is valid when required execution has not occurred.
- Evidence may describe concrete hardware as an observation, but it must not redefine the global hardware baseline.
- Raw secrets, tokens, passwords, and private keys must never be stored in evidence.

## Authority boundary

Canonical authority: repository canonical records and executable gates.
Projection authority: none.
If this file conflicts with a canonical record, contract, decision, executable gate, or verified evidence, stop and resolve the conflict at the higher-authority layer. Do not silently choose this file.
