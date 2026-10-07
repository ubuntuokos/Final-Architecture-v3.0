# CFA3 donor intake — MohamedElaassal/youtubeVideoGenerator — 2026-10-07

## Owner authorization

The owner explicitly marked the exact source as `donornak` on 2026-10-07.

Canonical source:
- https://github.com/MohamedElaassal/youtubeVideoGenerator
- normalized key: `github:mohamedelaassal/youtubevideogenerator`
- proposed donor ID: `FA3-DONOR-MOHAMEDELAASSAL-YOUTUBE-VIDEO-GENERATOR-001`

This is reference registration only. It does not authorize source copying, dependency installation, provider/model/runtime admission, hosted-service activation, a usage edge, or Current Host PASS.

## Exact upstream state

- default branch: `master`
- reviewed head: `2d56dddd540d5a4844617b0f1e19490037c599ed`
- repository license declaration: MIT
- parent CFA3 main: `fe8964026d9db75e8f573bfbde358c56f213102a`
- parent canonical donor registry blob: `062b7b27aeeaf74819ac315f30c5cbde4ed2c95b`
- parent donor count: **1919**
- proposed donor count: **1920**
- capability baseline: **175**
- capability delta: **0**
- authority delta: **0**
- usage-edge delta: **0**

## Reference value

The repository is useful primarily as an end-to-end automated content-production reference: topic/script generation, stock-media acquisition, TTS, FFmpeg composition, workflow orchestration, scheduled/autopilot execution and YouTube publishing.

CFA3 does not treat its FFmpeg assembly code as an advanced video-generation engine or editorial timeline. Its strongest value is workflow and integration structure.

## Mandatory L0–L5 dependency/reference analysis

A deterministic package lineage is pinned from the upstream `composer.lock`:

| Depth | Identity | Observed version / revision |
| --- | --- | --- |
| L0 | MohamedElaassal/youtubeVideoGenerator | `2d56dddd540d5a4844617b0f1e19490037c599ed` |
| L1 | googleapis/google-api-php-client (`google/apiclient`) | v2.18.3 / `4eee42d201eff054428a4836ec132944d271f051` |
| L2 | googleapis/google-auth-library-php (`google/auth`) | v1.47.1 / `d7a0a215ec42ca0c8cb40e9ae0c5960aa9a024b7` |
| L3 | guzzle/guzzle (`guzzlehttp/guzzle`) | 7.9.3 / `7b2f29fe81dc4da0ca0ea7d42107a0845946ea77` |
| L4 | guzzle/psr7 (`guzzlehttp/psr7`) | 2.7.1 / `c2270caaabe631b3b44c85f99e5a04bbb8060d16` |
| L5 | php-fig/http-message (`psr/http-message`) | 2.0 / `402d35bcb92c70c026d1a6a9883f06b2ead23d71` |

The depth value is provenance only. It does not reduce strategic importance or integration priority.

Direct reference families observed from the repository include n8n, FFmpeg, Laravel, Google/YouTube APIs, Gemini, gTTS, Pixabay, Unsplash, Vue/Inertia, Docker, MySQL and Redis. SDK/API/codec/orchestration references are flagged for fast-access discovery, but **none of these child identities are automatically admitted as donors by this intake**.

## CFA3 placement

Reference mapping only:
- n8n workflow concepts -> CFA3 orchestration / Temporal-owned durable lifecycle;
- Gemini/script generation -> Model Router mediated model/provider path;
- stock media APIs -> shared Asset Provider Registry;
- gTTS -> shared Voice/Speech provider layer;
- FFmpeg -> shared media/render backend;
- YouTube upload -> Publishing/Distribution connector;
- scheduled autopilot -> governed scheduled content-production workflow.

Existing CFA3 authorities remain unchanged.

## Security / rights / coexistence observations

Fail-closed observations:
- Docker Compose contains development-grade fixed credentials/defaults; they are not reusable production configuration.
- The repository demonstrates direct secret/API-key placement in environment/workflow configuration; CFA3 Secret Broker remains mandatory.
- The n8n generation workflow uses command execution with generated/script-derived content; CFA3 must not adopt unsafe shell-composition semantics.
- Direct Gemini, media-provider and YouTube calls remain subject to provider/network/rights/security admission.
- Repository MIT licensing does not automatically grant rights for third-party APIs, media assets, generated content, service terms, or transitive dependencies.
- No upstream Docker image, package, service, dependency or runtime is admitted by donor registration.

## Result boundary

Target state is one new `ACCEPTED_REFERENCE` canonical identity, **1919 -> 1920**, with zero capability, authority, runtime and usage-edge delta. Publication requires fresh exact-head donor serialization, reuse/application-donor checks, release projection reconciliation and all required repository gates.
