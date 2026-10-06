# CFA3 Antigravity-derived provider execution refresh plan — 2026-10-06

## Scope

This refresh preserves the original architecture: there is no standalone Antigravity application, no parallel model router and no parallel LLM gateway. Antigravity-derived behavior remains a shared CFA3 capability projection under existing authorities.

The refresh is based on the published CFA3 main at `c2e2ab2aa1c34ef555e2324e9b67af9d8723f76a` and the published donor registry blob `2bb6a74dd415b6374e4a6d5adce1bc9265229b63` with 1792 entries.

## Source separation

### lbjlaq/Antigravity-Manager

Observed on 2026-10-06:
- main: `b601f5e7375343343922ccab5e50653bc3450c3b`
- latest release: `v4.9.6`
- license: CC BY-NC-SA 4.0
- CFA3 status: external reference only, clean-room requirement derivation
- donor registry status: absent

The historical immutable CFA3 reference pinned to v4.8.0 remains valid historical provenance. It is not rewritten and does not become a donor registration.

### Google Antigravity Python SDK

Observed on 2026-10-06:
- main: `12f9a4c3becf487302dc799b0f59054f01f3ddb9`
- license: Apache-2.0
- donor id: `FA3-DONOR-GOOGLE-ANTIGRAVITY-SDK-PYTHON-001`
- donor state: `ACCEPTED_REFERENCE`

The donor record allows planning/reference use only. This refresh creates no usage edge, installs no wheel or compiled runtime, and admits no Google/Gemini/Vertex/LiteRT provider.

## What stays

The following original decisions remain correct and mandatory:

1. `FA3-AUTH-MODEL-ROUTER-001` is the only model/provider routing authority.
2. `FA3-LLM-GATEWAY-001` remains the single LLM data plane.
3. Credential values remain under the CFA3 secrets authority; provider execution consumes SecretReference/leases only.
4. Same-provider credential failover may be automated only with explicit receipts.
5. Cross-provider transition belongs to the Model Router only.
6. Silent local-to-cloud fallback remains forbidden.
7. Protocol degradation must be explicit; security-relevant schema loss fails closed.
8. GUI surfaces remain projections and cannot execute provider requests or reveal raw credentials.
9. CPU-only operation remains valid.
10. Static/reference PASS never implies Current Host or global runtime promotion.

## Obsolete material removed by this refresh

Active Antigravity-derived profile, contract, enforcement, gate and closure records no longer pin the obsolete 143-capability baseline. They bind to the active 175-capability release model with zero capability and authority delta.

The old decision wording that implied the generic core remained pending on one real provider E2E is removed. The generic core is closed independently; physical evidence is provider-specific and required only for that provider/runtime promotion.

Historical 2026-09-24 evidence remains immutable at 143 because it records the state that actually existed when the evidence was produced.

## Updated capability placement

### 1. Provider Execution — retain and strengthen

Owner: `FA3-AUTH-MODEL-ROUTER-001` child projection `FA3-MODEL-ROUTER-PROVIDER-EXECUTION-001`.

Future clean-room additions should include:
- bounded single-request credential-pool traversal;
- tiered per-credential backoff/cooldown;
- explicit sticky-session unbind taxonomy for authentication, missing-model, rate-limit and upstream-overload failures;
- success-driven transient failure counter reset;
- separate provider-health, credential-health and model-health state;
- explicit quota-window metadata without making quota state routing authority;
- deterministic tie-breaking for equivalent candidates.

These mechanisms may select only from candidates already admitted by the Model Router.

### 2. Reasoning / thinking budget — move decision upward, not into protocol adapters

Owner: Agent Workload task intent + Model Router.

The workload should express reasoning class/budget intent. The Model Router resolves it against admitted model capability. Protocol Compat only translates the resulting canonical budget into provider-specific syntax. Provider adapters may not invent or override reasoning policy.

### 3. Context budget and compaction — shared Agent Workload + Knowledge concern

Do not place context compaction inside Provider Execution or the LLM Gateway.

