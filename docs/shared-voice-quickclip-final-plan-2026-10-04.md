# FA3 Shared Voice I/O + Voice Studio + QuickClip Voice Plugin — final approved plan

Status: **OWNER-APPROVED / MATERIALIZED GUI PLAN**

This plan materializes the approved shared voice architecture without creating a new architectural authority or capability. The fixed capability baseline remains **175**.

## Existing authorities preserved

- Voice synthesis, cloning, voice identity and consent: `FA3-VOICE-001`
- Model/provider selection: `FA3-AUTH-MODEL-ROUTER-001`
- Host resources/device placement: `FA3-AUTH-HOST-RESOURCE-BROKER-001`
- Durable execution: existing Temporal orchestration
- Typed application actions: UAF / existing tool-action mediation
- Plugin placement: existing FA3 Platform Plugin & Extension Fabric

No GUI, plugin or donor may bypass these authorities.

## Materialized GUI surfaces

- `VoiceStudioPage.qml`: full Voice Studio workspace.
- `QuickVoicePluginPage.qml`: QUICK/STANDARD/ADVANCED shared plugin projection with QuickClip-oriented voice generation, Fit-to-Clip, takes and Quick Dub.
- `VoiceActivityOverlay.qml`: shared visible voice activity status surface.

Runtime action buttons remain disabled in this bounded GUI materialization until an admitted provider/model route and appropriate Current Host evidence exist.

## Voice Studio

Tabs:
Generate, Voices, Capture, Transform, Stories, Dubbing, Effects, History, Models, Providers, Jobs, Settings.

The Stories view is a multi-track projection for narrator, characters, music, ambience and SFX. It consumes shared story/character identity and media provenance; it is not a new project authority.

## Shared Voice Plugin

Three presentation profiles share one underlying service boundary:

- QUICK — QuickClip and compact narration use.
- STANDARD — Video Editor, Story/Screenplay, Messenger.
- ADVANCED — Audio/Narration/Voice Studio.

The plugin cannot directly pin a CUDA ordinal, arbitrary local checkpoint, provider endpoint or fallback.

## QuickClip workflow

`script → voice request → FA3-VOICE-001 → Model Router → HRB → admitted provider → audio asset → timing/alignment → editable audio/caption tracks → optional music ducking`

Fit-to-Clip options:
1. bounded speech-rate adjustment;
2. shorter-script proposal with Preview → explicit Apply;
3. extend video;
4. preserve original timing.

No silent text rewrite is allowed.

## Quick Dub

`STT → speaker segmentation → optional translation → Voice Profile mapping → TTS → alignment → editable mix`

Language, provider, rights, consent and resource gates remain fail-closed.

## Voice Activity Overlay

Visible states include LISTENING, RECORDING, TRANSCRIBING, REFINING, GENERATING, SPEAKING, PAUSED, BLOCKED and ERROR. Agent-initiated speech may not be hidden from the user.

## Donor usage

The implementation may use only already-published donor/reference patterns. The owner-marked `jamiepine/voicebox` source remains pending serialized donor publication; no Voicebox usage edge is created by this materialization. Once its intake is canonically published, actual pattern reuse may be registered only for the specific patterns demonstrably used.

Relevant published references/patterns include WhisperX timing/alignment, PySceneDetect temporal media, ComfyUI provenance/workflow patterns, LangGraph checkpoint/HITL patterns, Waveform Playlist multitrack UI concepts, CLAP extension ABI concepts, Amphion voice-conversion/evaluation reference, OpenCut editing/timeline reference, Premiere UXP plugin UX references and Short Video Maker composition patterns.

## Promotion

This GUI/reference materialization makes **no runtime PASS claim**. Runtime promotion requires normal License & Rights, consent/revocation, security, plugin isolation, Software Coexistence, Hardware Safety, CPU-only route where supported, provider-specific Current Host E2E, positive/negative/rollback evidence and physical Current Host qualification.
