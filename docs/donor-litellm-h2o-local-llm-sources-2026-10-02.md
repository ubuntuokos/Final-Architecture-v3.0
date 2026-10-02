# FA3 donor intake — LiteLLM / H2O.ai / local-LLM source indexes (2026-10-02)

## Owner authorization

The owner explicitly marked all six URLs with `donornak` on 2026-10-02 and requested canonical donor/reference registration after a fail-closed preflight.

Exact sources:

- https://github.com/BerriAI
- https://github.com/topics/litellm
- https://github.com/topics/litellm-ai-gateway?l=go
- https://github.com/h2oai
- https://github.com/LiteLLM-Labs
- https://github.com/topics/local-llm

## Fail-closed intake preflight

Preflight was performed against published `main` commit
`30eca4c7bcaaf523a260dbccd0d5a9018c902527`.

- canonical donor registry blob before intake: `3df76decf77f62235de0026bd5c12ed3b9f42561`
- canonical registry count before intake: **1333**
- declared backfill count: **1333**
- unique donor IDs: **1333**
- unique normalized source keys: **1333**
- capability baseline: **175**
- registry integrity findings: **0**
- matching rejected-source keys: **0**
- matching existing normalized source keys: **0**
- open PR inventory checked: **99**
- active canonical donor-intake PRs: **0**

The single-intake slot is therefore available for this batch.

A previous research mention of `BerriAI/litellm` does not collide with the
new organization-level source identity `github:berriai`.

## Classification

| Source | Canonical role |
| --- | --- |
| BerriAI organization | LiteLLM/provider/gateway upstream discovery index |
| `litellm` topic | LiteLLM ecosystem discovery index |
| `litellm-ai-gateway?l=go` | distinct Go-filtered gateway discovery viewpoint |
| H2O.ai organization | local-LLM/model-lifecycle/evaluation and fork-delta discovery index |
| LiteLLM-Labs organization | experimental LiteLLM-adjacent discovery index |
| `local-llm` topic | broad local/offline/CPU-capable LLM runtime discovery index |

All six records are `ACCEPTED_REFERENCE` metadata-only sources. Organization
and topic pages are collection indexes; their page-level registration does not
license, approve or adopt child repositories.

## Mandatory boundaries

This intake creates **no**:

- source-code import;
- package/dependency adoption;
- LiteLLM runtime or proxy installation;
- LiteLLM Enterprise admission;
- cloud/provider SDK admission;
- provider or model admission;
- hosted-service activation;
- model/dataset/weight download;
- architectural authority;
- capability count change;
- Current Host PASS;
- donor usage edge.

Any child repository later selected for material reuse requires independent
source-specific license/provenance, dependency and supply-chain review,
Security Governance, Software Coexistence & Host Non-Interference, Hardware
Safety, layer/shared-capability placement, and canonical usage-edge review.

## FA3 authority preservation

- capability baseline: **175**
- provider count policy: **dynamic / unchanged**
- `FA3-AUTH-MODEL-ROUTER-001` remains sole provider/model routing authority
- `FA3-LLM-GATEWAY-001` remains a data-plane boundary, not routing authority
- Host Resource Broker remains sole resource placement/lease authority
- Secret Broker remains credential authority
- no silent local-to-cloud fallback
- CPU-only viability remains mandatory

## Result

Six unique canonical reference identities are appended:

**1333 → 1339** donor/reference records.

Publication still requires exact-head donor serialization, application donor
inventory, permanent canonical/release, License & Rights, and related required
CI gates.
