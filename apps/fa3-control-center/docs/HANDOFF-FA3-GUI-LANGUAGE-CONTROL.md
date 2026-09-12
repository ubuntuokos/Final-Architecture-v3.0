# Handoff — FA3 GUI Language Control

Consumer workstream: **FA3 GUI készítése / FA3 Control Center**  
Source profile: `FA3-GUI-LANGUAGE-CONTROL-001`  
Source branch: `feat/fa3-gui-language-control`  
Parent GUI branch: `feat/fa3-gui-settings-mentor-coach` (PR #144)

## What is ready

The following artifacts are ready for the GUI workstream:

1. `qml/LanguageControlPage.qml` — native Qt/QML Language Control surface.
2. `docs/FA3-GUI-LANGUAGE-CONTROL-001.md` — architectural and acceptance contract.
3. CMake registration of the QML component on this branch.

## Integration intent

The page should be exposed from the FA3 Control Center without creating a new authority. Recommended placement is adjacent to Model Manager or as a first-class Language Control entry, because it projects model-language capability and mediation state rather than merely localizing static UI strings.

Do not merge it conceptually into the existing `Language & Region` static-GUI locale section. Static i18n and runtime Language Bridge mediation have different authority and policy boundaries.

## Required bindings

The GUI workstream may bind these properties when backend adapters become available:

```text
nativeLanguages
mediatedLanguages
executionLanguage
mediationRequired
mediationPath
translatorProvider
dataClassification
cloudEffective
validationStatus
confidence
evidenceId
protectedTokenStatus
speechRoute
```

User preference properties (`userLanguage`, `outputLanguage`, `preferNative`, `allowMediated`, `localFirst`, `cloudRequested`, `validationMode`, `viewMode`) are persisted through the existing `SettingsStore` surface.

## Required invariants

- Keep capability count unchanged by this GUI projection.
- Add no architectural authority.
- Keep native and mediated model-language capability separate.
- Never map missing backend state to PASS.
- Never allow the GUI to bypass a policy denial.
- `SECRET` data never becomes externally translatable through a UI toggle.
- Original source remains authoritative; translation remains derived.
- Preserve provider neutrality.

## Navigation integration

When integrating into `AppShell.qml`, add a navigation key such as `languageControl` and instantiate `LanguageControlPage` at the matching `StackLayout` index. Bind the existing `fa3Settings`, palette and scale properties exactly as other native pages do.

Illustrative binding shape:

```qml
LanguageControlPage {
    settings: fa3Settings
    surface1: window.surface1
    surface2: window.surface2
    textPrimary: window.textPrimary
    textMuted: window.textMuted
    accent: window.accent
    uiScale: window.uiScale
    fontScale: window.fontScale
    language: fa3Settings.language
}
```

Runtime-derived properties must stay unbound until a real backend projection exists. The default `UNKNOWN/PENDING_BACKEND` state is deliberate.

## Acceptance before parent-GUI reconciliation

Run/verify:

- QML/CMake build for `fa3-control-center`;
- `GLC-001` through `GLC-010` from the profile contract;
- visual check in User, Expert and Admin modes;
- `SECRET + cloudRequested` cannot appear effective/allowed;
- no regression to PR #144 settings, Mentor, Coach, Manager or Inspector surfaces;
- no capability-count or authority-count drift.

## Workstream relationship

This is intentionally a child change set of PR #144 so the Language Control can be reviewed and consumed by the ongoing GUI conversation without mutating the GUI branch out from under that workstream. Reconcile/merge this child only after the parent GUI branch state is understood.
