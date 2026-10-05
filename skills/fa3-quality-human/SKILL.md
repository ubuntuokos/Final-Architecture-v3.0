---
name: fa3-quality-human
description: Task-scoped FA3 human-interaction quality review for accessibility, keyboard, focus, states and understandable controls.
version: 1.0.0
trigger: quality.human
---

# FA3 Quality Human

## use_when
Use for UI work that changes interaction, accessibility exposure, keyboard/focus behavior, control states or human-readable status.

## inputs
- The changed interactive artifact.
- The intended control semantics and state model.
- Applicable accessibility and desktop contracts.

## procedure
1. Check interactive elements for keyboard reachability and visible, understandable state.
2. Review focus suppression and accessibility suppression as purpose-gated decisions.
3. Check that interaction text describes actions rather than gestures where practical.
4. Review contrast-sensitive or low-opacity content as a quality-lock finding.
5. Report findings without assigning execution or accessibility conformance authority to this skill.

## guardrails
- This skill does not replace formal accessibility testing or current-host GUI evidence.
- Do not mutate system accessibility settings.
- Do not hide a real state or failure merely to simplify the UI.
- Do not grant authority through a UI affordance.

## pitfalls
- Assuming mouse usability implies keyboard usability.
- Hiding unavailable/error states instead of explaining them.
- Treating a visual review as full accessibility certification.

## acceptance_checks
- No blocking HUMAN findings remain.
- Interactive controls preserve understandable state and authority boundaries.
- Any suppressed focus or accessibility exposure is explicitly justified.
