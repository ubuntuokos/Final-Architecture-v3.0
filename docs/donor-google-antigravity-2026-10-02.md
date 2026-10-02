# FA3 Google Antigravity donor intake — 2026-10-02

**Authority:** owner-explicit `donornak` registration.
**Scope:** reference metadata only; no code, dependency, provider, model, service or runtime admission.

This intake registers five exact owner-marked sources as `ACCEPTED_REFERENCE`:

- Google Antigravity Python SDK — https://github.com/google-antigravity/antigravity-sdk-python
- GitHub `antigravity-tools` topic — https://github.com/topics/antigravity-tools
- GitHub `antigravity` topic — https://github.com/topics/antigravity
- GitHub `google-antigravity` topic — https://github.com/topics/google-antigravity
- Google Antigravity GitHub organization — https://github.com/google-antigravity

## Current upstream observations

The Python SDK declares Apache-2.0 and documents a stateful agent architecture with `Agent` / `Conversation`, streaming responses, tool execution, policy hooks, triggers, MCP integration, multimodal input and local-model paths. Upstream also states that normal SDK installation relies on a platform-specific wheel containing a compiled runtime binary; cloning the source repository alone is not sufficient to run it.

The organization currently exposes `antigravity-sdk-python` and `antigravity-cli`. Only the Python SDK is separately registered here because the owner explicitly marked its exact repository URL. The CLI remains discoverable through the organization/topic indexes but is not recursively admitted.

## Intended FA3 planning value

The SDK is a reference source for patterns around:

- stateful agent/session lifecycle and streaming;
- tool dispatch and policy-hook/approval boundaries;
- MCP client/server wiring patterns;
- triggers and background task scheduling;
- multimodal agent input;
- local-model / hosted-model adapter separation.

These patterns are potentially relevant to FA3 Agent Fabric, Shared Orchestration, Central MCP Gateway, Model Router, Local / Workstation AI Server Fabric and the Layer Guard / testőr model.

## Admission boundary

This intake does **not**:

- install the `google-antigravity` PyPI package or its compiled binary;
- admit Google Antigravity, Gemini, Vertex AI, LiteRT-LM, local OpenAI-compatible endpoints or MCP servers;
- import upstream source code;
- create dependencies, providers, models, services, ports or runtime processes;
- create donor usage edges;
- change the fixed capability baseline of 175;
- add architectural authority;
- claim Current Host PASS.

Any material reuse remains separately gated by exact License & Rights/provenance, security, Software Coexistence, Hardware Safety, Model Router/HRB/MCP authority reconciliation and canonical usage-edge traceability.

Parent published main: `8e1f30528e3af7c001fa7b0be1acf1aa4731f8b4`
Parent donor count: **1349**
Proposed donor count: **1354**
Capability baseline: **175**
Capability delta: **0**
Authority delta: **0**
