# FA3 DAW and music-generation donor curation — 2026-09-28

Status: **research curation / candidate capture only**. No application, model or provider has been installed, admitted, routed or executed by this change. The canonical register is `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`; this document is not a second registry.

## Scope and discovery

User-supplied upstream discovery indexes:
- https://github.com/topics/daw
- https://github.com/topics/daw?l=javascript&o=desc&s=stars (same underlying topic, JavaScript filter)
- https://github.com/topics/music-generation

Directly supplied upstream repositories:
- https://github.com/Conceptual-Machines/magda-core
- https://github.com/ai-music/webdaw

Existing FA3 donor records for Ardour, LMMS, Zrythm, ACE-Step 1.5, Stable Audio 3 and openDAW/headless are reused, not duplicated. The existing `FA3-MUSIC-001` profile and `FA3-MUSIC-GENERATION-CONTRACTS-001` remain the implementation boundaries; FA3 Music Studio is a planned native FA3 application, not a mandate to deploy another complete DAW.

## Source-checked incremental donor candidates

| Source | Observed upstream licence | Selective donor use | FA3 target | Scope / hold |
|---|---|---|---|---|
| [MAGDA](https://github.com/Conceptual-Machines/magda-core) | GPL-3.0 | Hybrid audio/MIDI tracks; arrangement/session/mix workflow; natural language to typed DSL; remote API with shared operation registry, transport-independent scopes, revision-checked asynchronous jobs | Music Studio, Audio Fabric, Voice/Vocal | Reference/adapter investigation only. Upstream describes software as early v0; external token storage and embedded inference are not imported. |
| [WebDAW](https://github.com/ai-music/webdaw) | MIT | Client-side Web Audio/Web MIDI model; project/region/track abstractions; portable UI patterns | Music Studio, Creative Studio | Component-level investigation. Latest observed `main` commit is 2024-02-02, so verify current dependencies/tests. Web Audio Modules 2.0 is expressed as an *intention*, not assumed to be complete. |
| [openDAW](https://github.com/andremichelle/openDAW) | AGPL-3.0-or-later | Browser-first DAW workflow, privacy-aware UX, session patterns | Music Studio, Audio Fabric | Design reference only until network copyleft and distribution review. Distinct source identity from the existing openDAW/headless candidate. |
| [Waveform Playlist](https://github.com/naomiaro/waveform-playlist) | MIT | Multitrack waveform visualization, clip edit, time-synced annotations, recording/export | Music Studio, Voice/Vocal, Video Editor, QuickClip | Selective pattern/component investigation, not replacement of native Qt6/QML surfaces. |
| [CLAP](https://github.com/free-audio/clap) | MIT | Stable audio-plugin ABI and extension patterns | Music Studio, Audio Fabric | Standard/API donor. A host implementation additionally needs plugin isolation, trustworthy scanning and current-host audio tests. |
| [Tracktion Engine](https://github.com/Tracktion/tracktion_engine) | GPL-3.0-or-later / commercial | Sequence-model, automation, render, session and test-design reference | Music Studio, Audio Fabric | Reference only. JUCE is separately licensed; no dependency approved by this curation. |
| [Amphion](https://github.com/open-mmlab/Amphion) | MIT **code** | Singing-voice synthesis, voice conversion, vocoders, objective audio evaluation | Voice/Vocal, Music Studio, Audio Fabric | Model weights, data and speaker/voice rights must be reviewed independently. Not a new automatic model/provider. |
| [GridSound](https://github.com/gridsound/daw) | AGPL-3.0 | Web Audio editor and drum/synth UI patterns | Music Studio | Research/UI reference only; upstream calls the application “half open-source”, requiring component-level provenance before any copying. |

Upstream evidence: MAGDA `README.md`, `LICENSE`, `docs/architecture/remote-api-contract.md`, `docs/architecture/remote-api-permissions.md`; WebDAW `README.md`, `LICENSE`, `package.json`, `src/core`; the other sources' `README.md` and licence files. MAGDA observed `main` revision: `0d92b0e302da3d15b9d73e312422dddfb781d83e` (2026-09-28). WebDAW observed `main` revision: `b892a3a5de4974d6844d11413524ddc597ce0961` (2024-02-02).

These are upstream licence observations, **not completed FA3 distribution clearance**. All newly captured records retain `CANDIDATE` and `SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW`.

## Selective implementation proposal

1. **Keep one FA3-native Music Studio project model.** Define editable audio/MIDI tracks, clips/regions, timing/tempo-map, automation, sidecar provenance and lossless master assets. Preserve Ardour sessions and LMMS native files; use DAWproject and other verified interchange only where lossless round trips can be demonstrated. MIDI remains an audio-domain asset with native structured MIDI edit semantics.
2. **Typed AI editing, not arbitrary DAW shell commands.** Use MAGDA's DSL/operation-registry ideas as references for a typed, capability-scoped FA3 music edit grammar. Route external app adapters exclusively through Central MCP Gateway and UAF. Preview diffs, require human approval for destructive edits, use undo and revision checks; ban independent embedded model routing.
3. **Audio/multitrack visualisation.** Assess WebDAW and Waveform Playlist region, timeline, waveform and annotation abstractions. FA3 GUI remains Qt6/QML, Wayland-preferred and X11-compatible. A browser/mobile preview is optional and non-authoritative.
4. **Plugin and DSP layer.** Assess CLAP as one interoperable interface, existing Ardour/LMMS providers for native handoff, and Tracktion only as a sequencing/engine design reference until both Tracktion and JUCE licensing reviews pass.
5. **AI composition and singing.** Existing FA3 ACE-Step/Stable Audio provider contracts are consulted first. Amphion offers candidate vocoder and singing/voice-evaluation references. All proposed model invocations must be approved by FA3 Model Router -> HRB -> selected provider/runtime/model; no hard-coded model or silent fallback.
6. **Cross-app production.** Music Studio may export stems, score/cue sheets, MIDI and provenance to FA3 Video Editor; QuickClip may consume short mix variants; Voice/Vocal and Story/Screenplay share explicitly approved references without exchanging unreviewed model commands. Native project formats remain intact.

## Admission and acceptance gates

- Licence/SBOM and component provenance review for each exact upstream commit, plus independent third-party asset and model-weight rights.
- Typed Gateway operations with explicit `read`, `edit`, `transport`, `session` and `hardware-midi`-inspired permission boundaries; do **not** adopt MAGDA's self-identified bearer-token approach as FA3 authentication.
- Non-destructive edit/undo and exact project revision tests; denied commands must leave project state unchanged.
- Sample-accurate region/tempo conversion, MIDI round-trip, lossless stems/master verification and preserved original Ardour/LMMS/native FA3 project files.
- Realtime audio thread never waits on AI, network or plugin scanning; xrun/callback telemetry and cancellation tests.
- CPU-only and current-host paths validated separately; external plugin binaries require isolation and crash recovery.
- Music-generation provenance includes selected model, revision, backend, decoder, precision, seed and PCM/audio-affecting runtime identity as required by the existing canonical contracts.
- Gates distinguish documentation checks from current-host execution evidence; **no current-host execution PASS** is claimed by this donor-candidate PR.

## Hardware Audit — explicit boundary

**Compliant for this metadata-only change:** vendor-neutral, zero or more accelerators (0..N), CPU-only viable; no mandatory CUDA/ROCm/oneAPI, installation, GPU/NPU selection or hardware mutation. HRB remains sole resource authority and Model Router sole model-route authority. The display GPU is display-first: when it is the only GPU and there is no NPU, AI use may be allowed by policy; if another GPU and/or NPU exists, display-GPU AI use requires explicit in-app designation for a predefined model **and task**, never automatic scheduling or silent fallback. Production execution still requires its own hardware and current-host evidence gates.

## Registry and cross-application safeguards

Eight new source-unique GitHub candidates were recorded as non-authoritative metadata. The three GitHub topic URLs above are discovery *indexes*, not new applications and not separate engine/runtime donors. Existing donors retain their previous source identities. This curation makes no architectural authority, runtime/provider admission, installation or application lifecycle changes.
