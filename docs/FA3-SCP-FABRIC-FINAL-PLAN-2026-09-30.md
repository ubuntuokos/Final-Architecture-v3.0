# FA3 Secure Communication & Proxy Fabric (SCP Fabric)

Status: **OWNER-APPROVED IMPLEMENTATION PLAN**  
Date: 2026-09-30  
Capability baseline: **175 (unchanged)**  
Runtime promotion: **NOT CLAIMED**

## 1. Goal

Materialize a provider-neutral, fail-closed FA3 communication-security fabric for:

- application-to-application communication;
- application-to-shared-service communication;
- multi-host internal traffic;
- external egress;
- external ingress;
- high-bandwidth authorized data paths;
- workload identity, policy, audit and proxy-bypass protection.

Network reachability never grants authority. A request is allowed only when all required identity, scope/layer, capability, policy, security-state and destination conditions are explicitly satisfied.

## 2. Authority boundaries

SCP Fabric is **not** an orchestrator, conductor, Model Router, HRB, Secret authority, Security Governance authority or promotion authority.

It consumes existing FA3 authority decisions and enforces communication. Provider/runtime implementations remain replaceable.

## 3. Planes

1. **Local Inter-App Plane** — UDS-first local communication with peer identity.
2. **Shared Service Plane** — governed access to FA3 shared services.
3. **Multi-Host Secure Mesh Plane** — host encryption plus workload mTLS.
4. **External Egress Plane** — provider/Internet destination control.
5. **External Ingress Plane** — one governed publication boundary for FA3 services.
6. **Authorized High-Bandwidth Data Plane** — separate control/data paths for media, render, model and asset streams.

## 4. Mandatory security semantics

- default deny;
- fail closed;
- least privilege;
- explicit source and destination identity;
- Layer/Scope Guard result required;
- capability and role/project context required where applicable;
- signed/versioned policy;
- no silent provider or security fallback;
- Secret Broker references instead of plaintext secrets;
- audit metadata without raw credential or payload leakage;
- proxy-bypass protection at host/network-namespace level;
- physical Current Host evidence required before runtime promotion.

## 5. Runtime/provider adapter targets

The architecture may bind replaceable admitted adapters for:

- step-ca (existing FA3 PKI);
- Envoy-class L4/L7 enforcement;
- SPIFFE/SPIRE-class workload identity;
- OPA/Rego-class contextual policy evaluation;
- nftables generic-Linux firewall baseline;
- WireGuard-class multi-host encryption;
- Falco/Tetragon runtime monitoring/enforcement where supported;
- Cilium for optional advanced cluster/eBPF networking;
- Suricata for optional gateway/server IDS/IPS;
- Trivy, Sigstore/Cosign, ClamAV, YARA and bubblewrap through existing artifact-security boundaries;
- OpenTelemetry-compatible telemetry transport.

No listed runtime gains FA3 architectural authority by adoption.

## 6. Shared settings requirement

The configuration UI is one shared implementation:

**FA3 Shared Proxy & Network Security Settings Panel**

The same QML/backend source is used by:

- the standalone **FA3 SCP Manager**;
- FA3 Control Center;
- any FA3 application embedding a context-limited view.

Embedded applications pass a context descriptor (application/project/user/role/module/capability). They do not own independent proxy-policy implementations.

Policy inheritance:

`GLOBAL -> HOST -> USER/ROLE -> PROJECT -> APPLICATION -> MODULE/PLUGIN -> CAPABILITY`

A lower layer cannot weaken a locked higher-layer rule.

## 7. Shared panel sections

- Overview
- Application Access
- Internal Network / Mesh
- External Access / Egress
- Ingress
- DNS
- Identity & Trust
- Runtime Protection
- Audit

The panel distinguishes editable, inherited, governance-locked, temporary-exception and unavailable states.

## 8. AI/provider enforcement

AI/provider egress additionally requires:

