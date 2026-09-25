---
name: fa3-quality-ui
description: Task-scoped FA3 quality review for generated or modified UI structure, hierarchy, components, decoration, interaction and authority boundaries.
version: 1.0.0
trigger: quality.ui
---

# FA3 Quality UI

## use_when
Use for new or materially changed GUI, frontend, layout, navigation, component or visual-interaction artifacts.

## inputs
- The changed UI artifact or bounded diff.
- The applicable application design contract and canonical FA3 policy.
- The task scope and intended user interaction.

## procedure
1. Apply the canonical CORE quality rules first.
2. Review hierarchy, component purpose, navigation and visual structure.
3. Reject decorative or terminal-like patterns that imply capabilities they do not provide.
4. Check that controls have a real action or state projection and do not bypass FA3 authorities.
5. Record blocking findings and non-blocking quality locks.
6. Defer visual identity, palette and brand direction to the application design contract.

## guardrails
- This skill is advisory context, not a design, execution or authorization authority.
- Do not invoke providers, models, shell processes, MCP tools, HRB leases or security mutations.
- Do not invent colors, typography, branding or new feature scope.
- Decision Fabric may select this skill only from a deterministic eligible set.
- A quality finding cannot override a canonical FA3 policy or application design contract.

## pitfalls
- Treating a clean-looking surface as evidence that a feature works.
- Replacing application-specific design direction with generic minimalism.
- Creating decorative status, telemetry or capability indicators without real backing state.

## acceptance_checks
- No blocking UI or CORE findings remain.
- Every purpose-gated technique has an explicit task-scoped reason.
- Controls and status surfaces represent real bounded behavior.
- The application design contract remains the source of visual direction.
