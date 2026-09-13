# Handoff — FA3 GUI Language Control

Consumer workstream: **FA3 GUI készítése / FA3 Control Center**  
Source profile: `FA3-GUI-LANGUAGE-CONTROL-001`  
Original child PR: **#147** — merged into parent GUI branch  
Parent GUI branch: `feat/fa3-gui-settings-mentor-coach` (PR #144)

## Integrated state

The Language Control is now part of the parent FA3 GUI branch.

Available artifacts:

1. `qml/LanguageControlPage.qml` — native Qt/QML Language Control surface.
2. `qml/LanguageAwareAppShell.qml` — thin wrapper over the existing `AppShell` that exposes Language Control as a right-side drawer.
3. `docs/FA3-GUI-LANGUAGE-CONTROL-001.md` — P0/MUST architectural and GLC acceptance contract.
4. CMake registration for both Language Control QML components.
5. `src/main.cpp` launches `LanguageAwareAppShell.qml`.
6. Unified release-projection reconciliation remains automatic through repository automation.

## GUI access

Language Control is reachable directly from the running FA3 Control Center through:

- the floating `文/A` launcher button;
- application shortcut `Ctrl+Shift+L`;
- the right-side native drawer.

This integration deliberately avoids rewriting the large `AppShell.qml`, reducing merge risk with the ongoing GUI workstream. The GUI workstream may later promote the drawer to a first-class sidebar navigation entry without changing the authority contract.

## Architectural boundary

Do **not** merge runtime mediation into the static `Language & Region` locale settings. Static GUI i18n and runtime Language Bridge mediation are separate concerns.

The GUI contributes:

- authority: **0**
- capability-count change: **0**
- provider mandate: **none**

The GUI must not become translation, model-routing, policy, evidence, or promotion authority.

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

User preferences remain persisted through the existing `SettingsStore` surface:

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

## Mandatory invariants

- Native and mediated model-language capability remain separate.
- Missing backend state never becomes PASS/ALLOWED/NO by inference.
- GUI intent cannot bypass backend policy.
- `SECRET` external translation is denied by contract.
- Original source remains authoritative; translation remains derived.
- Provider neutrality is mandatory.
- Static GUI localization does not substitute for runtime mediation.
- Runtime-derived values stay fail-closed until a real adapter supplies them.

## Acceptance contract

Verify before claiming GUI implementation PASS for a new head:

- `FA3 GUI Gate` static-contract job passes;
- GUI canonical regression passes;
- GUI unit regression passes;
- Qt configure/build passes;
- `GLC-001` through `GLC-010` remain satisfied;
- unbound mediation state displays `UNKNOWN`, not `NO`;
- `SECRET + cloudRequested` never appears effective/allowed;
- no regression to Settings/Mentor/Coach/Manager/Inspector/Assistant surfaces;
- no capability-count or authority-count drift;
- unified release projection contains the current Language Control blobs.

## Runtime evidence boundary

A successful Qt/static GUI build proves the GUI implementation and contract shape only. It does **not** prove a production Language Bridge backend. Backend-derived fields remain `UNKNOWN/PENDING_BACKEND` until real local/online translation adapters, policy routing, semantic validation, speech routing, and Evidence Registry integration are materialized and evidenced.

This file and PR #144 are the repository-visible handoff source for the separate **FA3 GUI készítése** conversation/workstream.
