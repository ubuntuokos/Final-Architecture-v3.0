# FA3 LocalAI ecosystem donor intake — 2026-10-04

## Owner marker

The owner explicitly marked **10 URLs** as `donornak` on 2026-10-04. Every submitted URL is preserved in the intake delta.

## Normalization

- submitted URL occurrences: **10**
- exact duplicate occurrences: **0**
- unique submitted URLs: **10**
- published canonical identity reused: **0**
- filtered `local-ai` topic aliases collapsed: **2**
- planned new canonical identities: **8**
- capability baseline: **175 unchanged**
- capability / authority / usage-edge delta: **0**

The three submitted `local-ai` topic views share one canonical identity:

- `https://github.com/topics/local-ai`
- `https://github.com/topics/local-ai?l=c%2B%2B&o=asc&s=forks`
- `https://github.com/topics/local-ai?l=go&o=asc&s=updated`

They normalize to `FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-001` / `github:topics/local-ai`, while all exact source URLs remain provenance.

## Upstream verification snapshot

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

The `localai-org` organization is a discovery index only. Its currently visible ecosystem includes multiple focused native/C++ projects (for example speech, vision, detection, depth and media components), but no child repository is admitted by this organization-level intake.

## FA3 applicability assessment

### High-value donor patterns

1. **Provider/backend adapter fabric**
   - LocalAI's small-core / pluggable-backend design is a strong reference for FA3 provider adapters.
   - FA3 should reuse the pattern, not delegate Model Router authority to LocalAI.

2. **Unified multimodal local API**
   - The OpenAI/Anthropic/ElevenLabs compatibility layer is useful for reducing application-specific provider glue.
   - A future LocalAI adapter should sit below FA3 Model Router and expose normalized capabilities upward.

3. **Model/backend acquisition lifecycle**
   - Gallery/importer, backend metadata and on-demand backend packaging are useful references for FA3 Model Manager and Provider Manager.
   - FA3 must preserve explicit user-controlled acquisition and License & Rights checks.

4. **Hardware-aware routing**
   - Hardware probing, backend selection, distributed node routing and VRAM-aware scheduling are useful references for HRB-aware planning.
   - HRB remains the only FA3 device/resource placement authority.

5. **Distributed local inference**
   - Node registry, draining, replica routing, layer-split/distributed inference and authenticated cluster transport are relevant to FA3 workstation/server/single-machine execution modes.

6. **Supply-chain integrity**
   - Keyless cosign backend signing, digest-based verification, identity binding and revocation cutoffs are strong reference patterns.
   - FA3 should enforce strict verification rather than LocalAI's warning-only default for unsigned artifacts.

7. **Operational observability**
   - backend monitor, traces, logs, user attribution and usage metrics fit FA3 Manager/Monitoring surfaces.

8. **Agents / MCP / RAG / skills**
   - useful implementation and UI references for FA3 MCP Gateway, agent execution and shared knowledge/skill surfaces.
   - LocalAI agent orchestration must not replace Temporal or FA3 orchestration authorities.

9. **Realtime voice / multimodal interaction**
   - WebRTC, streaming transcription/LLM/TTS pipelines and tool-calling loops are relevant to Shared Voice, Voice Studio and QuickClip.

10. **Native lightweight backends**
    - the LocalAI ecosystem's focused C/C++ implementations are a useful discovery path for CPU-friendly, dependency-reduced local execution candidates.

## Mandatory FA3 adaptation boundaries

LocalAI cannot be integrated unchanged as an authority-bearing runtime.

- **Model Router authority:** LocalAI may become an optional provider/runtime adapter only; it cannot decide the canonical FA3 provider/model route.
- **HRB authority:** automatic GPU selection is not authoritative. FA3's display-GPU restriction and manual-selection exceptions remain mandatory.
- **No automatic install:** LocalAI's automatic backend detection/download must be mediated by FA3 Model Manager/Provider Manager and explicit user intent.
- **CPU-only baseline:** every admitted LocalAI-backed capability must retain a CPU-only viable path where the FA3 capability baseline requires it.
- **No silent fallback:** LocalAI backend/model/provider fallback behavior must be mapped to explicit typed FA3 decisions.
- **Strict artifact integrity:** unsigned/unhashed OCI/tarball/HTTP backends are not accepted merely with a warning. FA3 admission must fail closed when required integrity evidence is missing.
- **License & Rights:** the MIT top-level LocalAI code license does not automatically clear bundled backends, models, checkpoints, datasets or third-party engines.
- **Software Coexistence:** LocalAI runtime packaging must not replace or silently reconfigure existing FA3 providers/runtimes.
- **Temporal:** LocalAI agent/distributed lifecycle patterns may be reused, but Temporal remains the central durable workflow authority.
- **MCP:** LocalAI MCP support is an interoperability/reference source; FA3 Central MCP Gateway remains the policy boundary.
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

## FIFO waiting state

Verified parent published main:

`9b328ff1582ba92d67562b10336b1ccaf8a8da84`

Verified parent registry blob:

`1362d75186c6da74e5cf947fdf0b8867d462636a`

Parent entry count: **1427**.

Parent-relative count if these 8 new identities were materialized against this snapshot: **1435**.

At staging time the rolling five-slot donor window is occupied by canonical donor-intake PRs **#651, #657, #663, #664 and #671**. Earlier FIFO waiting intakes are **#672, #673, #675, #676 and #682**.

Therefore this intake is staged as **FIFO waiting**. The central donor registry is not modified yet, and these planned identities are not canonical planning inputs until their intake reaches an active slot and is reconciled against the then-current published main.
