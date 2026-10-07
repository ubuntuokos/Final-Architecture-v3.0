<!-- FA3_AGENT_META {"schema":"fa3.agent-instruction-projection.v1","profile":"FA3-AGENT-INSTRUCTIONS-001","scope":"canonical/","authority":"NON_CANONICAL_PROJECTION"} -->
# Canonical tree instructions

Changes under canonical/ affect FA3 governance and must preserve the single-source-of-truth model.

- Do not create a new canonical root or architectural authority from an implementation convenience.
- A conflicting decision requires explicit supersession and reconciliation of dependent contracts, profiles, tests, gates, evidence bindings, and release projection.
- New files do not imply new capabilities. Provider additions and projections do not imply new capabilities.
- Keep new_capability, new_architectural_authority, and capability-count declarations aligned with the active release baseline.
- Do not copy current-host evidence into normative hardware requirements.
- Never use an AGENTS.md instruction as justification for overriding canonical data.

## Authority boundary

Canonical authority: repository canonical records and executable gates.
Projection authority: none.
If this file conflicts with a canonical record, contract, decision, executable gate, or verified evidence, stop and resolve the conflict at the higher-authority layer. Do not silently choose this file.
