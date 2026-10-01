# FA3 Provider, Model & Gateway Assurance Fabric

This profile composes existing FA3 authorities; it does not create a new gateway, router, secret store, resource broker, workflow engine or evidence authority.

Flow:

`Provider Intelligence → Evidence Dossier → protocol/model-identity assurance → provider admission → deterministic eligibility → bounded advisory ranking → Model Router stage route → explicit bounded fallback/exhaustion → Gateway enforcement → execution → evidence`.

Key invariants:
- Model Router remains sole model/provider routing authority.
- Central MCP Gateway remains the MCP/tool trust boundary.
- HRB remains sole host-resource authority.
- Secret Broker remains credential custody/projection authority.
- Decision Fabric cannot expand the eligible candidate set.
- fallback is explicit, bounded and exhausted to failure; silent provider/model substitution is forbidden.
- MCP discovery may hide capabilities not visible to the principal/application/task context.
- REST/OpenAPI→MCP is a projection adapter, not a new authority.
- Wasm is only an optional plugin execution backend under the existing Plugin & Extension Manager.
- chat-analyzed sources without explicit owner `donornak` registration are not adopted.

Capability baseline: **175**. Capability delta: **0**. Authority delta: **0**. Runtime promotion: **none**.

## Evaluated donor patterns — 2026-10-01

Two owner-approved reference donors now have completed, pinned assessments and explicit Capability Map usage edges.

- **ferdiunal/laravel-ai-router**: adopt public-endpoint/provider-definition validation, provider/model visibility cache, non-secret health/rate-window/cooldown telemetry, usage/latency/token/error observations, and bounded transport/stream parsing patterns. Do **not** adopt its random/auto provider selection, internal failover authority, Laravel-local credential database/encryption as FA3 secret authority, Laravel/PHP runtime dependency, or provider/model auto-admission.
- **ai-resource-radar/ai-resource-radar**: adopt deterministic allow-listed source collection, ETag/Last-Modified caching, source failure isolation, official-vs-community separation, freshness/evidence timestamps, last-trusted-value handling on parser drift, two-success removal confirmation, country availability, normalized quota/price metadata, and change detection. Its A–D ranking is informational only and cannot become FA3 admission, Model Router ranking authority, or runtime activation.

Both are pattern-only use: no upstream runtime dependency, no code import, no provider/model admission, no new capability, no new architectural authority, and no physical Current Host promotion. Secret Broker, Model Router, HRB, Security Governance and Evidence remain authoritative.

