# FA3 LocalAI ecosystem donor intake — 2026-10-04

## Owner marker

The owner explicitly marked **14 URLs** as `donornak` in this LocalAI/local-AI intake conversation. Every exact submitted URL is preserved in the intake delta.

## Normalization

- submitted URL occurrences: **14**
- exact duplicate occurrences: **0**
- unique submitted URLs: **14**
- published canonical identity reused: **0**
- topic-filter/sort alias collapses: **3**
- planned new canonical identities: **11**
- capability baseline: **175 unchanged**
- capability / authority / usage-edge delta: **0**

The three submitted `local-ai` topic views share one canonical identity:

- `https://github.com/topics/local-ai`
- `https://github.com/topics/local-ai?l=c%2B%2B&o=asc&s=forks`
- `https://github.com/topics/local-ai?l=go&o=asc&s=updated`

They normalize to `FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-001` / `github:topics/local-ai`.

The two submitted `local-ai-agents` topic views also share one identity:

- `https://github.com/topics/local-ai-agents?l=javascript`
- `https://github.com/topics/local-ai-agents?o=desc&s=updated`

They normalize to `FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-AGENTS-001` / `github:topics/local-ai-agents`.

## Upstream verification snapshots

### LocalAI

Concrete repository:

- `mudler/LocalAI`
- default branch: `master`
- observed upstream head: `ed4a3975be786682631d700f104255cc8b9000df`
- latest observed release: `v4.11.0`, published 2026-10-02
- top-level license: **MIT**

Observed upstream design characteristics relevant to FA3:

- one API surface for LLM, vision, voice, image and video workloads;
- separate on-demand backends rather than one monolithic bundle;
- OpenAI-, Anthropic- and ElevenLabs-compatible API surfaces;
- CPU-only plus NVIDIA, AMD, Intel, Apple Silicon and Vulkan execution paths;
- model gallery/import paths and backend-specific execution;
- distributed routing, node draining, request routing and autoscaling patterns;
- agents, RAG, MCP, skills and realtime voice/tool-calling patterns;
- API-key / multi-user / quota / role-based administration patterns;
- backend OCI signing and verification using keyless cosign;
- runtime monitoring, backend trace and log surfaces.

The `localai-org` organization is a discovery index only. Its child repositories are not recursively admitted.

### AAIF goose organization

The owner submitted `https://github.com/aaif-goose` as an organization-level donor/reference source.

Observed organization snapshot:

- at least **5** visible public repositories in the checked result set;
- representative child: `aaif-goose/goose`;
- representative child observed head: `591edd47cf2cfea4957d720c607cf2a4def8673d`;
- representative child latest release: `v1.53.0`, published 2026-10-02;
- representative child top-level license: **Apache-2.0**.

The representative `goose` child is a native open-source AI agent with desktop, CLI and API surfaces, implemented in Rust. Its README documents 15+ model providers, 70+ MCP extensions, local execution, custom distributions, and membership in the Agentic AI Foundation at the Linux Foundation. Repository code/docs also expose local GGUF/MLX inference management, provider configuration, recipes, ACP surfaces and extension state.

This child inspection is **analysis evidence only**. The organization intake does not independently register `aaif-goose/goose` or any other child repository.

## FA3 applicability assessment

### High-value donor patterns

1. **Provider/backend adapter fabric**
   - LocalAI's small-core / pluggable-backend design is a strong reference for FA3 provider adapters.
   - FA3 should reuse the pattern, not delegate Model Router authority to LocalAI.

2. **Unified multimodal local API**
   - The OpenAI/Anthropic/ElevenLabs compatibility layer is useful for reducing application-specific provider glue.
   - A future LocalAI adapter should sit below FA3 Model Router and expose normalized capabilities upward.

3. **Offline-first application discovery**
   - `offline-ai` and `local-ai-app` topics widen discovery for applications that remain useful without remote providers, including local data, local model lifecycle, offline UX and constrained-device execution.
   - Topic membership is discovery metadata only; individual projects require separate review.

4. **Model/backend acquisition lifecycle**
   - Gallery/importer, backend metadata and on-demand backend packaging are useful references for FA3 Model Manager and Provider Manager.
   - FA3 must preserve explicit user-controlled acquisition and License & Rights checks.

5. **Hardware-aware routing**
   - Hardware probing, backend selection, distributed node routing and VRAM-aware scheduling are useful references for HRB-aware planning.
   - HRB remains the only FA3 device/resource placement authority.

6. **Distributed local inference**
   - Node registry, draining, replica routing, layer-split/distributed inference and authenticated cluster transport are relevant to FA3 workstation/server/single-machine execution modes.

