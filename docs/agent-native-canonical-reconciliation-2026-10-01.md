# Agent Native canonical reconciliation — 2026-10-01

## Decision

The existing FA3 Agent Native architecture remains the canonical authority model. The new research does **not** justify a second orchestrator, MCP gateway, browser authority, evidence authority, model router or capability family. Capability baseline stays **175** and authority delta stays **0**.

The only new shared materialized component is `FA3-SHARED-AGENT-WEB-INTERACTION-001`, a non-authoritative contract that binds three explicit rails:

1. **NATIVE_AGENT_CONTRACT** — typed manifest/state/action, preview, exact approval binding, idempotent commit and native receipt.
2. **SEMANTIC_HTTP_BRIDGE** — inert HTTP/HTML interpretation, deterministic request preview, exact approval, one dispatch and lower-assurance attempt receipt.
3. **BROWSER_VISUAL** — existing `FA3-BROWSER-ACTION-RUNTIME-001` for JavaScript/rendered/pixel-dependent work.

There is no silent fallback between rails and no authority, credential or assurance inheritance from a stronger rail to a weaker one.

## Existing shared hardening

- Tool & Action Mediation: state/revision binding → preview → approval binding → commit → effect receipt → outcome verification; ambiguous effects reconcile before redispatch.
- Conversation & Session: minimum-disclosure projections and non-delegable human ratification boundary.
- Multimodal Source: direct structured/source media preferred when pixels are not themselves the evidence.
- Central MCP Gateway: public-target/DNS/TLS/redirect/protocol/schema/OAuth/PKCE compatibility evidence before endpoint admission; diagnostics remain non-authoritative and do not execute tools by default.
- Web-AI / Browser Action: active metadata reconciled to 175 and the Browser gate enforces the Agent-Web child contract.

The machine-readable reconciliation matrix is `research/agent-native-canonical-reconciliation-2026-10-01.json`.

## Donor boundary

The three owner-submitted topic URLs are canonical discovery references on this branch. The individual repositories inspected during analysis remain **analysis-only sources**; no donor usage edge is created because no external donor code/runtime/pattern is adopted as a canonical implementation dependency.
