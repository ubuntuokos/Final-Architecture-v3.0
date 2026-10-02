# Apify ecosystem donor/reference assessment — 2026-10-02

This assessment closes the **analysis prerequisite** needed before FA3 can resume the `cporter202/openclaw-api-list` materialization work. It does **not** register Apify child repositories as donors, import code, enable Apify Cloud or Actors, admit a provider/MCP/skill, or create application-donor usage edges.

## Parent boundary

The only canonical donor registration in this scope is `FA3-DONOR-APIFY-ORG-001`, the owner-approved `https://github.com/apify` organization discovery index merged by PR #603.

Published-main anchor: `081b3ab23477d30365de04265620ec1704a0cddc`
Donor Registry blob: `c29638de9ac73f133a817cc239eba0d3837daac6`
Registry count: **1317**
Capability baseline: **175**, delta **0**
Provider count: **dynamic / unchanged**

## Child-source conclusions

| Source | Exact snapshot | Analysis disposition |
| --- | --- | --- |
| `apify/crawlee` | `438e3419626bd070f8984566bfb86ab9355f55d6` | strong donor-pattern candidate; analysis only |
| `apify/crawlee-python` | `ccdb72cdffd2dee93828c7cf420b7634b965f354` | primary Python donor-pattern candidate; analysis only |
| `apify/crawlee-storage` | `5bea28ede93f81ee27cc6ee4298dd2a608aa4472` | shared durable crawl-state pattern candidate; analysis only |
| `apify/apify-mcp-server` | `1b8d4e0236e3b4e17a51c42ebdfcb60d2d4956de` | optional provider/MCP reference; separate provider admission required |
| `apify/agent-skills` | `f5e84aa961e0ff2e890efebff64b0c5d04de1f1a` | reference only pending license/provenance resolution |
| `apify/apify-sdk-python` | `d1de6546b39cd213b816990373b6472c379d281b` | optional Apify provider-adapter reference |
| `apify/browser-pool` | `80ab2c57934648aaf08ee9d0d3fed8c69b413ac4` | deprecated/superseded historical reference; use Crawlee lineage instead |
| `apify/fingerprint-suite` | `67866a6196658076a7b61ecbe2c590a2ff3f4057` | security-restricted reference only |

### Strong reusable patterns

Crawlee/Crawlee Python are useful for HTTP/browser backend parity, request queues, retry and session lifecycle, and controlled concurrency. Crawlee Storage is especially useful for FA3-native durable crawl-state design: lock expiry, crash recovery, single/shared queue ownership, atomic writes and deterministic clock testing.

These are **pattern candidates**, not dependencies. Multi-application functionality remains shared-first and must reuse FA3 Browser Action Runtime, UAF, HRB, security, evidence and registry authorities rather than creating parallel authorities.

### MCP / cloud boundary

`apify/apify-mcp-server` and `apify/apify-sdk-python` are useful to understand Actor lifecycle and Actor-to-MCP exposure. Any actual use would require separate provider admission, credentials, network-egress, privacy, billing/entitlement and telemetry review. MCP execution must remain behind `FA3-AUTH-MCP-GATEWAY-001`.

### Agent Skills provenance boundary

At snapshot `f5e84aa...`, README/plugin metadata claims Apache-2.0, but a root license file was not observed and GitHub did not detect a repository license. Therefore no skill content or code is admitted or copied from this source by this assessment. It remains an untrusted/reference candidate until rights are resolved under the normal FA3 Skill Fabric admission path.

### Deprecated and security-sensitive sources

`apify/browser-pool` is upstream-deprecated and migrated into Crawlee; it must not become a separate modern FA3 dependency.

`apify/fingerprint-suite` stays security-restricted reference only. It does not create a default stealth, evasion or identity-misrepresentation capability.

## Identity model for the OpenClaw follow-up

The next reconciliation must keep these identities separate:

`Apify GitHub org index != child repository != Apify Actor != upstream target/service != MCP wrapper != admitted FA3 provider != OpenClaw/API catalogue link`.

An affiliate/catalog URL is only a discovery lead. Tracking parameters are not part of canonical provider identity. An Actor listing is not provider admission.

## OpenClaw prerequisite

Once this assessment is merged to published main, the **Apify analysis prerequisite** for the OpenClaw work is satisfied. That means FA3 may resume with a fresh three-source reconciliation:

`API-mega-list ↔ openclaw-api-list ↔ Apify ecosystem`.

This does **not** mean Apify runtime/provider admission is complete or required. Any later material adoption of a child repository still needs explicit source registration, license/provenance/security review, Software Coexistence & Host Non-Interference, Hardware Safety where applicable, shared-placement review, and a canonical usage edge.
