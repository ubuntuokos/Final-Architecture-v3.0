# FA3-GUI-LANGUAGE-CONTROL-001

Status: **P0 / MUST** GUI control and observability profile  
Authority contribution: **0**  
Capability-count effect: **0**  
Provider coupling: **none**

## Purpose

`FA3-GUI-LANGUAGE-CONTROL-001` is the native FA3 Control Center projection for multilingual semantic interoperability. It exposes operator intent, model language capability, mediation routing, data-policy outcome, semantic validation and evidence without becoming a translation, security, model-routing, evidence or promotion authority.

The GUI is a control/observability surface only. Effective decisions remain in canonical backend authorities.

## Architectural boundary

The surface composes with the following contracts/projections when materialized and bound:

- `FA3-LANGUAGE-BRIDGE-001` — multilingual semantic mediation;
- `FA3-MODEL-MANAGER-001` and canonical Model Registry — model inventory and native capability evidence;
- `FA3-VOICE-001` / STT / TTS — speech mediation;
- canonical security/policy enforcement — external-provider allow/deny decisions;
- Evidence Registry — provenance, validation and execution receipts.

It MUST NOT create a parallel model registry, translation authority, policy engine or evidence authority.

## Native vs mediated capability

Native and FA3-mediated language support MUST remain separate:

```text
Native:   EN
Mediated: HU, DE, FR
Route:    HU -> EN -> MODEL -> EN -> HU
```

Mediated support MUST NOT rewrite or inflate model-native capability evidence.

## User modes

**User** exposes input/output language, prefer-native intent, allow-mediated intent and concise mediation state.

**Expert** additionally exposes execution language, mediation route/provider, data classification, local-first/cloud intent, effective cloud-policy projection, semantic-validation status and confidence.

**Admin / Architecture** additionally exposes Evidence ID, protected-token integrity and speech mediation route.

## Runtime projection contract

Backend-bindable runtime values:

```text
nativeLanguages        = []
mediatedLanguages      = []
executionLanguage      = UNKNOWN
mediationStateKnown    = false
mediationRequired      = false   # meaningful only when mediationStateKnown=true
mediationPath          = PENDING_BACKEND
translatorProvider     = PENDING_BACKEND
dataClassification     = INTERNAL
cloudPolicyStatus      = PENDING_BACKEND
cloudEffective         = false   # meaningful only after an effective policy result
validationStatus       = PENDING_BACKEND
confidence             = -1      # UNKNOWN
 evidenceId            = PENDING_BACKEND
protectedTokenStatus   = PENDING_BACKEND
speechRoute            = PENDING_BACKEND
```

Operator-preference values are persisted by the existing `SettingsStore`:

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

`UNKNOWN` and `PENDING_BACKEND` are first-class states. `mediationRequired=false` MUST NOT render as `NO` until `mediationStateKnown=true`. An absent backend result MUST NOT be inferred as PASS, ALLOWED or successful mediation.

## Data-classification projection

| Classification | External translation |
|---|---|
| `PUBLIC` | may be allowed |
| `INTERNAL` | policy-dependent |
| `CONFIDENTIAL` | local-first / restricted |
| `SECRET` | forbidden |

`cloudRequested` is operator intent only. `cloudPolicyStatus` and `cloudEffective` come from backend policy enforcement. For `SECRET`, the GUI MUST visibly project external translation as denied and MUST NOT expose a bypass.

## Protected content

The Language Bridge contract preserves, unless an explicit typed rule says otherwise:

- source code and shell commands;
- paths;
- API names and structured keys;
- model identifiers;
- hashes;
- FA3 canonical IDs.

The GUI exposes `protectedTokenStatus`; it does not implement preservation logic itself.

## Authority and provenance

The original source remains authoritative. Translation is a derived projection with provenance. Displaying or accepting a translation in the GUI MUST NOT promote it into canonical authority.

Static Control Center localization and runtime semantic mediation are separate:

```text
GUI locale/i18n != FA3 Language Bridge runtime mediation
```

Changing GUI locale MUST NOT silently change model routing, data classification or external-provider policy.

## Acceptance contract

| ID | Requirement | Fail-closed expectation |
|---|---|---|
| `GLC-001` | Native and mediated languages visibly distinct | no merged language list |
| `GLC-002` | Effective routing/policy comes from backend authority | GUI cannot self-authorize |
| `GLC-003` | `SECRET` external translation denied | no bypass |
| `GLC-004` | Mediation route/provider provenance observable | unknown stays explicit |
| `GLC-005` | Protected-token integrity observable | absent evidence is not PASS |
| `GLC-006` | Semantic-validation status observable | absent evidence is not PASS |
| `GLC-007` | Provider-neutral contract | no mandatory vendor |
| `GLC-008` | Speech mediation route projectable | no duplicate Voice authority |
| `GLC-009` | `UNKNOWN` / `PENDING_BACKEND` never rendered as PASS | fail closed |
| `GLC-010` | Original source remains authoritative | translation stays derived |

## Current implementation boundary

`qml/LanguageControlPage.qml` implements the Qt/QML surface and preference capture. Backend Language Bridge results are intentionally not fabricated. Runtime-derived fields stay `UNKNOWN` or `PENDING_BACKEND` until actual adapters bind them.

This provides an executable GUI contract without claiming production Language Bridge runtime evidence that does not exist.