7. **Agent desktop / CLI / API convergence**
   - AAIF goose provides useful reference patterns for presenting the same agent system through desktop, CLI and embeddable API surfaces.
   - This is relevant to FA3 shared agent UI, command surfaces and application embedding.

8. **MCP extension lifecycle**
   - goose's extension catalog/configuration patterns, extension state, recipe binding and custom distributions are useful implementation references for FA3 Central MCP Gateway and Shared Plugin & Extension Fabric.
   - Extension availability never equals FA3 admission.

9. **Recipes and reusable task configurations**
   - goose recipes provide a useful pattern for reusable parameterized agent/task configurations and quick-start actions.
   - FA3 must preserve typed task scope, approval provenance and Temporal authority.

10. **Local model user experience**
    - goose's local inference UI/model picker and GGUF/MLX model-management patterns are relevant to the FA3 Model Manager and per-application compatible-alternative model presentation.
    - Model selection still belongs to Model Router + hardware-aware policy.

11. **Custom distributions**
    - goose custom-distribution patterns are relevant to FA3 product/domain packaging, preconfigured extensions and branding.
    - FA3 capability/authority/security contracts remain invariant across distributions.

12. **Supply-chain integrity**
    - LocalAI keyless-cosign backend signing, digest-based verification, identity binding and revocation cutoffs are strong reference patterns.
    - FA3 should enforce strict verification rather than LocalAI's warning-only default for unsigned artifacts.

13. **Operational observability**
    - backend monitor, traces, logs, user attribution and usage metrics fit FA3 Manager/Monitoring surfaces.

14. **Realtime voice / multimodal interaction**
    - WebRTC, streaming transcription/LLM/TTS pipelines and tool-calling loops are relevant to Shared Voice, Voice Studio and QuickClip.

## Mandatory FA3 adaptation boundaries

These sources cannot become authority-bearing runtimes merely through donor registration.

- **Model Router authority:** LocalAI/goose/provider selection cannot replace the FA3 Model Router.
- **HRB authority:** automatic GPU/device selection is not authoritative. FA3 display-GPU and manual-selection rules remain mandatory.
- **Model acquisition:** automatic model/backend downloads must be mediated by Model Manager/Provider Manager, explicit user intent, License & Rights and artifact security.
- **CPU-only path:** mandatory FA3 CPU-only requirements remain in force.
- **No silent fallback:** local/cloud, model, provider, backend and device changes require explicit typed decisions.
- **MCP:** goose/LocalAI MCP support is reference/interoperability input; Central MCP Gateway remains the policy boundary.
- **Temporal:** recipes, agent loops and background execution do not replace the central durable workflow authority.
- **Plugin/extension fabric:** upstream extension availability is discovery only, never automatic admission.
- **Supply chain:** unsigned or unhashed backend/model artifacts are fail-closed where FA3 integrity evidence is mandatory.
- **License & Rights:** repository-level MIT/Apache-2.0 observations do not automatically clear child dependencies, extensions, models, datasets or services.
- **Software Coexistence:** no upstream installation may silently replace or reconfigure existing FA3 providers or runtimes.
- **Current Host:** this metadata-only intake creates no runtime admission and no physical PASS.

## Planned canonical identities

1. `FA3-DONOR-MUDLER-LOCALAI-001`
2. `FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-001`
3. `FA3-DONOR-LOCALAI-ORG-001`
4. `FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-AGENTS-001`
5. `FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-MODELS-001`
6. `FA3-DONOR-GITHUB-TOPIC-LOCALAI-001`
7. `FA3-DONOR-GITHUB-TOPIC-MY-LOCAL-AI-001`
8. `FA3-DONOR-GITHUB-TOPIC-SELF-HOSTED-AI-001`
9. `FA3-DONOR-GITHUB-TOPIC-OFFLINE-AI-001`
10. `FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-APP-001`
11. `FA3-DONOR-AAIF-GOOSE-ORG-001`

## FIFO waiting state

Verified parent published main:

`9b328ff1582ba92d67562b10336b1ccaf8a8da84`

Verified parent registry blob:

`1362d75186c6da74e5cf947fdf0b8867d462636a`

Parent entry count: **1427**.

Parent-relative count if these 11 new identities were materialized against this snapshot: **1438**.

The rolling five-slot donor window remains occupied by **#651, #657, #663, #664 and #671**. Earlier FIFO waiting intakes remain **#672, #673, #675, #676 and #682**.

Therefore #683 remains **FIFO waiting**. The central donor registry is not modified yet, and these planned identities are not canonical planning inputs until the intake reaches an active slot and is reconciled against the then-current published main.
