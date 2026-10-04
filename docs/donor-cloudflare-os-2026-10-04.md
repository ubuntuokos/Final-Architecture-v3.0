# Cloudflare OS donor/reference intake — 2026-10-04

## Scope

Registers the owner's explicit `donornak` request for:

- https://github.com/cloudflare/cloudflare-os

as one metadata-only canonical donor/reference identity.

## Source classification

- canonical source key: `github:cloudflare/cloudflare-os`
- donor id: `FA3-DONOR-CLOUDFLARE-OS-001`
- source kind: `GITHUB`
- status: `ACCEPTED_REFERENCE`
- upstream repository license observed: `Apache-2.0`
- observed upstream head during intake: `5cae880e5e54563895a067e7f4dae67514e581be`
- reference mode: selective architecture/security/workflow study only

Cloudflare OS describes itself as an AI productivity environment rather than a traditional host operating system. The repository is early access and is under active development.

## High-value FA3 reference areas

The strongest reusable ideas are:

1. **Gatekeeper / capability security** — agents and applications receive narrowly scoped access to explicitly introduced resources rather than ambient connector authority.
2. **MCP mediation** — tool/resource access can be narrowed below whole-server scope.
3. **Sandboxed Gadgets** — per-user or per-workspace small applications run with constrained authority.
4. **Blueprints** — shareable application templates/code packages without transferring live credentials or ambient account access.
5. **Agent-friendly application APIs** — application surfaces are designed so agents can call typed RPC methods directly.
6. **Human approval workflows** — delayed/batched approval is a useful UX pattern, but any simulated result must stay non-authoritative in FA3.
7. **Real-time collaboration** — shared application state and multi-user interaction patterns.
8. **Model/provider administration** — operator-facing model configuration ideas relevant to FA3 Model Router administration.
9. **Observability/action audit** — typed event and action logging patterns for controlled agent/application execution.

## FA3 mapping

Primary study targets:

- FA3 Layer Guard / Testőr;
- Central MCP Gateway and receiver adapters;
- Shared Plugin & Extension Fabric;
- application/plugin Blueprint and dynamic utility surfaces;
- two-way Agent/Application API;
- Control Center approval and audit UI;
- Observability / Evidence integration;
- Model Router administrative UI.

This intake does **not** establish any of those mappings as material donor usage. A later adoption requires an explicit typed usage edge.

## Critical boundary: speculative approval

Cloudflare OS can let an agent continue against a simulated result while a side-effecting action is still awaiting human approval. FA3 may study this only as a **shadow/speculative planning pattern**.

A speculative result must never become:

- Current Host physical PASS;
- release-gate evidence;
- proof that an external side effect happened;
- committed workflow evidence;
- security or rights approval.

Actual execution and evidence remain fail-closed.

## Runtime and dependency boundary

This registration does not admit:

- Cloudflare Workers;
- Durable Objects;
- Dynamic Workers or Facets;
- `workerd`;
- Cap'n Web;
- Gatekeeper packages;
- repository dependencies;
- any model/provider;
- any external service.

Apache-2.0 is observed at repository root, but direct source reuse still requires exact provenance, transitive dependency, License & Rights, security, Software Coexistence and runtime/Current Host review.

## Invariants

- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- provider-count policy: dynamic, unchanged
- usage edges created: **0**
- code/runtime/provider/model admission: **none**
- Current Host PASS claimed: **false**

## Rolling intake state

At creation time the rolling five-slot donor-intake window is full with earlier open donor-intake PRs (#651, #657, #663, #664 and #671).

This request is therefore created as a **FIFO waiting intake**. It may be prepared and reviewed, but it must not finalize ahead of the active-window ordering.
