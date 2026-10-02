# OpenClaw API List → FA3 External Discovery reconciliation

`cporter202/openclaw-api-list` is materialized as a pinned, untrusted discovery
source inside the existing shared `FA3-EXTERNAL-API-DISCOVERY-001` capability.
It is not a donor registration, provider, MCP admission, skill admission, runtime
dependency or architectural authority.

Pinned snapshot: `3afa19dd12f3cdc6bc2e297e9b6945059ada0cae`.

No repository license was detected at assessment time, so FA3 keeps this source
discovery-metadata-only until license and service terms are separately admitted.

## Reconciliation

- API Mega List remains the high-breadth discovery baseline.
- OpenClaw API List adds an agent-oriented curated overlay for APIs, MCP, skills,
  webhooks and integrations.
- Apify is identity/provenance context. Its organization donor record and ecosystem
  assessment do not auto-admit child repositories, Actors, MCP wrappers or providers.

OpenClaw links commonly carry `fpr` affiliate parameters. The shared normalizer
removes affiliate/tracking keys before candidate identity is computed. Upstream
language such as “MCP = plug in directly” is catalogue advice, not FA3 admission.

The existing offline pipeline now accepts immutable snapshots for both catalogues,
preserves source identity in receipts, and rejects source-id/repository mismatch
fail-closed. OpenClaw accepts recursive `README.md` surfaces plus the root
`OPENCLAW_RECOMMENDED.md` curated surface.

Capability baseline remains 175; provider count remains dynamic; donor registry is
unchanged; Current Host obligation delta is zero.
