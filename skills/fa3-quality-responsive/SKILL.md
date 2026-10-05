---
name: fa3-quality-responsive
description: Task-scoped FA3 quality review for reflow, fixed-size constraints, overflow and interaction across window sizes.
version: 1.0.0
trigger: quality.responsive
---

# FA3 Quality Responsive

## use_when
Use for changed layouts, frontend surfaces, desktop-window reflow, mobile/responsive projections or fixed-size component work.

## inputs
- The changed layout artifact.
- Supported form factors or window-size contract.
- The application design contract.

## procedure
1. Review large fixed dimensions and hard min/max constraints.
2. Check whether content can reflow without clipping or inaccessible controls.
3. Treat form-factor exclusions as product decisions that require an explicit reason.
4. Preserve the application design direction while removing unnecessary rigidity.
5. Emit warnings for suspicious fixed dimensions and fail on extreme general-surface constraints.

## guardrails
- Do not invent unsupported form factors.
- Do not rewrite the visual system merely to satisfy a generic responsive pattern.
- This skill is not a runtime window-management authority.

## pitfalls
- Assuming a desktop application never needs resize behavior.
- Replacing a purposeful fixed canvas with generic fluid layout.
- Ignoring text expansion and localization.

## acceptance_checks
- No blocking RESPONSIVE findings remain.
- Required form factors remain usable within their declared scope.
- Purposeful fixed-layout decisions are explicit and bounded.
