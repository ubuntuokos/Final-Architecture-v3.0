# FA3-GUI-LANGUAGE-CONTROL-001

Status: **P0 / MUST** GUI control and observability profile  
Authority contribution: **0**  
Capability-count effect: **0**  
Provider coupling: **none**

## Purpose

`FA3-GUI-LANGUAGE-CONTROL-001` is the native FA3 Control Center projection for multilingual semantic interoperability. It exposes user intent, model language capability, mediation routing, data-policy outcome, validation state and evidence without becoming a translation, security, model-routing or promotion authority.

The GUI is a control/observability surface only. Effective decisions remain in the backend canonical authorities.

## Architectural boundary

The control surface is designed to compose with:

- `FA3-LANGUAGE-BRIDGE-001` — multilingual semantic mediation contract;
- `FA3-MODEL-MANAGER-001` and the canonical Model Registry — model inventory and capability evidence;
- `FA3-VOICE-001` / STT / TTS projections — speech mediation;
- canonical security/policy enforcement — external-provider allow/deny decisions;
- Evidence Registry — provenance, validation and execution receipts.

This profile MUST NOT create a parallel model registry, translation authority, policy engine or evidence authority.

## Native vs mediated capability

The GUI MUST expose native and FA3-mediated language support as separate fields.

Example:

```text
Native:   EN
Mediated: HU, DE, FR
Route:    HU -> EN -> MODEL -> EN -> HU
```

A mediated language MUST NOT be represented as a model-native capability and MUST NOT mutate native capability evidence.

## User modes

### User

Expose only the minimum interaction surface:

- input language (`auto` allowed);
- output language (`same-as-input` allowed);
- prefer-native intent;
- allow-mediated intent;
- concise mediation state.

### Expert

Additionally expose:

- execution language;
- mediation path;
- translator provider projection;
- data classification;
- local-first preference;
- cloud-translation request intent;
- effective cloud-policy result;
- semantic validation mode/status;
- confidence.

### Admin / Architecture

Additionally expose:

- Evidence ID;
- protected-token integrity status;
- speech mediation route;
- provenance / derived-projection status.

## Runtime projection contract

The QML component exposes the following backend-bindable fields:

```text
profileId              = FA3-GUI-LANGUAGE-CONTROL-001
userLanguage           = auto
outputLanguage         = same-as-input
nativeLanguages        = []
mediatedLanguages      = []
executionLanguage      = UNKNOWN
mediationRequired      = UNKNOWN until bound
mediationPath          = PENDING_BACKEND
translatorProvider     = PENDING_BACKEND
dataClassification     = INTERNAL
cloudRequested         = false
cloudEffective         = false until policy result is bound
validationStatus       = PENDING_BACKEND
confidence             = UNKNOWN until bound
evidenceId             = PENDING_BACKEND
protectedTokenStatus   = PENDING_BACKEND
speechRoute            = PENDING_BACKEND
```

`UNKNOWN` and `PENDING_BACKEND` are first-class states. The UI MUST NOT infer PASS from absent runtime evidence.

## Data-classification policy projection

The GUI reflects, but does not enforce as authority, the Language Bridge contract:

| Classification | External translation |
|---|---|
| `PUBLIC` | may be allowed |
| `INTERNAL` | policy-dependent |
| `CONFIDENTIAL` | local-first / restricted |
| `SECRET` | forbidden |

The GUI may collect `cloudRequested=true`, but `cloudEffective` MUST come from canonical policy enforcement. A SECRET classification MUST visibly indicate that external translation is denied and MUST NOT offer a bypass.

## Protected content

The Language Bridge contract treats the following as protected/non-translatable unless an explicit typed rule permits otherwise:

- source code;
- shell commands;
- paths;
- API names;
- model identifiers;
- hashes;
- FA3 canonical IDs;
- structured keys such as JSON/YAML keys by default.

The GUI exposes `protectedTokenStatus`; it does not implement token-preservation logic itself.

## Translation authority rule

The original source remains authoritative. A translation is a derived projection with provenance. The GUI MUST never promote a translated value into canonical authority merely because it is displayed or accepted by a user.

## Static i18n boundary

Control Center UI localization and runtime semantic mediation are separate concerns:

```text
GUI locale/i18n != FA3 Language Bridge runtime mediation
```

Changing the GUI language MUST NOT silently change model routing, data classification or online-provider policy.

## Acceptance contract

| ID | Requirement | Fail-closed expectation |
|---|---|---|
| `GLC-001` | Native and mediated languages are visibly distinct | no merged language list |
| `GLC-002` | Effective routing/policy comes from backend authority | GUI cannot self-authorize |
| `GLC-003` | `SECRET` external translation is denied | no bypass |
| `GLC-004` | Mediation path and provider provenance are observable | unknown remains explicit |
| `GLC-005` | Protected-token integrity is observable | absent evidence is not PASS |
| `GLC-006` | Semantic-validation status is observable | absent evidence is not PASS |
| `GLC-007` | Provider-neutral contract | no mandatory translator vendor |
| `GLC-008` | Speech mediation route can be projected | no duplicate Voice authority |
| `GLC-009` | `UNKNOWN` / `PENDING_BACKEND` is never rendered as PASS | fail closed |
| `GLC-010` | Original source remains authoritative | translation stays derived |

## Current implementation boundary

`qml/LanguageControlPage.qml` implements the native Qt/QML surface and preference capture. Backend Language Bridge bindings are intentionally not fabricated. Until they are wired, runtime-derived fields remain `UNKNOWN` or `PENDING_BACKEND`.

The profile therefore provides an executable GUI contract without claiming production Language Bridge runtime evidence that does not yet exist.
