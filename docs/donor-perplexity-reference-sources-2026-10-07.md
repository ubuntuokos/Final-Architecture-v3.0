# CFA3 Perplexity donor intake — 2026-10-07

## Owner authorization

The owner explicitly ordered all five submitted Perplexity-related links to be added **donornak**, then ordered the donor intake to be executed.

Staged source identities:

1. https://github.com/perplexityai
2. https://github.com/helallao/perplexity-ai
3. https://github.com/topics/perplexity-ai-api
4. https://github.com/topics/perplexity-clone
5. https://github.com/topics/perplexity?l=rust&o=desc&s=stars

This PR is source-intake staging for the existing single-writer rolling donor finalizer **#727**. It does not directly mutate the canonical donor registry.

## CFA3 boundary

- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- usage-edge delta: **0**
- provider/model/runtime admission: **none**
- automatic local-to-cloud fallback: **none**
- code/dependency installation: **none**
- Current Host PASS claim: **none**

`FA3-AUTH-MODEL-ROUTER-001` remains the sole model/provider routing authority. `FA3-LLM-GATEWAY-001` remains the LLM data plane. Perplexity registration does not itself promote Perplexity, an SDK, an MCP server, a search backend, a model, a cloud endpoint or any community project into CFA3 runtime.

## Source classification

| Source | Classification | CFA3 reference value |
|---|---|---|
| `github.com/perplexityai` | official organization discovery index | Agent API, Search API, official MCP, SDK, citation/provenance and research workflow patterns |
| `helallao/perplexity-ai` | unofficial repository | sync/async client, streaming, retry/error, file/MCP transport patterns; bypass/account-generation behavior excluded |
| `topics/perplexity-ai-api` | dynamic GitHub topic | API client, OpenAI-compatible schema, async/streaming and error-normalization patterns |
| `topics/perplexity-clone` | dynamic GitHub topic | RAG/search/citation UI, source presentation and research-session UX patterns |
| `topics/perplexity?l=rust&o=desc&s=stars` | dynamic GitHub topic with Rust filter | Rust async search federation, ranking/dedup, MCP and provider transport patterns |

Organization/topic pages have no single reusable code license. Every child repository selected for material use requires its own license, provenance, security and dependency review.

## Five-level dependency/reference analysis

The mandatory maximum **five-level** lineage policy was applied to representative paths without recursively admitting child projects.

### Official Agent/MCP/Search path

1. Perplexity AI organization
2. `perplexityai/modelcontextprotocol`
3. Perplexity Agent API + Search API
4. MCP search / ask / research / reason tools with streaming transport
5. CFA3 Research & Search Fabric + MCP/provider-adapter pattern

### Official research/citation path

1. Perplexity AI organization
2. `perplexityai/api-cookbook`
3. Agent API web access, citations, code execution, subagents and durable work
4. research provenance + long-running workflow semantics
5. CFA3 evidence-aware research workflow pattern

The current official cookbook states that the Agent API is the primary Perplexity API and the earlier Sonar `/chat/completions` path is deprecated. This is a current upstream observation, not a CFA3 authority change.

### Unofficial client/transport path

1. `helallao/perplexity-ai`
2. `curl_cffi` / `websocket-client` + optional Playwright / MCP
3. sync/async client, streaming, retry, rate-limit and file-handling surfaces
4. strict separation of reusable transport patterns from account/query-limit bypass behavior
5. CFA3 provider-client isolation and error-normalization pattern only

### API compatibility path

1. `perplexity-ai-api` topic
2. `gweidart/pyplexityai`
3. `requests` / `aiohttp` + typed OpenAI-compatible streaming client
4. provider-specific response/error normalization behind a generic client contract
5. CFA3 Provider Compatibility Adapter pattern

### RAG / Research Workspace path

1. `perplexity-clone` topic
2. `JonniTech/Perplexity-Clone`
3. SerpAPI retrieval + context extraction + LLM synthesis
4. streamed answer + citation/source UI + persistent research-session state
5. CFA3 Research Workspace / citation UX pattern

### Rust multi-provider search path

1. `perplexity` topic filtered to Rust
2. `paperfoot/search-cli`
3. Tokio parallel provider fan-out + timeout/cancellation
4. deterministic deduplication + reciprocal-rank fusion, synthesized answers separated
5. CFA3 Search Federation / Ranker pattern

These are reference-analysis chains, not dependency-admission chains.

## Restricted / non-admitted observations

The unofficial lineage includes implementations or descriptions involving account generation, query-limit bypass, cookie/session extraction, browser/TLS impersonation, anonymous proxying or similar service-access circumvention. Those behaviors are **not admitted for CFA3 reuse** by this intake.

Only architecture-level patterns such as transport abstraction, schema normalization, streaming, retry/error handling, MCP integration, RAG flow, ranking/deduplication and research UI may proceed to later independent review.

Observed child repositories, including official Perplexity SDK/MCP/cookbook projects and community projects, remain non-admitted. `mishamyrt/perplexity-web-api-mcp` was observed archived and is historical/architectural reference only.

No child project becomes a donor merely because it is listed by an organization or topic page. No code reuse is authorized by this intake.