Use a non-authoritative shared projection across `FA3-AGENT-WORKLOAD-RUNTIME-001` and Knowledge/Context fabrics for:
- context token accounting;
- protected/non-compactable segments;
- sliding-window compaction;
- summary/checkpoint lineage;
- anti-thrashing cooldown/headroom;
- tool-schema/token overhead accounting;
- explicit compaction receipts and retrieval backreferences.

### 4. Protocol Compatibility — strengthen existing projection

Owner: `FA3-LLM-PROTOCOL-COMPAT-001`.

Add/strengthen:
- OpenAI / Anthropic / Gemini reasoning metadata mapping;
- tool-call id canonicalization;
- strict JSON Schema capability descriptors;
- tool-schema normalization with fail-closed security boundaries;
- streaming/SSE heartbeat semantics where required;
- upstream HTTP/error fidelity: provider 429/503/504 or tool/runtime errors must not become fabricated success;
- multimodal payload size/reference rules;
- usage metadata normalization.

### 5. Agent/runtime patterns from the registered Google Antigravity SDK donor

Potential future donor usage, only after explicit usage-edge adoption:
- stateful session lifecycle -> Agent Workload Runtime;
- lifecycle/policy hooks -> UAF + Security/Layer Guard;
- background triggers -> existing durable orchestration, never a new scheduler authority;
- MCP wiring -> Central MCP Gateway;
- scoped tool dispatch -> Skill Fabric/UAF;
- local-vs-hosted model adapter separation -> Model Router + Local AI Server Fabric;
- session budgets/stop reasons -> Agent Workload limits and execution ledger;
- compaction hooks -> the shared Context Budget & Compaction projection.

Do not adopt the SDK compiled runtime binary automatically.

## Explicitly rejected or obsolete Antigravity-local mechanisms

The following must not become CFA3 architecture:
- standalone Antigravity proxy/router;
- standalone account database as a credential authority;
- direct system-keyring crawling for provider credentials;
- IDE-specific credential switching as a global CFA3 mechanism;
- provider/model hardcoded redirects inside protocol adapters;
- upstream self-updater as CFA3 update authority;
- direct local MCP discovery bypassing the Central MCP Gateway;
- client-process detection as provider/model routing authority;
- direct provider execution from application GUIs;
- automatic installation or activation of Antigravity runtimes.

Provider runtime isolation is already owned by `FA3-PROVIDER-RUNTIME-001`; duplicate venv/container/runtime management inside Provider Execution is forbidden.

## Consumer placement

All CFA3 applications that use LLM/model providers consume these capabilities indirectly through the shared layers. High-value consumers are Developer Agent, Agent Workbench, Knowledge/Research, Story/Screenplay, Webdesign, Presentation/DTP, Marketing and Business/Collaboration. Media/DCC applications use this only for their AI-assistant/model-provider paths; render engines, codecs and graphics engines remain under their own engine/provider fabrics.

## Implementation sequence

1. **P0 — baseline cleanup:** completed in this refresh branch; active 143 bindings removed, historical evidence preserved.
2. **P1 — provider-execution resilience:** bounded pool traversal, tiered backoff, health separation, deterministic tie-breaks, new regression cases.
3. **P2 — reasoning arbitration:** canonical workload reasoning intent and provider-specific projection contract.
4. **P3 — context lifecycle:** shared non-authoritative context budget/compaction projection under Agent Workload + Knowledge.
5. **P4 — protocol hardening:** reasoning metadata, tool-id/schema normalization, streaming/error fidelity and multimodal bounds.
6. **P5 — donor usage decision:** decide which Google Antigravity SDK patterns become canonical usage edges; no donor adoption is implied by this plan.
7. **P6 — GUI observability:** extend the existing read-only Provider Execution surface with health/backoff/rebind/reasoning/context receipts, without secrets or direct execution.
8. **P7 — physical admission:** provider-specific Current Host evidence only after the normal PR/current-host ordering allows it; no generic core re-certification.

## Completion rules

- capability baseline remains 175 with delta 0;
- architectural authority delta remains 0;
- no silent fallback;
- CPU-only path remains valid;
- no upstream lbjlaq source/assets/runtime enter commercial CFA3 distribution;
- donor reference does not equal runtime/provider admission;
- every material donor adoption requires canonical usage-edge traceability;
- historical evidence is never rewritten.
