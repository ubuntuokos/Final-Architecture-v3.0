# FA3 Shared Voice Studio + Quick Video Voice Plugin

Status: **owner-approved materialization plan**

This package materializes the finalized Voice/QuickClip plan over the existing provider-neutral `FA3-VOICE-001` authority. It does not create a second model router, MCP gateway, scheduler, hardware authority, voice identity authority or provider registry.

## Surfaces

- **FA3 Voice Studio**: Generate, Voices, Capture, Transform, Stories, Dubbing, Effects, History, Models, Providers, Jobs and Settings.
- **Shared Voice Plugin**: context-sensitive QUICK / STANDARD / ADVANCED projections.
- **QuickClip**: Quick Voice, Fit to Clip, Generate & Insert, takes, editable captions, music ducking, Quick Dub and Quick Narration.
- **Voice Profile Manager**: identity, consent, reference samples, rights and application/project scope.
- **Voice Activity Overlay**: visible LISTENING / RECORDING / TRANSCRIBING / REFINING / GENERATING / SPEAKING / PAUSED / BLOCKED / ERROR state. Hidden agent speech is forbidden.

## Execution boundary

```
GUI / host plugin
  -> typed action intent
  -> FA3-VOICE-001
  -> Model Router
  -> HRB
  -> admitted provider/runtime
```

No GUI may encode `cuda:0`, a direct localhost provider, a fixed model, a cloud endpoint or an automatic device fallback.

## QuickClip workflow

```
script
 -> provider-neutral voice request
 -> generated audio asset
 -> measured duration
 -> word/alignment timing
 -> editable QuickClip audio track
 -> editable captions
 -> optional music ducking
 -> provenance/evidence
```

Fit-to-Clip offers bounded rate adjustment, a reviewable script-shortening proposal, video extension or keeping original timing. Text is never silently rewritten.

Quick Dub is:

`STT -> speaker mapping -> optional translation -> voice-profile mapping -> TTS -> alignment -> editable mix`.

## Donor boundary

The owner-marked `jamiepine/voicebox` source is not yet a published canonical donor in this materialization snapshot. It is therefore **not** used to create a donor usage edge, code import, runtime dependency, provider admission or model admission in this PR. The implementation is FA3-native and uses already-published FA3 voice/transformation/shared patterns. A later canonical Voicebox intake may register exact reference-pattern usage only if the published donor state and reuse assessment permit it.

## Invariants

- capability baseline remains **175**;
- capability delta **0**;
- architectural authority delta **0**;
- CPU-only path remains required;
- accelerator placement remains HRB-only;
- Model Router remains sole model/provider routing authority;
- AI functions remain independently switchable;
- physical Current Host PASS is not claimed by static GUI materialization.
