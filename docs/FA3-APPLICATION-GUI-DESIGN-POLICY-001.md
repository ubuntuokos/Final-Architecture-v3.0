# FA3 Application GUI Design Policy

Status: **CANONICAL P0**  
Policy: `FA3-APPLICATION-GUI-DESIGN-POLICY-001`  
Gate set: `FA3-APPLICATION-GUI-DESIGN-GATESET-001`  
Capability baseline: **175 unchanged**  
Scope: **RETROACTIVE / FORWARD-ENFORCED / CHANGE-SYNCHRONIZED / DESIGN-SYSTEM-LOCKED**

## Rule

Every FA3 application must be classified as `GUI_REQUIRED`, `GUI_POSSIBLE`, or `HEADLESS_ONLY`. GUI-required or GUI-possible applications must include GUI design in the application plan. Headless-only classification requires an explicit justification.

The policy is retroactive: planned, in-progress, materialized, updated and future FA3 applications are in scope. There is no grandfathering. Existing GUI is preserved when it is functionally correct, correctly placed, FA3-design-system compliant and synchronized with the manual.

## Placement

Two placement decisions are required:

1. FA3-level placement: `FA3 Platform -> Product Family -> Application -> Surface`.
2. Application-local placement: menu/submenu, toolbar, panel, workspace, context menu, command palette, settings, status/progress, shortcut and Help/Manual surfaces as applicable.

A planner may propose placement. Exact final application-local placement requires explicit owner approval. Missing prior approval becomes `GUI_PLACEMENT_REVIEW_REQUIRED`; approval must never be fabricated.

## FA3 appearance lock

All application GUI must use the FA3 visual and interaction language. An application may have a function-specific layout, but it may not establish an independent typography, color system, component style, iconography standard, navigation language, accessibility model or interaction system.

External/donor UI may inform workflow or interaction patterns, but the final integrated UI requires FA3-native adaptation.

## Change synchronization

Any material functional delta requires a GUI impact assessment. The result is one of:

- `NO_GUI_CHANGE`
- `GUI_UPDATE_REQUIRED`
- `GUI_REDESIGN_REQUIRED`
- `NEW_GUI_SURFACE_REQUIRED`
- `GUI_ELEMENT_REMOVAL_REQUIRED`

A removed function may not leave orphan GUI. A required GUI change ships in the same change set as the function it exposes. GUI may not advertise an unavailable function, and a user-facing function may not be treated as complete when its required GUI is still pending.

## Shared GUI

Shared FA3 GUI components are reused first. Application-local code contains only the context-specific projection/adapter unless a reviewed exception justifies duplication.

## Manual synchronization

The application manual must reflect the materialized FA3 GUI: real names, real menu/toolbar placement and actual workflow. Removed GUI may not remain documented, and unmaterialized GUI may not be described as available.

## Retroactive audit

`FA3-APPLICATION-GUI-RETROACTIVE-AUDIT-001` defines the mandatory review dimensions and lifecycle dispositions. It intentionally creates review obligations where evidence is absent instead of inventing historical owner approval.

## Runtime boundary

This is a static governance/materialization change. It does not claim physical Current Host PASS or runtime promotion.
