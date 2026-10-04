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

The Gist itself has no verified reusable source license in the donor record. It therefore remains a discovery/provenance reference only: it is not a material donor adoption, and no Gist code, child-project code, runtime, model, provider, dataset or asset is copied or depended upon. The transformation contracts and enforcement are FA3-native extensions of the pre-existing FA3-VOICE-001 fabric.

## Shared GUI

`apps/shared/voice/qml/VoiceTransformationPanel.qml` provides a non-authoritative intent surface. The first projection is Narration Studio. Runtime actions remain disabled until an independently admitted provider/model binding exists.

## Consumer impact

Only Narration Studio receives a materialized GUI projection in this change. The following registered applications are **planned impact targets**, not implemented consumers yet:

- `fa3.music-studio`
- `fa3.character-studio`
- `fa3.story-screenplay`
- `fa3.video-editor`
- `fa3.quickclip`

Each becomes an implemented consumer only when its own adapter/workflow and required manual projection are materialized and verified.

## Hardware and Current Host

CPU-capable execution remains mandatory for any future provider admission. Accelerator use requires an HRB lease and the display-GPU policy remains unchanged.

This structural materialization creates **no physical runtime PASS**. Any future provider must separately pass license/provenance, Security, Software Coexistence, Hardware Safety, CPU execution, quality and Current Host evidence.

## Invariants

- capability baseline: **175**
- capability delta: **0**
- authority delta: **0**
- child donor auto-admission: **false**
- provider/model admission in this change: **none**

## Explicit owner approval

The owner explicitly marked the Gist `donornak`, approved the resulting plan with `Készítsd el`, and subsequently instructed `Készítsd el a teljes lezárásig. de ezt már írtam`. This approval authorizes completion of the FA3-native reference plan; it does **not** override License & Rights or Universal Capability Access gates and therefore does not convert the unknown-rights Gist into a material donor dependency.
