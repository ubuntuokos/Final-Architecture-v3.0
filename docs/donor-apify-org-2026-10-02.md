# Apify organization donor intake — 2026-10-02

**Authority:** owner-explicit `donornak` registration.

This intake adds exactly one source to `FA3-DONOR-REFERENCE-REGISTRY-001`:

- https://github.com/apify

## Classification

`github:apify` is a `GITHUB_ORGANIZATION` **discovery index** and research reference. Organization-level registration does not recursively register repositories and does not create runtime/provider admission.

The organization record therefore does **not**:

- import or copy source code;
- install a package or dependency;
- enable Apify Cloud, Actors, hosted storage or paid services;
- admit an MCP/provider/model/runtime;
- create an application-donor usage edge;
- change the fixed capability baseline of 175;
- create architectural authority.

## Child repository boundary

The approved ecosystem decomposition identifies repositories such as `apify/crawlee`, `apify/crawlee-python`, `apify/crawlee-storage`, `apify/apify-mcp-server`, `apify/agent-skills`, `apify/apify-sdk-python`, historical `apify/browser-pool`, and the separately security-sensitive `apify/fingerprint-suite` as potential analysis targets.

They are **not registered or adopted by this intake**. Each selected child repository requires an independent source-specific donor assessment, exact revision/provenance, license/rights, security, Software Coexistence & Host Non-Interference, Hardware Safety Envelope, Reuse Assessment, shared-capability placement review and—only for actual material adoption—a canonical usage edge.

## FA3 placement boundary

The organization is expected to inform the already existing FA3-native Web Acquisition / Browser Action / Knowledge-RAG ingestion / MCP / Skill Fabric work. Multi-application deltas remain shared-first. No duplicate capability is created by this registration.

The strongest planned study area is durable crawl-state hardening: queue ownership, lock/lease extension, reclaim/requeue, retry/recovery, HTTP/browser backend parity, session lifecycle, origin politeness and crash-consistent storage. These remain design/adoption work after child-repository review.

## Invariants

- published parent main: `bf50877f64c41cfea49c69dc274812370dfcb77b`
- parent donor registry: **1316** entries / blob `12cbc13cd95c98533603c0746df58c4cfc0b1cfc`
- proposed donor registry: **1317** entries
- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- provider count: dynamic / unchanged
- Current Host runtime promotion: **not claimed**

## CI maintenance note

Donor-registry regression tests owned by earlier append-only intake batches must not freeze the global registry at their historical count. They may assert their own delta boundary and that the live registry is at least that large; later owner-approved donor additions remain valid append-only growth.
