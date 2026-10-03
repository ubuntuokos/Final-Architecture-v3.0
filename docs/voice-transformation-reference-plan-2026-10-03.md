# FA3 Voice Transformation reference materialization — 2026-10-03

## Scope

This change extends the existing `FA3-VOICE-001` fabric. It does **not** create a second voice authority and does not admit any child engine or service from the 0xdevalias AI Voice Cloning Gist.

Published donor input:

- donor: `FA3-DONOR-0XDEVALIAS-AI-VOICE-CLONING-GIST-001`
- published main snapshot: `fd8adf5ab2ef12882c47250ecb5d5f22ff8e796b`
- donor registry count: **1423**
- donor status: `ACCEPTED_REFERENCE`

## Materialized modes

- `VOICE_CONVERSION`
- `REALTIME_VOICE_CONVERSION`
- `SINGING_VOICE_CONVERSION`
- `STYLE_TRANSFER`
- `SPEECH_REPRESENTATION`

The modes are provider-neutral intent and contract vocabulary. They do not select or execute an upstream project.

## Authority boundaries

- Model/provider route: `FA3-AUTH-MODEL-ROUTER-001`
- CPU/GPU/NPU placement and leases: `FA3-AUTH-HOST-RESOURCE-BROKER-001`
- Evidence: `FA3-AUTH-OBS-EVIDENCE-001`
- Voice identity/consent and License & Rights: existing FA3 governance
- durable workflow/session lifecycle: existing FA3 authorities

No silent fallback is allowed.

## Rights and consent

Human-target conversion, realtime conversion and singing conversion require explicit purpose-scoped consent that is valid at execution time. Code, runtime, model, voice/dataset and output rights remain separate. Unknown rights fail closed.

The Gist itself has no verified reusable source license in the donor record, so this materialization is clean-room functional re-expression only. No Gist code or child-project code is copied.

## Shared GUI

`apps/shared/voice/qml/VoiceTransformationPanel.qml` provides a non-authoritative intent surface. The first projection is Narration Studio. Runtime actions remain disabled until an independently admitted provider/model binding exists.

## Consumer impact

Canonical application consumers are limited to applications already present in the application inventory:

- `fa3.music-studio`
- `fa3.character-studio`
- `fa3.story-screenplay`
- `fa3.video-editor`
- `fa3.quickclip`

## Hardware and Current Host

CPU-capable execution remains mandatory for any future provider admission. Accelerator use requires an HRB lease and the display-GPU policy remains unchanged.

This structural materialization creates **no physical runtime PASS**. Any future provider must separately pass license/provenance, Security, Software Coexistence, Hardware Safety, CPU execution, quality and Current Host evidence.

## Invariants

- capability baseline: **175**
- capability delta: **0**
- authority delta: **0**
- child donor auto-admission: **false**
- provider/model admission in this change: **none**
