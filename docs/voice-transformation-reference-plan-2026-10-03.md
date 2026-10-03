# FA3 Voice transformation plan — 2026-10-03

## Decision

Extend the existing `FA3-VOICE-001` provider-neutral Voice Fabric. Do not create a second voice, routing, identity, consent, hardware or evidence authority.

The planning input is the published donor record `FA3-DONOR-0XDEVALIAS-AI-VOICE-CLONING-GIST-001` on main commit `fd8adf5ab2ef12882c47250ecb5d5f22ff8e796b`. The Gist is a discovery index only. Its child projects are not donor/provider/runtime admissions.

## Planned functional extension

The shared Voice Fabric will cover speech synthesis and cloning plus voice conversion, realtime voice conversion, singing voice conversion, style/prosody transformation and engine-independent speech representation. All execution remains behind the Model Router and Host Resource Broker.

## Shared placement

The functional core remains shared under `FA3-VOICE-001` and `FA3-VOICE-CONTRACTS-001`. Canonical application impact is reviewed for:
- `fa3.video-editor`
- `fa3.quickclip`
- `fa3.story-screenplay`
- `fa3.music-studio`
- `fa3.character-studio`
- `fa3.ai-module-factory`

No application receives a duplicate local voice authority.

## Rights and consent

Code, runtime dependency, model, voice/dataset and output rights are independent gates. Unknown rights fail closed. Human voice use remains purpose-scoped, non-expired and non-revoked, and transformation scope must be authorized explicitly.

## Hardware

A CPU-only path remains mandatory. GPU/NPU use requires Host Resource Broker admission. The display GPU may not be selected automatically for AI. No provider may bypass the Model Router or HRB.

## Child-source boundary

OpenVoice, RVC, w-okada voice-changer, DDSP-SVC, QuickVC, ContentVec, AICoverGen, MMVC Trainer and so-vits-svc are discovery examples from the Gist, not admitted FA3 donors or providers. Each requires a separate explicit owner `donornak` marker before donor registration, followed by normal license/provenance/security/Software Coexistence/Hardware Safety/model/runtime review before material adoption.

## Baseline

Capability baseline remains **175**. Capability delta: **0**. Architectural authority delta: **0**. No Current Host runtime PASS is claimed by this plan.
