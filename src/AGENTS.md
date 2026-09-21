<!-- FA3_AGENT_META {"schema":"fa3.agent-instruction-projection.v1","profile":"FA3-AGENT-INSTRUCTIONS-001","scope":"src/","authority":"NON_CANONICAL_PROJECTION"} -->
# Source implementation instructions

Code under src/ implements canonical contracts; it does not define them.

- Keep provider selection, hardware discovery, and accelerator execution paths capability-driven and replaceable.
- Accelerator discovery is 0..N. Do not hard-code a vendor, runtime API, runtime ordinal, device count, PCI address, GPU SKU, or current-host topology as a global requirement.
- Keep logical CPU and physical-core accounting separate.
- Fail closed on ambiguous device/backend binding, missing required evidence, invalid authority, or silent fallback.
- Do not add a bypass path around MCP, HRB, security, approval, or evidence authorities.
- A gate implementation must report failure rather than manufacture a passing default.

## Authority boundary

Canonical authority: repository canonical records and executable gates.
Projection authority: none.
If this file conflicts with a canonical record, contract, decision, executable gate, or verified evidence, stop and resolve the conflict at the higher-authority layer. Do not silently choose this file.
