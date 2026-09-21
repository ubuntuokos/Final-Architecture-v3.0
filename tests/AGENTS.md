<!-- FA3_AGENT_META {"schema":"fa3.agent-instruction-projection.v1","profile":"FA3-AGENT-INSTRUCTIONS-001","scope":"tests/","authority":"NON_CANONICAL_PROJECTION"} -->
# Test instructions

Tests protect canonical behavior and negative boundaries.

- Never weaken, delete, skip, or rewrite a valid test merely to make a change pass.
- When a test and implementation disagree, determine whether the implementation, test, or canonical contract is stale before changing anything.
- Add negative tests for authority escalation, silent fallback, bypass behavior, fabricated evidence, and hardware-baseline regression when relevant.
- Synthetic/reference tests cannot be reported as current-host runtime evidence.
- Keep tests deterministic and independent of a specific accelerator vendor unless the test is explicitly provider-scoped.

## Authority boundary

Canonical authority: repository canonical records and executable gates.
Projection authority: none.
If this file conflicts with a canonical record, contract, decision, executable gate, or verified evidence, stop and resolve the conflict at the higher-authority layer. Do not silently choose this file.
