# FA3 Unified Story Studio — Presentation and Dubbing Integration

Date: 2026-09-27

## Scope

This materialization keeps screenplay, story planning, production-type profiles, presentation handoff,
and dubbing/localization scripting inside one FA3-native Story Studio surface in the existing
FA3 Control Center. External applications and providers remain replaceable workers or interchange
targets; they do not become Story authority.

## Presentation layer relationship

The canonical direction is:

```
FA3 Story / Screenplay IR
        |
        +--> Pitch Deck
        +--> Treatment Deck
        +--> Series / Season Bible Deck
        +--> Character / Location Deck
        +--> Storyboard Deck
        +--> Production Brief
        +--> Live Show Deck
                 |
                 +--> CAP-018 Documents/Knowledge Authoring
                      +--> LibreOffice Impress / UNO (primary human authoring)
                      +--> FA3-PROVIDER-PRESENTON-001 (optional generation worker)
```

Each presentation projection carries source Story node references. A slide/deck may return notes,
linked references or explicit change proposals, but it may not silently mutate canonical Story state
or acquire final screenplay release authority.

Presenton is deliberately optional. Story Studio binds to the presentation contract and CAP-018,
not to a fixed Presenton runtime behavior. Future Presenton changes or a replacement provider do
not change Story authority.

## Dubbing / localization script relationship

Dubbing is a derived post-production script profile, not merely translated screenplay text:

```
Source Story / Screenplay
        |
Locked picture + source video digest
        |
Dialogue List / Pivot Dialogue List
        |
Target translation
        |
Lip-sync adaptation
        |
ADR / dubbing cue plan
        |
Recording
        |
As-Recorded Dubbing Script
        |
Final dubbed audio
```

Canonical Story Studio dubbing document types:

- Dialogue List
- Pivot Dialogue List
- Dubbing Adaptation Script
- As-Recorded Dubbing Script
- ADR Cue Sheet
- Character Script

A dubbing cue binds at least:

- cue ID and source event reference;
- source character;
- in/out timecode;
- source text;
- target language and target text;
- source-video SHA-256 lineage.

Optional structured fields include pivot text, adapted and as-recorded text, annotations,
phonetic hints, reactions/efforts, lip-sync notes, key-moment flags, take count/preferred take,
voice actor / voice identity references and terminology references.

## Authority boundaries

- Story identity and narrative lineage: `FA3-STORY-001`
- Caption/timing semantics: `FA3-CAPTION-SUBTITLE-001`
- Voice identity, consent and synthesis: `FA3-VOICE-001`
- AI model/provider selection: `FA3-AUTH-MODEL-ROUTER-001`
- accelerator/resource admission: `FA3-AUTH-HOST-RESOURCE-BROKER-001`
- final release/sign-off: existing human approval authority

Story Studio does not directly select a TTS provider and does not transfer authority to Presenton,
a dubbing tool, or a presentation editor.

## Dubbing conformance

A source Dialogue List or picture revision must not silently rewrite an existing localized script.
Conformance is explicitly split into:

1. `ALIGN_AND_RETIME` — align events and timing to the new source;
2. `REVIEW_AND_EXPLICITLY_ADAPT_CONTENT` — human-reviewed target text changes.

The As-Recorded Dubbing Script is a distinct final state and must correspond to the delivered dubbed
audio. Static reference validation does not claim that TTAL or any external studio format adapter is
runtime-admitted; each external format still requires bidirectional import/export and round-trip
validation under the Story Studio interchange invariant.

## External workflow references

Research sources used as capability references only:

- Netflix Dialogue List Scope of Work:
  https://partnerhelp.netflixstudios.com/hc/en-us/articles/360000427707-Dialogue-List-Scope-of-Work
- Netflix As Recorded Dubbing Script Scope of Work:
  https://partnerhelp.netflixstudios.com/hc/en-us/articles/4407306862611-As-Recorded-Dubbing-Script-Scope-of-Work
- Netflix Originator Studio Dub Script User Guide:
  https://partnerhelp.netflixstudios.com/hc/en-us/articles/53288006720915-Originator-Studio-Dub-Script-User-Guide
- VoiceQ feature/workflow reference:
  https://www.voiceq.com/features

No external code or commercial runtime is imported by this document.

## Hardware Audit

The Story, Presentation projection and Dubbing Script authoring cores are CPU-only viable and
vendor-neutral. Accelerator cardinality is 0..N. Synthesis/generation is delegated to existing
Model Router / Voice / HRB contracts. Story Studio performs no hardware parameter mutation.
