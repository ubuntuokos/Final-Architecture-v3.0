# FA3 AI Voice Cloning Gist donor intake and Voice transformation closure — 2026-10-03

## Owner marker

The owner explicitly marked the exact source `https://gist.github.com/0xdevalias/bb618bba1f0c9038e4bf740de884ac99` as **donornak** on 2026-10-03 and authorized execution through full closure.

## Source classification

- canonical source key: `gist:0xdevalias/bb618bba1f0c9038e4bf740de884ac99`
- donor id: `FA3-DONOR-0XDEVALIAS-AI-VOICE-CLONING-GIST-001`
- source kind: `GIST`
- status: `ACCEPTED_REFERENCE`
- mode: metadata-only `DISCOVERY_INDEX`
- capability delta: **0**
- authority delta: **0**
- capability baseline: **175**
- runtime impact: **NO_RUNTIME_IMPACT**

The inspected GitHub page identifies the source as **AI Voice Cloning**, created 2025-03-24 and forked from `d00m4ace/ai-voice-cloning.md`. It groups external services, guides/Colabs and tools. The tool list includes OpenVoice, RVC WebUI, AICoverGen, w-okada voice-changer, DDSP-SVC, MMVC Trainer, so-vits-svc, so-vits-svc-fork, QuickVC and ContentVec.

## Canonical FA3 disposition

The discovery source does **not** create a new Voice authority. `FA3-VOICE-001` remains the single provider-neutral Voice Fabric under `FA3-AUDIO-001`.

The reference plan closes the design disposition for:

1. speech synthesis and cloning preservation;
2. provider-neutral voice conversion;
3. realtime voice conversion;
4. singing voice conversion;
5. style/prosody and cross-lingual voice intent;
6. engine-independent speech representation;
7. context-sensitive shared Voice UI;
8. Engine/Provider Selector integration without changing Model Router authority.

The governing decision is `FA3-DEC-VOICE-TRANSFORMATION-REFERENCE-PLAN-2026-10-03`.

## Authority boundary

```text
Applications / contextual Voice UI
              |
        FA3-VOICE-001
              |
   Engine/Provider preference
              |
          Model Router
              |
     Host Resource Broker
              |
      admitted execution only
```

The Engine/Provider Selector may record eligible user preference; it never becomes execution authority. Model Router retains provider/model routing, HRB retains CPU/GPU/NPU admission, License & Rights and Security remain fail-closed, and Current Host promotion requires real evidence.

## Rights model

Future material voice transformation must keep these dimensions independent:

- code license;
- runtime/dependency rights;
- model/checkpoint rights;
- reference voice/dataset rights;
- generated output rights.

Human voice use additionally requires explicit purpose-scoped consent, expiry/revocation enforcement and immutable reference lineage. A permissive software license never grants rights to a person's voice or to arbitrary model/dataset assets.

## Hardware and fallback

CPU-only viability remains mandatory for FA3 capability coverage. Optional accelerator use is admitted only through HRB. Display-GPU policy is unchanged. Silent provider/model/device/cloud/language fallback remains prohibited.

## Child-source boundary

The Gist is a discovery index. The child repositories and services it links are **not** recursively registered or admitted by this intake. No OpenVoice, RVC, DDSP-SVC, w-okada, QuickVC, ContentVec or commercial provider runtime is installed or promoted by this change.

If a concrete child source is later proposed for source-specific donor reuse, it must satisfy the normal explicit donor-eligibility rule and the independent provenance/license, security, Software Coexistence, Hardware Safety, model/runtime, rights/consent, usage-edge and Current Host gates.

## Application impact

The closed reference plan targets Audio/Voice Studio, Music Studio, Dubbing & Synchronization, Digital Human, Character Studio, Story/Screenplay, Video Editor, Film/Virtual Production, Unified Messenger, Meeting/Conference and Coach/Mentor/Assistant through one shared provider-neutral fabric and contextual adapters.

This intake changes no runtime, no provider admission, no application executable path, no physical-host state and no capability identity. The fixed capability baseline remains **175**.
