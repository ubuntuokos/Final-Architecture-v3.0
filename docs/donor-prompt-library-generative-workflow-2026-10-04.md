# FA3 prompt-library / prompt-template / generative-workflow donor intake — 2026-10-04

## Owner marker

The owner explicitly marked **23 URLs** as `donornak` on 2026-10-04. Every submitted occurrence is preserved in the intake delta.

## Normalization and deduplication

- submitted URL occurrences: **23**
- exact duplicate occurrences removed from mutation scope: **4**
- unique submitted URLs: **19**
- published canonical identity reused: **1** (`Comfy-Org`)
- unique mutation URLs after published reuse: **18**
- topic-filter alias collapses: **2**
- new canonical identities planned by this intake: **16**

Exact repeated submissions:

- `https://github.com/topics/prompts` — 2 occurrences
- `https://github.com/aakashg/pm-prompt-library` — 2 occurrences
- `https://github.com/hubertusgbecker/prompt-library` — 2 occurrences
- `https://github.com/carson-katri/dream-textures` — 2 occurrences

The three filtered `prompt-library` topic views share one canonical identity:
`FA3-DONOR-GITHUB-TOPIC-PROMPT-LIBRARY-001` / `github:topics/prompt-library`.

## Published-registry reuse

`https://github.com/Comfy-Org` is not registered again. Published main already contains:

- donor id: `FA3-DONOR-COMFY-ORG-001`
- normalized key: `github:comfy-org`

The submitted URL is retained as provenance and resolves to that existing identity.

## Planned new identities

1. `FA3-DONOR-GITHUB-TOPIC-PROMPTS-001`
2. `FA3-DONOR-GITHUB-TOPIC-PROMPT-LIBRARY-001`
3. `FA3-DONOR-JULIUSBRUSSEE-THE-PROMPT-LIBRARY-001`
4. `FA3-DONOR-HUBERTUSGBECKER-PROMPT-LIBRARY-001`
5. `FA3-DONOR-AAKASHG-PM-PROMPT-LIBRARY-001`
6. `FA3-DONOR-GITHUB-TOPIC-PROMPTS-TEMPLATE-001`
7. `FA3-DONOR-GITHUB-TOPIC-AI-PROMPTS-001`
8. `FA3-DONOR-JAMEZ-BONDOS-AWESOME-GPT4O-IMAGES-001`
9. `FA3-DONOR-JAMEZ-BONDOS-PROFILE-001`
10. `FA3-DONOR-CARSON-KATRI-DREAM-TEXTURES-001`
11. `FA3-DONOR-LLLYASVIEL-PROFILE-001`
12. `FA3-DONOR-SYGIL-DEV-ORG-001`
13. `FA3-DONOR-GITHUB-TOPIC-PROMPT-TEMPLATES-001`
14. `FA3-DONOR-GITHUB-TOPIC-PROMPT-001`
15. `FA3-DONOR-GITHUB-TOPIC-SYSTEM-PROMPTS-001`
16. `FA3-DONOR-GITHUB-TOPIC-CHATGPT-PROMPTS-001`

## FA3 reference scope

This batch is useful for later, separately approved reuse discovery around prompt-library organization, prompt-template metadata, prompt categorization, system-prompt governance patterns, reusable role/task/context schemas, product-management prompt workflows, image-generation prompt collections, creative image/texture workflows and prompt-to-generation UX.

Topic/profile/organization pages remain discovery indexes only. A child repository is not admitted merely because it appears under one of these sources.

## Rights, security and authority boundary

Donor registration alone does **not** authorize copying prompt text, system prompts, images, code, workflows, model configuration or assets. Any material reuse requires exact source-level provenance, License & Rights review, security review, Software Coexistence review where relevant, correct application/shared-layer placement and a typed approved donor usage edge.

Prompt or system-prompt sources never override FA3 Security Governance, application authority boundaries, Model Router, HRB, hardware policy or existing prompt/context contracts. No provider, model, engine, runtime or architectural authority is created by this intake.

Capability baseline remains **175**.

## FIFO waiting state

Verified parent published main: `9b328ff1582ba92d67562b10336b1ccaf8a8da84`

Verified parent registry blob: `1362d75186c6da74e5cf947fdf0b8867d462636a`

Parent entry count: **1427**

Parent-relative count if these 16 new identities were materialized against the verified parent: **1443**.

At staging time the rolling five-slot window remains occupied by canonical donor-intake PRs **#651, #657, #663, #664 and #671**. Earlier FIFO waiting intakes are **#672, #673, #675 and #676**.

Therefore this intake is intentionally staged as **FIFO waiting**. The central donor registry is not modified yet, and these 16 planned identities are not canonical planning inputs.

When a slot reaches this intake, it must be reconciled against the then-current published main, recheck both published and earlier pending identities, append only genuinely new identities, regenerate exact counts/tests, and pass exact-head gates before finalization.