- AI enabled for the relevant app/module/capability;
- admitted provider;
- Model Router-approved route;
- external data transfer policy;
- Secret Broker credential reference;
- cost/rate/data-classification policy.

AI OFF must result in no provider network connection. Silent fallback is forbidden.

## 9. High-bandwidth data path

Large media/render/model transfers do not need to traverse a generic L7 proxy byte-for-byte. SCP authorizes a short-lived, resource-bound, audited data session first; the approved data path may then use UDS/shared memory/zero-copy/encrypted stream/RDMA only when separately admitted.

## 10. Generic Linux / hardware

- CPU-only remains valid.
- No GPU/NPU is required.
- No Kubernetes requirement.
- eBPF/Cilium/Tetragon/RDMA are optional and capability-detected.
- No unsafe CPU/GPU/network tuning.
- HRB remains resource authority.
- Software Coexistence remains mandatory.

## 11. Shared UI materialization in this change

This change materializes:

- canonical SCP profile, contract, enforcement policy and UI binding;
- static fail-closed SCP gate;
- shared C++ settings/status backend;
- shared QML settings surface;
- standalone Qt6/QML **FA3 SCP Manager**;
- draft-only local ChangeSet creation;
- runtime adapter discovery that reports only `UNAVAILABLE` or `DISCOVERED_NOT_ADMITTED`;
- tests and dedicated CI workflow.

It does **not** claim Envoy/SPIRE/WireGuard/etc. installation or production admission.

## 12. Control Center integration sequencing

Open GUI PRs #557 and #564 currently modify the same Control Center Main.qml/CMake/main.cpp and GUI surface registry paths. To avoid unsafe parallel overwrite, this materialization creates the shared component and an explicit Control Center binding contract now, but does not overwrite those concurrently modified GUI files.

After the active GUI work is reconciled, Control Center imports the same shared QML/backend component; no second implementation is permitted.

## 13. Retroactive migration

All existing and planned FA3 applications/modules/plugins/extensions/agents/MCP/providers must be classified for:

- LOCAL_IPC
- INTERNAL_HOST
- INTERNAL_MULTI_HOST
- EXTERNAL_EGRESS
- EXTERNAL_INGRESS
- HIGH_BANDWIDTH_DATA
- FORBIDDEN

Existing verified capability may not be lost during migration.

## 14. Current Host alignment

Structural SCP changes require Current Host alignment. Required physical evidence includes at minimum:

- local-agent identity;
- default-deny and allow paths;
- mTLS when applicable;
- Layer/Scope deny;
- direct-egress block;
- authorized-egress path;
- secret non-disclosure;
- firewall/network-namespace enforcement;
- signed-policy tamper denial;
- DNS/ingress controls when applicable;
- control-plane-loss fail-closed behavior;
- high-bandwidth session authorization;
- Software Coexistence;
- Hardware Safety.

No simulated or historical-only receipt can promote a new runtime state.

## 15. Donor / Reuse Discovery binding

Implementation is bound to published main:

- main: `6d9512df4bd449b0e3d7098d6d32a7393e7bb2fc`
- donor registry blob: `7e900cac93936d2f319e132def4c172b2a415d4d`
- donor registry SHA-256: `740593d1df5c64bf0ff6e87f7baddbd0d01789e479e840af3f22f1e5d3abf1dd`
- donor count: 1233
- capability baseline: 175

Pending donor intake is excluded from this implementation. No donor is adopted by this plan; existing FA3 security authorities/components are reused under their current contracts.

## 16. Acceptance

Static materialization may PASS only when:

- canonical files parse and preserve capability 175;
- authority=false remains explicit;
- default decision is DENY;
- incomplete/unknown request is denied;
- external egress requires explicit permission;
- AI-disabled request is denied;
- runtime discovery cannot claim admission;
- shared panel emits draft-only changes;
- no raw secret storage is introduced.

Production/current-host promotion remains separate and pending.
