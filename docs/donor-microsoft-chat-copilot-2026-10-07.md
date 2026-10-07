# CFA3 Microsoft Chat Copilot donor intake — 2026-10-07

## Owner authorization

The owner explicitly marked the submitted source **donornak**:

- https://github.com/microsoft/chat-copilot

This intake stages exactly one normalized donor identity for the existing single-writer rolling donor finalizer **#727**. The staging PR does not independently mutate the canonical donor registry.

## Exact upstream review

- repository: `microsoft/chat-copilot`
- normalized key: `github:microsoft/chat-copilot`
- donor ID: `FA3-DONOR-MICROSOFT-CHAT-COPILOT-001`
- reviewed default branch: `main`
- reviewed upstream head: `23b27821baa11b2a1639070434628e5b151ce706`
- reviewed head date: **2024-11-13**
- repository state at intake: **archived**
- upstream license declaration: **MIT**
- upstream disposition: **sample / educational; not recommended for production deployments**

The archived/sample state is not a rejection of the donor. It classifies the source as an architectural and historical implementation reference rather than a production runtime baseline.

## CFA3 reference value

The source provides useful patterns for:

- React frontend / .NET REST backend separation;
- Semantic Kernel orchestration and plugin/function boundaries;
- a separately deployable asynchronous semantic-memory ingestion pipeline;
- content-storage, queue and vector-database provider separation;
- delegated Microsoft Graph access through an On-Behalf-Of user identity flow;
- provider configuration and connector abstraction;
- chat/application integration and integration-test organization.

CFA3 does not inherit the source's architectural authority. `FA3-AUTH-MODEL-ROUTER-001`, `FA3-LLM-GATEWAY-001`, the Application Agent Adapter, Skill/Plugin Fabric, CapabilityGrant, Knowledge/Memory Fabric and Temporal remain CFA3-native authorities/boundaries.

## Five-level dependency/reference analysis

### Chat application layering

1. `microsoft/chat-copilot`
2. React webapp presentation layer
3. .NET webapi service boundary
4. Semantic Kernel orchestration/plugin invocation
5. CFA3 Messenger → Application Agent Adapter → Agent Runtime layering pattern

### Asynchronous memory processing

1. `microsoft/chat-copilot`
2. Microsoft Kernel Memory integration
3. separate asynchronous `memorypipeline` service
4. queue + content storage + vector-database separation
5. CFA3 Capture & Inbox → Knowledge/Memory Fabric → Temporal durable-ingestion pattern

### Delegated identity

1. `microsoft/chat-copilot`
2. `plugins/OBO` native Semantic Kernel function
3. Microsoft Identity / Entra On-Behalf-Of flow
4. Microsoft Graph delegated user permissions
5. CFA3 CapabilityGrant-scoped delegated external-service authority pattern

### Model/provider abstraction

1. `microsoft/chat-copilot`
2. Microsoft.SemanticKernel 1.28.0 abstractions
3. OpenAI / Azure OpenAI connector/configuration boundary
4. explicit provider/model service binding
5. CFA3 Model Router + LLM Gateway adapter pattern, without authority transfer

### Plugin/tool boundary

1. `microsoft/chat-copilot`
2. Semantic Kernel plugin/function layer
3. OpenAPI / Web / Microsoft Graph plugin surfaces
4. backend authorization boundary around tool execution
5. CFA3 Skill/Plugin Fabric + Application Agent Adapter capability-gated tool pattern

These are reference chains, not dependency-admission chains. Semantic Kernel, Kernel Memory, Microsoft Graph, identity libraries, queues, vector databases and provider connectors remain non-admitted until separately authorized and reviewed.

## Invariants

- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- usage-edge delta: **0**
- provider/model/runtime admission: **none**
- automatic code/dependency import: **none**
- automatic local→cloud fallback: **none**
- Current Host PASS claim: **none**

Any later material adoption requires a separately approved usage edge and the normal License & Rights, provenance, Security, Software Coexistence, Hardware Safety and Current Host gates.
