# CFA3 Groq donor intake — 2026-10-06

## Owner authorization

The owner explicitly ordered **all submitted Groq links** to be added **donornak**, then ordered the intake to be executed.

Five unique source identities are staged:

1. https://github.com/groq
2. https://github.com/topics/groq-cloud?o=asc&s=updated
3. https://github.com/topics/groq-ai
4. https://github.com/topics/groq-api?l=go
5. https://github.com/topics/groq-ai-real-time

The `groq-ai` topic was submitted twice in the conversation; exact duplicate normalization intentionally yields one canonical donor identity.

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

`FA3-AUTH-MODEL-ROUTER-001` remains the sole model/provider routing authority. `FA3-LLM-GATEWAY-001` remains the LLM data plane. Registering Groq references does not promote Groq, an LPU service, an SDK, an MCP server, a model, a cloud endpoint or any community project into CFA3 runtime.

## Source classification

| Source | Classification | CFA3 reference value |
|---|---|---|
| `github.com/groq` | official organization discovery index | official SDK/API/protocol examples, MCP, batch, streaming and provider patterns |
| `topics/groq-cloud` | dynamic GitHub topic | local+cloud application, RAG, agent and MCP integration patterns |
| `topics/groq-ai` | dynamic GitHub topic | agentic, multi-provider, tool registry, MCP/A2A and extension patterns |
| `topics/groq-api?l=go` | dynamic GitHub topic with Go filter | Go-native provider client, streaming, batch, retry/backpressure and service patterns |
| `topics/groq-ai-real-time` | dynamic GitHub topic | realtime collaboration and AI-inference plane separation patterns |

Organization/topic pages have no single reusable code license. Any child repository selected for material use requires its own license, provenance, security and dependency review.

## Five-level dependency/reference analysis

The intake applied the mandatory **maximum five-level** lineage policy to representative paths without recursively admitting child projects.

### Official SDK transport path

1. Groq organization
2. `groq/groq-python`
3. `httpx` / optional `aiohttp` transport choices
4. REST + SSE streaming semantics
5. CFA3 provider-adapter / LLM Gateway pattern

### Official MCP path

1. Groq organization
2. `groq/groq-mcp-server`
3. MCP-exposed Groq model/tool operations
4. tool discovery/invocation boundary
5. CFA3 MCP compatibility / Application Agent Adapter pattern

### Hybrid RAG path

1. `groq-cloud` topic
2. `Balaji-R-05/askdocs-ai`
3. LangChain + ChromaDB + BM25
4. local retrieval/preprocessing + remote inference split
5. CFA3 local-plus-cloud RAG execution pattern

### Agent modularity path

1. `groq-ai` topic
2. `phenobarbital/ai-parrot`
3. MCP/A2A transports + tool registry
4. loaders / embeddings / integrations packages
5. CFA3 Agent Skills / Application Agent Adapter pattern

### Go provider-service path

1. `groq-api?l=go` topic
2. `ZaguanLabs/groq-go`
3. context / SSE / retry / rate-limit / batch surfaces
4. provider-service execution and cancellation semantics
5. CFA3 Groq Provider Adapter behind the existing LLM Gateway

### Realtime path

1. `groq-ai-real-time` topic
2. `Durgesh1008/Real-TimeCollaborativeDevelopmentEnvironment`
3. Socket.io/WebSocket collaborative state + separate Groq HTTP AI path
4. realtime state plane separated from AI inference plane
5. CFA3 Shared Realtime Interaction Fabric pattern

These are **reference-analysis chains**, not dependency admission chains. Child sources remain non-admitted. Material use must repeat exact upstream, license, rights, provenance, security, coexistence and supply-chain checks.

## Notable non-admitted observations

The inspection identified useful children including official Groq SDK/cookbook/MCP repositories, AI-Parrot, Eclipse, extensionOS, Go Groq clients, OmniTrace and the realtime collaboration example. They are recorded only as lineage observations.

Two stale-state cautions are explicit:

- `groq/groqflow` was observed archived and is historical/architectural reference only.
- `run-llama/LlamaIndexTS` was observed archived/deprecated and is historical reference only.

No child project becomes a donor merely because it is listed by an organization/topic page. No code reuse is authorized by this intake.
