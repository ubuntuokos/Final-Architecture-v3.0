# Handoff — FA3 GUI Language Control

Consumer workstream: **FA3 GUI készítése / FA3 Control Center**  
Source profile: `FA3-GUI-LANGUAGE-CONTROL-001`  
Source branch: `feat/fa3-gui-language-control`  
Child PR: **#147**  
Parent GUI branch: `feat/fa3-gui-settings-mentor-coach` (PR #144)

## Ready for the GUI workstream

1. `qml/LanguageControlPage.qml` — native Qt/QML Language Control surface.
2. `docs/FA3-GUI-LANGUAGE-CONTROL-001.md` — P0/MUST architectural and GLC acceptance contract.
3. CMake registration for `LanguageControlPage.qml`.
4. Automatic unified release-projection reconciliation on the child branch.

## Integration intent

Expose this page from FA3 Control Center without creating new authority. Recommended placement is adjacent to Model Manager or as a first-class Language Control entry because it projects model-language capability and mediation state.

Do **not** merge the concept into the existing static `Language & Region` locale settings. Static GUI i18n and runtime Language Bridge mediation have different authority and policy boundaries.

## Backend bindings

Bind runtime values only when real backend projections exist:

```text
nativeLanguages
mediatedLanguages
executionLanguage
mediationStateKnown
mediationRequired
mediationPath
translatorProvider
dataClassification
cloudPolicyStatus
cloudEffective
validationStatus
confidence
evidenceId
protectedTokenStatus
speechRoute
```

`mediationRequired` is meaningful only when `mediationStateKnown=true`. `cloudEffective` is meaningful only after an effective backend policy result. Missing runtime state remains `UNKNOWN/PENDING_BACKEND`.

User preferences are already expressed through the existing `SettingsStore` surface:

```text
userLanguage
outputLanguage
preferNative
allowMediated
localFirst
cloudRequested
validationMode
viewMode
```

## Invariants

- Capability count is unchanged by this GUI projection.
- Architectural authority contribution is zero.
- Native and mediated model-language capability remain separate.
- Missing backend state never becomes PASS/ALLOWED/NO by inference.
- GUI intent cannot bypass backend policy.
- `SECRET` external translation is denied by contract.
- Original source remains authoritative; translation remains derived.
- Provider neutrality is mandatory.

## Navigation integration

When the parent GUI workstream reconciles this child PR, add a navigation key such as `languageControl` to `AppShell.qml` and instantiate `LanguageControlPage` at the matching `StackLayout` index.

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

Do not bind runtime-derived properties to placeholders other than the component's fail-closed defaults until real adapters exist.

## Acceptance before parent reconciliation

Verify:

- QML/CMake build for `fa3-control-center`;
- `GLC-001` through `GLC-010`;
- User, Expert and Admin views;
- unbound mediation state displays `UNKNOWN`, not `NO`;
- `SECRET + cloudRequested` never appears effective/allowed;
- no regression to PR #144 Settings/Mentor/Coach/Manager/Inspector surfaces;
- no capability-count or authority-count drift;
- unified release projection contains the current LanguageControlPage blob.

## Current evidence boundary

An earlier child-head state passed the `FA3 GUI Gate`. After the explicit fail-closed mediation-state correction, the release projection was automatically reconciled, but the newest GUI Gate invocation may require an external/manual workflow action. Do not claim production GUI PASS for the newest head until a successful gate run exists.

This child PR and this handoff are the repository-visible source for the separate **FA3 GUI készítése** conversation/workstream.
