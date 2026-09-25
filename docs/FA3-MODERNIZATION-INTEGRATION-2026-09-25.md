# FA3 Modernization Integration — 2026-09-25

## Scope
This materialization converts the useful parts of the reviewed modernization proposal into existing FA3 authorities. It creates no Unified Execution Engine, distributed HRB, Semantic Router, financial HRB authority, or other parallel architectural authority.

Capability count remains **143**. New capabilities: **0**. New architectural authorities: **0**.

## Mandatory Hardware Audit
- vendor-neutral baseline;
- CPU-only host remains conformant;
- accelerators remain optional `0..N`;
- no NVIDIA/AMD/Intel SKU, ordinal, VRAM or runtime pin becomes a global baseline;
- accelerator use requires live compatibility discovery and an HRB lease;
- provider-specific hardware requirements may narrow only the selected provider scope.

## Mandatory software coexistence
The extension is additive and namespaced. It must not uninstall, replace, shadow or globally reconfigure upstream software. No default port is claimed. Provider runtimes must use `FA3-PROVIDER-RUNTIME-001` and the existing supply-chain admission path.

## Existing authority bindings
| Concern | Authority / existing boundary |
|---|---|
| Model/provider routing | `FA3-AUTH-MODEL-ROUTER-001` |
| Host resource admission / placement / leases | `FA3-AUTH-HOST-RESOURCE-BROKER-001` |
| Knowledge | `FA3-KNOWLEDGE-001` |
| Security / rights policy | `FA3-AUTH-SECURITY-GOV-001` |
| Actions | `FA3-UNIFIED-ACTION-FABRIC-001` |
| Evidence | `FA3-AUTH-OBS-EVIDENCE-001` |
| Provider runtime | `FA3-PROVIDER-RUNTIME-001` |\n| Cross-host coordination | `FA3-AGENT-FEDERATION-001` with remote HRB admission |
| Secrets / private keys | existing Secret Broker / PKI boundary |

## Materialized lanes
- **Inference:** vLLM is only a future optional serving-runtime candidate. StableHLO/OpenXLA and TVM are portable-IR/compiler candidates. None may choose the canonical model route or host resources; silent fallback is forbidden.
- **Runtime enforcement:** Tetragon remains reference-only below Security Governance. Promotion is `OBSERVE -> SHADOW_ENFORCE -> ENFORCE`, and a block claim requires operation-prevention evidence.
- **Usage Rights Asset:** existing voice-consent semantics are generalized across voice/face/likeness/avatar/motion/image/video/dataset/persona/training material. Signature, issuer trust, validity, revocation freshness, purpose and source hashes are fail-closed. Private keys stay in Secret Broker/PKI.
- **Knowledge:** LanceDB is only a future derived/rebuildable accelerator. It cannot become Knowledge authority, self-select embeddings, bypass retrieval, or replace native source/project files. PR #390 remains the owner of active Embedding Fabric work.
- **FinOps:** a derived projection over HRB/runtime/energy/provider billing receipts. HRB never becomes financial authority; tariffs, FX and amortization are versioned runtime inputs.
- **Quality:** existing Anti-Slop and hu-HU AQC are reused. AI evaluation is advisory and Model-Router-mediated only.
- **Cross-host execution:** CAP-070 Agent Federation carries authenticated, signed and bounded coordination only. It is not a resource authority; the remote host must independently pass remote HRB and provider-runtime admission. Local multi-node protocol evidence is not cross-host production evidence.
- **Structured knowledge metadata:** metadata is a derived Knowledge projection. Native files/project formats remain authoritative source assets; domain extensions cannot replace the core provenance/approval/evidence fields.
- **Degraded execution:** any fallback/reroute is explicit, policy-authorized, receives fresh resource admission, records the original route failure/unavailability, and emits reroute plus execution receipts. Silent fallback remains forbidden.

## Current-host truth boundary
This change materializes contracts, immutable upstream references and an executable static gate. It does **not** install candidates and does **not** claim current-host or production admission.

Each runtime candidate still requires Reuse Discovery, immutable identity, license/SBOM/vulnerability/supply-chain admission, Provider Runtime environment, Hardware Audit, HRB admission when local resources are used, Model Router binding when applicable, positive/negative executable conformance, real current-host evidence and normal Evidence Registry promotion.

## Reconciled open work
- PR #390: do not duplicate Embedding Fabric authority/contracts.
- PR #241: preserve `FA3-KNOWLEDGE-001` and central Model Router boundaries.
- PR #177: reuse valid consent/revocation semantics only; stale branch is not current implementation.
- PR #176: reuse measured-compute ideas only as derived telemetry; no HRB financial authority.

## Explicitly rejected
New UEE/distributed-HRB/Semantic-Router/financial-HRB authorities; global vendor/runtime pinning; silent fallback; fixed FA3 default-port ownership; plaintext secrets/private keys in repository/environment/command line; upstream uninstall/replacement/host hijack; document-derived or CI-fabricated current-host PASS.
